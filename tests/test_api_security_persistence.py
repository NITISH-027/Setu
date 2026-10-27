"""
Comprehensive security, persistence, and negative-control test suite.
Verifies Fix 1 (Auth enforcement, no-session fallback removal, 401/403 matrices),
Fix 2 (Zero answer leak on next-step and pack),
Fix 4 (Unregistered device reset, stale reset, sync auth),
Fix 5 (Clean deletion with full DB scan for zero student_id / reason text residue, purge tokens),
Fix 6 (Production startup refusal on seeded users).
"""

import sys
import os
import json
import secrets
from datetime import datetime, timedelta
import pytest
from starlette.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app, verify_production_safeguards
from app.db import (
    init_db, SessionLocal, StudentDB, PlanDB, MasteryStateDB,
    HypothesisDB, AttemptDB, DecisionDB, TeacherOverrideDB,
    TombstoneDB, DeviceDB, AuditEventDB, PinProfileDB, UserDB, SessionDB
)
from app.auth.security import hash_password, hash_pin


@pytest.fixture
def client():
    init_db()
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_security_fixtures():
    init_db()
    db = SessionLocal()
    try:
        # 1. Admin
        if not db.query(UserDB).filter(UserDB.username == "sec_admin").first():
            db.add(UserDB(
                id="usr_sec_admin",
                username="sec_admin",
                password_hash=hash_password("admin_sec_pass"),
                role="admin",
                assigned_classes="[]"
            ))

        # 2. Teacher 8-A
        if not db.query(UserDB).filter(UserDB.username == "sec_teacher_8a").first():
            db.add(UserDB(
                id="usr_sec_tea_8a",
                username="sec_teacher_8a",
                password_hash=hash_password("tea_8a_pass"),
                role="teacher",
                assigned_classes='["8-A"]'
            ))

        # 3. Teacher 8-B
        if not db.query(UserDB).filter(UserDB.username == "sec_teacher_8b").first():
            db.add(UserDB(
                id="usr_sec_tea_8b",
                username="sec_teacher_8b",
                password_hash=hash_password("tea_8b_pass"),
                role="teacher",
                assigned_classes='["8-B"]'
            ))

        # 4. Reviewer
        if not db.query(UserDB).filter(UserDB.username == "sec_reviewer").first():
            db.add(UserDB(
                id="usr_sec_rev",
                username="sec_reviewer",
                password_hash=hash_password("rev_pass"),
                role="reviewer",
                assigned_classes="[]"
            ))

        # 5. Student in 8-A
        sid = "stu_sec_01"
        if not db.query(StudentDB).filter(StudentDB.pseudonymous_id == sid).first():
            salt = secrets.token_hex(8)
            pin_h = hash_pin("4321", salt)
            db.add(StudentDB(
                pseudonymous_id=sid,
                subject_key="subj_sec_k1",
                class_id="8-A",
                board="CBSE",
                medium_language="en",
                pin_hash=pin_h,
                salt=salt,
                consent_status="not requested"
            ))
            db.add(PlanDB(
                student_id=sid,
                class_id="8-A",
                current_stage="solve",
                current_concept_id="c8_math_linear_eq_one_var",
                reason="Initial solve"
            ))
            db.add(MasteryStateDB(
                student_id=sid,
                concept_id="c8_math_linear_eq_one_var",
                mastery_estimate=0.3
            ))
            db.add(DeviceDB(
                device_id="dev_sec_01",
                class_id="8-A"
            ))
            db.add(PinProfileDB(
                device_id="dev_sec_01",
                student_id=sid,
                class_id="8-A",
                pin_hash=pin_h,
                salt=salt
            ))

        # 6. Student in 8-B
        sid2 = "stu_sec_02_8b"
        if not db.query(StudentDB).filter(StudentDB.pseudonymous_id == sid2).first():
            salt2 = secrets.token_hex(8)
            pin_h2 = hash_pin("9876", salt2)
            db.add(StudentDB(
                pseudonymous_id=sid2,
                subject_key="subj_sec_k2",
                class_id="8-B",
                board="CBSE",
                medium_language="en",
                pin_hash=pin_h2,
                salt=salt2,
                consent_status="not requested"
            ))
            db.add(PlanDB(
                student_id=sid2,
                class_id="8-B",
                current_stage="solve",
                current_concept_id="c8_math_linear_eq_one_var",
                reason="Initial solve 8B"
            ))
            db.add(MasteryStateDB(
                student_id=sid2,
                concept_id="c8_math_linear_eq_one_var",
                mastery_estimate=0.2
            ))
            db.add(DeviceDB(
                device_id="dev_sec_02",
                class_id="8-B"
            ))
            db.add(PinProfileDB(
                device_id="dev_sec_02",
                student_id=sid2,
                class_id="8-B",
                pin_hash=pin_h2,
                salt=salt2
            ))

        db.commit()
    finally:
        db.close()


