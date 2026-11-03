import sys
import os
import json
import secrets
import pytest
from starlette.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app, pack
from app.db import (
    init_db, SessionLocal, StudentDB, PlanDB, MasteryStateDB, UserDB, DeviceDB,
    PinProfileDB, AttemptDB, DecisionDB, TestSessionDB, TestItemDB
)
from app.db.database import engine as default_engine
from app.auth.security import hash_password, hash_pin
from app.engine.test_engine import AdaptiveTestEngine


AID = secrets.token_hex(4)
SID = "stu_test_leg_01"
DEVICE = "dev_test_leg_tablet"
PIN = "4321"
TEACHER_A = ("tea_test_leg_a", "tea_pass_a_123")
TEACHER_B = ("tea_test_leg_b", "tea_pass_b_456")


@pytest.fixture
def client():
    init_db()
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_fixtures():
    init_db()
    db = SessionLocal()
    try:
        if not db.query(UserDB).filter(UserDB.username == TEACHER_A[0]).first():
            db.add(UserDB(id="usr_test_leg_a", username=TEACHER_A[0],
                          password_hash=hash_password(TEACHER_A[1]), role="teacher",
                          assigned_classes='["8-A"]'))
        if not db.query(UserDB).filter(UserDB.username == TEACHER_B[0]).first():
            db.add(UserDB(id="usr_test_leg_b", username=TEACHER_B[0],
                          password_hash=hash_password(TEACHER_B[1]), role="teacher",
                          assigned_classes='["8-B"]'))
        if not db.query(StudentDB).filter(StudentDB.pseudonymous_id == SID).first():
            salt = secrets.token_hex(8)
            db.add(StudentDB(
                pseudonymous_id=SID, subject_key="subj_test_leg_k1", class_id="8-A",
                board="CBSE", medium_language="en",
                pin_hash=hash_pin(PIN, salt), salt=salt, consent_status="not requested"
            ))
            db.add(PlanDB(student_id=SID, class_id="8-A", current_stage="solve",
                          current_concept_id="c8_math_linear_eq_one_var", reason="Practice sequence"))
            db.add(MasteryStateDB(student_id=SID, concept_id="c8_math_linear_eq_one_var",
                                  mastery_estimate=0.25))
            db.add(DeviceDB(device_id=DEVICE, class_id="8-A"))
            db.add(PinProfileDB(device_id=DEVICE, student_id=SID, class_id="8-A",
                                pin_hash=hash_pin(PIN, salt), salt=salt))
        # Clean prior test data for deterministic assertions
        for s in db.query(TestSessionDB).filter(TestSessionDB.student_id == SID).all():
            db.query(TestItemDB).filter(TestItemDB.session_id == s.id).delete(synchronize_session=False)
            db.delete(s)
        db.query(AttemptDB).filter(AttemptDB.student_id == SID).delete(synchronize_session=False)
        db.query(DecisionDB).filter(DecisionDB.student_id == SID).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def student_token(client):
    res = client.post("/api/auth/pin", json={"device_id": DEVICE, "student_id": SID, "pin": PIN})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def teacher_token(client, creds):
    res = client.post("/api/auth/login", json={"username": creds[0], "password": creds[1]})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def start_session(client, auth, length=4):
    res = client.post(f"/api/student/{SID}/test/start", json={"length": length}, headers=auth)
    assert res.status_code == 200, res.text
    return res.json()


def answer_current(client, auth, state, correct=True, attempt_id=None):
    q = state["current_item"]["question"]
    opt = next(o for o in q["options"] if (o["id"] and True))
    # Choose a correct or deliberately wrong option using the pack (server-side truth)
    full_q = pack.get_question(q["id"])
    target = next(o for o in full_q.options if o.is_correct == correct)
    body = {
        "session_id": state["session_id"],
        "question_id": q["id"],
        "selected_option_id": target.id,
    }
    if attempt_id:
        body["attempt_id"] = attempt_id
    res = client.post(f"/api/student/{SID}/test/answer", json=body, headers=auth)
    assert res.status_code == 200, res.text
    return res.json()


# ---------- Engine unit tests ----------

