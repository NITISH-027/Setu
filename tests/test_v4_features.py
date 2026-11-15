"""
Round 3 v4 features:
1. Teacher overrides refine the STARTING estimate for the next student on that
   concept (Beta-style shrinkage, hand-set targets) - visible via the
   'learned from N overrides' counter in the attention summary.
2. Attention summary carries a per-student 'why' evidence line.
3. /api/demo/footprint reports measured byte sizes honestly.
"""
import sys
import os
import secrets
from datetime import datetime

import pytest
from starlette.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app, load_or_create_mastery_state
from app.db import init_db, SessionLocal, UserDB, StudentDB, PlanDB, MasteryStateDB
from app.db.models import TeacherOverrideDB
from app.auth.security import hash_password, hash_pin
from app.override_learning import refined_prior, override_stats, BASE_PRIOR, PRIOR_STRENGTH, OVERRIDE_TARGETS

TEACHER = ("tea_v4_01", "tea_pass_v4_123")
SID = "stu_v4_01"
CONCEPT = "c7_math_equivalent_fractions"


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
                id="usr_tea_v4_01",
                username=TEACHER[0],
                password_hash=hash_password(TEACHER[1]),
                role="teacher",
                assigned_classes='["8-A"]',
            ))
        db.query(TeacherOverrideDB).filter(TeacherOverrideDB.concept_id == CONCEPT).delete()
        db.query(MasteryStateDB).filter(MasteryStateDB.student_id == SID).delete()
        db.query(PlanDB).filter(PlanDB.student_id == SID).delete()
        db.query(StudentDB).filter(StudentDB.pseudonymous_id == SID).delete()
        salt = secrets.token_hex(8)
        db.add(StudentDB(
            pseudonymous_id=SID, subject_key="subj_v4_01", class_id="8-A",
            board="CBSE", medium_language="ta",
            pin_hash=hash_pin("1234", salt), salt=salt,
        ))
        db.add(PlanDB(student_id=SID, class_id="8-A", current_stage="solve",
                      current_concept_id=CONCEPT, reason="Practice sequence",
                      stuck_attempts_count=3))
        db.commit()
        yield
    finally:
        db.query(TeacherOverrideDB).filter(TeacherOverrideDB.concept_id == CONCEPT).delete()
        db.query(MasteryStateDB).filter(MasteryStateDB.student_id == SID).delete()
        db.query(PlanDB).filter(PlanDB.student_id == SID).delete()
        db.query(StudentDB).filter(StudentDB.pseudonymous_id == SID).delete()
        db.commit()
        db.close()


def _teacher_token(client):
    res = client.post("/api/auth/login", json={"username": TEACHER[0], "password": TEACHER[1]})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _add_override(db, action, concept=CONCEPT):
    db.add(TeacherOverrideDB(
        student_id=SID, teacher_id="usr_tea_v4_01", class_id="8-A",
        concept_id=concept, override_action=action,
        reason="test override", timestamp=datetime.utcnow(),
    ))
    db.commit()


def test_refined_prior_shrinkage_math():
    """One mark_cleared: (4*0.2 + 0.7)/5 = 0.30; many converge toward 0.70."""
    init_db()
    db = SessionLocal()
    try:
        assert refined_prior(db, "concept_with_no_overrides_xyz") is None
        _add_override(db, "mark_cleared")
        prior, n = refined_prior(db, CONCEPT)
        assert n == 1
        assert prior == round((PRIOR_STRENGTH * BASE_PRIOR + OVERRIDE_TARGETS["mark_cleared"]) / (PRIOR_STRENGTH + 1), 4)
        for _ in range(9):
            _add_override(db, "mark_cleared")
        prior2, n2 = refined_prior(db, CONCEPT)
        assert n2 == 10
        assert prior2 > prior  # converges toward the target
        assert prior2 < OVERRIDE_TARGETS["mark_cleared"]  # shrinkage caps below target
    finally:
        db.close()


def test_new_mastery_row_uses_refined_prior_and_label():
    """The next student on an overridden concept starts at the refined estimate."""
    init_db()
    db = SessionLocal()
    try:
        _add_override(db, "mark_cleared")
        st = load_or_create_mastery_state(db, SID, CONCEPT)
        assert st.mastery_estimate == refined_prior(db, CONCEPT)[0]
        assert "refined from 1 teacher overrides" in st.bkt_params.label
        # existing rows are NOT retroactively changed
        again = load_or_create_mastery_state(db, SID, CONCEPT)
        assert again.mastery_estimate == st.mastery_estimate
    finally:
        db.close()


def test_attention_summary_has_evidence_line_and_override_counter(client):
    headers = _teacher_token(client)
    _add_override(SessionLocal(), "reinforce")
    res = client.get("/api/teacher/class/8-A/attention-summary", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "override_learning" in data
    assert data["override_learning"]["total_overrides"] >= 1
    assert CONCEPT in data["override_learning"]["refined_concepts"]
    # the fixture student is stuck (3 attempts) so must appear with a why line
    entry = next((s for s in data["students_needing_attention"] if s["student_id"] == SID), None)
    assert entry is not None, data
    assert entry["evidence_line"].startswith("Recent:")
    assert "not a diagnosis" in entry["evidence_line"]


def test_footprint_endpoint_is_honest(client):
    res = client.get("/api/demo/footprint")
    assert res.status_code == 200, res.text
    data = res.json()
    assert "measured" in data and "label" in data
    if data["measured"]:
        assert data["js_bytes"] > 0
        assert "MEASURED" in data["label"]
    else:
        assert "MEASURE" in data["label"]
    assert data["pack_bytes"] is None or data["pack_bytes"] > 10000


def test_override_stats_scoped_to_class():
    init_db()
    db = SessionLocal()
    try:
        _add_override(db, "assign_concept")
        stats = override_stats(db, "8-A")
        assert stats["per_concept"].get(CONCEPT, 0) >= 1
        stats_none = override_stats(db, "class-that-does-not-exist")
        assert stats_none["total_overrides"] == 0
    finally:
        db.close()