def get_tokens(client):
    admin_token = client.post("/api/auth/login", json={"username": "sec_admin", "password": "admin_sec_pass"}).json()["access_token"]
    t8a_token = client.post("/api/auth/login", json={"username": "sec_teacher_8a", "password": "tea_8a_pass"}).json()["access_token"]
    t8b_token = client.post("/api/auth/login", json={"username": "sec_teacher_8b", "password": "tea_8b_pass"}).json()["access_token"]
    s1_token = client.post("/api/auth/pin", json={"device_id": "dev_sec_01", "student_id": "stu_sec_01", "pin": "4321"}).json()["access_token"]
    s2_token = client.post("/api/auth/pin", json={"device_id": "dev_sec_02", "student_id": "stu_sec_02_8b", "pin": "9876"}).json()["access_token"]
    return {
        "admin": admin_token,
        "teacher_8a": t8a_token,
        "teacher_8b": t8b_token,
        "student_1": s1_token,
        "student_2": s2_token
    }


# ==========================================
# FIX 1: AUTH ENFORCEMENT & NEGATIVE CONTROLS
# ==========================================

def test_negative_controls_no_token_returns_401(client):
    """
    FIX 1: Every protected route MUST return 401 when called with NO token or invalid token.
    Verified failures from audit: GET class, POST override, POST bulk-paper-submit,
    GET export, GET next-step, POST attempt, POST delete-student, POST sync.
    """
    # 1. GET /api/teacher/class/{id}
    assert client.get("/api/teacher/class/8-A").status_code == 401
    assert client.get("/api/teacher/class/8-A", headers={"Authorization": "Bearer badtoken"}).status_code == 401

    # 2. POST /api/teacher/override
    assert client.post("/api/teacher/override", json={"class_id": "8-A", "student_id": "stu_sec_01", "concept_id": "c8_math_linear_eq_one_var", "action": "reassign", "reason": "Test"}).status_code == 401

    # 3. POST /api/teacher/bulk-paper-submit
    assert client.post("/api/teacher/bulk-paper-submit", json={"responses": []}).status_code == 401

    # 4. GET /api/student/{id}/export
    assert client.get("/api/student/stu_sec_01/export").status_code == 401

    # 5. GET /api/student/{id}/next-step
    assert client.get("/api/student/stu_sec_01/next-step").status_code == 401

    # 6. POST /api/student/{id}/attempt (Fix 1d: missing token must return 401, never 500)
    assert client.post("/api/student/stu_sec_01/attempt", json={"question_id": "q1", "selected_option_id": "opt1"}).status_code == 401

    # 7. POST /api/privacy/delete-student (Anonymous caller must NOT delete)
    assert client.post("/api/privacy/delete-student", json={"student_id": "stu_sec_01"}).status_code == 401

    # 8. POST /api/privacy/sync (Requires auth)
    assert client.post("/api/privacy/sync", json={"device_id": "dev_sec_01", "class_id": "8-A"}).status_code == 401

    # 9. GET /api/student/{id}/offline-pack
    assert client.get("/api/student/stu_sec_01/offline-pack").status_code == 401