def test_engine_excludes_probes_and_reports_excluded_concepts():
    te = AdaptiveTestEngine(pack)
    eligible = te.eligible_concepts()
    assert "c8_math_linear_eq_one_var" in eligible
    # Graph-only / sparse concepts are reported, not hidden
    assert "c6_math_integers_add_sub" in te.excluded_concepts()
    # No probe question is ever an assessment item
    for qs in te.questions_by_concept.values():
        for q in qs:
            assert not q.probe_for_misconception


def test_engine_adapts_item_difficulty_to_mastery():
    te = AdaptiveTestEngine(pack)
    cid = "c8_math_linear_eq_one_var"
    _, q_low, _, _ = te.select_next([cid], {cid: 0.1}, {cid: 0}, set(), set(), "en")
    _, q_high, _, _ = te.select_next([cid], {cid: 0.9}, {cid: 0}, set(), set(), "en")
    assert q_low.difficulty < q_high.difficulty


def test_engine_coverage_first_rotation():
    te = AdaptiveTestEngine(pack)
    concepts = ["c8_math_linear_eq_one_var", "c8_math_squares_square_roots"]
    c1, q1, _, _ = te.select_next(concepts, {}, {}, set(), set(), "en")
    c2, q2, _, _ = te.select_next(concepts, {}, {c1: 1}, set(), {q1.id}, "en")
    assert c2 != c1  # fewest-served wins


def test_engine_english_students_never_get_drafts():
    te = AdaptiveTestEngine(pack)
    cid, q, _, fb = te.select_next(te.eligible_concepts(), {}, {}, set(), set(), "en")
    assert getattr(q, "language", "en") == "en"
    assert fb is False


def test_engine_summary_weakest_and_recommendation():
    te = AdaptiveTestEngine(pack)
    items = [
        {"concept_id": "c8_math_linear_eq_one_var", "is_correct": True, "misconception_tag": None},
        {"concept_id": "c8_math_linear_eq_one_var", "is_correct": True, "misconception_tag": None},
        {"concept_id": "c8_math_squares_square_roots", "is_correct": False, "misconception_tag": "sqrt_confusion"},
        {"concept_id": "c8_math_squares_square_roots", "is_correct": False, "misconception_tag": "sqrt_confusion"},
    ]
    s = te.summarize(
        ["c8_math_linear_eq_one_var", "c8_math_squares_square_roots"],
        {"c8_math_linear_eq_one_var": 0.25, "c8_math_squares_square_roots": 0.25},
        {"c8_math_linear_eq_one_var": 0.6, "c8_math_squares_square_roots": 0.1},
        items
    )
    assert s["total_served"] == 4 and s["total_correct"] == 2
    assert s["weakest_concept_id"] == "c8_math_squares_square_roots"
    assert "sqrt_confusion" in s["misconception_tags"]
    assert s["mastery_label"] == "uncalibrated, hand-set"
    assert "focused practice" in s["recommendation"]


# ---------- API integration tests ----------

def test_test_requires_student_auth(client):
    res = client.post(f"/api/student/{SID}/test/start", json={"length": 3})
    assert res.status_code in (401, 403)


def test_start_serves_sanitized_first_item(client):
    auth = student_token(client)
    state = start_session(client, auth, length=3)
    assert state["status"] == "in_progress"
    assert state["current_item"] is not None
    q = state["current_item"]["question"]
    for opt in q["options"]:
        assert "is_correct" not in opt
        assert "misconception_tag" not in opt
    assert state["resumed"] is False
    # Second start resumes rather than duplicating
    again = client.post(f"/api/student/{SID}/test/start", json={"length": 3}, headers=auth).json()
    assert again["resumed"] is True
    assert again["session_id"] == state["session_id"]


