import sys
import os
import pytest
from starlette.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "Uncalibrated models" in data["honesty_notice"]


def test_get_pack_and_coverage(client):
    res_pack = client.get("/api/pack")
    assert res_pack.status_code == 200
    pack_data = res_pack.json()
    assert len(pack_data["concepts"]) >= 20

    res_cov = client.get("/api/coverage")
    assert res_cov.status_code == 200
    cov = res_cov.json()
    assert cov["percent_human_reviewed"] == 0.0


def test_student_flow_via_api(client):
    # 1. Fetch next step for demo student
    res = client.get("/api/student/stu_demo_01/next-step")
    assert res.status_code == 200
    step_data = res.json()
    assert step_data["step"]["stage"] == "solve"
    assert step_data["item"] is not None

    q_id = step_data["item"]["id"]
    concept_id = step_data["item"]["concept"]

    # 2. Submit wrong attempt
    att_payload = {
        "question_id": q_id,
        "concept_id": concept_id,
        "selected_option_id": "opt_2",
        "is_correct": False,
        "misconception_tag": "tag_sign_error_on_transposition"
    }
    res_att = client.post("/api/student/stu_demo_01/attempt", json=att_payload)
    assert res_att.status_code == 200
    att_data = res_att.json()
    assert att_data["decision"]["action"] == "ADMINISTER_PROBE"
    assert att_data["mastery_label"] == "uncalibrated, hand-set"

    # 3. Next step is now PROBE
    res_probe = client.get("/api/student/stu_demo_01/next-step")
    assert res_probe.status_code == 200
    probe_step = res_probe.json()
    assert probe_step["step"]["stage"] == "probe"


def test_teacher_class_dashboard_and_override_via_api(client):
    # 1. Valid access for 8-A by tea_01
    res = client.get("/api/teacher/class/8-A?teacher_id=tea_01")
    assert res.status_code == 200
    dash = res.json()
    assert dash["class_id"] == "8-A"

    # 2. Unauthorized access: tea_01 tries to view 8-B
    res_unauth = client.get("/api/teacher/class/8-B?teacher_id=tea_01")
    assert res_unauth.status_code == 403

    # 3. Apply override with empty reason -> must fail 400
    bad_override = {
        "teacher_id": "tea_01",
        "class_id": "8-A",
        "student_id": "stu_demo_01",
        "concept_id": "c8_math_rational_ops",
        "action": "assign_concept",
        "reason": "   "
    }
    res_bad = client.post("/api/teacher/override", json=bad_override)
    assert res_bad.status_code == 400

    # 4. Valid override
    valid_override = {
        "teacher_id": "tea_01",
        "class_id": "8-A",
        "student_id": "stu_demo_01",
        "concept_id": "c8_math_rational_ops",
        "action": "assign_concept",
        "reason": "Move to rational numbers after clinic"
    }
    res_ov = client.post("/api/teacher/override", json=valid_override)
    assert res_ov.status_code == 200
    assert res_ov.json()["override"]["reason"] == "Move to rational numbers after clinic"


def test_privacy_delete_and_sync_via_api(client):
    # Delete student
    del_res = client.post("/api/privacy/delete-student", json={"student_id": "stu_demo_01"})
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["student_id"] == "stu_demo_01"
    assert len(del_data["tombstone_key"]) >= 16

    # Device sync applies tombstone
    sync_res = client.post("/api/privacy/sync", json={"device_id": "dev_demo_tablet", "class_id": "8-A"})
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert del_data["tombstone_key"] in sync_data["applied_tombstones"]


def test_paper_mode_html_endpoint(client):
    res = client.get("/api/paper/sheet/c8_math_linear_eq_one_var")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Setu Paper Mode Worksheet" in res.text
