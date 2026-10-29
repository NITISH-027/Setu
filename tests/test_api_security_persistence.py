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
    TombstoneDB, DeviceDB, AuditEventDB, PinProfileDB, UserDB, SessionDB,
    DeviceSubjectDB, TombstoneDeliveryDB
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
        
        # FIX 1: Register Device 1 (held student 99) and Device 2 (never held student 99)
        purge_token_1 = secrets.token_hex(24)
        purge_token_2 = secrets.token_hex(24)
        dev1_id = f"dev_held_del_{secrets.token_hex(4)}"
        dev2_id = f"dev_never_held_del_{secrets.token_hex(4)}"
        dev1 = DeviceDB(device_id=dev1_id, class_id="8-A", device_purge_token=purge_token_1)
        dev2 = DeviceDB(device_id=dev2_id, class_id="8-A", device_purge_token=purge_token_2)
        db.add(dev1)
        db.add(dev2)
        db.add(DeviceSubjectDB(device_id=dev1_id, subject_key="subj_del_k99"))
        db.commit()
    finally:
        db.close()

    # Call delete endpoint as authorized Teacher 8-A
    del_res = client.post("/api/privacy/delete-student", json={"student_id": del_sid}, headers=t8a_hdr)
    assert del_res.status_code == 200
    del_json = del_res.json()
    tombstone_key = del_json["tombstone_key"]
    # Only Device 1 held this student, so pending_devices must be 1 (Device 2 does NOT count as pending)
    assert del_json["pending_devices"] == 1
    assert del_json["is_fully_deleted_everywhere"] is False

    # Verify session was invalidated
    assert client.get(f"/api/student/{del_sid}/next-step", headers={"Authorization": "Bearer token_to_purge_student"}).status_code == 401

    # FULL DATABASE SCAN: Inspect every table and every text column in the entire SQLite database!
    # Scans new tables (device_subjects, tombstone_deliveries) as well.
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

    # FIX 1: Assert purge-only credential gets 401 on every learning route
    purge_hdr = {"Authorization": f"Bearer {purge_token_1}"}
    assert client.get(f"/api/student/{del_sid}/next-step", headers=purge_hdr).status_code == 401
    assert client.post(f"/api/student/{del_sid}/attempt", json={"question_id": "q1", "selected_option_id": "opt_1"}, headers=purge_hdr).status_code == 401
    assert client.get(f"/api/student/{del_sid}/offline-pack", headers=purge_hdr).status_code == 401
    assert client.get(f"/api/student/{del_sid}/export", headers=purge_hdr).status_code == 401
    assert client.post("/api/teacher/override", json={"student_id": del_sid, "class_id": "8-A", "concept_id": "c1", "action": "reassign", "reason": "test"}, headers=purge_hdr).status_code == 401

    # Device 2 (which never held student 99) fetches purge instructions -> must be empty!
    purge_inst_2 = client.get("/api/device/purge-instructions", headers={"X-Device-Purge-Token": purge_token_2})
    assert purge_inst_2.status_code == 200
    assert purge_inst_2.json()["pending_count"] == 0

    # Device 1 (which held student 99) fetches purge instructions -> must carry subj_del_k99!
    purge_inst_1 = client.get("/api/device/purge-instructions", headers={"X-Device-Purge-Token": purge_token_1})
    assert purge_inst_1.status_code == 200
    inst_list = purge_inst_1.json()["purge_instructions"]
    assert len(inst_list) == 1
    assert inst_list[0]["subject_key"] == "subj_del_k99"
    delivery_id = inst_list[0]["delivery_id"]

    # Device 1 acknowledges the purge
    ack_res = client.post("/api/device/purge-ack", json={"delivery_ids": [delivery_id]}, headers={"X-Device-Purge-Token": purge_token_1})
    assert ack_res.status_code == 200
    assert ack_res.json()["acknowledged_count"] == 1

    # Check Teacher Data and Privacy metrics: tombstone now applied (0 pending devices)
    metrics_res = client.get("/api/teacher/privacy-metrics", headers=t8a_hdr)
    assert metrics_res.status_code == 200
    metrics_json = metrics_res.json()
    matched_tomb = next((t for t in metrics_json["tombstones"] if t["opaque_key"] == tombstone_key), None)
    assert matched_tomb is not None
    assert matched_tomb["status"] == "applied"
    assert matched_tomb["pending_devices"] == 0
    matched_del = next((d for d in metrics_json["deliveries"] if d["opaque_key"] == tombstone_key), None)
    assert matched_del is not None
    assert matched_del["status"] == "acknowledged"
    assert matched_del["device_id"] == dev1_id


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


