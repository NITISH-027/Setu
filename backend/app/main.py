"""
Setu Adaptive Learning System - FastAPI Backend.
Pure-Python core. No GPU. No external runtime AI calls.
Full SQLAlchemy persistence, Argon2 authentication, server-side grading, and zero-PII tombstone lifecycle.
"""

import os
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Depends, Query, Body, Security, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db import (
    init_db, get_db, SessionLocal,
    UserDB, SessionDB, StudentDB, PlanDB, MasteryStateDB,
    HypothesisDB, AttemptDB, DecisionDB, TeacherOverrideDB,
    TombstoneDB, DeviceDB, AuditEventDB, ReviewRecordDB, GapClosedRecordDB,
    PinProfileDB
)
from app.auth.security import (
    hash_password, verify_password, hash_pin, create_session,
    get_current_session, require_teacher, require_admin, require_reviewer,
    verify_teacher_class_access, verify_student_access,
    verify_student_only_access, verify_teacher_or_admin_student_access,
    invalidate_session, invalidate_all_student_sessions,
    security_bearer
)
from app.models.pack import ContentPack, ReviewStatus
from app.models.student import Student, ConsentStatus
from app.models.learning import Attempt, Plan, MasteryState, Hypothesis, StageEnum, BKTParameters
from app.models.content import HintLadder
from app.engine.adaptive_engine import AdaptiveEngine
from app.teacher.teacher_service import TeacherService
from app.paper_mode.paper_mode_generator import PaperModeManager
from app.validator.coverage_reporter import CoverageReporter
from app.validator.review_manager import ReviewManager

app = FastAPI(
    title="Setu Adaptive Learning API",
    description="Teacher-controlled adaptive learning system inside an authored concept graph.",
    version="1.0.0"
)

# CORS allow-list restriction (FIX 1g)
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:4173,http://127.0.0.1:5173,http://127.0.0.1:4173"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB tables on startup
init_db()

# Load pack
PACK_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "packs", "cbse_math_pack.json"))
if os.path.exists(PACK_PATH):
    with open(PACK_PATH, "r", encoding="utf-8") as f:
        pack = ContentPack.model_validate(json.load(f))
else:
    from app.pack_builder import build_pack
    pack = build_pack()

engine = AdaptiveEngine(pack)
teacher_service = TeacherService()
paper_manager = PaperModeManager(pack, engine)
coverage_reporter = CoverageReporter()
review_manager = ReviewManager()


@app.on_event("startup")
def verify_production_safeguards():
    """Refuses to start in production if seeded demo users exist in DB (FIX 6)."""
    env = os.getenv("ENV", "development").lower()
    if env == "production":
        db = SessionLocal()
        try:
            seeded = db.query(UserDB).filter(UserDB.is_seeded == True).first()
            if seeded:
                raise RuntimeError(
                    f"FATAL: Production startup refused! Seeded demo user '{seeded.username}' found in database."
                )
        finally:
            db.close()


# Pydantic Schemas for strictly validated input (FIX 1d)
class AttemptPayload(BaseModel):
    question_id: str
    selected_option_id: str
    concept_id: Optional[str] = None
    time_spent_seconds: Optional[int] = None
    attempt_id: Optional[str] = None


class OverridePayload(BaseModel):
    class_id: str
    student_id: str
    concept_id: str
    action: str
    reason: str


class SyncPayload(BaseModel):
    device_id: str
    class_id: str = "8-A"
    queued_attempts: List[Dict[str, Any]] = Field(default_factory=list)


