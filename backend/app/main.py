"""
Setu Adaptive Learning System - FastAPI Backend.
Pure-Python core. No GPU. No external runtime AI calls.
"""

import os
import json
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Depends, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.models.pack import ContentPack
from app.models.student import Student, ConsentStatus
from app.models.learning import Attempt, Plan, MasteryState, StageEnum
from app.engine.adaptive_engine import AdaptiveEngine
from app.teacher.teacher_service import TeacherService
from app.privacy.data_protection_manager import DataProtectionManager
from app.auth.pin_manager import PinManager
from app.paper_mode.paper_mode_generator import PaperModeManager
from app.validator.coverage_reporter import CoverageReporter
from app.validator.review_manager import ReviewManager

app = FastAPI(
    title="Setu Adaptive Learning API",
    description="Teacher-controlled adaptive learning system inside an authored concept graph.",
    version="1.0.0"
)

# Enable CORS for frontend PWA
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize application components
pack_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "packs", "cbse_math_pack.json"))
if os.path.exists(pack_path):
    with open(pack_path, "r", encoding="utf-8") as f:
        pack = ContentPack.model_validate(json.load(f))
else:
    from app.pack_builder import build_pack
    pack = build_pack()

engine = AdaptiveEngine(pack)
teacher_service = TeacherService()
privacy_manager = DataProtectionManager()
pin_manager = PinManager()
paper_manager = PaperModeManager(pack, engine)
coverage_reporter = CoverageReporter()
review_manager = ReviewManager()

# In-memory stores for active session demonstration
# In production, backed by SQLite / PostgreSQL
active_students: Dict[str, Student] = {}
active_plans: Dict[str, Plan] = {}
active_masteries: Dict[str, MasteryState] = {}
active_hypotheses: Dict[str, Any] = {}

# Seed initial synthetic demo students
def seed_demo_students():
    # Synthetic student 1: Class 8-A, struggling with linear equation transposition
    s1 = Student(pseudonymous_id="stu_demo_01", class_id="8-A", pin_hash="hash")
    active_students[s1.pseudonymous_id] = s1
    active_plans[s1.pseudonymous_id] = Plan(
        student_id=s1.pseudonymous_id,
        class_id="8-A",
        current_concept_id="c8_math_linear_eq_one_var"
    )
    active_masteries[s1.pseudonymous_id] = MasteryState(
        student_id=s1.pseudonymous_id,
        concept_id="c8_math_linear_eq_one_var",
        mastery_estimate=0.25
    )
    privacy_manager.add_student(s1, active_plans[s1.pseudonymous_id])
    privacy_manager.register_device("8-A", "dev_demo_tablet")
    pin_manager.register_student_profile("dev_demo_tablet", s1.pseudonymous_id, "8-A", "1234")

seed_demo_students()


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": "Setu Adaptive Learning",
        "version": "1.0.0",
        "honesty_notice": "Uncalibrated models, synthetic demo data, intended NCERT alignment unverified until reviewed"
    }


@app.get("/api/pack")
def get_shipped_pack():
    return pack.model_dump()


@app.get("/api/coverage")
def get_coverage_report():
    report = coverage_reporter.generate_report(pack)
    return report.to_dict()


@app.post("/api/auth/pin")
def verify_pin(payload: Dict[str, str] = Body(...)):
    device_id = payload.get("device_id", "dev_demo_tablet")
    student_id = payload.get("student_id")
    candidate_pin = payload.get("pin")

    if not student_id or not candidate_pin:
        raise HTTPException(status_code=400, detail="student_id and pin are required.")

    success, message = pin_manager.authenticate_sibling(device_id, student_id, candidate_pin)
    if not success:
        raise HTTPException(status_code=401, detail=message)

    return {"authenticated": True, "message": message, "student_id": student_id}