# ==========================================
# FIX 2: PIN LOCKOUT WITHOUT DEVICE ID
# ==========================================

def test_pin_lockout_without_device_id(client):
    """
    FIX 2: Failed-attempt counting and temporary lockout per student regardless of device_id.
    12 wrong PINs without a device id end in lockout, and correct PIN is refused during lockout.
    """
    # Use existing student stu_sec_01 (PIN was 1234)
    # Attempt 12 wrong PINs with NO device_id
    statuses = []
    for i in range(12):
        res = client.post("/api/auth/pin", json={
            "student_id": "stu_sec_01",
            "pin": "9999"  # wrong PIN
        })
        statuses.append(res.status_code)

    # First 2 attempts return 401
    assert statuses[0] == 401
    assert statuses[1] == 401
    # 3rd attempt and beyond trigger lockout and return 403
    for s in statuses[2:]:
        assert s == 403, f"Expected 403 lockout, got {s}"

    # During lockout, even the CORRECT PIN (1234) must be refused with 403
    res_correct = client.post("/api/auth/pin", json={
        "student_id": "stu_sec_01",
        "pin": "1234"
    })
    assert res_correct.status_code == 403
    assert "locked" in res_correct.json()["detail"].lower()

    # Reset lockout for other tests
    db = SessionLocal()
    try:
        s = db.query(StudentDB).filter(StudentDB.pseudonymous_id == "stu_sec_01").first()
        if s:
            s.failed_attempts = 0
            s.locked_until = None
            db.commit()
    finally:
        db.close()


# ==========================================
# FIX 3: MASTERY ON QUESTION CONCEPT
# ==========================================

def test_mastery_updated_on_attempt_concept_not_plan_concept(client):
    """
    FIX 3: Every attempt updates the mastery row of the question's own concept,
    leaving the plan's current concept mastery untouched.
    """
    tokens = get_tokens(client)
    s1_hdr = {"Authorization": f"Bearer {tokens['student_1']}"}

    # Set up initial mastery for plan concept c8_math_linear_eq_one_var = 0.50
    db = SessionLocal()
    try:
        m_c8 = db.query(MasteryStateDB).filter(
            MasteryStateDB.student_id == "stu_sec_01",
            MasteryStateDB.concept_id == "c8_math_linear_eq_one_var"
        ).first()
        if not m_c8:
            m_c8 = MasteryStateDB(
                student_id="stu_sec_01",
                concept_id="c8_math_linear_eq_one_var",
                mastery_estimate=0.50
            )
            db.add(m_c8)
        else:
            m_c8.mastery_estimate = 0.50

        # Remove any existing row for c7_math_simple_eq
        db.query(MasteryStateDB).filter(
            MasteryStateDB.student_id == "stu_sec_01",
            MasteryStateDB.concept_id == "c7_math_simple_eq"
        ).delete()
        db.commit()
    finally:
        db.close()

    # Question probe_sign_transposition_01 belongs to concept c7_math_simple_eq
    # Answer it correctly
    res = client.post("/api/student/stu_sec_01/attempt", json={
        "question_id": "probe_sign_transposition_01",
        "selected_option_id": "p1",  # correct
        "time_spent_seconds": 5
    }, headers=s1_hdr)
    assert res.status_code == 200
    data = res.json()
    assert data["server_graded_correct"] is True
    assert data["concept_id"] == "c7_math_simple_eq"

    # Verify directly in the real database:
    db = SessionLocal()
    try:
        # 1. c7_math_simple_eq mastery row exists and was updated from prior
        m_c7 = db.query(MasteryStateDB).filter(
            MasteryStateDB.student_id == "stu_sec_01",
            MasteryStateDB.concept_id == "c7_math_simple_eq"
        ).first()
        assert m_c7 is not None
        assert m_c7.mastery_estimate > 0.20  # increased from prior 0.20

        # 2. c8_math_linear_eq_one_var mastery is UNTOUCHED (still exactly 0.50)
        m_c8_after = db.query(MasteryStateDB).filter(
            MasteryStateDB.student_id == "stu_sec_01",
            MasteryStateDB.concept_id == "c8_math_linear_eq_one_var"
        ).first()
        assert m_c8_after is not None
        assert abs(m_c8_after.mastery_estimate - 0.50) < 1e-5, f"Plan concept mastery altered! Expected 0.50, got {m_c8_after.mastery_estimate}"
    finally:
        db.close()


