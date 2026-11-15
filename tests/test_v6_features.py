"""
Round 3 v6 features:
1. Chain probing: a passed probe clears ONE prerequisite; the engine walks the
   rest of the prerequisite chain before returning to practice.
2. Draft review workflow: reviewer approves/rejects teacher drafts; only
   reviewed items are served to students.
3. /health exists for keep-warm pings.
"""
import sys
import os
import random

import pytest
from starlette.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app, pack
from app.db import init_db, SessionLocal, UserDB
from app.auth.security import hash_password
from app.authoring import AuthoredQuestionDB
from app.models.pack import ContentPack
from app.models.student import Student
from app.models.learning import Plan, MasteryState, Attempt
from app.engine.adaptive_engine import AdaptiveEngine
from app.simulation.learner_simulator import SyntheticLearnerProfile

TEACHER = ("tea_v6_01", "tea_pass_v6_123")
REVIEWER = ("rev_v6_01", "rev_pass_v6_123")

VALID_Q = {
    "concept": "c8_math_linear_eq_one_var",
    "language": "en",
    "question_text": "Solve for x: 2x = 14",
    "options": [
        {"text": "7", "is_correct": True},
        {"text": "12", "is_correct": False, "misconception_tag": "tag_sign_error_on_transposition"},
        {"text": "16", "is_correct": False, "misconception_tag": "tag_dividing_instead_of_subtracting"},
        {"text": "28", "is_correct": False, "misconception_tag": "tag_grouping_variables_wrong_sign"},
    ],
}


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
            db.add(UserDB(id="usr_tea_v6_01", username=TEACHER[0],
                          password_hash=hash_password(TEACHER[1]), role="teacher",
                          assigned_classes='["8-A"]'))
        if not db.query(UserDB).filter(UserDB.username == REVIEWER[0]).first():
            db.add(UserDB(id="usr_rev_v6_01", username=REVIEWER[0],
                          password_hash=hash_password(REVIEWER[1]), role="reviewer",
                          assigned_classes='[]'))
        db.commit()
        yield
    finally:
        rows = db.query(AuthoredQuestionDB).filter(AuthoredQuestionDB.created_by == "usr_tea_v6_01").all()
        ids = [r.id for r in rows]
        for r in rows:
            db.delete(r)
        db.commit()
        pack.questions[:] = [q for q in pack.questions if q.id not in ids]
        db.close()


def _login(client, creds):
    res = client.post("/api/auth/login", json={"username": creds[0], "password": creds[1]})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_chain_probing_walks_prerequisites_after_passed_probe():
    """Unit-level: passing the first probe must not end gap-finding when more
    of the chain is unprobed. Drive deterministically: wrong on the topic,
    PASS the c7 probe, then the engine must continue the chain to c6 - where
    we FAIL, confirming the deeper gap."""
    engine = AdaptiveEngine(pack)
    student = Student(pseudonymous_id="syn_chain", class_id="8-A", pin_hash="h")
    plan = Plan(student_id="syn_chain", class_id="8-A", current_concept_id="c8_math_linear_eq_one_var")
    mastery = MasteryState(student_id="syn_chain", concept_id="c8_math_linear_eq_one_var")
    hyp = None

    def answer(nxt, correct):
        nonlocal plan, mastery, hyp
        q = nxt.item
        opt = next(o for o in q.options if o.is_correct == correct and (correct or o.misconception_tag))
        plan, mastery, hyp, _ = engine.process_attempt(
            student, plan,
            Attempt(student_id="syn_chain", question_id=q.id, concept_id=q.concept,
                    selected_option_id=opt.id, is_correct=correct,
                    misconception_tag=None if correct else opt.misconception_tag),
            mastery, hyp)

    # 1. wrong on the topic question -> hypothesis opens, probe administered
    nxt = engine.get_next_step(student, plan, mastery, hyp)
    answer(nxt, correct=False)
    # 2. PASS the c7 probe -> chain must NOT stop here
    nxt = engine.get_next_step(student, plan, mastery, hyp)
    assert nxt.stage.value == "probe"
    assert nxt.item.concept == "c7_math_simple_eq"
    answer(nxt, correct=True)
    assert "c7_math_simple_eq" in plan.chain_probed
    # 3. engine continues the chain to c6 integers instead of returning to SOLVE
    nxt = engine.get_next_step(student, plan, mastery, hyp)
    assert nxt.stage.value == "probe", nxt.reason
    assert nxt.item.concept == "c6_math_integers_add_sub", nxt.item.id
    # 4. FAIL the c6 probe -> two-probe confirmation: fail the second probe too
    answer(nxt, correct=False)
    nxt = engine.get_next_step(student, plan, mastery, hyp)
    assert nxt.stage.value == "probe"
    assert nxt.item.concept == "c6_math_integers_add_sub"
    answer(nxt, correct=False)
    assert plan.gap_concept_id == "c6_math_integers_add_sub"