def test_full_session_persists_real_events_and_routes_plan(client):
    auth = student_token(client)
    state = start_session(client, auth, length=3)

    # Answer: correct, wrong, correct
    r1 = answer_current(client, auth, state, correct=True, attempt_id=f"{AID}-t1")
    assert r1["server_graded_correct"] is True
    assert r1["completed"] is False
    next_q = r1["session"]["current_item"]["question"]

    state2 = r1["session"]
    r2 = answer_current(client, auth, state2, correct=False, attempt_id=f"{AID}-t2")
    assert r2["server_graded_correct"] is False
    assert r2["authoritative_misconception"] is not None

    state3 = r2["session"]
    r3 = answer_current(client, auth, state3, correct=True, attempt_id=f"{AID}-t3")
    assert r3["completed"] is True
    summary = r3["summary"]
    assert summary["total_served"] == 3
    assert summary["total_correct"] == 2
    assert summary["weakest_concept_id"] is not None

    db = SessionLocal()
    try:
        # Attempts persisted
        attempts = db.query(AttemptDB).filter(AttemptDB.student_id == SID).all()
        assert len(attempts) >= 3
        # Decisions persisted with test-stage entries
        decisions = db.query(DecisionDB).filter(
            DecisionDB.student_id == SID, DecisionDB.stage == "test"
        ).all()
        assert any(d.action == "ADAPTIVE_TEST_START" for d in decisions)
        assert any(d.action == "ADAPTIVE_TEST_ITEM" for d in decisions)
        assert any(d.action == "ADAPTIVE_TEST_COMPLETE" for d in decisions)
        # Plan routed to weakest concept in SOLVE stage
        plan = db.query(PlanDB).filter(PlanDB.student_id == SID).first()
        assert plan.current_concept_id == summary["weakest_concept_id"]
        assert plan.current_stage == "solve"
        assert any(d.action == "ROUTE_AFTER_TEST" for d in
                   db.query(DecisionDB).filter(DecisionDB.student_id == SID).all())
        # Session persisted with summary
        s_db = db.query(TestSessionDB).filter(TestSessionDB.id == state["session_id"]).first()
        assert s_db.status == "completed"
        assert json.loads(s_db.summary_json)["total_correct"] == 2
    finally:
        db.close()

    # Post-test: next-step now serves the routed weakest concept
    step = client.get(f"/api/student/{SID}/next-step", headers=auth)
    assert step.status_code == 200
    assert step.json()["step"]["target_concept_id"] == summary["weakest_concept_id"]


def test_adaptive_difficulty_direction_live(client):
    auth = student_token(client)
    state = start_session(client, auth, length=6)
    first_concept = state["current_item"]["concept_id"]
    first_diff = None
    # Answer correctly repeatedly: when the same concept returns, served difficulty must not decrease
    seen = []
    current = state
    for i in range(5):
        item = current["current_item"]
        seen.append((item["concept_id"], item["question"]["id"]))
        r = answer_current(client, auth, current, correct=True, attempt_id=f"{AID}-dir{i}")
        if r.get("completed"):
            break
        current = r["session"]
    db = SessionLocal()
    try:
        items = db.query(TestItemDB).filter(
            TestItemDB.session_id == state["session_id"]
        ).order_by(TestItemDB.sequence.asc()).all()
        by_concept = {}
        for it in items:
            by_concept.setdefault(it.concept_id, []).append(it.served_difficulty)
        for cid, diffs in by_concept.items():
            assert diffs == sorted(diffs), f"difficulty should not decrease after correct answers in {cid}: {diffs}"
    finally:
        db.close()


def test_idempotent_retry_and_conflict(client):
    auth = student_token(client)
    state = start_session(client, auth, length=3)
    q = state["current_item"]["question"]
    full_q = pack.get_question(q["id"])
    correct_opt = next(o for o in full_q.options if o.is_correct)

    r1 = answer_current(client, auth, state, correct=True, attempt_id=f"{AID}-idem")
    # Identical retry: same result, no double-processing
    retry = client.post(f"/api/student/{SID}/test/answer", json={
        "session_id": state["session_id"], "question_id": q["id"],
        "selected_option_id": correct_opt.id, "attempt_id": f"{AID}-idem"
    }, headers=auth)
    assert retry.status_code == 200
    assert retry.json().get("idempotent_replay") is True

    db = SessionLocal()
    try:
        assert db.query(AttemptDB).filter(AttemptDB.id == f"{SID}:{AID}-idem").count() == 1
    finally:
        db.close()

    # Same id, different payload -> 409
    wrong_opt = next(o for o in full_q.options if not o.is_correct)
    conflict = client.post(f"/api/student/{SID}/test/answer", json={
        "session_id": state["session_id"], "question_id": q["id"],
        "selected_option_id": wrong_opt.id, "attempt_id": f"{AID}-idem"
    }, headers=auth)
    assert conflict.status_code == 409