@app.get("/api/student/{student_id}/next-step")
def get_student_next_step(student_id: str):
    student = active_students.get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    plan = active_plans.get(student_id)
    mastery = active_masteries.get(student_id)
    hyp = active_hypotheses.get(student_id)

    step = engine.get_next_step(student, plan, mastery, hyp)
    ladder = engine.get_hint_ladder(step.item.id) if (step.item and hasattr(step.item, "id")) else None

    return {
        "step": step.to_dict(),
        "item": step.item.model_dump() if (step.item and hasattr(step.item, "model_dump")) else None,
        "hint_ladder": ladder.model_dump() if ladder else None
    }


@app.post("/api/student/{student_id}/attempt")
def submit_attempt(student_id: str, payload: Dict[str, Any] = Body(...)):
    student = active_students.get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    plan = active_plans.get(student_id)
    mastery = active_masteries.get(student_id)
    hyp = active_hypotheses.get(student_id)

    attempt = Attempt(
        student_id=student_id,
        question_id=payload["question_id"],
        concept_id=payload["concept_id"],
        selected_option_id=payload["selected_option_id"],
        is_correct=payload["is_correct"],
        misconception_tag=payload.get("misconception_tag")
    )

    plan, mastery, hyp, decision = engine.process_attempt(student, plan, attempt, mastery, hyp)
    active_plans[student_id] = plan
    active_masteries[student_id] = mastery
    active_hypotheses[student_id] = hyp

    return {
        "decision": decision.to_dict(),
        "updated_mastery": mastery.mastery_estimate,
        "mastery_label": mastery.mastery_label,
        "hypothesis": hyp.model_dump() if hyp else None
    }


@app.get("/api/teacher/class/{class_id}")
def get_teacher_class_dashboard(class_id: str, teacher_id: str = Query(default="tea_01")):
    try:
        # Gather students in this class
        class_students_data = []
        for sid, stu in active_students.items():
            if stu.class_id == class_id:
                class_students_data.append({
                    "student_id": sid,
                    "plan": active_plans[sid],
                    "mastery": active_masteries[sid],
                    "hypothesis": active_hypotheses.get(sid)
                })

        dashboard = teacher_service.get_class_dashboard(teacher_id, class_id, class_students_data)
        return dashboard.model_dump()
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.post("/api/teacher/override")
def apply_teacher_override(payload: Dict[str, Any] = Body(...)):
    teacher_id = payload.get("teacher_id", "tea_01")
    class_id = payload.get("class_id", "8-A")
    student_id = payload.get("student_id")
    concept_id = payload.get("concept_id")
    action = payload.get("action")
    reason = payload.get("reason")

    if not reason or not reason.strip():
        raise HTTPException(status_code=400, detail="Teacher override reason is mandatory.")

    plan = active_plans.get(student_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Student plan not found.")

    try:
        updated_plan, override = teacher_service.apply_override(
            teacher_id, class_id, student_id, concept_id, action, reason, plan
        )
        active_plans[student_id] = updated_plan
        return {"override": override.model_dump(), "plan": updated_plan.model_dump()}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.post("/api/privacy/delete-student")
def delete_student(payload: Dict[str, str] = Body(...)):
    student_id = payload.get("student_id")
    actor = payload.get("actor", "teacher")

    if not student_id:
        raise HTTPException(status_code=400, detail="student_id is required.")

    # Remove from active local stores
    active_students.pop(student_id, None)
    active_plans.pop(student_id, None)
    active_masteries.pop(student_id, None)
    active_hypotheses.pop(student_id, None)

    report = privacy_manager.delete_student(student_id, actor=actor)
    return report.to_dict()


@app.post("/api/privacy/sync")
def sync_device(payload: Dict[str, Any] = Body(...)):
    device_id = payload.get("device_id")
    class_id = payload.get("class_id", "8-A")
    queued_attempts = payload.get("queued_attempts", [])

    result = privacy_manager.sync_device(device_id, class_id, queued_attempts)
    return result


@app.get("/api/paper/sheet/{concept_id}", response_class=HTMLResponse)
def get_printable_sheet(concept_id: str):
    sheet = paper_manager.generate_printable_sheet(concept_id)
    return sheet.to_html()
