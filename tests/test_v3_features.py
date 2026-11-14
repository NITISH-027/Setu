"""
Round 3 v3 features:
1. Teacher overrides feed back into the model (human-in-the-loop mastery feedback).
2. One-screen 'who needs help now' attention summary.
3. Misconception explainers served with graded attempts (en + ta fallback).
4. Tamil/low-data robustness: explainer fallback is honest (is_fallback label).
"""
import sys
import os
import secrets

import pytest
from starlette.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app
from app.db import init_db, SessionLocal, UserDB, StudentDB, PlanDB, MasteryStateDB
from app.auth.security import hash_password, hash_pin
from app.misconception_explainers import get_explainer

TEACHER = ("tea_v3_01", "tea_pass_v3_123")
SID = "stu_v3_01"
CONCEPT = "c8_math_linear_eq_one_var"


@pytest.fixture
def client():
    init_db()
    return TestClient(app)


@pytest.fixture(autouse=True)
def fixtures():
    init_db()
    db = SessionLocal()
    try:
        if not db.query(UserDB).filter(UserDB.username == TEACHER[0]).first():
            db.add(UserDB(
                id="usr_tea_v3_01",
                username=TEACHER[0],
                password_hash=hash_password(TEACHER[1]),
                role="teacher",
                assigned_classes='["8-A"]',
            ))
        # idempotent student reset
        for model, col in [(MasteryStateDB, "student_id"), (PlanDB, "student_id")]:
            db.query(model).filter(getattr(model, col) == SID).delete()
        db.query(StudentDB).filter(StudentDB.pseudonymous_id == SID).delete()
        salt = secrets.token_hex(8)
        db.add(StudentDB(
            pseudonymous_id=SID, subject_key="subj_v3_01", class_id="8-A",
            board="CBSE", medium_language="en",
            pin_hash=hash_pin("1234", salt), salt=salt,
        ))
        db.add(PlanDB(student_id=SID, class_id="8-A", current_stage="solve",
                      current_concept_id=CONCEPT, reason="Practice sequence"))
        db.add(MasteryStateDB(student_id=SID, concept_id=CONCEPT, mastery_estimate=0.25))
        db.commit()
    finally:
        db.close()


def _teacher_token(client):
    res = client.post("/api/auth/login", json={"username": TEACHER[0], "password": TEACHER[1]})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_override_mark_cleared_raises_starting_estimate(client):
    header = _teacher_token(client)
    res = client.post("/api/teacher/override", json={
        "class_id": "8-A", "student_id": SID, "concept_id": CONCEPT,
        "action": "mark_cleared", "reason": "Clinic done, gap closed in class"
    }, headers=header)
    assert res.status_code == 200, res.text
    fb = res.json()["mastery_feedback"]
    assert fb is not None
    assert fb["before"] == 0.25
    assert fb["after"] == 0.70
    assert fb["label"] == "teacher-adjusted, hand-set"


def test_override_reinforce_lowers_starting_estimate(client):
    header = _teacher_token(client)
    res = client.post("/api/teacher/override", json={
        "class_id": "8-A", "student_id": SID, "concept_id": CONCEPT,
        "action": "reinforce", "reason": "Needs another week on this"
    }, headers=header)
    assert res.status_code == 200, res.text
    fb = res.json()["mastery_feedback"]
    assert fb["after"] == 0.25  # min(0.25, 0.30) = stays 0.25
    assert fb["label"] == "teacher-adjusted, hand-set"


def test_attention_summary_lists_only_needy_students(client):
    header = _teacher_token(client)
    # make SID flagged
    db = SessionLocal()
    plan = db.query(PlanDB).filter(PlanDB.student_id == SID).first()
    plan.current_stage = "flag"
    db.commit()
    db.close()

    res = client.get("/api/teacher/class/8-A/attention-summary", headers=header)
    assert res.status_code == 200, res.text
    data = res.json()
    ids = [s["student_id"] for s in data["students_needing_attention"]]
    assert SID in ids
    entry = [s for s in data["students_needing_attention"] if s["student_id"] == SID][0]
    assert entry["urgency"] == 3
    assert any("clinic" in r.lower() for r in entry["reasons"])
    assert data["note"].startswith("Rule-based")


def test_attention_summary_requires_teacher(client):
    res = client.get("/api/teacher/class/8-A/attention-summary")
    assert res.status_code == 401


def test_explainer_content_english_and_tamil_fallback():
    ex = get_explainer("tag_sign_error_on_transposition", "en")
    assert ex and ex["language"] == "en" and ex["is_fallback"] is False
    ex_ta = get_explainer("tag_sign_error_on_transposition", "ta")
    assert ex_ta and ex_ta["language"] == "ta" and ex_ta["is_fallback"] is False
    assert "DRAFT" in ex_ta["review_status"] or "DRAFT" in ex_ta["text"]
    # tag without Tamil entry: honest English fallback
    ex_fb = get_explainer("tag_grouping_variables_wrong_sign", "ta")
    assert ex_fb["language"] == "en" and ex_fb["is_fallback"] is True
    # unknown tag: nothing invented
    assert get_explainer("tag_does_not_exist", "en") is None
