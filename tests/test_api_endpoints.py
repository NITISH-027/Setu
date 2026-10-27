import sys
import os
import secrets
import pytest
from starlette.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app
from app.db import init_db, SessionLocal, StudentDB, PlanDB, MasteryStateDB, UserDB, DeviceDB, PinProfileDB
from app.auth.security import hash_password, hash_pin


@pytest.fixture
def client():
    init_db()
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_api_test_fixtures():
    init_db()
    db = SessionLocal()
    try:
        # Teacher for 8-A
        if not db.query(UserDB).filter(UserDB.username == "tea_api_01").first():
            db.add(UserDB(
                id="usr_tea_api_01",
                username="tea_api_01",
                password_hash=hash_password("tea_pass_api_123"),
                role="teacher",
                assigned_classes='["8-A"]'
            ))

        # Teacher for 8-B
        if not db.query(UserDB).filter(UserDB.username == "tea_api_02").first():
            db.add(UserDB(
                id="usr_tea_api_02",
                username="tea_api_02",
                password_hash=hash_password("tea_pass_api_456"),
                role="teacher",
                assigned_classes='["8-B"]'
            ))

        # Student for 8-A
        s_id = "stu_api_demo_01"
        if not db.query(StudentDB).filter(StudentDB.pseudonymous_id == s_id).first():
            salt = secrets.token_hex(8)
            pin_h = hash_pin("1234", salt)
            db.add(StudentDB(
                pseudonymous_id=s_id,
                subject_key="subj_api_demo_k1",
                class_id="8-A",
                board="CBSE",
                medium_language="en",
                pin_hash=pin_h,
                salt=salt,
                consent_status="not requested"
            ))
            db.add(PlanDB(
                student_id=s_id,
                class_id="8-A",
                current_stage="solve",
                current_concept_id="c8_math_linear_eq_one_var",
                reason="Practice sequence"
            ))
            db.add(MasteryStateDB(
                student_id=s_id,
                concept_id="c8_math_linear_eq_one_var",
                mastery_estimate=0.25
            ))
            if not db.query(DeviceDB).filter(DeviceDB.device_id == "dev_api_tablet").first():
                db.add(DeviceDB(
                    device_id="dev_api_tablet",
                    class_id="8-A"
                ))
            if not db.query(PinProfileDB).filter(PinProfileDB.device_id == "dev_api_tablet", PinProfileDB.student_id == s_id).first():
                db.add(PinProfileDB(
                    device_id="dev_api_tablet",
                    student_id=s_id,
                    class_id="8-A",
                    pin_hash=pin_h,
                    salt=salt
                ))
        db.commit()
    finally:
        db.close()


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "Uncalibrated models" in data["honesty_notice"]


def test_get_pack_and_coverage(client):
    # Public pack download: must be answer-free
    res_pack = client.get("/api/pack")
    assert res_pack.status_code == 200
    pack_data = res_pack.json()
    assert len(pack_data["concepts"]) >= 20
    # FIX 2: Check questions in public pack have no is_correct
    for q in pack_data.get("questions", []):
        assert "worked_solution" not in q
        for opt in q.get("options", []):
            assert "is_correct" not in opt
            assert "misconception_tag" not in opt

    # Coverage endpoint requires session
    t_login = client.post("/api/auth/login", json={"username": "tea_api_01", "password": "tea_pass_api_123"})
    token = t_login.json()["access_token"]
    res_cov = client.get("/api/coverage", headers={"Authorization": f"Bearer {token}"})
    assert res_cov.status_code == 200
    cov = res_cov.json()
    assert cov["percent_human_reviewed"] == 0.0