def test_review_workflow_approve_makes_live(client):
    th = _login(client, TEACHER)
    rh = _login(client, REVIEWER)
    qid = client.post("/api/teacher/authoring/questions", json=VALID_Q, headers=th).json()["id"]
    assert pack.get_question(qid) is None  # draft, not live

    # teacher cannot approve their own draft
    res_forbidden = client.post(f"/api/review/drafts/{qid}/approve",
                                json={"reviewer_name": "x", "attestation": "I checked this item"}, headers=th)
    assert res_forbidden.status_code == 403

    # reviewer lists it, approves with attestation
    drafts = client.get("/api/review/drafts", headers=rh).json()["drafts"]
    entry = next(d for d in drafts if d["id"] == qid)
    assert entry["review_status"] == "author-drafted, unreviewed"
    assert entry["live"] is False
    res = client.post(f"/api/review/drafts/{qid}/approve",
                      json={"reviewer_name": "Sunita (demo)", "attestation": "I checked this item"}, headers=rh)
    assert res.status_code == 200, res.text
    assert res.json()["live"] is True
    q = pack.get_question(qid)
    assert q is not None
    assert q.review_record.status.value == "reviewed"
    assert q.review_record.reviewer_name == "Sunita (demo)"
    assert q.review_record.is_human_reviewed()

    # approve requires attestation
    qid2 = client.post("/api/teacher/authoring/questions", json=VALID_Q, headers=th).json()["id"]
    res_no_att = client.post(f"/api/review/drafts/{qid2}/approve",
                             json={"reviewer_name": "Sunita"}, headers=rh)
    assert res_no_att.status_code == 400


def test_review_workflow_reject_keeps_out_and_edit_resubmits(client):
    th = _login(client, TEACHER)
    rh = _login(client, REVIEWER)
    qid = client.post("/api/teacher/authoring/questions", json=VALID_Q, headers=th).json()["id"]
    res = client.post(f"/api/review/drafts/{qid}/reject",
                      json={"reviewer_name": "Sunita (demo)", "reason": "Option 3 tag does not match the error"}, headers=rh)
    assert res.status_code == 200, res.text
    assert res.json()["review_status"] == "flagged"
    assert res.json()["live"] is False
    assert pack.get_question(qid) is None

    # teacher edits -> back to unreviewed draft
    edited = dict(VALID_Q, question_text="Solve for x: 2x = 16")
    res2 = client.put(f"/api/teacher/authoring/questions/{qid}", json=edited, headers=th)
    assert res2.status_code == 200
    drafts = client.get("/api/review/drafts", headers=rh).json()["drafts"]
    entry = next(d for d in drafts if d["id"] == qid)
    assert entry["review_status"] == "author-drafted, unreviewed"


def test_health_endpoint_for_keepwarm(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_demo_mode_seeds_teacher_and_reviewer():
    """One-tap demo teacher/reviewer entries must work on a fresh demo DB."""
    import app.main as main_mod
    main_mod.DEMO_MODE = True  # flag is read at import time in production; force for the test
    from app.main import ensure_demo_users
    from app.db import SessionLocal
    from app.db.models import UserDB
    ensure_demo_users()
    db = SessionLocal()
    try:
        roles = {u.username: u.role for u in db.query(UserDB).all()}
        assert roles.get("demo_teacher") == "teacher"
        assert roles.get("demo_reviewer") == "reviewer"
    finally:
        db.close()
