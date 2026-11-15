"""
Round 3 v5 features:
1. Teacher authoring: validated add/edit of questions without code, draft-only.
2. Simulated-classroom benchmark script: reproducible, labelled simulation.
3. Fitted override learning script: held-out-by-concept metrics, labelled synthetic.
"""
import sys
import os
import json
import subprocess

import pytest
from starlette.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app, pack
from app.db import init_db, SessionLocal, UserDB
from app.auth.security import hash_password
from app.authoring import AuthoredQuestionDB

TEACHER = ("tea_v5_01", "tea_pass_v5_123")
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

VALID_Q = {
    "concept": "c8_math_linear_eq_one_var",
    "language": "en",
    "question_text": "Solve for x: x + 3 = 10",
    "options": [
        {"text": "7", "is_correct": True},
        {"text": "13", "is_correct": False, "misconception_tag": "tag_sign_error_on_transposition"},
        {"text": "3", "is_correct": False, "misconception_tag": "tag_dividing_instead_of_subtracting"},
        {"text": "30", "is_correct": False, "misconception_tag": "tag_grouping_variables_wrong_sign"},
    ],
    "difficulty": 0.4,
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
            db.add(UserDB(
                id="usr_tea_v5_01", username=TEACHER[0],
                password_hash=hash_password(TEACHER[1]), role="teacher",
                assigned_classes='["8-A"]',
            ))
            db.commit()
        yield
    finally:
        # remove authored rows created by the tests and un-hook them from the pack
        rows = db.query(AuthoredQuestionDB).filter(AuthoredQuestionDB.created_by == "usr_tea_v5_01").all()
        ids = [r.id for r in rows]
        for r in rows:
            db.delete(r)
        db.commit()
        pack.questions[:] = [q for q in pack.questions if q.id not in ids]
        db.close()


def _headers(client):
    res = client.post("/api/auth/login", json={"username": TEACHER[0], "password": TEACHER[1]})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_authoring_create_serves_as_draft(client):
    h = _headers(client)
    res = client.post("/api/teacher/authoring/questions", json=VALID_Q, headers=h)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["stored"] is True
    assert data["review_status"] == "author-drafted, unreviewed"
    qid = data["id"]
    # v6: drafts are stored but NOT served to students until a reviewer approves
    assert data["live"] is False
    assert pack.get_question(qid) is None
    # listed
    lst = client.get("/api/teacher/authoring/questions", headers=h).json()
    assert any(item["id"] == qid for item in lst["questions"])


def test_authoring_rejects_invalid(client):
    h = _headers(client)
    # two correct options
    bad = dict(VALID_Q, options=[dict(o) for o in VALID_Q["options"]])
    bad["options"][1]["is_correct"] = True
    res = client.post("/api/teacher/authoring/questions", json=bad, headers=h)
    assert res.status_code == 422
    codes = {i["code"] for i in res.json()["detail"]["issues"]}
    assert "CORRECT_COUNT" in codes
    # untagged wrong option
    bad2 = dict(VALID_Q, options=[dict(o) for o in VALID_Q["options"]])
    bad2["options"][1]["misconception_tag"] = None
    res2 = client.post("/api/teacher/authoring/questions", json=bad2, headers=h)
    assert res2.status_code == 422
    codes2 = {i["code"] for i in res2.json()["detail"]["issues"]}
    assert "UNTAGGED_WRONG_OPTION" in codes2
    # unknown concept
    bad3 = dict(VALID_Q, concept="c99_nope")
    res3 = client.post("/api/teacher/authoring/questions", json=bad3, headers=h)
    assert res3.status_code == 422


def test_authoring_new_tag_warns_but_stores(client):
    h = _headers(client)
    q = dict(VALID_Q, options=[dict(o) for o in VALID_Q["options"]])
    q["options"][1]["misconception_tag"] = "tag_brand_new_misconception_x"
    res = client.post("/api/teacher/authoring/questions", json=q, headers=h)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["stored"] is True
    assert any(i["code"] == "NEW_TAG_WITHOUT_PROBE" and i["severity"] == "WARNING" for i in data["issues"])


def test_authoring_edit_keeps_draft_and_bumps_version(client):
    h = _headers(client)
    res = client.post("/api/teacher/authoring/questions", json=VALID_Q, headers=h)
    qid = res.json()["id"]
    edited = dict(VALID_Q, question_text="Solve for x: x + 5 = 12")
    res2 = client.put(f"/api/teacher/authoring/questions/{qid}", json=edited, headers=h)
    assert res2.status_code == 200, res2.text
    data2 = res2.json()
    assert data2["version"] == 2
    assert data2["review_status"] == "author-drafted, unreviewed"
    assert pack.get_question(qid) is None  # still a draft, not served


def test_classroom_benchmark_reproducible_and_labelled():
    cmd = [sys.executable, os.path.join("scripts", "setu_classroom_benchmark.py"), "--students", "20"]
    out1 = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=True).stdout
    out2 = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=True).stdout
    assert out1 == out2  # deterministic
    r = json.loads(out1)
    assert "SIMULATED STUDENTS - NOT REAL CHILDREN" in r["label"]
    assert r["students"] == 20
    for arm in ("arm_setu_adaptive", "arm_fixed_order_quiz"):
        assert {"mean", "median", "stdev", "p10", "p90", "gap_found_rate"} <= set(r[arm])


def test_override_fit_heldout_and_labelled():
    cmd = [sys.executable, os.path.join("scripts", "setu_override_fit.py"), "--concepts", "20", "--events", "10"]
    out1 = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=True).stdout
    out2 = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=True).stdout
    assert out1 == out2  # deterministic
    r = json.loads(out1)
    assert "SYNTHETIC OVERRIDES" in r["label"]
    assert "BY CONCEPT" in r["split"]
    assert 0.0 <= r["heldout"]["accuracy"] <= 1.0
    assert r["heldout"]["auc"] is None or 0.0 <= r["heldout"]["auc"] <= 1.0
