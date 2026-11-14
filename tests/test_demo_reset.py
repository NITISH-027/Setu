"""
Round 3 judge-demo hygiene: demo profile reset on logout / session expiry.

Covers:
1. Demo logout restores the profile to the startup (seeded) baseline.
2. Concurrency: two judges on the same demo profile - the first logout does NOT
   wipe the second judge's live session; the reset happens when the last one ends.
3. Real (non-demo) sessions and non-snapshotted students are never wiped,
   even in demo mode.
4. With SETU_DEMO_MODE off, the sweep is a strict no-op.
5. An expired demo session triggers the reset on the next authenticated request.
"""
import sys
import os
import secrets
from datetime import datetime, timedelta

import pytest
from starlette.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app import main, demo_reset
from app.main import app
from app.db import (
    init_db, SessionLocal, StudentDB, PlanDB, MasteryStateDB, AttemptDB,
    SessionDB, DemoSessionDB,
)
from app.auth.security import hash_pin, create_session


@pytest.fixture
def db():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client():
    init_db()
    return TestClient(app)


@pytest.fixture
def demo_on(monkeypatch):
    monkeypatch.setattr(main, "DEMO_MODE", True)
    monkeypatch.setattr(demo_reset, "DEMO_MODE", True)
    yield


def _make_student(db, sid, mastery=0.25):
    # Idempotent: the suite shares one dev DB file, so clear leftovers from prior runs.
    db.query(AttemptDB).filter(AttemptDB.student_id == sid).delete()
    db.query(MasteryStateDB).filter(MasteryStateDB.student_id == sid).delete()
    db.query(PlanDB).filter(PlanDB.student_id == sid).delete()
    db.query(DemoSessionDB).filter(DemoSessionDB.student_id == sid).delete()
    db.query(SessionDB).filter(SessionDB.student_id == sid).delete()
    db.query(StudentDB).filter(StudentDB.pseudonymous_id == sid).delete()
    db.commit()
    if True:
        salt = secrets.token_hex(8)
        db.add(StudentDB(
            pseudonymous_id=sid,
            subject_key=f"subj_{sid}",
            class_id="8-A",
            board="CBSE",
            medium_language="en",
            pin_hash=hash_pin("1234", salt),
            salt=salt,
            consent_status="not requested",
        ))
        db.add(PlanDB(
            student_id=sid,
            class_id="8-A",
            current_stage="solve",
            current_concept_id="c8_math_linear_eq_one_var",
            reason="Practice sequence",
        ))
        db.add(MasteryStateDB(
            student_id=sid,
            concept_id="c8_math_linear_eq_one_var",
            mastery_estimate=mastery,
        ))
        db.commit()


def _add_attempt(db, sid, correct=False):
    db.add(AttemptDB(
        id=f"att_{sid}_{secrets.token_hex(4)}",
        student_id=sid,
        question_id="q_c8_leq_01",
        concept_id="c8_math_linear_eq_one_var",
        selected_option_id="opt_2",
        is_correct=correct,
    ))
    ms = db.query(MasteryStateDB).filter(
        MasteryStateDB.student_id == sid,
        MasteryStateDB.concept_id == "c8_math_linear_eq_one_var",
    ).first()
    ms.mastery_estimate = 0.99  # simulate judge-driven progress
    db.commit()


def _attempt_count(db, sid):
    return db.query(AttemptDB).filter(AttemptDB.student_id == sid).count()


def _mastery(db, sid):
    return db.query(MasteryStateDB).filter(
        MasteryStateDB.student_id == sid,
        MasteryStateDB.concept_id == "c8_math_linear_eq_one_var",
    ).first().mastery_estimate


def _demo_login(client, sid):
    res = client.post("/api/auth/demo-login", json={"profile": f"student:{sid}", "device_id": "dev_judge"})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["demo"] is True
    return data["access_token"]


def _logout(client, token):
    res = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text