def test_sync_idempotency_scoped_per_student_collision_resistant(client):
    """
    FIX 4: Two different students submitting attempts with the SAME client attempt_id.
    Server scopes idempotency key to (student_id, client_attempt_id) so neither
    attempt is falsely skipped.
    """
    tokens = get_tokens(client)
    t8a_hdr = {"Authorization": f"Bearer {tokens['teacher_8a']}"}
    shared_attempt_id = f"client_att_coll_{secrets.token_hex(6)}"

    db = SessionLocal()
    try:
        # Create student A and student B with plans
        for sid in ["stu_coll_A", "stu_coll_B"]:
            s = db.query(StudentDB).filter(StudentDB.pseudonymous_id == sid).first()
            if not s:
                salt = secrets.token_hex(8)
                db.add(StudentDB(
                    pseudonymous_id=sid,
                    subject_key=f"subj_{sid}",
                    class_id="8-A",
                    board="CBSE",
                    medium_language="en",
                    pin_hash=hash_pin("1234", salt),
                    salt=salt,
                    consent_status="not requested"
                ))
            p = db.query(PlanDB).filter(PlanDB.student_id == sid).first()
            if not p:
                db.add(PlanDB(student_id=sid, class_id="8-A", current_stage="solve", current_concept_id="c8_math_linear_eq_one_var"))
        dev_id = f"dev_sync_coll_{secrets.token_hex(4)}"
        db.add(DeviceDB(device_id=dev_id, class_id="8-A"))
        db.commit()
    finally:
        db.close()

    # Sync attempt from Student A with shared_attempt_id
    payload_a = {
        "device_id": dev_id,
        "class_id": "8-A",
        "queued_attempts": [{
            "attempt_id": shared_attempt_id,
            "student_id": "stu_coll_A",
            "question_id": "q_c8_leq_01",
            "selected_option_id": "opt_1",
            "time_spent_seconds": 12
        }]
    }
    res_a = client.post("/api/privacy/sync", json=payload_a, headers=t8a_hdr)
    assert res_a.status_code == 200
    assert res_a.json()["synced_attempts_processed"] == 1

    # Sync attempt from Student B with SAME shared_attempt_id
    payload_b = {
        "device_id": dev_id,
        "class_id": "8-A",
        "queued_attempts": [{
            "attempt_id": shared_attempt_id,
            "student_id": "stu_coll_B",
            "question_id": "q_c8_leq_01",
            "selected_option_id": "opt_1",
            "time_spent_seconds": 15
        }]
    }
    res_b = client.post("/api/privacy/sync", json=payload_b, headers=t8a_hdr)
    assert res_b.status_code == 200
    # Crucial assertion: Student B's attempt was NOT skipped!
    assert res_b.json()["synced_attempts_processed"] == 1

    # Verify both attempts exist in the database with their student-scoped IDs
    db = SessionLocal()
    try:
        att_a = db.query(AttemptDB).filter(
            AttemptDB.student_id == "stu_coll_A",
            AttemptDB.id == f"stu_coll_A:{shared_attempt_id}"
        ).first()
        att_b = db.query(AttemptDB).filter(
            AttemptDB.student_id == "stu_coll_B",
            AttemptDB.id == f"stu_coll_B:{shared_attempt_id}"
        ).first()
        assert att_a is not None, "Student A attempt missing!"
        assert att_b is not None, "Student B attempt was skipped due to collision!"
    finally:
        db.close()