def test_student_flow_via_api(client):
    # Authenticate student via PIN
    pin_res = client.post("/api/auth/pin", json={
        "device_id": "dev_api_tablet",
        "student_id": "stu_api_demo_01",
        "pin": "1234"
    })
    assert pin_res.status_code == 200
    token = pin_res.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    # 1. Fetch next step for student
    res = client.get("/api/student/stu_api_demo_01/next-step", headers=auth_header)
    assert res.status_code == 200
    step_data = res.json()
    assert step_data["step"]["stage"] == "solve"
    assert step_data["item"] is not None

    # FIX 2: Confirm returned item options have no is_correct or misconception_tag
    for opt in step_data["item"]["options"]:
        assert "is_correct" not in opt
        assert "misconception_tag" not in opt

    q_id = step_data["item"]["id"]
    concept_id = step_data["item"]["concept"]

    # 2. Submit wrong attempt
    att_payload = {
        "question_id": q_id,
        "concept_id": concept_id,
        "selected_option_id": "opt_2"
    }
    res_att = client.post("/api/student/stu_api_demo_01/attempt", json=att_payload, headers=auth_header)
    assert res_att.status_code == 200
    att_data = res_att.json()
    assert att_data["decision"]["action"] == "ADMINISTER_PROBE"
    assert att_data["mastery_label"] == "uncalibrated, hand-set"

    # 3. Next step is now PROBE
    res_probe = client.get("/api/student/stu_api_demo_01/next-step", headers=auth_header)
    assert res_probe.status_code == 200
    probe_step = res_probe.json()
    assert probe_step["step"]["stage"] == "probe"


def test_teacher_class_dashboard_and_override_via_api(client):
    # Login as Teacher 8-A
    t_login = client.post("/api/auth/login", json={"username": "tea_api_01", "password": "tea_pass_api_123"})
    assert t_login.status_code == 200
    token_8a = t_login.json()["access_token"]
    header_8a = {"Authorization": f"Bearer {token_8a}"}

    # 1. Valid access for 8-A
    res = client.get("/api/teacher/class/8-A", headers=header_8a)
    assert res.status_code == 200
    dash = res.json()
    assert dash["class_id"] == "8-A"

    # 2. Unauthorized access: Teacher 8-A tries to view 8-B -> 403
    res_unauth = client.get("/api/teacher/class/8-B", headers=header_8a)
    assert res_unauth.status_code == 403

    # 3. Apply override with empty reason -> 400
    bad_override = {
        "class_id": "8-A",
        "student_id": "stu_api_demo_01",
        "concept_id": "c8_math_rational_ops",
        "action": "assign_concept",
        "reason": "   "
    }
    res_bad = client.post("/api/teacher/override", json=bad_override, headers=header_8a)
    assert res_bad.status_code == 400

    # 4. Valid override
    valid_override = {
        "class_id": "8-A",
        "student_id": "stu_api_demo_01",
        "concept_id": "c8_math_rational_ops",
        "action": "assign_concept",
        "reason": "Move to rational numbers after clinic"
    }
    res_ov = client.post("/api/teacher/override", json=valid_override, headers=header_8a)
    assert res_ov.status_code == 200
    assert res_ov.json()["override"]["reason"] == "Move to rational numbers after clinic"


def test_privacy_delete_and_sync_via_api(client):
    # Teacher 8-A login
    t_login = client.post("/api/auth/login", json={"username": "tea_api_01", "password": "tea_pass_api_123"})
    token_8a = t_login.json()["access_token"]
    header_8a = {"Authorization": f"Bearer {token_8a}"}

    # Delete student
    del_res = client.post("/api/privacy/delete-student", json={"student_id": "stu_api_demo_01"}, headers=header_8a)
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert len(del_data["tombstone_key"]) >= 16

    # Device sync with teacher session applies tombstone
    sync_res = client.post("/api/privacy/sync", json={"device_id": "dev_api_tablet", "class_id": "8-A"}, headers=header_8a)
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert del_data["tombstone_key"] in sync_data["applied_tombstones"]


def test_paper_mode_html_endpoint(client):
    # Teacher login
    t_login = client.post("/api/auth/login", json={"username": "tea_api_01", "password": "tea_pass_api_123"})
    token_8a = t_login.json()["access_token"]
    header_8a = {"Authorization": f"Bearer {token_8a}"}

    res = client.get("/api/paper/sheet/c8_math_linear_eq_one_var", headers=header_8a)
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Setu Paper Mode Worksheet" in res.text