def test_attempt_validation_returns_422_never_500(client):
    """FIX 1d: Attempt route with malformed payload returns 422, never 500."""
    tokens = get_tokens(client)
    s1_hdr = {"Authorization": f"Bearer {tokens['student_1']}"}

    # Malformed body: missing required question_id / selected_option_id
    res_bad1 = client.post("/api/student/stu_sec_01/attempt", json={}, headers=s1_hdr)
    assert res_bad1.status_code == 422

    # Malformed body: invalid types
    res_bad2 = client.post("/api/student/stu_sec_01/attempt", json={"question_id": 12345, "selected_option_id": None}, headers=s1_hdr)
    assert res_bad2.status_code == 422


def test_role_and_class_scoping_matrix(client):
    """
    FIX 1c:
    - student token may only access its own student_id
    - teacher token: only classes assigned to that teacher
    - delete-student: teacher scoped to assigned class, admin allowed, student forbidden
    """
    tokens = get_tokens(client)
    s1_hdr = {"Authorization": f"Bearer {tokens['student_1']}"}
    s2_hdr = {"Authorization": f"Bearer {tokens['student_2']}"}
    t8a_hdr = {"Authorization": f"Bearer {tokens['teacher_8a']}"}
    t8b_hdr = {"Authorization": f"Bearer {tokens['teacher_8b']}"}

    # Student 1 accessing Student 2 next-step -> 403
    assert client.get("/api/student/stu_sec_02_8b/next-step", headers=s1_hdr).status_code == 403

    # Student 1 attempting for Student 2 -> 403
    assert client.post("/api/student/stu_sec_02_8b/attempt", json={"question_id": "q_c8_leq_01", "selected_option_id": "opt_1"}, headers=s1_hdr).status_code == 403

    # Teacher accessing next-step -> 403 (student-only endpoint)
    assert client.get("/api/student/stu_sec_01/next-step", headers=t8a_hdr).status_code == 403

    # Teacher 8-A accessing Class 8-B dashboard -> 403
    assert client.get("/api/teacher/class/8-B", headers=t8a_hdr).status_code == 403

    # Teacher 8-B accessing Class 8-A dashboard -> 403
    assert client.get("/api/teacher/class/8-A", headers=t8b_hdr).status_code == 403

    # Teacher 8-A trying to override Class 8-B student -> 403
    ov_res = client.post("/api/teacher/override", json={
        "class_id": "8-B",
        "student_id": "stu_sec_02_8b",
        "concept_id": "c8_math_linear_eq_one_var",
        "action": "reassign",
        "reason": "Unauthorized override"
    }, headers=t8a_hdr)
    assert ov_res.status_code == 403

    # Student trying to delete another student or self -> 403
    assert client.post("/api/privacy/delete-student", json={"student_id": "stu_sec_01"}, headers=s1_hdr).status_code == 403

    # Teacher 8-A trying to delete Student in 8-B -> 403
    assert client.post("/api/privacy/delete-student", json={"student_id": "stu_sec_02_8b"}, headers=t8a_hdr).status_code == 403


def test_logout_session_invalidation(client):
    """FIX 1h: Tokens expire and logout invalidates token."""
    t_login = client.post("/api/auth/login", json={"username": "sec_teacher_8a", "password": "tea_8a_pass"})
    token = t_login.json()["access_token"]
    hdr = {"Authorization": f"Bearer {token}"}

    # Before logout: works
    assert client.get("/api/teacher/class/8-A", headers=hdr).status_code == 200

    # Logout
    logout_res = client.post("/api/auth/logout", headers=hdr)
    assert logout_res.status_code == 200

    # After logout: token is invalidated -> 401
    assert client.get("/api/teacher/class/8-A", headers=hdr).status_code == 401


# ==========================================
# FIX 2: ZERO ANSWER LEAK
# ==========================================

