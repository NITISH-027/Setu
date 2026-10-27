import secrets
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import SessionDB, UserDB

ph = PasswordHasher()
security_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return ph.verify(hashed, password)
    except VerifyMismatchError:
        return False


def hash_pin(pin: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}{pin}".encode("utf-8")).hexdigest()


def create_session(
    db: Session,
    user_id: Optional[str] = None,
    role: str = "student",
    student_id: Optional[str] = None,
    device_id: Optional[str] = None,
    duration_hours: int = 24
) -> SessionDB:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
    session = SessionDB(
        token=token,
        user_id=user_id,
        role=role,
        student_id=student_id,
        device_id=device_id,
        expires_at=expires_at,
        created_at=datetime.utcnow()
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_current_session(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: Session = Depends(get_db)
) -> SessionDB:
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials"
        )
    token = auth.credentials
    session = db.query(SessionDB).filter(SessionDB.token == token).first()
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token"
        )
    return session


def require_role(allowed_roles: List[str]):
    def role_checker(session: SessionDB = Depends(get_current_session)) -> SessionDB:
        if session.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: required role in {allowed_roles}, got '{session.role}'"
            )
        return session
    return role_checker


def require_teacher(session: SessionDB = Depends(require_role(["teacher", "admin"]))) -> SessionDB:
    return session


def require_admin(session: SessionDB = Depends(require_role(["admin"]))) -> SessionDB:
    return session


def require_reviewer(session: SessionDB = Depends(require_role(["reviewer", "admin"]))) -> SessionDB:
    return session


def verify_teacher_class_access(session: SessionDB, class_id: str, db: Session):
    """
    Ensures teacher can only read or change their assigned class(es).
    Admin role can access any class.
    """
    if session.role == "admin":
        return True
    if session.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can access class dashboards.")

    user = db.query(UserDB).filter(UserDB.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=403, detail="Teacher user record not found.")

    allowed_classes = user.get_classes()
    if class_id not in allowed_classes:
        raise HTTPException(
            status_code=403,
            detail=f"Access Denied: Teacher '{user.username}' is not assigned to class '{class_id}'."
        )
    return True


def verify_student_access(session: SessionDB, target_student_id: str):
    """
    Ensures student token can only read and write to their own student record.
    Teacher or admin can also access.
    """
    if session.role in ["admin", "teacher"]:
        return True
    if session.role == "student":
        if session.student_id != target_student_id:
            raise HTTPException(
                status_code=403,
                detail=f"Access Denied: Student session '{session.student_id}' cannot access student '{target_student_id}'."
            )
        return True
    raise HTTPException(status_code=403, detail="Unauthorized role.")
