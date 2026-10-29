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
from pydantic import BaseModel, Field, ValidationError
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
    PinProfileDB, DeviceSubjectDB, TombstoneDeliveryDB
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
from app.models.learning import Attempt, Plan, MasteryState, Hypothesis, HypothesisStatus, StageEnum, BKTParameters
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
    reason: str = Field(..., min_length=3, description="Mandatory pedagogical reason (at least 3 characters)")


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
            mastery_label=mastery_db.mastery_label,
            consecutive_successes=mastery_db.consecutive_successes or 0
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


def load_or_create_mastery_state(db: Session, student_id: str, concept_id: str) -> MasteryState:
    """FIX 3 & FIX 6: Loads or creates the mastery row for the question's own concept at its prior, persisting consecutive_successes."""
    m_db = db.query(MasteryStateDB).filter(
        MasteryStateDB.student_id == student_id,
        MasteryStateDB.concept_id == concept_id
    ).first()
    if not m_db:
        bkt_params = BKTParameters()
        m_db = MasteryStateDB(
            student_id=student_id,
            concept_id=concept_id,
            mastery_estimate=bkt_params.prior,
            bkt_prior=bkt_params.prior,
            bkt_learn=bkt_params.learn,
            bkt_guess=bkt_params.guess,
            bkt_slip=bkt_params.slip,
            mastery_label=bkt_params.label,
            consecutive_successes=0
        )
        db.add(m_db)
        db.commit()

    return MasteryState(
        student_id=m_db.student_id,
        concept_id=m_db.concept_id,
        mastery_estimate=m_db.mastery_estimate,
        bkt_params=BKTParameters(
            prior=m_db.bkt_prior,
            learn=m_db.bkt_learn,
            guess=m_db.bkt_guess,
            slip=m_db.bkt_slip,
            label=m_db.mastery_label
        ),
        mastery_label=m_db.mastery_label,
        consecutive_successes=m_db.consecutive_successes or 0
    )


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
        m_db.consecutive_successes = mastery.consecutive_successes
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
@app.post("/api/auth/student-pin-login")
def verify_pin(payload: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    """
    PIN verification for student session on a shared device.
    FIX 2: Failed-attempt counting and temporary lockout per student regardless of device_id,
    plus per-device rate limiting and lockout.
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

    now = datetime.utcnow()

    # 1. Global student lockout check (applies regardless of device_id)
    if student.locked_until and now < student.locked_until:
        rem = max(1, int((student.locked_until - now).total_seconds()))
        raise HTTPException(status_code=403, detail=f"Account locked due to multiple failed tries. Please wait {rem} seconds.")

    # 2. Device profile lockout check (if device_id provided)
    profile = None
    if device_id:
        profile = db.query(PinProfileDB).filter(
            PinProfileDB.device_id == device_id,
            PinProfileDB.student_id == student_id
        ).first()
        if profile and profile.locked_until and now < profile.locked_until:
            rem = max(1, int((profile.locked_until - now).total_seconds()))
            raise HTTPException(status_code=403, detail=f"Device locked due to multiple failed tries. Please wait {rem} seconds.")

    # 3. Hash verification
    salt = profile.salt if profile else student.salt
    expected_hash = profile.pin_hash if profile else student.pin_hash
    computed_hash = hash_pin(candidate_pin, salt)

    if computed_hash != expected_hash:
        # Increment failed attempts per student regardless of device_id
        student.failed_attempts = (student.failed_attempts or 0) + 1
        if student.failed_attempts >= 3:
            student.locked_until = now + timedelta(seconds=60)

        if profile:
            profile.failed_attempts = (profile.failed_attempts or 0) + 1
            if profile.failed_attempts >= 3:
                profile.locked_until = now + timedelta(seconds=60)

        db.commit()
        if (student.failed_attempts or 0) >= 3:
            raise HTTPException(status_code=403, detail="Incorrect PIN. Account locked for 60 seconds.")
        raise HTTPException(status_code=401, detail="Incorrect PIN.")

    # Success: reset failed attempts and lockout
    student.failed_attempts = 0
    student.locked_until = None
    if profile:
        profile.failed_attempts = 0
        profile.locked_until = None

    # Register device bound to student and class upon authenticated login (FIX 1, FIX 4)
    device_purge_token = None
    if device_id:
        dev = db.query(DeviceDB).filter(DeviceDB.device_id == device_id).first()
        if not dev:
            device_purge_token = secrets.token_hex(24)
            dev = DeviceDB(
                device_id=device_id,
                class_id=student.class_id,
                device_purge_token=device_purge_token
            )
            db.add(dev)
            db.commit()
        else:
            dev.class_id = student.class_id
            dev.last_sync_at = datetime.utcnow()
            if not dev.device_purge_token:
                dev.device_purge_token = secrets.token_hex(24)
            device_purge_token = dev.device_purge_token
            db.commit()

        # FIX 1: Track per device which student subject_keys have been active on it (opaque keys only)
        dev_sub = db.query(DeviceSubjectDB).filter(
            DeviceSubjectDB.device_id == device_id,
            DeviceSubjectDB.subject_key == student.subject_key
        ).first()
        if not dev_sub:
            dev_sub = DeviceSubjectDB(
                device_id=device_id,
                subject_key=student.subject_key,
                last_seen_at=datetime.utcnow()
            )
            db.add(dev_sub)
        else:
            dev_sub.last_seen_at = datetime.utcnow()
        db.commit()

    session = create_session(db, role="student", student_id=student_id, device_id=device_id)
    return {
        "authenticated": True,
        "access_token": session.token,
        "token_type": "bearer",
        "student_id": student_id,
        "class_id": student.class_id,
        "subject_key": student.subject_key,
        "device_purge_token": device_purge_token,
        "device_id": device_id
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
    language: Optional[str] = None,
    session: SessionDB = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Online next step (FIX 1c, FIX 2, FIX 5).
    Requires student token matching student_id.
    Options returned are STRICTLY SANITIZED: no is_correct or misconception_tag.
    Does NOT mutate plan stage in GET.
    """
    verify_student_only_access(session, student_id)

    student, plan, mastery, hyp = load_student_domain_state(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    if language:
        student.medium_language = language

    # Exclude recently seen items for the active concept
    recent_attempts = db.query(AttemptDB.question_id).filter(
        AttemptDB.student_id == student_id,
        AttemptDB.concept_id == plan.current_concept_id
    ).all()
    seen_qids = {a[0] for a in recent_attempts}

    step = engine.get_next_step(student, plan, mastery, hyp, seen_question_ids=seen_qids)
    ladder = engine.get_hint_ladder(step.item.id) if (step.item and hasattr(step.item, "id")) else None

    sanitized_item = None
    if step.item:
        if step.item_type == "question" and hasattr(step.item, "model_dump"):
            sanitized_item = sanitize_question_for_client(step.item.model_dump())
        elif step.item_type == "lesson" and hasattr(step.item, "model_dump"):
            sanitized_item = step.item.model_dump()

    sanitized_ladder = None
    if ladder:
        sanitized_ladder = ladder.model_dump()

    step_dict = step.to_dict()
    step_dict["target_concept_id"] = plan.current_concept_id
    step_dict["gap_concept_id"] = plan.gap_concept_id
    step_dict["misconception_tag"] = hyp.misconception_tag if hyp else None
    step_dict["stuck_attempts"] = plan.stuck_attempts_count
    step_dict["bridge_recheck_fails"] = plan.bridge_recheck_fails
    step_dict["consecutive_successes"] = mastery.consecutive_successes

    return {
        "step": step_dict,
        "item": sanitized_item,
        "hint_ladder": sanitized_ladder
    }


@app.post("/api/student/{student_id}/continue-lesson")
def continue_from_lesson(
    student_id: str,
    session: SessionDB = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Explicit stage transition from micro-lesson (LEARN) to bridge re-check (BRIDGE_RECHECK).
    Saves the stage transition to the database. Does not mutate state in GET.
    """
    verify_student_only_access(session, student_id)
    student, plan, mastery, hyp = load_student_domain_state(db, student_id)
    if not student or not plan:
        raise HTTPException(status_code=404, detail="Student or plan not found.")

    plan.current_stage = StageEnum.BRIDGE_RECHECK
    plan.reason = "Micro-lesson completed by student. Transitioned to bridge re-check."
    save_student_domain_state(db, student_id, plan, mastery, hyp)
    db.commit()

    return {"status": "transitioned", "stage": StageEnum.BRIDGE_RECHECK.value}


@app.post("/api/student/{student_id}/attempt")
def submit_attempt(
    student_id: str,
    payload: AttemptPayload,
    session: SessionDB = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    CRITICAL: Server-Side Grading (FIX 1c, 1d) with per-student idempotency.
    Requires student token matching student_id.
    Malformed bodies return 422 (never 500).
    Missing token returns 401.
    Identical retry returns original saved result (HTTP 200).
    Same ID with conflicting payload returns HTTP 409 (never 500).
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
    target_concept_id = question.concept

    # FIX 9: Idempotency per student
    client_attempt_id = payload.attempt_id
    stored_attempt_id = f"{student_id}:{client_attempt_id}" if client_attempt_id else secrets.token_hex(12)

    existing = db.query(AttemptDB).filter(
        AttemptDB.student_id == student_id,
        AttemptDB.id == stored_attempt_id
    ).first()

    if existing:
        if existing.question_id == q_id and existing.selected_option_id == selected_opt_id:
            # Identical retry: return original saved result with HTTP 200, no duplicate attempt or mastery change
            qm = load_or_create_mastery_state(db, student_id, existing.concept_id)
            last_decision = db.query(DecisionDB).filter(
                DecisionDB.student_id == student_id
            ).order_by(DecisionDB.id.desc()).first()

            return {
                "decision": {
                    "action": last_decision.action if last_decision else "CONTINUE_PRACTICE",
                    "rule_id": last_decision.rule_id if last_decision else "idempotent_retry",
                    "reason": last_decision.reason if last_decision else "Idempotent attempt retry",
                    "metadata": {"idempotent_replay": True}
                },
                "server_graded_correct": existing.is_correct,
                "authoritative_misconception": existing.misconception_tag,
                "updated_mastery": qm.mastery_estimate,
                "mastery_label": qm.mastery_label,
                "concept_id": existing.concept_id,
                "hypothesis": hyp.model_dump() if hyp else None
            }
        else:
            # Same attempt id with different payload -> HTTP 409 Conflict
            raise HTTPException(
                status_code=409,
                detail="Conflict: Attempt ID already submitted with a different payload."
            )

    attempt = Attempt(
        student_id=student_id,
        question_id=q_id,
        concept_id=target_concept_id,
        selected_option_id=selected_opt_id,
        is_correct=server_is_correct,
        misconception_tag=server_misconception_tag,
        time_spent_seconds=payload.time_spent_seconds
    )

    attempt_db = AttemptDB(
        id=stored_attempt_id,
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

    # FIX 3: Load or create mastery row for the question's OWN concept, leaving plan's concept untouched
    question_mastery = load_or_create_mastery_state(db, student_id, target_concept_id)
    original_mastery = question_mastery if target_concept_id == plan.current_concept_id else load_or_create_mastery_state(db, student_id, plan.current_concept_id)
    plan, updated_question_mastery, hyp, decision = engine.process_attempt(
        student, plan, attempt, question_mastery, hyp, original_concept_mastery=original_mastery
    )

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

    save_student_domain_state(db, student_id, plan, updated_question_mastery, hyp)

    return {
        "decision": decision.to_dict(),
        "server_graded_correct": server_is_correct,
        "authoritative_misconception": server_misconception_tag,
        "updated_mastery": updated_question_mastery.mastery_estimate,
        "mastery_label": updated_question_mastery.mastery_label,
        "concept_id": updated_question_mastery.concept_id,
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
            if not mastery:
                mastery = load_or_create_mastery_state(db, stu.pseudonymous_id, plan.current_concept_id)
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
    Loads class assignments dynamically from DB and returns 403 on permission error.
    """
    class_id = payload.class_id
    verify_teacher_class_access(session, class_id, db)

    user = db.query(UserDB).filter(UserDB.id == session.user_id).first()
    if user:
        teacher_service.teacher_class_assignments[session.user_id] = set(user.get_classes()) if session.role != "admin" else {class_id}

    teacher_id = session.user_id
    student_id = payload.student_id
    concept_id = payload.concept_id
    action = payload.action
    reason = payload.reason

    if not reason or len(reason.strip()) < 3:
        raise HTTPException(status_code=400, detail="Teacher override reason must be at least 3 characters.")

    stu, plan, mastery, hyp = load_student_domain_state(db, student_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Student plan not found.")

    try:
        updated_plan, override = teacher_service.apply_override(
            teacher_id, class_id, student_id, concept_id, action, reason.strip(), plan
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except (ValueError, ValidationError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Release any active hypothesis on teacher override
    if hyp:
        hyp.status = HypothesisStatus.REJECTED

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
    db.commit()

    return {"override": override.model_dump(), "plan": updated_plan.model_dump()}


@app.post("/api/teacher/bulk-paper-submit")
def submit_paper_responses(
    payload: Dict[str, Any] = Body(...),
    session: SessionDB = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """
    Teacher paper mode response submission. Requires teacher session.
    Saves real AttemptDB and DecisionDB records, updates real MasteryStateDB,
    and returns per-student next steps and structured errors for bad question IDs.
    """
    responses = payload.get("responses", [])
    graded_count = 0
    results = []
    errors = []

    for resp in responses:
        student_id = resp.get("student_id")
        q_id = resp.get("question_id")
        selected_opt = resp.get("selected_option_id")

        if not student_id or not q_id or not selected_opt:
            errors.append({
                "student_id": student_id,
                "question_id": q_id,
                "error": "Missing student_id, question_id, or selected_option_id."
            })
            continue

        q = pack.get_question(q_id)
        if not q:
            errors.append({
                "student_id": student_id,
                "question_id": q_id,
                "error": f"Question '{q_id}' not found in pack."
            })
            continue

        opt = next((o for o in q.options if o.id == selected_opt), None)
        if not opt:
            errors.append({
                "student_id": student_id,
                "question_id": q_id,
                "error": f"Option '{selected_opt}' not found for question '{q_id}'."
            })
            continue

        stu, plan, mastery, hyp = load_student_domain_state(db, student_id)
        if not stu or not plan:
            errors.append({
                "student_id": student_id,
                "question_id": q_id,
                "error": f"Student '{student_id}' not found."
            })
            continue

        # Check teacher authorization for this student's class
        try:
            verify_teacher_or_admin_student_access(session, student_id, stu.class_id, db)
        except HTTPException:
            errors.append({
                "student_id": student_id,
                "question_id": q_id,
                "error": f"Access Denied: Teacher not assigned to student's class '{stu.class_id}'."
            })
            continue

        is_corr = opt.is_correct
        misc_tag = opt.misconception_tag if not is_corr else None

        attempt_id = f"paper_{student_id}_{q_id}_{int(datetime.utcnow().timestamp())}_{secrets.token_hex(4)}"
        attempt = Attempt(
            student_id=student_id,
            question_id=q_id,
            concept_id=q.concept,
            selected_option_id=selected_opt,
            is_correct=is_corr,
            misconception_tag=misc_tag,
            time_spent_seconds=resp.get("time_spent_seconds", 30)
        )

        att_db = AttemptDB(
            id=f"{student_id}:{attempt_id}",
            student_id=student_id,
            subject_key=stu.subject_key if hasattr(stu, "subject_key") else None,
            question_id=q_id,
            concept_id=q.concept,
            selected_option_id=selected_opt,
            is_correct=is_corr,
            misconception_tag=misc_tag,
            time_spent_seconds=attempt.time_spent_seconds,
            timestamp=datetime.utcnow()
        )
        db.add(att_db)

        # Update per-concept mastery state
        target_mastery = load_or_create_mastery_state(db, student_id, q.concept)
        plan, updated_target_mastery, hyp, decision = engine.process_attempt(
            stu, plan, attempt, target_mastery, hyp
        )
        save_student_domain_state(db, student_id, plan, updated_target_mastery, hyp)

        dec_db = DecisionDB(
            student_id=student_id,
            class_id=stu.class_id,
            action=decision.action,
            rule_id=decision.rule_id,
            reason=decision.reason,
            stage=plan.current_stage.value if hasattr(plan.current_stage, "value") else str(plan.current_stage),
            timestamp=datetime.utcnow()
        )
        db.add(dec_db)
        graded_count += 1
        results.append({
            "student_id": student_id,
            "question_id": q_id,
            "is_correct": is_corr,
            "updated_mastery": updated_target_mastery.mastery_estimate,
            "next_stage": plan.current_stage.value if hasattr(plan.current_stage, "value") else str(plan.current_stage),
            "action": decision.action
        })

    db.commit()
    return {
        "status": "success" if graded_count > 0 else ("partial" if errors else "failed"),
        "processed_count": graded_count,
        "processed_records": graded_count,
        "results": results,
        "errors": errors
    }


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

    # FIX 1: Find only devices that have held this student's subject_key!
    active_device_records = db.query(DeviceSubjectDB).filter(
        DeviceSubjectDB.subject_key == subject_key
    ).all()
    device_ids = list({rec.device_id for rec in active_device_records})

    # Clear active mapping from DeviceSubjectDB
    db.query(DeviceSubjectDB).filter(DeviceSubjectDB.subject_key == subject_key).delete()

    # 2. Create Opaque Tombstone using subject_key (FIX 1)
    opaque_key = secrets.token_hex(16)
    pending_count = len(device_ids)
    now = datetime.utcnow()
    expires_at = now + timedelta(days=30)  # Documented 30-day retention policy

    tombstone = TombstoneDB(
        opaque_key=opaque_key,
        subject_key=subject_key,
        status="pending" if pending_count > 0 else "applied",
        pending_devices=pending_count,
        created_at=now,
        expires_at=expires_at,
        purged_at=now if pending_count == 0 else None
    )
    db.add(tombstone)
    db.flush()

    # 3. Create per-device, per-tombstone delivery and acknowledgment records (FIX 1)
    for dev_id in device_ids:
        delivery = TombstoneDeliveryDB(
            tombstone_id=tombstone.id,
            opaque_tombstone_key=opaque_key,
            device_id=dev_id,
            subject_key=subject_key,
            status="pending",
            created_at=now
        )
        db.add(delivery)

    # 4. Zero-PII Audit Event (NO student_id, NO reason text)
    audit = AuditEventDB(
        event_type="DELETE_STUDENT",
        actor=session.user_id or session.role,
        class_id=class_id,
        record_count=1,
        opaque_tombstone_key=opaque_key,
        timestamp=now
    )
    db.add(audit)
    db.commit()

    return {
        "status": "deleted",
        "tombstone_key": opaque_key,
        "pending_devices": pending_count,
        "is_fully_deleted_everywhere": (pending_count == 0),
        "status_message": "All app stores deleted." if pending_count == 0 else f"Deletion pending, not yet applied on {pending_count} device(s)."
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
    purge_token_device = None

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
                purge_token_device = dev_with_token

    if x_device_purge_token:
        dev_with_header = db.query(DeviceDB).filter(DeviceDB.device_purge_token == x_device_purge_token).first()
        if dev_with_header:
            purge_token_device = dev_with_header
            if not session:
                is_purge_credential = True
        else:
            raise HTTPException(status_code=403, detail="Access Denied: Unrecognized device purge token.")

    if not session and not is_purge_credential:
        raise HTTPException(status_code=401, detail="Authentication required for sync.")

    # DEFECT 2: Explicitly deny content-reviewer role access before any read or write
    if session:
        if session.role in ("reviewer", "content_reviewer", "content-reviewer"):
            raise HTTPException(
                status_code=403,
                detail="Access Denied: Content reviewer role is strictly denied access to student sync, attempts, mastery, and learning state."
            )
        if session.role not in ("student", "teacher", "admin"):
            raise HTTPException(
                status_code=403,
                detail="Access Denied: Caller role is not authorized for student sync."
            )

    # Credential-to-device binding: Purge token must match its own device
    if purge_token_device and purge_token_device.device_id != payload.device_id:
        raise HTTPException(
            status_code=403,
            detail=f"Access Denied: Purge token belongs to device '{purge_token_device.device_id}', not '{payload.device_id}'."
        )

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

    # Authorization checks before any read or write (DEFECT 2 & existing cross-class restrictions)
    if session and session.role == "teacher":
        user = db.query(UserDB).filter(UserDB.id == session.user_id).first()
        allowed_classes = set(user.get_classes()) if user else set()
        if device.class_id and device.class_id not in allowed_classes and session.role != "admin":
            raise HTTPException(
                status_code=403,
                detail=f"Access Denied: Teacher '{user.username if user else session.user_id}' is not assigned to device class '{device.class_id}'."
            )
        if payload.class_id and payload.class_id not in allowed_classes and session.role != "admin":
            raise HTTPException(
                status_code=403,
                detail=f"Access Denied: Teacher '{user.username if user else session.user_id}' is not assigned to payload class '{payload.class_id}'."
            )

    if session and session.role == "student":
        stu_caller = db.query(StudentDB).filter(StudentDB.pseudonymous_id == session.student_id).first()
        if not stu_caller:
            raise HTTPException(
                status_code=403,
                detail="Access Denied: Student profile not found."
            )

        if device.class_id and stu_caller.class_id != device.class_id:
            raise HTTPException(
                status_code=403,
                detail=f"Access Denied: Student in class '{stu_caller.class_id}' cannot sync device assigned to class '{device.class_id}'."
            )

        # Credential-to-device binding: Student access must use registered session/device association, not class matching alone
        if session.device_id:
            if session.device_id != payload.device_id:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access Denied: Student session is registered to device '{session.device_id}', not '{payload.device_id}'."
                )
        else:
            # Fallback for unpopulated session.device_id: verify registered device association
            has_device_association = db.query(DeviceSubjectDB).filter(
                DeviceSubjectDB.device_id == payload.device_id,
                DeviceSubjectDB.subject_key == stu_caller.subject_key
            ).first() or db.query(PinProfileDB).filter(
                PinProfileDB.device_id == payload.device_id,
                PinProfileDB.student_id == stu_caller.pseudonymous_id
            ).first()
            if not has_device_association:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access Denied: Student '{session.student_id}' has no registered association with device '{payload.device_id}'."
                )

    # Fetch pending purge instructions specifically for this device and caller
    # Preserves authorized class/device scope without depending on deleted StudentDB rows
    raw_deliveries = db.query(TombstoneDeliveryDB).filter(
        TombstoneDeliveryDB.device_id == device_id,
        TombstoneDeliveryDB.status == "pending"
    ).all()

    pending_deliveries = []
    if session and session.role == "teacher":
        user_t = db.query(UserDB).filter(UserDB.id == session.user_id).first()
        t_classes = set(user_t.get_classes()) if user_t else set()
        if session.role == "admin" or (device.class_id and device.class_id in t_classes):
            pending_deliveries = list(raw_deliveries)
    elif session and session.role == "student":
        pending_deliveries = list(raw_deliveries)
    elif is_purge_credential and not session:
        # Purge-only credential: device authorized to purge all tombstones intended for this device
        pending_deliveries = list(raw_deliveries)

    now = datetime.utcnow()
    purge_instructions = []
    applied_keys = []
    for d in pending_deliveries:
        d.delivered_at = now
        applied_keys.append(d.opaque_tombstone_key)
        purge_instructions.append({
            "delivery_id": d.id,
            "tombstone_id": d.tombstone_id,
            "opaque_key": d.opaque_tombstone_key,
            "subject_key": d.subject_key
        })
    db.commit()

    if is_purge_credential and not session:
        return {
            "device_id": device_id,
            "is_stale_reset_required": False,
            "applied_tombstones": applied_keys,
            "purge_instructions": purge_instructions,
            "synced_attempts_processed": 0,
            "purge_mode": True
        }

    # Re-grade queued attempts with idempotency (FIX 3f)
    # Check teacher cross-class access restriction
    if session and session.role == "teacher":
        user = db.query(UserDB).filter(UserDB.id == session.user_id).first()
        allowed_classes = set(user.get_classes()) if user else set()
        if device.class_id and device.class_id not in allowed_classes and session.role != "admin":
            raise HTTPException(
                status_code=403,
                detail=f"Access Denied: Teacher '{user.username if user else session.user_id}' is not assigned to device class '{device.class_id}'."
            )
        if payload.class_id and payload.class_id not in allowed_classes and session.role != "admin":
            raise HTTPException(
                status_code=403,
                detail=f"Access Denied: Teacher '{user.username if user else session.user_id}' is not assigned to payload class '{payload.class_id}'."
            )

    processed_count = 0
    synced_ids = []
    latest_mastery = None
    last_processed_student_id = None

    for att_dict in payload.queued_attempts:
        s_id = att_dict.get("student_id")
        q_id = att_dict.get("question_id")
        sel_opt = att_dict.get("selected_option_id")
        client_attempt_id = att_dict.get("attempt_id") or att_dict.get("id")

        # Session student isolation on sync: student token can only sync own attempts
        if session and session.role == "student" and session.student_id != s_id:
            continue

        # Session teacher isolation: teacher cannot sync attempts of students outside assigned classes
        if session and session.role == "teacher":
            user = db.query(UserDB).filter(UserDB.id == session.user_id).first()
            allowed_classes = set(user.get_classes()) if user else set()
            stu_record = db.query(StudentDB).filter(StudentDB.pseudonymous_id == s_id).first()
            if stu_record and stu_record.class_id not in allowed_classes and session.role != "admin":
                raise HTTPException(
                    status_code=403,
                    detail=f"Access Denied: Teacher cannot sync attempts for student in class '{stu_record.class_id}'."
                )

        # FIX 4: Scope attempt idempotency key to (student_id, client_attempt_id) so multiple students can use same client IDs
        stored_attempt_id = f"{s_id}:{client_attempt_id}" if client_attempt_id else secrets.token_hex(12)
        existing = db.query(AttemptDB).filter(
            AttemptDB.student_id == s_id,
            AttemptDB.id == stored_attempt_id
        ).first()
        if existing:
            if client_attempt_id:
                synced_ids.append(client_attempt_id)
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
        target_concept_id = q.concept

        valid_att = Attempt(
            student_id=s_id,
            question_id=q_id,
            concept_id=target_concept_id,
            selected_option_id=sel_opt,
            is_correct=real_is_correct,
            misconception_tag=real_tag
        )

        attempt_db = AttemptDB(
            id=stored_attempt_id,
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

        # FIX 3: Update mastery row for question's own concept upon sync re-grading
        question_mastery = load_or_create_mastery_state(db, s_id, target_concept_id)
        original_mastery = question_mastery if target_concept_id == plan.current_concept_id else load_or_create_mastery_state(db, s_id, plan.current_concept_id)
        plan, updated_question_mastery, hyp, dec = engine.process_attempt(
            stu, plan, valid_att, question_mastery, hyp, original_concept_mastery=original_mastery
        )
        save_student_domain_state(db, s_id, plan, updated_question_mastery, hyp)
        processed_count += 1
        last_processed_student_id = s_id
        if client_attempt_id:
            synced_ids.append(client_attempt_id)
        if updated_question_mastery:
            latest_mastery = {
                "concept_id": updated_question_mastery.concept_id,
                "mastery_estimate": updated_question_mastery.mastery_estimate,
                "mastery_label": updated_question_mastery.mastery_label
            }

    device.last_sync_at = datetime.utcnow()
    db.commit()

    # Authoritative state resolution: strictly resolve target student from authorized context (FIX 2)
    target_student_id = None
    if session and session.role == "student":
        # Student session can ONLY ever receive their own state (never another student's)
        target_student_id = session.student_id
    elif session and session.role == "teacher":
        user_t = db.query(UserDB).filter(UserDB.id == session.user_id).first()
        t_classes = set(user_t.get_classes()) if user_t else set()
        if last_processed_student_id:
            stu_t = db.query(StudentDB).filter(StudentDB.pseudonymous_id == last_processed_student_id).first()
            if stu_t and (stu_t.class_id in t_classes or session.role == "admin"):
                target_student_id = last_processed_student_id

    authoritative_state = None
    authoritative_mastery = latest_mastery
    if target_student_id:
        t_stu, t_plan, t_mast, t_hyp = load_student_domain_state(db, target_student_id)
        # Device-level isolation check: student must match device's class
        if t_stu and device.class_id and t_stu.class_id != device.class_id and (not session or session.role != "admin"):
            authoritative_state = None
            authoritative_mastery = None
        elif t_plan:
            orig_m = load_or_create_mastery_state(db, target_student_id, t_plan.current_concept_id)
            authoritative_state = {
                "student_id": target_student_id,
                "current_stage": t_plan.current_stage,
                "current_concept_id": t_plan.current_concept_id,
                "gap_concept_id": t_plan.gap_concept_id,
                "stuck_attempts_count": t_plan.stuck_attempts_count,
                "bridge_recheck_fails": t_plan.bridge_recheck_fails,
                "consecutive_successes": orig_m.consecutive_successes if orig_m else 0,
                "mastery_estimate": orig_m.mastery_estimate if orig_m else 0.0,
                "mastery_label": orig_m.mastery_label if orig_m else "Hand-set initial prior"
            }
            authoritative_mastery = {
                "concept_id": t_plan.current_concept_id,
                "mastery_estimate": orig_m.mastery_estimate if orig_m else 0.0,
                "mastery_label": orig_m.mastery_label if orig_m else "Hand-set initial prior"
            }

    return {
        "device_id": device_id,
        "is_stale_reset_required": False,
        "applied_tombstones": applied_keys,
        "purge_instructions": purge_instructions,
        "synced_attempts_processed": processed_count,
        "synced_attempt_ids": synced_ids,
        "authoritative_mastery": authoritative_mastery,
        "authoritative_state": authoritative_state
    }


@app.get("/api/device/purge-instructions")
def get_device_purge_instructions(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    x_device_purge_token: Optional[str] = Header(None, alias="X-Device-Purge-Token"),
    db: Session = Depends(get_db)
):
    """
    FIX 1: Per-device purge-only credential path.
    Can ONLY fetch that device's pending purge instructions and acknowledge them.
    Cannot read student data, fetch packs, or submit attempts.
    """
    token = auth.credentials if auth else x_device_purge_token
    if not token:
        raise HTTPException(status_code=401, detail="X-Device-Purge-Token header required.")

    device = db.query(DeviceDB).filter(DeviceDB.device_purge_token == token).first()
    if not device:
        raise HTTPException(status_code=401, detail="Invalid device purge token.")

    pending_deliveries = db.query(TombstoneDeliveryDB).filter(
        TombstoneDeliveryDB.device_id == device.device_id,
        TombstoneDeliveryDB.status == "pending"
    ).all()

    now = datetime.utcnow()
    instructions = []
    for d in pending_deliveries:
        d.delivered_at = now
        instructions.append({
            "delivery_id": d.id,
            "tombstone_id": d.tombstone_id,
            "opaque_key": d.opaque_tombstone_key,
            "subject_key": d.subject_key
        })
    db.commit()

    return {
        "device_id": device.device_id,
        "pending_count": len(instructions),
        "purge_instructions": instructions
    }


@app.post("/api/device/purge-ack")
def acknowledge_purge(
    payload: Dict[str, Any] = Body(default_factory=dict),
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    x_device_purge_token: Optional[str] = Header(None, alias="X-Device-Purge-Token"),
    db: Session = Depends(get_db)
):
    """
    FIX 1: Device acknowledges that purge instruction for specific subject_key was applied.
    Updates delivery record to 'acknowledged' and decrements only that tombstone's pending count.
    """
    token = auth.credentials if auth else x_device_purge_token
    device = None
    if token:
        device = db.query(DeviceDB).filter(DeviceDB.device_purge_token == token).first()

    device_id = payload.get("device_id")
    if not device and device_id:
        dev_candidate = db.query(DeviceDB).filter(DeviceDB.device_id == device_id).first()
        if dev_candidate and (dev_candidate.device_purge_token == token or not dev_candidate.device_purge_token):
            device = dev_candidate

    if not device:
        raise HTTPException(status_code=401, detail="Valid purge token or registered device required.")

    delivery_ids = payload.get("delivery_ids") or []
    subject_keys = payload.get("subject_keys") or []
    if payload.get("delivery_id"):
        delivery_ids.append(payload.get("delivery_id"))
    if payload.get("subject_key"):
        subject_keys.append(payload.get("subject_key"))

    query = db.query(TombstoneDeliveryDB).filter(
        TombstoneDeliveryDB.device_id == device.device_id,
        TombstoneDeliveryDB.status == "pending"
    )
    if delivery_ids:
        query = query.filter(TombstoneDeliveryDB.id.in_(delivery_ids))
    elif subject_keys:
        query = query.filter(TombstoneDeliveryDB.subject_key.in_(subject_keys))

    matched_deliveries = query.all()
    now = datetime.utcnow()
    affected_tombstone_ids = set()

    for d in matched_deliveries:
        d.status = "acknowledged"
        d.acknowledged_at = now
        affected_tombstone_ids.add(d.tombstone_id)

    db.commit()

    # Re-evaluate pending count for affected tombstones
    for tid in affected_tombstone_ids:
        tombstone = db.query(TombstoneDB).filter(TombstoneDB.id == tid).first()
        if tombstone:
            remaining_pending = db.query(TombstoneDeliveryDB).filter(
                TombstoneDeliveryDB.tombstone_id == tid,
                TombstoneDeliveryDB.status == "pending"
            ).count()
            tombstone.pending_devices = remaining_pending
            if remaining_pending == 0:
                tombstone.status = "applied"
                tombstone.purged_at = now

    db.commit()
    return {
        "status": "purge_acknowledged",
        "device_id": device.device_id,
        "acknowledged_count": len(matched_deliveries)
    }


@app.get("/api/teacher/privacy-metrics")
def get_teacher_privacy_metrics(
    session: SessionDB = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    """
    FIX 1: Displays pending and acknowledged state of tombstones per device
    to the teacher in the Data and Privacy tab. Zero student ID or PII.
    """
    tombstones = db.query(TombstoneDB).order_by(TombstoneDB.id.desc()).all()
    deliveries = db.query(TombstoneDeliveryDB).order_by(TombstoneDeliveryDB.id.desc()).all()

    return {
        "retention_policy_days": 30,
        "tombstones": [
            {
                "id": t.id,
                "opaque_key": t.opaque_key,
                "status": t.status,
                "pending_devices": t.pending_devices,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "expires_at": t.expires_at.isoformat() if t.expires_at else None,
                "purged_at": t.purged_at.isoformat() if t.purged_at else None
            }
            for t in tombstones
        ],
        "deliveries": [
            {
                "id": d.id,
                "tombstone_id": d.tombstone_id,
                "opaque_key": d.opaque_tombstone_key,
                "device_id": d.device_id,
                "status": d.status,
                "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
                "acknowledged_at": d.acknowledged_at.isoformat() if d.acknowledged_at else None,
                "created_at": d.created_at.isoformat() if d.created_at else None
            }
            for d in deliveries
        ]
    }


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
    """
    Admin only: executes data retention policy (FIX 1).
    Purges tombstones and per-device deliveries older than 30 days or past expiration.
    Cleans up stale devices (>90 days inactive) so nothing stays pending forever.
    """
    now = datetime.utcnow()
    cutoff_30d = now - timedelta(days=30)
    cutoff_90d = now - timedelta(days=90)

    # Find expired tombstones
    expired_tombstones = db.query(TombstoneDB).filter(
        (TombstoneDB.created_at < cutoff_30d) |
        ((TombstoneDB.expires_at != None) & (TombstoneDB.expires_at < now))
    ).all()
    expired_tids = [t.id for t in expired_tombstones]

    purged_deliveries = 0
    if expired_tids:
        purged_deliveries = db.query(TombstoneDeliveryDB).filter(
            TombstoneDeliveryDB.tombstone_id.in_(expired_tids)
        ).delete(synchronize_session=False)
        db.query(TombstoneDB).filter(TombstoneDB.id.in_(expired_tids)).delete(synchronize_session=False)

    # Stale devices (>90 days without sync)
    purged_stale_devices = db.query(DeviceDB).filter(DeviceDB.last_sync_at < cutoff_90d).delete(synchronize_session=False)

    db.add(AuditEventDB(
        event_type="RETENTION_PURGE",
        actor=session.user_id or "admin",
        class_id="all",
        record_count=len(expired_tids),
        timestamp=now
    ))
    db.commit()

    return {
        "status": "success",
        "purged_tombstones": len(expired_tids),
        "purged_deliveries": purged_deliveries,
        "purged_stale_devices": purged_stale_devices,
        "cutoff": cutoff_30d.isoformat()
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
    Rule: Modifying an item strictly validates schema and resets its review status to 'author-drafted, unreviewed'.
    Invalid edits are rejected with HTTP 422 and the pack is not modified.
    """
    item_id = payload.get("id")
    if not item_id:
        raise HTTPException(status_code=400, detail="Item 'id' is required.")

    # Validation checks
    if "options" in payload:
        options = payload.get("options")
        if not isinstance(options, list) or len(options) < 2:
            raise HTTPException(status_code=422, detail="Validator error: question must contain at least 2 options.")
        
        correct_count = sum(1 for o in options if o.get("is_correct") is True)
        if correct_count != 1:
            raise HTTPException(status_code=422, detail="Validator error: question must contain exactly one correct option.")

        for opt in options:
            if not opt.get("id") or not opt.get("text"):
                raise HTTPException(status_code=422, detail="Validator error: option missing id or text.")
            if not opt.get("is_correct") and not opt.get("misconception_tag"):
                raise HTTPException(status_code=422, detail="Validator error: every wrong option must have a misconception_tag.")

    if not payload.get("question_text") and not payload.get("content"):
        raise HTTPException(status_code=422, detail="Validator error: item must contain question_text or content.")

    # Reset review status: Modifying an item ALWAYS resets review status to 'author-drafted, unreviewed'
    payload["review_record"] = {
        "status": "author-drafted, unreviewed",
        "reviewer_name": None,
        "attestation_statement": None,
        "reviewed_at": None
    }
    payload["review_status"] = "author-drafted, unreviewed"

    updated = False
    for i, q in enumerate(pack.questions):
        if q.id == item_id:
            from app.models.content import Question
            try:
                validated_q = Question.model_validate(payload)
                pack.questions[i] = validated_q
                updated = True
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"Validator error: {str(e)}")
            break

    if not updated:
        for i, l in enumerate(pack.lessons):
            if l.id == item_id:
                from app.models.content import Lesson
                try:
                    validated_l = Lesson.model_validate(payload)
                    pack.lessons[i] = validated_l
                    updated = True
                except Exception as e:
                    raise HTTPException(status_code=422, detail=f"Validator error: {str(e)}")
                break

    if not updated:
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found in pack.")

    with open(PACK_PATH, "w", encoding="utf-8") as f:
        f.write(pack.model_dump_json(indent=2))

    return {
        "status": "saved",
        "item_id": item_id,
        "review_status": "author-drafted, unreviewed",
        "details": "Item successfully updated. Review status reset to 'author-drafted, unreviewed'."
    }


@app.get("/api/paper/sheet/{concept_id}", response_class=HTMLResponse)
def get_printable_sheet(concept_id: str, session: SessionDB = Depends(require_teacher)):
    sheet = paper_manager.generate_printable_sheet(concept_id)
    return sheet.to_html()


# --- Demo deployment: serve the built frontend from the same origin ---
# Placed after all API routes so /api/* and /health keep precedence.
from fastapi.staticfiles import StaticFiles
FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