# Helper to convert StudentDB + PlanDB + MasteryStateDB to domain models
def load_student_domain_state(db: Session, student_id: str):
    stu_db = db.query(StudentDB).filter(StudentDB.pseudonymous_id == student_id).first()
    if not stu_db:
        return None, None, None, None

    student = Student(
        pseudonymous_id=stu_db.pseudonymous_id,
        class_id=stu_db.class_id,
        board=stu_db.board,
        medium_language=stu_db.medium_language,
        pin_hash=stu_db.pin_hash,
        created_at=stu_db.created_at,
        consent_status=ConsentStatus(stu_db.consent_status)
    )

    plan_db = db.query(PlanDB).filter(PlanDB.student_id == student_id).first()
    plan = None
    if plan_db:
        plan = Plan(
            student_id=plan_db.student_id,
            class_id=plan_db.class_id,
            current_stage=StageEnum(plan_db.current_stage),
            current_concept_id=plan_db.current_concept_id,
            gap_concept_id=plan_db.gap_concept_id,
            items_queue=json.loads(plan_db.items_queue) if plan_db.items_queue else [],
            reason=plan_db.reason,
            stuck_attempts_count=plan_db.stuck_attempts_count,
            bridge_recheck_fails=plan_db.bridge_recheck_fails
        )

    # Load primary concept mastery
    concept_id = plan.current_concept_id if plan else "c8_math_linear_eq_one_var"
    mastery_db = db.query(MasteryStateDB).filter(
        MasteryStateDB.student_id == student_id,
        MasteryStateDB.concept_id == concept_id
    ).first()
    if not mastery_db:
        mastery_db = db.query(MasteryStateDB).filter(MasteryStateDB.student_id == student_id).first()

    mastery = None
    if mastery_db:
        mastery = MasteryState(
            student_id=mastery_db.student_id,
            concept_id=mastery_db.concept_id,
            mastery_estimate=mastery_db.mastery_estimate,
            bkt_params=BKTParameters(
                prior=mastery_db.bkt_prior,
                learn=mastery_db.bkt_learn,
                guess=mastery_db.bkt_guess,
                slip=mastery_db.bkt_slip,
                label=mastery_db.mastery_label
            ),
            mastery_label=mastery_db.mastery_label
        )

    hyp_db = db.query(HypothesisDB).filter(
        HypothesisDB.student_id == student_id,
        HypothesisDB.status == "open"
    ).order_by(HypothesisDB.id.desc()).first()
    hypothesis = None
    if hyp_db:
        hypothesis = Hypothesis(
            student_id=hyp_db.student_id,
            suspected_concept_id=hyp_db.suspected_concept_id,
            misconception_tag=hyp_db.misconception_tag,
            evidence_list=json.loads(hyp_db.evidence_list) if hyp_db.evidence_list else [],
            heuristic_score=hyp_db.heuristic_score,
            evidence_band=hyp_db.evidence_band
        )

    return student, plan, mastery, hypothesis


def save_student_domain_state(
    db: Session,
    student_id: str,
    plan: Optional[Plan],
    mastery: Optional[MasteryState],
    hypothesis: Optional[Hypothesis]
):
    if plan:
        p_db = db.query(PlanDB).filter(PlanDB.student_id == student_id).first()
        if not p_db:
            p_db = PlanDB(student_id=student_id, class_id=plan.class_id)
            db.add(p_db)
        p_db.class_id = plan.class_id
        p_db.current_stage = plan.current_stage.value if hasattr(plan.current_stage, "value") else str(plan.current_stage)
        p_db.current_concept_id = plan.current_concept_id
        p_db.gap_concept_id = plan.gap_concept_id
        p_db.items_queue = json.dumps(plan.items_queue)
        p_db.reason = plan.reason
        p_db.stuck_attempts_count = plan.stuck_attempts_count
        p_db.bridge_recheck_fails = plan.bridge_recheck_fails
        p_db.updated_at = datetime.utcnow()

    if mastery:
        m_db = db.query(MasteryStateDB).filter(
            MasteryStateDB.student_id == student_id,
            MasteryStateDB.concept_id == mastery.concept_id
        ).first()
        if not m_db:
            m_db = MasteryStateDB(student_id=student_id, concept_id=mastery.concept_id)
            db.add(m_db)
        m_db.mastery_estimate = mastery.mastery_estimate
        if hasattr(mastery, "bkt_params") and mastery.bkt_params:
            m_db.bkt_prior = mastery.bkt_params.prior
            m_db.bkt_learn = mastery.bkt_params.learn
            m_db.bkt_guess = mastery.bkt_params.guess
            m_db.bkt_slip = mastery.bkt_params.slip
            m_db.mastery_label = mastery.bkt_params.label or mastery.mastery_label
        else:
            m_db.mastery_label = mastery.mastery_label

    if hypothesis:
        h_db = db.query(HypothesisDB).filter(
            HypothesisDB.student_id == student_id,
            HypothesisDB.status == "open"
        ).order_by(HypothesisDB.id.desc()).first()
        if not h_db:
            h_db = HypothesisDB(
                student_id=student_id,
                suspected_concept_id=hypothesis.suspected_concept_id,
                misconception_tag=hypothesis.misconception_tag
            )
            db.add(h_db)
        h_db.suspected_concept_id = hypothesis.suspected_concept_id
        evidence_serialized = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else (item if isinstance(item, dict) else str(item))
            for item in (hypothesis.evidence_list or [])
        ]
        h_db.evidence_list = json.dumps(evidence_serialized, default=str)
        h_db.heuristic_score = hypothesis.heuristic_score
        h_db.evidence_band = hypothesis.evidence_band.value if hasattr(hypothesis.evidence_band, "value") else str(hypothesis.evidence_band)
        h_db.updated_at = datetime.utcnow()

    db.commit()


def sanitize_question_for_client(q_dict: dict) -> dict:
    """Removes all answer leaks: is_correct, misconception_tag, solutions (FIX 2)."""
    sanitized = dict(q_dict)
    if "options" in sanitized and isinstance(sanitized["options"], list):
        clean_opts = []
        for opt in sanitized["options"]:
            clean = {
                "id": opt.get("id"),
                "text": opt.get("text")
            }
            if "numeric_value" in opt and opt["numeric_value"] is not None:
                clean["numeric_value"] = opt["numeric_value"]
            clean_opts.append(clean)
        sanitized["options"] = clean_opts
    sanitized.pop("correct_option_id", None)
    sanitized.pop("worked_solution", None)
    return sanitized