def test_demo_logout_resets_profile_to_baseline(db, client, demo_on):
    sid = "stu_dr_basic"
    _make_student(db, sid, mastery=0.25)
    demo_reset.capture_snapshot(db)  # simulates server startup baseline

    token = _demo_login(client, sid)
    _add_attempt(db, sid)
    assert _attempt_count(db, sid) == 1
    assert _mastery(db, sid) == 0.99

    _logout(client, token)

    assert _attempt_count(db, sid) == 0, "demo attempt rows must be wiped on demo logout"
    assert _mastery(db, sid) == 0.25, "mastery must return to the seeded baseline"
    # markers cleaned
    assert db.query(DemoSessionDB).filter(DemoSessionDB.student_id == sid).count() == 0


def test_concurrent_judges_first_logout_does_not_wipe(db, client, demo_on):
    sid = "stu_dr_race"
    _make_student(db, sid, mastery=0.25)
    demo_reset.capture_snapshot(db)

    judge_a = _demo_login(client, sid)
    judge_b = _demo_login(client, sid)
    _add_attempt(db, sid)

    _logout(client, judge_a)
    assert _attempt_count(db, sid) == 1, "judge B is still live: first logout must not wipe"
    assert _mastery(db, sid) == 0.99

    _logout(client, judge_b)
    assert _attempt_count(db, sid) == 0, "last live session ended: profile must reset"
    assert _mastery(db, sid) == 0.25


def test_real_pin_session_data_untouched_in_demo_mode(db, client, demo_on):
    """A seeded profile used via a REAL (non-demo) session is never wiped."""
    sid = "stu_dr_real"
    _make_student(db, sid, mastery=0.25)
    demo_reset.capture_snapshot(db)

    # Real session (as PIN login would create): no demo marker.
    session = create_session(db, role="student", student_id=sid, device_id="dev_real")
    _add_attempt(db, sid)

    _logout(client, session.token)

    assert _attempt_count(db, sid) == 1, "real session data must survive - no demo marker"
    assert _mastery(db, sid) == 0.99


def test_student_created_after_startup_never_reset(db, client, demo_on):
    """Students absent from the startup snapshot are never eligible for reset."""
    demo_reset.capture_snapshot(db)  # baseline BEFORE the student exists
    sid = "stu_dr_late"
    _make_student(db, sid, mastery=0.25)

    token = _demo_login(client, sid)
    _add_attempt(db, sid)
    _logout(client, token)

    assert _attempt_count(db, sid) == 1, "not in startup snapshot: never reset"
    assert _mastery(db, sid) == 0.99


def test_sweep_noop_when_demo_mode_off(db, monkeypatch):
    sid = "stu_dr_off"
    _make_student(db, sid, mastery=0.25)
    monkeypatch.setattr(demo_reset, "DEMO_MODE", True)
    demo_reset.capture_snapshot(db)
    _add_attempt(db, sid)

    monkeypatch.setattr(demo_reset, "DEMO_MODE", False)
    reset = demo_reset.sweep_idle_demo_profiles(db)
    assert reset == []
    assert _attempt_count(db, sid) == 1, "demo mode off: nothing may be wiped"
    assert demo_reset.is_demo_session(db, "any-token") is False


def test_expired_demo_session_triggers_reset(db, client, demo_on):
    sid = "stu_dr_expiry"
    _make_student(db, sid, mastery=0.25)
    demo_reset.capture_snapshot(db)

    token = _demo_login(client, sid)
    _add_attempt(db, sid)

    # Simulate the 2h demo session timing out (judge closed the laptop).
    sess = db.query(SessionDB).filter(SessionDB.token == token).first()
    sess.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.commit()

    # Next request with the stale token: 401, and the idle profile gets reset.
    res = client.get(f"/api/student/{sid}/next-step", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert _attempt_count(db, sid) == 0, "expired demo session must trigger reset"
    assert _mastery(db, sid) == 0.25