def test_out_of_sequence_rejected(client):
    auth = student_token(client)
    state = start_session(client, auth, length=3)
    other_q = next(q for q in pack.questions
                   if not q.probe_for_misconception and q.id != state["current_item"]["question"]["id"])
    res = client.post(f"/api/student/{SID}/test/answer", json={
        "session_id": state["session_id"], "question_id": other_q.id,
        "selected_option_id": other_q.options[0].id, "attempt_id": "oos1"
    }, headers=auth)
    assert res.status_code == 400


def test_resume_active_session(client):
    auth = student_token(client)
    state = start_session(client, auth, length=4)
    res = client.get(f"/api/student/{SID}/test/active", headers=auth)
    assert res.status_code == 200
    assert res.json()["active"]["session_id"] == state["session_id"]
    # Cross-student access denied
    other = client.get("/api/student/stu_api_demo_01/test/active", headers=auth)
    assert other.status_code in (401, 403)


def test_teacher_class_scoping(client):
    auth = student_token(client)
    state = start_session(client, auth, length=2)
    answer_current(client, auth, state, correct=True, attempt_id=f"{AID}-sc1")
    r2 = answer_current(client, auth, client.get(f"/api/student/{SID}/test/active", headers=auth).json()["active"],
                        correct=False, attempt_id=f"{AID}-sc2")
    assert r2["completed"] is True

    ta = teacher_token(client, TEACHER_A)
    res = client.get("/api/teacher/class/8-A/tests", headers=ta)
    assert res.status_code == 200
    sessions = res.json()["test_sessions"]
    assert any(s["session_id"] == state["session_id"] and s["correct_count"] == 1 for s in sessions)

    tb = teacher_token(client, TEACHER_B)
    forbidden = client.get("/api/teacher/class/8-A/tests", headers=tb)
    assert forbidden.status_code == 403


def test_spaced_review_schedule_is_durable(client):
    auth = student_token(client)
    state = start_session(client, auth, length=2)
    answer_current(client, auth, state, correct=True, attempt_id=f"{AID}-sr1")
    r = answer_current(client, auth, client.get(f"/api/student/{SID}/test/active", headers=auth).json()["active"],
                       correct=True, attempt_id=f"{AID}-sr2")
    assert r["completed"] is True
    db = SessionLocal()
    try:
        cid = r["summary"]["per_concept"][0]["concept_id"]
        m = db.query(MasteryStateDB).filter(
            MasteryStateDB.student_id == SID, MasteryStateDB.concept_id == cid
        ).first()
        assert m.next_review is not None, "next_review must persist after test completion"
        assert m.last_seen is not None
        assert m.interval_days > 0
        # Reload through the loader to prove the value round-trips
        from app.main import load_or_create_mastery_state
        loaded = load_or_create_mastery_state(db, SID, cid)
        assert loaded.next_review is not None
    finally:
        db.close()


def test_additive_schema_is_idempotent_on_existing_db(tmp_path):
    """Simulates an existing deployment database: init_db twice, old rows survive, new tables appear."""
    from sqlalchemy import create_engine, text
    from app.db import init_db as run_init
    from app.db.database import Base

    db_file = tmp_path / "existing.db"
    eng = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    run_init(target_engine=eng)
    with eng.connect() as conn:
        conn.execute(text(
            "INSERT INTO mastery_states (student_id, concept_id, mastery_estimate) VALUES ('s1','c1',0.5)"
        ))
        conn.commit()
    # Second startup on the same file (idempotent, non-destructive)
    run_init(target_engine=eng)
    with eng.connect() as conn:
        row = conn.execute(text("SELECT mastery_estimate FROM mastery_states WHERE student_id='s1'")).fetchone()
        assert row and abs(row[0] - 0.5) < 1e-9
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(test_sessions)")).fetchall()]
        assert "summary_json" in cols
        cols_items = [r[1] for r in conn.execute(text("PRAGMA table_info(test_items)")).fetchall()]
        assert "served_reason" in cols_items