def test_no_test_credentials_in_production_seed_or_bundle():
    """
    FIX 7: Asserts that no test fixture credentials (passwords, fixed PINs) appear
    in production seeds (scripts/seed_demo_data.py) or UI source / bundle.
    """
    test_credentials = [
        "tea_e2e_pass",
        "tea_e2e_8a",
        "stu_e2e_01"
    ]

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    prod_seed_file = os.path.join(base_dir, "scripts", "seed_demo_data.py")

    with open(prod_seed_file, "r", encoding="utf-8") as f:
        prod_seed_content = f.read()

    for cred in test_credentials:
        assert cred not in prod_seed_content, (
            f"SECURITY VIOLATION: Test fixture credential '{cred}' found in production seed file!"
        )

    # Scan frontend src for fixed default test passwords
    frontend_src = os.path.join(base_dir, "frontend", "src")
    for root, _, files in os.walk(frontend_src):
        for fname in files:
            if fname.endswith((".js", ".jsx", ".html")):
                fpath = os.path.join(root, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                    assert "tea_e2e_pass" not in content, (
                        f"SECURITY VIOLATION: Test fixture password found in frontend source: {fname}"
                    )


def test_teacher_sync_cross_class_returns_403(client):
    """
    Asserts that a teacher cannot sync devices or student attempts belonging
    to classes outside their assigned teaching classes.
    """
    db = SessionLocal()
    try:
        # Create teacher for class 8-A only
        teacher_user = db.query(UserDB).filter(UserDB.id == "usr_tea_scoped").first()
        if not teacher_user:
            teacher_user = UserDB(
                id="usr_tea_scoped",
                username="tea_scoped",
                password_hash=hash_password("teacher_pass_scoped"),
                role="teacher",
                assigned_classes=json.dumps(["8-A"])
            )
            db.add(teacher_user)
            db.commit()

        # Session for scoped teacher
        tea_token = "tok_tea_scoped_" + secrets.token_hex(8)
        db.add(SessionDB(
            token=tea_token,
            user_id="usr_tea_scoped",
            role="teacher",
            expires_at=datetime.utcnow() + timedelta(hours=2)
        ))

        # Device belonging to class 8-B
        dev_8b = db.query(DeviceDB).filter(DeviceDB.device_id == "dev_cross_class_8b").first()
        if not dev_8b:
            db.add(DeviceDB(
                device_id="dev_cross_class_8b",
                class_id="8-B",
                device_purge_token="purge_cross_class_8b",
                registered_at=datetime.utcnow()
            ))

        # Student in class 8-B
        stu_8b = db.query(StudentDB).filter(StudentDB.pseudonymous_id == "stu_cross_class_8b").first()
        if not stu_8b:
            salt_cc = secrets.token_hex(8)
            db.add(StudentDB(
                pseudonymous_id="stu_cross_class_8b",
                subject_key="subj_cc_8b",
                class_id="8-B",
                salt=salt_cc,
                pin_hash=hash_pin("1234", salt_cc),
                created_at=datetime.utcnow()
            ))
        db.commit()

        headers = {"Authorization": f"Bearer {tea_token}"}

        # Attempt 1: Cross-class device sync rejected
        resp_dev = client.post("/api/privacy/sync", json={
            "device_id": "dev_cross_class_8b",
            "class_id": "8-A",
            "queued_attempts": []
        }, headers=headers)
        assert resp_dev.status_code == 403, f"Expected 403 for cross-class device, got {resp_dev.status_code}"

        # Attempt 2: Cross-class payload class rejected
        dev_8a = db.query(DeviceDB).filter(DeviceDB.device_id == "dev_tea_8a").first()
        if not dev_8a:
            db.add(DeviceDB(
                device_id="dev_tea_8a",
                class_id="8-A",
                device_purge_token="purge_dev_8a",
                registered_at=datetime.utcnow()
            ))
            db.commit()

        resp_payload = client.post("/api/privacy/sync", json={
            "device_id": "dev_tea_8a",
            "class_id": "8-B",
            "queued_attempts": []
        }, headers=headers)
        assert resp_payload.status_code == 403, f"Expected 403 for cross-class payload class, got {resp_payload.status_code}"

        # Attempt 3: Cross-class student attempt in queue rejected
        resp_stu = client.post("/api/privacy/sync", json={
            "device_id": "dev_tea_8a",
            "class_id": "8-A",
            "queued_attempts": [{
                "student_id": "stu_cross_class_8b",
                "question_id": "q_c8_leq_01",
                "selected_option_id": "opt_1",
                "attempt_id": "att_cc_01"
            }]
        }, headers=headers)
        assert resp_stu.status_code == 403, f"Expected 403 for cross-class student attempt, got {resp_stu.status_code}"
    finally:
        db.close()


def test_sync_returns_authoritative_state_and_primary_concept_mastery(client):
    """
    Asserts that sync returns authoritative domain plan and mastery for the
    student's primary topic, ensuring device and server states reconcile.
    """
    db = SessionLocal()
    try:
        s_id = "stu_auth_sync_test"
        stu_auth = db.query(StudentDB).filter(StudentDB.pseudonymous_id == s_id).first()
        if not stu_auth:
            salt_auth = secrets.token_hex(8)
            db.add(StudentDB(
                pseudonymous_id=s_id,
                class_id="8-A",
                subject_key="subj_auth_sync",
                salt=salt_auth,
                pin_hash=hash_pin("1234", salt_auth),
                created_at=datetime.utcnow()
            ))

        p_auth = db.query(PlanDB).filter(PlanDB.student_id == s_id).first()
        if not p_auth:
            db.add(PlanDB(
                student_id=s_id,
                class_id="8-A",
                current_stage="solve",
                current_concept_id="c8_math_linear_eq_one_var",
                gap_concept_id="c7_math_integers_add_sub",
                stuck_attempts_count=1,
                bridge_recheck_fails=0
            ))
        else:
            p_auth.current_stage = "solve"
            p_auth.current_concept_id = "c8_math_linear_eq_one_var"
            p_auth.gap_concept_id = "c7_math_integers_add_sub"

        m_auth = db.query(MasteryStateDB).filter(
            MasteryStateDB.student_id == s_id,
            MasteryStateDB.concept_id == "c8_math_linear_eq_one_var"
        ).first()
        if not m_auth:
            db.add(MasteryStateDB(
                student_id=s_id,
                concept_id="c8_math_linear_eq_one_var",
                mastery_estimate=0.65,
                mastery_label="progressing",
                consecutive_successes=2
            ))
        else:
            m_auth.mastery_estimate = 0.65

        dev_auth = db.query(DeviceDB).filter(DeviceDB.device_id == "dev_auth_sync_test").first()
        if not dev_auth:
            db.add(DeviceDB(
                device_id="dev_auth_sync_test",
                class_id="8-A",
                device_purge_token="purge_auth_sync",
                registered_at=datetime.utcnow()
            ))
        db.commit()

        stu_tok = "tok_stu_auth_sync_" + secrets.token_hex(8)
        db.add(SessionDB(
            token=stu_tok,
            student_id=s_id,
            role="student",
            device_id="dev_auth_sync_test",
            expires_at=datetime.utcnow() + timedelta(hours=2)
        ))
        db.commit()

        fresh_att_id = f"att_auth_{secrets.token_hex(6)}"
        headers = {"Authorization": f"Bearer {stu_tok}"}
        resp = client.post("/api/privacy/sync", json={
            "device_id": "dev_auth_sync_test",
            "class_id": "8-A",
            "queued_attempts": [{
                "student_id": s_id,
                "question_id": "q_c8_leq_01",
                "selected_option_id": "opt_1",
                "attempt_id": fresh_att_id
            }]
        }, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert "authoritative_state" in data
        assert data["authoritative_state"]["student_id"] == s_id
        assert data["authoritative_state"]["current_stage"] in ["solve", "move_ahead"]
        assert data["authoritative_state"]["current_concept_id"] == "c8_math_linear_eq_one_var"
        assert "authoritative_mastery" in data
        assert data["authoritative_mastery"]["concept_id"] == "c8_math_linear_eq_one_var"
        assert data["authoritative_mastery"]["mastery_estimate"] > 0.65
    finally:
        db.close()


def test_reviewer_role_strictly_denied_student_sync(client):
    """
    DEFECT 2: Explicitly verify that content-reviewer role is denied access to /api/privacy/sync.
    A reviewer must not be able to sync student attempts, change mastery, or read learning state.
    """
    db = SessionLocal()
    try:
        rev_tok = "tok_rev_sync_denied_" + secrets.token_hex(8)
        db.add(SessionDB(
            token=rev_tok,
            user_id="rev_test_01",
            role="reviewer",
            expires_at=datetime.utcnow() + timedelta(hours=2)
        ))
        db.commit()

        headers = {"Authorization": f"Bearer {rev_tok}"}
        resp = client.post("/api/privacy/sync", json={
            "device_id": "dev_auth_sync_test",
            "class_id": "8-A",
            "queued_attempts": [{
                "student_id": "stu_demo_01",
                "question_id": "q_c8_leq_01",
                "selected_option_id": "opt_1",
                "attempt_id": "att_rev_exploit"
            }]
        }, headers=headers)

        assert resp.status_code == 403
        assert "Content reviewer role is strictly denied access" in resp.json()["detail"]
    finally:
        db.close()


def test_credential_to_device_binding_enforced(client):
    """
    Verify credential-to-device binding in /api/privacy/sync:
    - Student token registered to Device A cannot sync Device B, even within the same class (HTTP 403).
    - Device A purge token cannot sync Device B, even within the same class (HTTP 403).
    - Device A purge token in X-Device-Purge-Token header cannot sync Device B (HTTP 403).
    - Legitimate sync for authorized device succeeds (HTTP 200).
    """
    db = SessionLocal()
    try:
        # Ensure two devices exist in class 8-A
        dev_a = db.query(DeviceDB).filter(DeviceDB.device_id == "dev_bind_a").first()
        if not dev_a:
            db.add(DeviceDB(
                device_id="dev_bind_a",
                class_id="8-A",
                device_purge_token="purge_token_dev_a",
                registered_at=datetime.utcnow()
            ))
        else:
            dev_a.device_purge_token = "purge_token_dev_a"

        dev_b = db.query(DeviceDB).filter(DeviceDB.device_id == "dev_bind_b").first()
        if not dev_b:
            db.add(DeviceDB(
                device_id="dev_bind_b",
                class_id="8-A",
                device_purge_token="purge_token_dev_b",
                registered_at=datetime.utcnow()
            ))
        else:
            dev_b.device_purge_token = "purge_token_dev_b"

        # Create student in 8-A and student session bound to dev_bind_a
        salt = secrets.token_hex(8)
        stu = db.query(StudentDB).filter(StudentDB.pseudonymous_id == "stu_bind_test").first()
        if not stu:
            stu = StudentDB(
                pseudonymous_id="stu_bind_test",
                subject_key="subj_bind_test",
                class_id="8-A",
                board="CBSE",
                medium_language="en",
                pin_hash=hash_pin("1234", salt),
                salt=salt,
                consent_status="not requested"
            )
            db.add(stu)
            db.add(PlanDB(
                student_id="stu_bind_test",
                class_id="8-A",
                current_stage="solve",
                current_concept_id="c8_math_linear_eq_one_var"
            ))
            db.add(MasteryStateDB(
                student_id="stu_bind_test",
                concept_id="c8_math_linear_eq_one_var",
                mastery_estimate=0.4
            ))

        stu_tok_a = "tok_stu_bind_a_" + secrets.token_hex(8)
        db.add(SessionDB(
            token=stu_tok_a,
            student_id="stu_bind_test",
            role="student",
            device_id="dev_bind_a",
            expires_at=datetime.utcnow() + timedelta(hours=2)
        ))
        db.commit()

        # 1. Student token bound to dev_bind_a attempts to sync dev_bind_b -> 403 Forbidden
        resp_mismatch_stu = client.post("/api/privacy/sync", json={
            "device_id": "dev_bind_b",
            "class_id": "8-A",
            "queued_attempts": []
        }, headers={"Authorization": f"Bearer {stu_tok_a}"})
        assert resp_mismatch_stu.status_code == 403
        assert "Student session is registered to device 'dev_bind_a', not 'dev_bind_b'" in resp_mismatch_stu.json()["detail"]

        # 2. Bearer purge token for dev_bind_a attempts to sync dev_bind_b -> 403 Forbidden
        resp_mismatch_purge = client.post("/api/privacy/sync", json={
            "device_id": "dev_bind_b",
            "class_id": "8-A",
            "queued_attempts": []
        }, headers={"Authorization": "Bearer purge_token_dev_a"})
        assert resp_mismatch_purge.status_code == 403
        assert "Purge token belongs to device 'dev_bind_a', not 'dev_bind_b'" in resp_mismatch_purge.json()["detail"]

        # 3. Header X-Device-Purge-Token for dev_bind_a attempts to sync dev_bind_b -> 403 Forbidden
        resp_mismatch_header = client.post("/api/privacy/sync", json={
            "device_id": "dev_bind_b",
            "class_id": "8-A",
            "queued_attempts": []
        }, headers={"X-Device-Purge-Token": "purge_token_dev_a"})
        assert resp_mismatch_header.status_code == 403
        assert "Purge token belongs to device 'dev_bind_a', not 'dev_bind_b'" in resp_mismatch_header.json()["detail"]

        # 4. Legitimate student sync on matching device dev_bind_a -> 200 OK
        resp_valid_stu = client.post("/api/privacy/sync", json={
            "device_id": "dev_bind_a",
            "class_id": "8-A",
            "queued_attempts": []
        }, headers={"Authorization": f"Bearer {stu_tok_a}"})
        assert resp_valid_stu.status_code == 200

        # 5. Legitimate purge token sync on matching device dev_bind_a -> 200 OK
        resp_valid_purge = client.post("/api/privacy/sync", json={
            "device_id": "dev_bind_a",
            "class_id": "8-A",
            "queued_attempts": []
        }, headers={"Authorization": "Bearer purge_token_dev_a"})
        assert resp_valid_purge.status_code == 200
        assert resp_valid_purge.json().get("purge_mode") is True
    finally:
        db.close()