def test_zero_answer_leak_online(client):
    """
    FIX 2: Online question and public pack endpoints are answer-free.
    Never contain is_correct, misconception_tag, or worked_solution.
    """
    tokens = get_tokens(client)
    s1_hdr = {"Authorization": f"Bearer {tokens['student_1']}"}

    # 1. Online next-step
    res = client.get("/api/student/stu_sec_01/next-step", headers=s1_hdr)
    assert res.status_code == 200
    item = res.json()["item"]
    assert "worked_solution" not in item
    assert "correct_option_id" not in item
    for opt in item["options"]:
        assert "is_correct" not in opt, f"LEAK: is_correct found in online next-step option {opt}"
        assert "misconception_tag" not in opt, f"LEAK: misconception_tag found in online next-step option {opt}"

    # 2. Public pack download
    res_pack = client.get("/api/pack")
    assert res_pack.status_code == 200
    pack_data = res_pack.json()
    for q in pack_data.get("questions", []):
        assert "worked_solution" not in q
        for opt in q.get("options", []):
            assert "is_correct" not in opt, f"LEAK: is_correct in public pack option {opt}"
            assert "misconception_tag" not in opt, f"LEAK: misconception_tag in public pack option {opt}"

    # 3. Offline pack (authenticated student session only) DOES contain answers for local grading
    res_offline = client.get("/api/student/stu_sec_01/offline-pack", headers=s1_hdr)
    assert res_offline.status_code == 200
    offline_pack = res_offline.json()
    assert any("is_correct" in opt for q in offline_pack["questions"] for opt in q["options"])


# ==========================================
# FIX 4: SYNC, DEVICES, STALE RESET
# ==========================================

def test_sync_unregistered_device_returns_reset(client):
    """
    FIX 4: Sync from an unregistered device id returns an explicit RESET-required response,
    NOT a silent registration.
    """
    tokens = get_tokens(client)
    s1_hdr = {"Authorization": f"Bearer {tokens['student_1']}"}

    res = client.post("/api/privacy/sync", json={
        "device_id": "dev_completely_unknown_999",
        "class_id": "8-A",
        "queued_attempts": []
    }, headers=s1_hdr)
    assert res.status_code == 200
    data = res.json()
    assert data["is_stale_reset_required"] is True
    assert data["reset_reason"] == "unregistered_device"


def test_sync_stale_device_returns_reset(client):
    """
    FIX 4: A device that has not synced within retention period (>30 days) gets RESET.
    """
    tokens = get_tokens(client)
    s1_hdr = {"Authorization": f"Bearer {tokens['student_1']}"}

    db = SessionLocal()
    try:
        dev = db.query(DeviceDB).filter(DeviceDB.device_id == "dev_sec_01").first()
        dev.last_sync_at = datetime.utcnow() - timedelta(days=35)
        db.commit()
    finally:
        db.close()

    res = client.post("/api/privacy/sync", json={
        "device_id": "dev_sec_01",
        "class_id": "8-A",
        "queued_attempts": []
    }, headers=s1_hdr)
    assert res.status_code == 200
    data = res.json()
    assert data["is_stale_reset_required"] is True
    assert data["reset_reason"] == "retention_expired"


# ==========================================
# FIX 5: DELETION RESIDUE & FULL DB SCAN
# ==========================================