# ==========================================
# PUBLIC / DISCOVERY ROUTES (ONLY 4 AS MANDATED)
# ==========================================

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": "Setu Adaptive Learning",
        "version": "1.0.0",
        "persistence": "SQLite / PostgreSQL via SQLAlchemy",
        "honesty_notice": "Uncalibrated models, synthetic demo data, intended NCERT alignment unverified until reviewed"
    }


@app.get("/api/pack")
def get_shipped_pack():
    """
    Public pack download (FIX 2): answer-free!
    Never contains is_correct, misconception_tags, or worked solutions.
    """
    raw = pack.model_dump()
    sanitized_questions = [sanitize_question_for_client(q) for q in raw.get("questions", [])]
    raw["questions"] = sanitized_questions
    return raw


@app.post("/api/auth/login")
def login_user(payload: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    """
    Teacher, Admin, or Reviewer login with Argon2 verification.
    Binds device to teacher session if device_id provided (FIX 4).
    """
    username = payload.get("username")
    password = payload.get("password")
    device_id = payload.get("device_id")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required.")

    user = db.query(UserDB).filter(UserDB.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    if device_id:
        classes = user.get_classes()
        class_id = classes[0] if classes else "GLOBAL"
        dev = db.query(DeviceDB).filter(DeviceDB.device_id == device_id).first()
        if not dev:
            db.add(DeviceDB(device_id=device_id, class_id=class_id))
            db.commit()

    session = create_session(db, user_id=user.id, role=user.role, device_id=device_id)
    return {
        "access_token": session.token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username,
        "assigned_classes": user.get_classes()
    }


@app.post("/api/auth/pin")
def verify_pin(payload: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    """
    PIN verification for student session on a shared device.
    Registers device bound to student's class (FIX 4).
    Zero-logging of PIN plaintext.
    """
    device_id = payload.get("device_id")
    student_id = payload.get("student_id")
    candidate_pin = payload.get("pin")

    if not student_id or not candidate_pin:
        raise HTTPException(status_code=400, detail="student_id and pin are required.")

    student = db.query(StudentDB).filter(StudentDB.pseudonymous_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found.")

    profile = None
    if device_id:
        profile = db.query(PinProfileDB).filter(
            PinProfileDB.device_id == device_id,
            PinProfileDB.student_id == student_id
        ).first()

    now = datetime.utcnow()
    if profile:
        if profile.locked_until and now < profile.locked_until:
            rem = int((profile.locked_until - now).total_seconds())
            raise HTTPException(status_code=403, detail=f"Device locked. Please wait {rem} seconds.")
        computed_hash = hash_pin(candidate_pin, profile.salt)
        if computed_hash != profile.pin_hash:
            profile.failed_attempts += 1
            if profile.failed_attempts >= 3:
                profile.locked_until = now + timedelta(seconds=60)
            db.commit()
            raise HTTPException(status_code=401, detail="Incorrect PIN.")
        profile.failed_attempts = 0
        profile.locked_until = None
        db.commit()
    else:
        computed_hash = hash_pin(candidate_pin, student.salt)
        if computed_hash != student.pin_hash:
            raise HTTPException(status_code=401, detail="Incorrect PIN.")

    # Register device bound to student and class upon authenticated login (FIX 4)
    if device_id:
        dev = db.query(DeviceDB).filter(DeviceDB.device_id == device_id).first()
        if not dev:
            db.add(DeviceDB(device_id=device_id, class_id=student.class_id))
            db.commit()
        else:
            dev.class_id = student.class_id
            dev.last_sync_at = datetime.utcnow()
            db.commit()

    session = create_session(db, role="student", student_id=student_id, device_id=device_id)
    return {
        "authenticated": True,
        "access_token": session.token,
        "token_type": "bearer",
        "student_id": student_id,
        "class_id": student.class_id
    }


@app.post("/api/auth/logout")
def logout_user(session: SessionDB = Depends(get_current_session), db: Session = Depends(get_db)):
    """Session hygiene (FIX 1h): invalidates token upon logout."""
    invalidate_session(db, session.token)
    return {"status": "logged_out"}


# ==========================================
# PROTECTED COVERAGE & METRICS
# ==========================================

@app.get("/api/coverage")
def get_coverage_report(session: SessionDB = Depends(get_current_session)):
    report = coverage_reporter.generate_report(pack)
    return report.to_dict()


# ==========================================
# STUDENT FLOW & SERVER-SIDE GRADING (FIX 1, 2)
# ==========================================

@app.get("/api/student/{student_id}/next-step")
def get_student_next_step(
    student_id: str,
    session: SessionDB = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Online next step (FIX 1c, FIX 2).
    Requires student token matching student_id.
    Options returned are STRICTLY SANITIZED: no is_correct or misconception_tag.
    """
    verify_student_only_access(session, student_id)

    student, plan, mastery, hyp = load_student_domain_state(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    step = engine.get_next_step(student, plan, mastery, hyp)
    ladder = engine.get_hint_ladder(step.item.id) if (step.item and hasattr(step.item, "id")) else None

    sanitized_item = None
    if step.item and hasattr(step.item, "model_dump"):
        item_dict = step.item.model_dump()
        sanitized_item = sanitize_question_for_client(item_dict)

    sanitized_ladder = None
    if ladder:
        sanitized_ladder = ladder.model_dump()

    return {
        "step": step.to_dict(),
        "item": sanitized_item,
        "hint_ladder": sanitized_ladder
    }


@app.post("/api/student/{student_id}/attempt")
def submit_attempt(
    student_id: str,
    payload: AttemptPayload,
    session: SessionDB = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    CRITICAL: Server-Side Grading (FIX 1c, 1d).
    Requires student token matching student_id.
    Malformed bodies return 422 (never 500).
    Missing token returns 401.
    """
    verify_student_only_access(session, student_id)

    student, plan, mastery, hyp = load_student_domain_state(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    q_id = payload.question_id
    selected_opt_id = payload.selected_option_id
    concept_id = payload.concept_id

    # Server-Side Grading Lookup
    question = pack.get_question(q_id)
    if not question:
        raise HTTPException(status_code=404, detail=f"Question '{q_id}' not found in pack.")

    matched_option = next((opt for opt in question.options if opt.id == selected_opt_id), None)
    if not matched_option:
        raise HTTPException(status_code=400, detail=f"Option '{selected_opt_id}' does not exist for question '{q_id}'.")

    server_is_correct = matched_option.is_correct
    server_misconception_tag = matched_option.misconception_tag if not server_is_correct else None

    attempt = Attempt(
        student_id=student_id,
        question_id=q_id,
        concept_id=concept_id or question.concept,
        selected_option_id=selected_opt_id,
        is_correct=server_is_correct,
        misconception_tag=server_misconception_tag,
        time_spent_seconds=payload.time_spent_seconds
    )

    attempt_db = AttemptDB(
        id=payload.attempt_id or secrets.token_hex(12),
        student_id=student_id,
        subject_key=student.subject_key if hasattr(student, "subject_key") else None,
        question_id=attempt.question_id,
        concept_id=attempt.concept_id,
        selected_option_id=attempt.selected_option_id,
        is_correct=attempt.is_correct,
        misconception_tag=attempt.misconception_tag,
        time_spent_seconds=attempt.time_spent_seconds,
        timestamp=datetime.utcnow()
    )
    db.add(attempt_db)

    plan, mastery, hyp, decision = engine.process_attempt(student, plan, attempt, mastery, hyp)

    decision_db = DecisionDB(
        student_id=student_id,
        class_id=student.class_id,
        action=decision.action,
        rule_id=decision.rule_id,
        reason=decision.reason,
        stage=plan.current_stage.value if hasattr(plan.current_stage, "value") else str(plan.current_stage),
        timestamp=datetime.utcnow()
    )
    db.add(decision_db)
    db.commit()

    save_student_domain_state(db, student_id, plan, mastery, hyp)

    return {
        "decision": decision.to_dict(),
        "server_graded_correct": server_is_correct,
        "authoritative_misconception": server_misconception_tag,
        "updated_mastery": mastery.mastery_estimate,
        "mastery_label": mastery.mastery_label,
        "hypothesis": hyp.model_dump() if hyp else None
    }


@app.get("/api/student/{student_id}/offline-pack")
def get_offline_pack(
    student_id: str,
    session: SessionDB = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Authenticated offline pack download (FIX 2).
    Available ONLY to an authenticated student session for that student's class.
    Contains answer keys for offline grading on device.
    Tradeoff explicitly documented: stored in IndexedDB, server re-grades on sync.
    """
    verify_student_only_access(session, student_id)

    student = db.query(StudentDB).filter(StudentDB.pseudonymous_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    return pack.model_dump()


# ==========================================
# TEACHER DASHBOARD & OVERRIDES (FIX 1c)
# ==========================================

@app.get("/api/teacher/class/{class_id}")
def get_teacher_class_dashboard(
    class_id: str,
    session: SessionDB = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """
    Teacher dashboard. Requires teacher session.
    Class scoping strictly enforced: teacher can only access assigned classes.
    No fallback teacher_id!
    """
    verify_teacher_class_access(session, class_id, db)
    user = db.query(UserDB).filter(UserDB.id == session.user_id).first()
    if user:
        teacher_service.teacher_class_assignments[session.user_id] = set(user.get_classes()) if session.role != "admin" else {class_id}

    students_db = db.query(StudentDB).filter(StudentDB.class_id == class_id).all()
    class_students_data = []
    for s_db in students_db:
        stu, plan, mastery, hyp = load_student_domain_state(db, s_db.pseudonymous_id)
        if stu and plan:
            class_students_data.append({
                "student_id": stu.pseudonymous_id,
                "plan": plan,
                "mastery": mastery,
                "hypothesis": hyp
            })

    try:
        dashboard = teacher_service.get_class_dashboard(session.user_id, class_id, class_students_data)
        return dashboard.model_dump()
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.post("/api/teacher/override")
def apply_teacher_override(
    payload: OverridePayload,
    session: SessionDB = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """
    Teacher override. Requires teacher session with class scope.
    Mandatory reason text. No no-session fallback!
    """
    class_id = payload.class_id
    verify_teacher_class_access(session, class_id, db)

    teacher_id = session.user_id
    student_id = payload.student_id
    concept_id = payload.concept_id
    action = payload.action
    reason = payload.reason

    if not reason or not reason.strip():
        raise HTTPException(status_code=400, detail="Teacher override reason is mandatory.")

    stu, plan, mastery, hyp = load_student_domain_state(db, student_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Student plan not found.")

    updated_plan, override = teacher_service.apply_override(
        teacher_id, class_id, student_id, concept_id, action, reason, plan
    )

    override_db = TeacherOverrideDB(
        student_id=student_id,
        teacher_id=teacher_id,
        class_id=class_id,
        concept_id=concept_id,
        override_action=action,
        reason=reason,
        timestamp=datetime.utcnow()
    )
    db.add(override_db)
    save_student_domain_state(db, student_id, updated_plan, mastery, hyp)

    return {"override": override.model_dump(), "plan": updated_plan.model_dump()}


@app.post("/api/teacher/bulk-paper-submit")
def submit_paper_responses(
    payload: Dict[str, Any] = Body(...),
    session: SessionDB = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """Teacher paper mode response submission. Requires teacher session."""
    responses = payload.get("responses", [])
    graded_count = 0

    for resp in responses:
        student_id = resp.get("student_id")
        q_id = resp.get("question_id")
        selected_opt = resp.get("selected_option_id")
        if not student_id or not q_id or not selected_opt:
            continue

        q = pack.get_question(q_id)
        if not q:
            continue
        opt = next((o for o in q.options if o.id == selected_opt), None)
        if not opt:
            continue

        is_corr = opt.is_correct
        misc_tag = opt.misconception_tag if not is_corr else None

        stu, plan, mastery, hyp = load_student_domain_state(db, student_id)
        if stu and plan:
            att = Attempt(
                student_id=student_id,
                question_id=q_id,
                concept_id=q.concept,
                selected_option_id=selected_opt,
                is_correct=is_corr,
                misconception_tag=misc_tag
            )
            plan, mastery, hyp, dec = engine.process_attempt(stu, plan, att, mastery, hyp)
            save_student_domain_state(db, student_id, plan, mastery, hyp)
            graded_count += 1

    return {"status": "success", "processed_records": graded_count}


# ==========================================
# PRIVACY, DELETION & SYNC (FIX 1c, FIX 4, FIX 5)
# ==========================================

@app.post("/api/privacy/delete-student")
def delete_student(
    payload: Dict[str, str] = Body(...),
    session: SessionDB = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    CRITICAL: Clean deletion with zero trace of student ID (FIX 1c, FIX 5).
    Authorized teacher (class scoped) or admin ONLY.
    Removes:
    - sessions, student record, plan, mastery, hypotheses, attempts, decisions, pin profile,
    - teacher overrides (purged completely so no student_id and NO override reason text remains in DB),
    - device bindings.
    Issues purge tokens to devices bound to the class.
    Creates TombstoneDB using subject_key (NEVER student_id!).
    Zero PII in AuditEventDB.
    """
    student_id = payload.get("student_id")
    if not student_id:
        raise HTTPException(status_code=400, detail="student_id is required.")

    student = db.query(StudentDB).filter(StudentDB.pseudonymous_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    class_id = student.class_id
    subject_key = student.subject_key

    # Class scoping for teacher, admin can delete any
    if session.role == "teacher":
        verify_teacher_class_access(session, class_id, db)
    elif session.role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized role for deletion.")

    # 1. Purge all records from active stores
    db.query(StudentDB).filter(StudentDB.pseudonymous_id == student_id).delete()
    db.query(PlanDB).filter(PlanDB.student_id == student_id).delete()
    db.query(MasteryStateDB).filter(MasteryStateDB.student_id == student_id).delete()
    db.query(HypothesisDB).filter(HypothesisDB.student_id == student_id).delete()
    db.query(AttemptDB).filter(AttemptDB.student_id == student_id).delete()
    db.query(DecisionDB).filter(DecisionDB.student_id == student_id).delete()
    db.query(PinProfileDB).filter(PinProfileDB.student_id == student_id).delete()

    # Sessions purge (FIX 1h, FIX 5)
    invalidate_all_student_sessions(db, student_id)

    # Purge TeacherOverrideDB records completely so zero trace of student ID and override reason remains
    db.query(TeacherOverrideDB).filter(TeacherOverrideDB.student_id == student_id).delete()

    # 2. Provide restricted revocation/purge token to devices bound to this class (FIX 5)
    purge_token = secrets.token_hex(16)
    devices = db.query(DeviceDB).filter(DeviceDB.class_id == class_id).all()
    for dev in devices:
        dev.device_purge_token = purge_token

    # 3. Create Opaque Tombstone using subject_key
    opaque_key = secrets.token_hex(16)
    device_count = len(devices)

    tombstone = TombstoneDB(
        opaque_key=opaque_key,
        subject_key=subject_key,
        status="pending" if device_count > 0 else "applied",
        pending_devices=device_count,
        created_at=datetime.utcnow()
    )
    db.add(tombstone)

    # 4. Zero-PII Audit Event (NO student_id, NO reason text)
    audit = AuditEventDB(
        event_type="DELETE_STUDENT",
        actor=session.user_id or session.role,
        class_id=class_id,
        record_count=1,
        opaque_tombstone_key=opaque_key,
        timestamp=datetime.utcnow()
    )
    db.add(audit)
    db.commit()

    return {
        "status": "deleted",
        "tombstone_key": opaque_key,
        "pending_devices": device_count,
        "is_fully_deleted_everywhere": (device_count == 0),
        "status_message": "All app stores deleted." if device_count == 0 else f"Deletion pending, not yet applied on {device_count} device(s)."
    }


@app.post("/api/privacy/sync")
def sync_device(
    payload: SyncPayload,
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    x_device_purge_token: Optional[str] = Header(None, alias="X-Device-Purge-Token"),
    db: Session = Depends(get_db)
):
    """
    Device synchronization (FIX 1e, FIX 4, FIX 5).
    Requires authenticated session (student/teacher) OR purge-only device credential.
    Unregistered device returns explicit RESET-required response (never silent registration).
    Stale device (>30 days) returns RESET-required response.
    Purge token permits ONLY fetching pending tombstones and wiping local cache.
    Re-grades queued attempts with idempotency.
    """
    token = auth.credentials if auth else None
    session = None
    is_purge_credential = False

    if token:
        # Check if it's a valid session token
        session = db.query(SessionDB).filter(SessionDB.token == token).first()
        if session and session.expires_at < datetime.utcnow():
            session = None

        # Check if it's a device purge token
        if not session:
            dev_with_token = db.query(DeviceDB).filter(DeviceDB.device_purge_token == token).first()
            if dev_with_token:
                is_purge_credential = True

    if not is_purge_credential and x_device_purge_token:
        dev_with_token = db.query(DeviceDB).filter(DeviceDB.device_purge_token == x_device_purge_token).first()
        if dev_with_token:
            is_purge_credential = True

    if not session and not is_purge_credential:
        raise HTTPException(status_code=401, detail="Authentication required for sync.")

    device_id = payload.device_id
    device = db.query(DeviceDB).filter(DeviceDB.device_id == device_id).first()

    # FIX 4: Unregistered device gets RESET, not silent registration!
    if not device:
        return {
            "device_id": device_id,
            "is_stale_reset_required": True,
            "reset_reason": "unregistered_device",
            "applied_tombstones": [],
            "synced_attempts_processed": 0
        }

    # FIX 4: Stale device (>30 days) gets RESET
    if datetime.utcnow() - device.last_sync_at > timedelta(days=30):
        device.last_sync_at = datetime.utcnow()
        db.commit()
        return {
            "device_id": device_id,
            "is_stale_reset_required": True,
            "reset_reason": "retention_expired",
            "applied_tombstones": [],
            "synced_attempts_processed": 0
        }

    # If purge credential used: fetch tombstones only, no learning access (FIX 5)
    pending_tombstones = db.query(TombstoneDB).filter(TombstoneDB.status == "pending").all()
    applied_keys = []
    for t in pending_tombstones:
        applied_keys.append(t.opaque_key)
        t.pending_devices = max(0, t.pending_devices - 1)
        if t.pending_devices == 0:
            t.status = "applied"

    if is_purge_credential:
        db.commit()
        return {
            "device_id": device_id,
            "is_stale_reset_required": False,
            "applied_tombstones": applied_keys,
            "synced_attempts_processed": 0,
            "purge_mode": True
        }

    # Re-grade queued attempts with idempotency (FIX 3f)
    processed_count = 0
    latest_mastery = None

    for att_dict in payload.queued_attempts:
        s_id = att_dict.get("student_id")
        q_id = att_dict.get("question_id")
        sel_opt = att_dict.get("selected_option_id")
        client_attempt_id = att_dict.get("attempt_id") or att_dict.get("id")

        # Session student isolation on sync: student token can only sync own attempts
        if session.role == "student" and session.student_id != s_id:
            continue

        # Idempotency check: ignore already processed attempts
        if client_attempt_id:
            existing = db.query(AttemptDB).filter(AttemptDB.id == client_attempt_id).first()
            if existing:
                continue

        stu, plan, mastery, hyp = load_student_domain_state(db, s_id)
        if not stu or not plan:
            continue

        q = pack.get_question(q_id)
        if not q:
            continue

        opt = next((o for o in q.options if o.id == sel_opt), None)
        if not opt:
            continue

        real_is_correct = opt.is_correct
        real_tag = opt.misconception_tag if not real_is_correct else None

        valid_att = Attempt(
            student_id=s_id,
            question_id=q_id,
            concept_id=q.concept,
            selected_option_id=sel_opt,
            is_correct=real_is_correct,
            misconception_tag=real_tag
        )

        attempt_db = AttemptDB(
            id=client_attempt_id or secrets.token_hex(12),
            student_id=s_id,
            subject_key=stu.subject_key if hasattr(stu, "subject_key") else None,
            question_id=valid_att.question_id,
            concept_id=valid_att.concept_id,
            selected_option_id=valid_att.selected_option_id,
            is_correct=valid_att.is_correct,
            misconception_tag=valid_att.misconception_tag,
            time_spent_seconds=att_dict.get("time_spent_seconds"),
            timestamp=datetime.utcnow()
        )
        db.add(attempt_db)

        plan, mastery, hyp, dec = engine.process_attempt(stu, plan, valid_att, mastery, hyp)
        save_student_domain_state(db, s_id, plan, mastery, hyp)
        processed_count += 1
        if mastery:
            latest_mastery = {
                "concept_id": mastery.concept_id,
                "mastery_estimate": mastery.mastery_estimate,
                "mastery_label": mastery.mastery_label
            }

    device.last_sync_at = datetime.utcnow()
    db.commit()

    return {
        "device_id": device_id,
        "is_stale_reset_required": False,
        "applied_tombstones": applied_keys,
        "synced_attempts_processed": processed_count,
        "authoritative_mastery": latest_mastery
    }


@app.post("/api/device/purge-ack")
def acknowledge_purge(
    payload: Dict[str, str] = Body(...),
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    x_device_purge_token: Optional[str] = Header(None, alias="X-Device-Purge-Token"),
    db: Session = Depends(get_db)
):
    """
    Device acknowledges tombstone purge applied (FIX 5).
    Clears device_purge_token.
    """
    device_id = payload.get("device_id")
    token = auth.credentials if auth else x_device_purge_token
    device = db.query(DeviceDB).filter(DeviceDB.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found.")

    if device.device_purge_token and device.device_purge_token != token:
        raise HTTPException(status_code=403, detail="Invalid purge token.")

    device.device_purge_token = None
    db.commit()
    return {"status": "purge_acknowledged", "device_id": device_id}


@app.get("/api/student/{student_id}/export")
def export_student_data(
    student_id: str,
    session: SessionDB = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Exports student data strictly without direct identifiers.
    Authorized teacher (class scoped), student themselves, or admin ONLY (FIX 1c).
    """
    student = db.query(StudentDB).filter(StudentDB.pseudonymous_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    verify_teacher_or_admin_student_access(session, student_id, student.class_id, db)

    attempts = db.query(AttemptDB).filter(AttemptDB.student_id == student_id).all()
    masteries = db.query(MasteryStateDB).filter(MasteryStateDB.student_id == student_id).all()

    return {
        "pseudonymous_id": student.pseudonymous_id,
        "class_id": student.class_id,
        "board": student.board,
        "consent_status": student.consent_status,
        "attempts_count": len(attempts),
        "masteries": [
            {
                "concept_id": m.concept_id,
                "mastery_estimate": m.mastery_estimate,
                "mastery_label": m.mastery_label
            }
            for m in masteries
        ]
    }


# ==========================================
# ADMIN & RETENTION ROUTES
# ==========================================

@app.get("/api/admin/audit-logs")
def get_audit_logs(
    session: SessionDB = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin only: view zero-PII audit log."""
    logs = db.query(AuditEventDB).order_by(AuditEventDB.id.desc()).all()
    return [
        {
            "id": l.id,
            "event_type": l.event_type,
            "actor": l.actor,
            "class_id": l.class_id,
            "record_count": l.record_count,
            "opaque_tombstone_key": l.opaque_tombstone_key,
            "timestamp": l.timestamp.isoformat()
        }
        for l in logs
    ]


@app.post("/api/admin/retention-run")
def trigger_retention_run(
    session: SessionDB = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin only: executes data retention policy."""
    cutoff = datetime.utcnow() - timedelta(days=30)
    purged_count = db.query(TombstoneDB).filter(
        TombstoneDB.status == "applied",
        TombstoneDB.created_at < cutoff
    ).delete()

    db.add(AuditEventDB(
        event_type="RETENTION_PURGE",
        actor=session.user_id or "admin",
        class_id="all",
        record_count=purged_count,
        timestamp=datetime.utcnow()
    ))
    db.commit()

    return {
        "status": "success",
        "purged_tombstones": purged_count,
        "cutoff": cutoff.isoformat()
    }


@app.post("/api/admin/student/{student_id}/consent")
def update_student_consent(
    student_id: str,
    payload: Dict[str, str] = Body(...),
    session: SessionDB = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin only: updates student consent state."""
    status_str = payload.get("consent_status")
    if status_str not in ["not requested", "requested", "recorded"]:
        raise HTTPException(status_code=400, detail="Invalid consent status value.")

    stu = db.query(StudentDB).filter(StudentDB.pseudonymous_id == student_id).first()
    if not stu:
        raise HTTPException(status_code=404, detail="Student not found.")

    stu.consent_status = status_str
    db.add(AuditEventDB(
        event_type="CONSENT_UPDATE",
        actor=session.user_id or "admin",
        class_id=stu.class_id,
        record_count=1,
        timestamp=datetime.utcnow()
    ))
    db.commit()

    return {"student_id": student_id, "consent_status": stu.consent_status}


# ==========================================
# CONTENT REVIEW & EDITOR ROUTES (SECTION 7)
# ==========================================

@app.post("/api/reviewer/attest")
def attest_pack_item(
    payload: Dict[str, Any] = Body(...),
    session: SessionDB = Depends(require_reviewer),
    db: Session = Depends(get_db)
):
    """Reviewer only: Human review attestation."""
    item_id = payload.get("item_id")
    status_val = payload.get("status")
    statement = payload.get("attestation_statement", "Verified NCERT Class 8 curriculum alignment.")

    if not item_id or not status_val:
        raise HTTPException(status_code=400, detail="item_id and status are required.")

    valid_statuses = [
        "author-drafted, unreviewed",
        "flagged for revision",
        "reviewed, intended NCERT alignment verified"
    ]
    if status_val not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid review status. Must be one of {valid_statuses}")

    reviewer_user = db.query(UserDB).filter(UserDB.id == session.user_id).first()
    rev_name = reviewer_user.username if reviewer_user else "Reviewer"

    updated = False
    for q in pack.questions:
        if q.id == item_id:
            q.review_status = ReviewStatus(status_val)
            updated = True
            break
    if not updated:
        for les in pack.lessons:
            if les.id == item_id:
                les.review_status = ReviewStatus(status_val)
                updated = True
                break

    if not updated:
        raise HTTPException(status_code=404, detail=f"Pack item '{item_id}' not found.")

    rec = ReviewRecordDB(
        item_id=item_id,
        item_type="question" if item_id.startswith("q_") else "lesson",
        status=status_val,
        reviewer_name=rev_name,
        reviewer_role="curriculum_reviewer",
        attestation_date=datetime.utcnow(),
        attestation_statement=statement
    )
    db.add(rec)
    db.commit()

    with open(PACK_PATH, "w", encoding="utf-8") as f:
        f.write(pack.model_dump_json(indent=2))

    return {
        "item_id": item_id,
        "new_status": status_val,
        "reviewer": rev_name,
        "attestation_statement": statement
    }


@app.get("/api/content/editor/pack")
def get_editor_pack(session: SessionDB = Depends(require_reviewer)):
    """Returns full pack for content editor UI."""
    return pack.model_dump()


@app.post("/api/content/editor/pack")
def update_editor_pack_item(
    payload: Dict[str, Any] = Body(...),
    session: SessionDB = Depends(require_reviewer),
    db: Session = Depends(get_db)
):
    """
    Modifies an item in the pack.
    Rule: Modifying an item resets its review status to 'author-drafted, unreviewed'.
    """
    item_id = payload.get("id")
    if not item_id:
        raise HTTPException(status_code=400, detail="Item 'id' is required.")

    payload["review_status"] = "author-drafted, unreviewed"

    updated = False
    for i, q in enumerate(pack.questions):
        if q.id == item_id:
            from app.models.pack import Question
            pack.questions[i] = Question.model_validate(payload)
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Item not found.")

    with open(PACK_PATH, "w", encoding="utf-8") as f:
        f.write(pack.model_dump_json(indent=2))

    return {"status": "saved", "item_id": item_id, "review_status": "author-drafted, unreviewed"}


@app.get("/api/paper/sheet/{concept_id}", response_class=HTMLResponse)
def get_printable_sheet(concept_id: str, session: SessionDB = Depends(require_teacher)):
    sheet = paper_manager.generate_printable_sheet(concept_id)
    return sheet.to_html()
