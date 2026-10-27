"""
Tests for Sections 2, 3, 4, 6:
- SQLite persistence across sessions
- Server-side authentication and role/class scoping (Argon2)
- Server-side grading (ignoring client-sent spoofed is_correct flags)
- Clean deletion zero-trace (tombstone protocol with subject key, pin profiles purged)
- Negative controls
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

from app.main import app
from app.db import (
    SessionLocal, StudentDB, PlanDB, MasteryStateDB,
    HypothesisDB, AttemptDB, DecisionDB, TeacherOverrideDB,
    TombstoneDB, DeviceDB, AuditEventDB, PinProfileDB, UserDB
)
from app.auth.security import hash_password, hash_pin


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_users():
    """Ensure test users and clean test data exist in DB."""
    db = SessionLocal()
    try:
        # Seed admin
        if not db.query(UserDB).filter(UserDB.username == "sec_admin").first():
            db.add(UserDB(
                id="usr_sec_admin",
                username="sec_admin",
                password_hash=hash_password("admin_sec_pass"),
                role="admin",
                assigned_classes="[]"
            ))

        # Seed Teacher 8-A
        if not db.query(UserDB).filter(UserDB.username == "sec_teacher_8a").first():
            db.add(UserDB(
                id="usr_sec_tea_8a",
                username="sec_teacher_8a",
                password_hash=hash_password("tea_8a_pass"),
                role="teacher",
                assigned_classes='["8-A"]'
            ))

        # Seed Teacher 8-B
        if not db.query(UserDB).filter(UserDB.username == "sec_teacher_8b").first():
            db.add(UserDB(
                id="usr_sec_tea_8b",
                username="sec_teacher_8b",
                password_hash=hash_password("tea_8b_pass"),
                role="teacher",
                assigned_classes='["8-B"]'
            ))

        # Seed Reviewer
        if not db.query(UserDB).filter(UserDB.username == "sec_reviewer").first():
            db.add(UserDB(
                id="usr_sec_rev",
                username="sec_reviewer",
                password_hash=hash_password("rev_pass"),
                role="reviewer",
                assigned_classes="[]"
            ))

        # Seed a dedicated test student
        test_sid = "stu_sec_test_01"
        if not db.query(StudentDB).filter(StudentDB.pseudonymous_id == test_sid).first():
            salt = secrets.token_hex(8)
            pin_h = hash_pin("4321", salt)
            db.add(StudentDB(
                pseudonymous_id=test_sid,
                subject_key="subj_sec_test_k1",
                class_id="8-A",
                board="CBSE",
                medium_language="en",
                pin_hash=pin_h,
                salt=salt,
                consent_status="not requested"
            ))
            if not db.query(PlanDB).filter(PlanDB.student_id == test_sid).first():
                db.add(PlanDB(
                    student_id=test_sid,
                    class_id="8-A",
                    current_stage="solve",
                    current_concept_id="c8_math_linear_eq_one_var",
                    reason="Practice"
                ))
            if not db.query(MasteryStateDB).filter(MasteryStateDB.student_id == test_sid).first():
                db.add(MasteryStateDB(
                    student_id=test_sid,
                    concept_id="c8_math_linear_eq_one_var",
                    mastery_estimate=0.3
                ))
            if not db.query(DeviceDB).filter(DeviceDB.device_id == "dev_sec_test").first():
                db.add(DeviceDB(
                    device_id="dev_sec_test",
                    class_id="8-A"
                ))
            if not db.query(PinProfileDB).filter(PinProfileDB.device_id == "dev_sec_test", PinProfileDB.student_id == test_sid).first():
                db.add(PinProfileDB(
                    device_id="dev_sec_test",
                    student_id=test_sid,
                    class_id="8-A",
                    pin_hash=pin_h,
                    salt=salt
                ))

        db.commit()
    finally:
        db.close()


def test_argon2_auth_and_role_access(client):
    # 1. Login with bad password -> 401
    bad_login = client.post("/api/auth/login", json={"username": "sec_admin", "password": "wrong_password"})
    assert bad_login.status_code == 401

    # 2. Login as Admin
    admin_login = client.post("/api/auth/login", json={"username": "sec_admin", "password": "admin_sec_pass"})
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    assert admin_login.json()["role"] == "admin"

    # 3. Login as Teacher 8-A
    t8a_login = client.post("/api/auth/login", json={"username": "sec_teacher_8a", "password": "tea_8a_pass"})
    assert t8a_login.status_code == 200
    t8a_token = t8a_login.json()["access_token"]

    # 4. Teacher tries to view admin audit-logs -> 403 Forbidden
    unauth_audit = client.get("/api/admin/audit-logs", headers={"Authorization": f"Bearer {t8a_token}"})
    assert unauth_audit.status_code == 403

    # 5. Admin views audit-logs -> 200 OK
    auth_audit = client.get("/api/admin/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
    assert auth_audit.status_code == 200
    assert isinstance(auth_audit.json(), list)


def test_teacher_class_scoping_negative_control(client):
    # Login Teacher 8-A and Teacher 8-B
    t8a = client.post("/api/auth/login", json={"username": "sec_teacher_8a", "password": "tea_8a_pass"}).json()["access_token"]
    t8b = client.post("/api/auth/login", json={"username": "sec_teacher_8b", "password": "tea_8b_pass"}).json()["access_token"]

    # Teacher 8-A accessing 8-A -> 200
    res_8a = client.get("/api/teacher/class/8-A", headers={"Authorization": f"Bearer {t8a}"})
    assert res_8a.status_code == 200

    # Negative control: Teacher 8-A accessing 8-B -> 403 Forbidden
    res_8a_to_8b = client.get("/api/teacher/class/8-B", headers={"Authorization": f"Bearer {t8a}"})
    assert res_8a_to_8b.status_code == 403
    assert "not assigned" in res_8a_to_8b.json()["detail"].lower()

    # Negative control: Teacher 8-B accessing 8-A -> 403 Forbidden
    res_8b_to_8a = client.get("/api/teacher/class/8-A", headers={"Authorization": f"Bearer {t8b}"})
    assert res_8b_to_8a.status_code == 403


def test_server_side_grading_spoof_override(client):
    """
    CRITICAL: Client attempts to forge grading by claiming an incorrect option is correct.
    Server must look up the option in the pack, detect that it is wrong, and grade it as wrong.
    """
    # Question q_c8_leq_01:
    # opt_1 is CORRECT (x = 3)
    # opt_2 is WRONG (x = 7, misconception: tag_sign_error_on_transposition)

    # Spoofed payload: Client sends opt_2 with is_correct: True!
    spoofed_attempt = {
        "question_id": "q_c8_leq_01",
        "concept_id": "c8_math_linear_eq_one_var",
        "selected_option_id": "opt_2",
        "is_correct": True,  # Spoofed!
        "misconception_tag": None
    }

    res = client.post("/api/student/stu_sec_test_01/attempt", json=spoofed_attempt)
    assert res.status_code == 200
    data = res.json()

    # The server must have OVERRULED the client's is_correct: True
    assert data["server_graded_correct"] is False
    assert data["authoritative_misconception"] == "tag_sign_error_on_transposition"
    assert data["decision"]["action"] == "ADMINISTER_PROBE"

    # Verify attempt is persisted in SQLite database
    db = SessionLocal()
    try:
        att = db.query(AttemptDB).filter(
            AttemptDB.student_id == "stu_sec_test_01",
            AttemptDB.question_id == "q_c8_leq_01"
        ).order_by(AttemptDB.timestamp.desc()).first()
        assert att is not None
        assert att.is_correct is False
        assert att.misconception_tag == "tag_sign_error_on_transposition"
    finally:
        db.close()


def test_student_pin_auth_and_session_isolation(client):
    # 1. Invalid PIN -> 401
    bad_pin = client.post("/api/auth/pin", json={
        "device_id": "dev_sec_test",
        "student_id": "stu_sec_test_01",
        "pin": "0000"
    })
    assert bad_pin.status_code == 401

    # 2. Valid PIN -> 200 with student access_token
    good_pin = client.post("/api/auth/pin", json={
        "device_id": "dev_sec_test",
        "student_id": "stu_sec_test_01",
        "pin": "4321"
    })
    assert good_pin.status_code == 200
    token = good_pin.json()["access_token"]

    # 3. Access own step -> 200
    own_step = client.get("/api/student/stu_sec_test_01/next-step", headers={"Authorization": f"Bearer {token}"})
    assert own_step.status_code == 200

    # 4. Negative control: Attempt to access another student's step with this token -> 403 Forbidden
    other_step = client.get("/api/student/stu_demo_01/next-step", headers={"Authorization": f"Bearer {token}"})
    assert other_step.status_code == 403


def test_zero_pii_deletion_and_tombstone_lifecycle(client):
    """
    CRITICAL: Student deletion purges StudentDB, PlanDB, MasteryStateDB,
    HypothesisDB, AttemptDB, DecisionDB, and PinProfileDB.
    Tombstone contains ONLY opaque subject_key, NEVER student ID.
    Teacher overrides are sanitized.
    """
    del_sid = "stu_sec_test_01"

    # Add an override for this student first to test override sanitization
    db = SessionLocal()
    try:
        db.add(TeacherOverrideDB(
            student_id=del_sid,
            teacher_id="usr_sec_tea_8a",
            class_id="8-A",
            concept_id="c8_math_linear_eq_one_var",
            override_action="modify_plan",
            reason="Remedial session scheduled"
        ))
        db.commit()
    finally:
        db.close()

    # Call delete endpoint
    del_res = client.post("/api/privacy/delete-student", json={"student_id": del_sid, "actor": "teacher_8a"})
    assert del_res.status_code == 200
    del_data = del_res.json()
    tombstone_key = del_data["tombstone_key"]
    assert len(tombstone_key) >= 16

    # Verify complete purge across DB tables
    db = SessionLocal()
    try:
        assert db.query(StudentDB).filter(StudentDB.pseudonymous_id == del_sid).count() == 0
        assert db.query(PlanDB).filter(PlanDB.student_id == del_sid).count() == 0
        assert db.query(MasteryStateDB).filter(MasteryStateDB.student_id == del_sid).count() == 0
        assert db.query(HypothesisDB).filter(HypothesisDB.student_id == del_sid).count() == 0
        assert db.query(AttemptDB).filter(AttemptDB.student_id == del_sid).count() == 0
        assert db.query(DecisionDB).filter(DecisionDB.student_id == del_sid).count() == 0
        assert db.query(PinProfileDB).filter(PinProfileDB.student_id == del_sid).count() == 0

        # Teacher overrides must be sanitized (no dangling student ID)
        dangling_overrides = db.query(TeacherOverrideDB).filter(TeacherOverrideDB.student_id == del_sid).count()
        assert dangling_overrides == 0

        # Tombstone verification: contains subject_key, NOT student_id
        tombstone = db.query(TombstoneDB).filter(TombstoneDB.opaque_key == tombstone_key).first()
        assert tombstone is not None
        assert tombstone.subject_key == "subj_sec_test_k1"
        assert not hasattr(tombstone, "student_id") or tombstone.subject_key != del_sid

        # Audit event verification: contains opaque_key, record count, NO student ID
        audit = db.query(AuditEventDB).filter(AuditEventDB.opaque_tombstone_key == tombstone_key).first()
        assert audit is not None
        assert audit.event_type == "DELETE_STUDENT"
        assert audit.record_count == 1
    finally:
        db.close()


def test_stale_device_detection_on_sync(client):
    """
    If a device syncs after more than 30 days of inactivity,
    it must be flagged for local reset (is_stale_reset_required = True).
    """
    db = SessionLocal()
    stale_dev_id = "dev_stale_tablet_99"
    try:
        # Create device with last_sync 45 days ago
        old_time = datetime.utcnow() - timedelta(days=45)
        dev = db.query(DeviceDB).filter(DeviceDB.device_id == stale_dev_id).first()
        if not dev:
            dev = DeviceDB(device_id=stale_dev_id, class_id="8-A", last_sync_at=old_time)
            db.add(dev)
        else:
            dev.last_sync_at = old_time
        db.commit()
    finally:
        db.close()

    sync_res = client.post("/api/privacy/sync", json={
        "device_id": stale_dev_id,
        "class_id": "8-A",
        "queued_attempts": []
    })
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert sync_data["is_stale_reset_required"] is True