def test_zero_residue_deletion_and_full_db_scan(client):
    """
    FIX 5:
    Delete through real route.
    Scans every table and column of the real database for student_id and override reason text
    and asserts zero hits.
    Also verifies device purge token lifecycle.
    """
    tokens = get_tokens(client)
    t8a_hdr = {"Authorization": f"Bearer {tokens['teacher_8a']}"}

    del_sid = "stu_to_delete_99"
    salt = secrets.token_hex(8)
    pin_h = hash_pin("1111", salt)
    unique_reason_text = "UNIQUE_REASON_REMEDIAL_FOR_DELETION_TEST_XYZ"

    db = SessionLocal()
    try:
        db.add(StudentDB(
            pseudonymous_id=del_sid,
            subject_key="subj_del_k99",
            class_id="8-A",
            board="CBSE",
            medium_language="en",
            pin_hash=pin_h,
            salt=salt,
            consent_status="not requested"
        ))
        db.add(PlanDB(student_id=del_sid, class_id="8-A", current_stage="solve", current_concept_id="c8_math_linear_eq_one_var"))
        db.add(MasteryStateDB(student_id=del_sid, concept_id="c8_math_linear_eq_one_var", mastery_estimate=0.4))
        db.add(AttemptDB(id="att_del_01", student_id=del_sid, question_id="q1", concept_id="c8_math_linear_eq_one_var", selected_option_id="opt_1", is_correct=True))
        db.add(DecisionDB(id=9999, student_id=del_sid, class_id="8-A", action="NEXT", rule_id="R1", reason="Practice", stage="solve"))
        db.add(TeacherOverrideDB(student_id=del_sid, teacher_id="usr_sec_tea_8a", class_id="8-A", concept_id="c8_math_linear_eq_one_var", override_action="reassign", reason=unique_reason_text))
        db.add(SessionDB(token="token_to_purge_student", role="student", student_id=del_sid, expires_at=datetime.utcnow() + timedelta(hours=1)))
        db.commit()
    finally:
        db.close()

    # Call delete endpoint as authorized Teacher 8-A
    del_res = client.post("/api/privacy/delete-student", json={"student_id": del_sid}, headers=t8a_hdr)
    assert del_res.status_code == 200
    tombstone_key = del_res.json()["tombstone_key"]

    # Verify session was invalidated
    assert client.get(f"/api/student/{del_sid}/next-step", headers={"Authorization": "Bearer token_to_purge_student"}).status_code == 401

    # FULL DATABASE SCAN: Inspect every table and every text column in the entire SQLite database!
    db = SessionLocal()
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.bind)
        table_names = inspector.get_table_names()

        for table in table_names:
            columns = inspector.get_columns(table)
            for col in columns:
                col_name = col["name"]
                col_type = str(col["type"]).lower()
                if "char" in col_type or "text" in col_type or "string" in col_type:
                    # Check for student ID hit
                    query_sid = text(f"SELECT COUNT(*) FROM {table} WHERE {col_name} = :val")
                    res_sid = db.execute(query_sid, {"val": del_sid}).scalar()
                    assert res_sid == 0, f"RESIDUE FOUND: Table '{table}', Column '{col_name}' has hit for deleted student ID '{del_sid}'!"

                    # Check for override reason text hit
                    query_reason = text(f"SELECT COUNT(*) FROM {table} WHERE {col_name} LIKE :val")
                    res_reason = db.execute(query_reason, {"val": f"%{unique_reason_text}%"}).scalar()
                    assert res_reason == 0, f"RESIDUE FOUND: Table '{table}', Column '{col_name}' has hit for override reason text!"
    finally:
        db.close()

    # Verify offline purge token path (Fix 5)
    db = SessionLocal()
    try:
        dev = db.query(DeviceDB).filter(DeviceDB.class_id == "8-A").first()
        purge_token = dev.device_purge_token
        assert purge_token is not None
    finally:
        db.close()

    # Purge token used to fetch tombstones
    sync_purge = client.post("/api/privacy/sync", json={"device_id": dev.device_id, "class_id": "8-A"}, headers={"X-Device-Purge-Token": purge_token})
    assert sync_purge.status_code == 200
    assert tombstone_key in sync_purge.json()["applied_tombstones"]

    # Purge acknowledge
    ack_res = client.post("/api/device/purge-ack", json={"device_id": dev.device_id}, headers={"X-Device-Purge-Token": purge_token})
    assert ack_res.status_code == 200


# ==========================================
# FIX 6: PRODUCTION REFUSAL TEST
# ==========================================

def test_production_refusal_when_seeded_users_exist():
    """FIX 6: Startup refuses to start if ENV=production and seeded demo users exist."""
    db = SessionLocal()
    try:
        user = db.query(UserDB).first()
        if user:
            user.is_seeded = True
            db.commit()

        os.environ["ENV"] = "production"
        with pytest.raises(RuntimeError) as exc:
            verify_production_safeguards()
        assert "Production startup refused" in str(exc.value)
    finally:
        os.environ["ENV"] = "development"
        if user:
            user.is_seeded = False
            db.commit()
        db.close()
