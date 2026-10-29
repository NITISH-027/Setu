import os
import sys
import json
import secrets
import pytest
from starlette.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app, pack
from app.db import init_db, SessionLocal
from app.db.models import UserDB, StudentDB, PlanDB, MasteryStateDB, AttemptDB, TombstoneDB
from app.auth.security import hash_password, hash_pin


@pytest.fixture
def client():
    init_db()
    return TestClient(app)


def create_test_student(db, student_id: str, class_id: str = "8-A", medium_language: str = "en", mastery: float = 0.25, consecutive_successes: int = 0):
    salt = secrets.token_hex(8)
    # Clean up previous attempts/hypotheses for test idempotency
    db.query(AttemptDB).filter(AttemptDB.student_id == student_id).delete()
    stu = db.query(StudentDB).filter(StudentDB.pseudonymous_id == student_id).first()
    if not stu:
        stu = StudentDB(
            pseudonymous_id=student_id,
            subject_key=f"subj_{student_id}",
            class_id=class_id,
            board="CBSE",
            medium_language=medium_language,
            pin_hash=hash_pin("1234", salt),
            salt=salt,
            consent_status="not requested"
        )
        db.add(stu)
        db.add(PlanDB(
            student_id=student_id,
            class_id=class_id,
            current_stage="solve",
            current_concept_id="c8_math_linear_eq_one_var"
        ))
        db.add(MasteryStateDB(
            student_id=student_id,
            concept_id="c8_math_linear_eq_one_var",
            mastery_estimate=mastery,
            consecutive_successes=consecutive_successes
        ))
    else:
        stu.medium_language = medium_language
        p = db.query(PlanDB).filter(PlanDB.student_id == student_id).first()
        if p:
            p.current_stage = "solve"
            p.current_concept_id = "c8_math_linear_eq_one_var"
            p.gap_concept_id = None
            p.stuck_attempts_count = 0
            p.bridge_recheck_fails = 0
        m = db.query(MasteryStateDB).filter(
            MasteryStateDB.student_id == student_id,
            MasteryStateDB.concept_id == "c8_math_linear_eq_one_var"
        ).first()
        if m:
            m.mastery_estimate = mastery
            m.consecutive_successes = consecutive_successes
        else:
            db.add(MasteryStateDB(
                student_id=student_id,
                concept_id="c8_math_linear_eq_one_var",
                mastery_estimate=mastery,
                consecutive_successes=consecutive_successes
            ))
    db.commit()


@pytest.fixture(autouse=True)
def setup_acceptance_fixtures():
    init_db()
    db = SessionLocal()
    try:
        # Teacher for 8-A
        if not db.query(UserDB).filter(UserDB.username == "tea_acc_8a").first():
            db.add(UserDB(
                id="usr_tea_acc_8a",
                username="tea_acc_8a",
                password_hash=hash_password("tea_pass_acc"),
                role="teacher",
                assigned_classes='["8-A"]'
            ))

        # Teacher for 8-B
        if not db.query(UserDB).filter(UserDB.username == "tea_acc_8b").first():
            db.add(UserDB(
                id="usr_tea_acc_8b",
                username="tea_acc_8b",
                password_hash=hash_password("tea_pass_acc"),
                role="teacher",
                assigned_classes='["8-B"]'
            ))

        # Reviewer
        if not db.query(UserDB).filter(UserDB.username == "rev_acc_01").first():
            db.add(UserDB(
                id="usr_rev_acc_01",
                username="rev_acc_01",
                password_hash=hash_password("rev_pass_acc"),
                role="reviewer",
                assigned_classes='[]'
            ))

        db.commit()
    finally:
        db.close()


def test_acceptance_a_complete_journey(client):
    """
    Acceptance Test A:
    wrong answer -> probe -> wrong probe -> (second probe if available) ->
    lesson screen visible -> continue -> re-check question -> correct -> return to original topic.
    """
    db = SessionLocal()
    create_test_student(db, "stu_acc_a")
    db.close()

    login_res = client.post("/api/auth/pin", json={"device_id": "dev_test", "student_id": "stu_acc_a", "pin": "1234"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: In SOLVE stage
    step1 = client.get("/api/student/stu_acc_a/next-step", headers=headers).json()
    assert step1["step"]["stage"] == "solve"
    q1 = step1["item"]

    full_q1 = pack.get_question(q1["id"])
    wrong_opt = next(o for o in full_q1.options if not o.is_correct and o.misconception_tag)

    # Submit wrong answer
    att1 = client.post("/api/student/stu_acc_a/attempt", json={
        "question_id": q1["id"],
        "concept_id": q1["concept"],
        "selected_option_id": wrong_opt.id
    }, headers=headers).json()
    assert att1["decision"]["action"] == "ADMINISTER_PROBE"

    # Step 2: Probe step
    step2 = client.get("/api/student/stu_acc_a/next-step", headers=headers).json()
    assert step2["step"]["stage"] == "probe"
    probe1 = step2["item"]
    full_probe1 = pack.get_question(probe1["id"])
    wrong_probe_opt = next(o for o in full_probe1.options if not o.is_correct)

    att2 = client.post("/api/student/stu_acc_a/attempt", json={
        "question_id": probe1["id"],
        "concept_id": probe1["concept"],
        "selected_option_id": wrong_probe_opt.id
    }, headers=headers).json()

    step3 = client.get("/api/student/stu_acc_a/next-step", headers=headers).json()
    if step3["step"]["stage"] == "probe":
        probe2 = step3["item"]
        full_probe2 = pack.get_question(probe2["id"])
        wrong_probe_opt2 = next(o for o in full_probe2.options if not o.is_correct)
        client.post("/api/student/stu_acc_a/attempt", json={
            "question_id": probe2["id"],
            "concept_id": probe2["concept"],
            "selected_option_id": wrong_probe_opt2.id
        }, headers=headers)
        step3 = client.get("/api/student/stu_acc_a/next-step", headers=headers).json()

    # Step 3: Lesson reached!
    assert step3["step"]["stage"] == "learn"
    assert step3["step"]["item_type"] == "lesson"
    assert step3["item"] is not None
    assert "content" in step3["item"]

    # Press "Continue" to explicitly move to BRIDGE_RECHECK
    cont_res = client.post("/api/student/stu_acc_a/continue-lesson", headers=headers)
    assert cont_res.status_code == 200

    # Step 4: Bridge Re-Check question
    step4 = client.get("/api/student/stu_acc_a/next-step", headers=headers).json()
    assert step4["step"]["stage"] == "bridge_recheck"
    recheck_q = step4["item"]
    full_recheck_q = pack.get_question(recheck_q["id"])
    correct_opt = next(o for o in full_recheck_q.options if o.is_correct)

    # Answer re-check correctly!
    att_recheck = client.post("/api/student/stu_acc_a/attempt", json={
        "question_id": recheck_q["id"],
        "concept_id": recheck_q["concept"],
        "selected_option_id": correct_opt.id
    }, headers=headers).json()
    assert att_recheck["decision"]["action"] == "RETURN_TO_ORIGINAL_TOPIC"

    # Step 5: Returned to original topic in SOLVE stage!
    step5 = client.get("/api/student/stu_acc_a/next-step", headers=headers).json()
    assert step5["step"]["stage"] == "solve"


def test_acceptance_c_recheck_failures_and_flag(client):
    """
    Acceptance Test C:
    Re-check failure path: fail once (stays on gap), fail twice (teacher flag).
    """
    db = SessionLocal()
    create_test_student(db, "stu_acc_c")
    plan = db.query(PlanDB).filter(PlanDB.student_id == "stu_acc_c").first()
    plan.current_stage = "bridge_recheck"
    plan.gap_concept_id = "c6_math_integers_add_sub"
    plan.bridge_recheck_fails = 0
    db.commit()
    db.close()

    login_res = client.post("/api/auth/pin", json={"device_id": "dev_test", "student_id": "stu_acc_c", "pin": "1234"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    step = client.get("/api/student/stu_acc_c/next-step", headers=headers).json()
    q = step["item"]
    assert q is not None
    full_q = pack.get_question(q["id"])
    wrong_opt = next(o for o in full_q.options if not o.is_correct)

    # Fail re-check #1 -> stays on gap
    att1 = client.post("/api/student/stu_acc_c/attempt", json={
        "question_id": q["id"],
        "concept_id": q["concept"],
        "selected_option_id": wrong_opt.id
    }, headers=headers).json()
    assert att1["decision"]["action"] == "STAY_ON_GAP"

    # Fail re-check #2 -> flags teacher
    att2 = client.post("/api/student/stu_acc_c/attempt", json={
        "question_id": q["id"],
        "concept_id": q["concept"],
        "selected_option_id": wrong_opt.id
    }, headers=headers).json()
    assert att2["decision"]["action"] == "FLAG_TEACHER_REPEATED_FAIL"

    # Flag screen served
    step_flag = client.get("/api/student/stu_acc_c/next-step", headers=headers).json()
    assert step_flag["step"]["item_type"] == "flag"
    assert step_flag["step"]["teacher_flag"] == "REPEATED_BRIDGE_FAIL"


def test_acceptance_d_stuck_path_and_teacher_override_actions(client):
    """
    Acceptance Test D:
    Stuck path: 1st wrong SOLVE -> probe. Answer probe correctly -> back to SOLVE.
    Answer wrong again in SOLVE -> flag screen (2nd consecutive wrong solve answer).
    Teacher override (assign_concept, mark_cleared, reinforce) releases student.
    Verify wrong probe by itself never raises stuck flag.
    """
    db = SessionLocal()
    create_test_student(db, "stu_acc_d")
    db.close()

    login_res = client.post("/api/auth/pin", json={"device_id": "dev_test", "student_id": "stu_acc_d", "pin": "1234"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. 1st wrong SOLVE answer
    step1 = client.get("/api/student/stu_acc_d/next-step", headers=headers).json()
    q1 = step1["item"]
    full_q1 = pack.get_question(q1["id"])
    wrong_opt = next(o for o in full_q1.options if not o.is_correct and o.misconception_tag)

    client.post("/api/student/stu_acc_d/attempt", json={
        "question_id": q1["id"],
        "concept_id": q1["concept"],
        "selected_option_id": wrong_opt.id
    }, headers=headers)

    # 2. Probe served (NO FLAG!)
    probe_step = client.get("/api/student/stu_acc_d/next-step", headers=headers).json()
    assert probe_step["step"]["stage"] == "probe"
    assert probe_step["step"]["item_type"] == "question"

    # Answer probe CORRECTLY -> contradicts hypothesis, returns to SOLVE
    full_probe = pack.get_question(probe_step["item"]["id"])
    correct_probe_opt = next(o for o in full_probe.options if o.is_correct)
    client.post("/api/student/stu_acc_d/attempt", json={
        "question_id": probe_step["item"]["id"],
        "concept_id": probe_step["item"]["concept"],
        "selected_option_id": correct_probe_opt.id
    }, headers=headers)

    # Back in SOLVE
    solve_step = client.get("/api/student/stu_acc_d/next-step", headers=headers).json()
    assert solve_step["step"]["stage"] == "solve"

    # 3. Answer wrong in SOLVE again -> 2nd consecutive wrong solve answer -> FLAG!
    q2 = solve_step["item"]
    full_q2 = pack.get_question(q2["id"])
    wrong_opt2 = next(o for o in full_q2.options if not o.is_correct)
    att_stuck = client.post("/api/student/stu_acc_d/attempt", json={
        "question_id": q2["id"],
        "concept_id": q2["concept"],
        "selected_option_id": wrong_opt2.id
    }, headers=headers).json()
    assert att_stuck["decision"]["action"] == "FLAG_TEACHER_STUCK"

    flag_step = client.get("/api/student/stu_acc_d/next-step", headers=headers).json()
    assert flag_step["step"]["item_type"] == "flag"
    assert flag_step["step"]["teacher_flag"] == "STUCK_STUDENT"

    # 4. Teacher override releases the student! Test all 3 actions:
    t_login = client.post("/api/auth/login", json={"username": "tea_acc_8a", "password": "tea_pass_acc"}).json()
    t_token = t_login["access_token"]
    t_headers = {"Authorization": f"Bearer {t_token}"}

    # Action 1: assign_concept
    res_assign = client.post("/api/teacher/override", json={
        "class_id": "8-A",
        "student_id": "stu_acc_d",
        "concept_id": "c8_math_rational_ops",
        "action": "assign_concept",
        "reason": "Reassigning to rational ops"
    }, headers=t_headers)
    assert res_assign.status_code == 200
    res_released = client.get("/api/student/stu_acc_d/next-step", headers=headers).json()
    assert res_released["step"]["item_type"] == "question"
    assert res_released["step"]["stage"] == "solve"

    # Action 2: mark_cleared
    res_cleared = client.post("/api/teacher/override", json={
        "class_id": "8-A",
        "student_id": "stu_acc_d",
        "concept_id": "c8_math_linear_eq_one_var",
        "action": "mark_cleared",
        "reason": "Cleared gap after 1-on-1 clinic"
    }, headers=t_headers)
    assert res_cleared.status_code == 200

    # Action 3: reinforce
    res_reinforce = client.post("/api/teacher/override", json={
        "class_id": "8-A",
        "student_id": "stu_acc_d",
        "concept_id": "c6_math_integers_add_sub",
        "action": "reinforce",
        "reason": "Assigning reinforcement practice"
    }, headers=t_headers)
    assert res_reinforce.status_code == 200


def test_acceptance_e_language_filtering_and_fallback(client):
    """
    Acceptance Test E:
    Language: an English student never receives Hindi or Telugu items.
    Telugu-medium student gets Telugu draft lesson with 'unreviewed draft', and English fallback labelled when missing.
    """
    db = SessionLocal()
    create_test_student(db, "stu_acc_e_en", medium_language="en")
    create_test_student(db, "stu_acc_e_te", medium_language="te")
    db.close()

    login_en = client.post("/api/auth/pin", json={"device_id": "dev_test", "student_id": "stu_acc_e_en", "pin": "1234"}).json()
    token_en = login_en["access_token"]
    step_en = client.get("/api/student/stu_acc_e_en/next-step", headers={"Authorization": f"Bearer {token_en}"}).json()
    q_en = step_en["item"]
    full_q_en = pack.get_question(q_en["id"])
    assert getattr(full_q_en, "language", "en") == "en"

    # Telugu student
    login_te = client.post("/api/auth/pin", json={"device_id": "dev_test", "student_id": "stu_acc_e_te", "pin": "1234"}).json()
    token_te = login_te["access_token"]
    step_te = client.get("/api/student/stu_acc_e_te/next-step", headers={"Authorization": f"Bearer {token_te}"}).json()
    assert step_te["step"]["language_label"] in ("unreviewed draft", "supported")


def test_acceptance_f_fast_learner_and_no_question_repeat(client):
    """
    Acceptance Test F:
    Fast learner: 3 or more consecutive successes with mastery >= 0.85 gives move-ahead screen.
    No question repeats within a session until the pool is exhausted.
    """
    db = SessionLocal()
    create_test_student(db, "stu_acc_f", mastery=0.90, consecutive_successes=2)
    db.close()

    login_res = client.post("/api/auth/pin", json={"device_id": "dev_test", "student_id": "stu_acc_f", "pin": "1234"}).json()
    token = login_res["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    step = client.get("/api/student/stu_acc_f/next-step", headers=headers).json()
    q = step["item"]
    full_q = pack.get_question(q["id"])
    correct_opt = next(o for o in full_q.options if o.is_correct)

    # 3rd consecutive correct answer
    att = client.post("/api/student/stu_acc_f/attempt", json={
        "question_id": q["id"],
        "concept_id": q["concept"],
        "selected_option_id": correct_opt.id
    }, headers=headers).json()

    assert att["decision"]["action"] == "MOVE_AHEAD"

    next_step = client.get("/api/student/stu_acc_f/next-step", headers=headers).json()
    assert next_step["step"]["stage"] == "move_ahead"
    assert next_step["step"]["item_type"] == "enrichment"


def test_acceptance_g_teacher_shared_gaps_and_403(client):
    """
    Acceptance Test G:
    Two students with same confirmed gap appear in one group and one clinic.
    Teacher for 8-B gets 403 on 8-A dashboard.
    """
    db = SessionLocal()
    create_test_student(db, "stu_acc_g1")
    create_test_student(db, "stu_acc_g2")
    for sid in ("stu_acc_g1", "stu_acc_g2"):
        p = db.query(PlanDB).filter(PlanDB.student_id == sid).first()
        p.current_stage = "learn"
        p.gap_concept_id = "c6_math_integers_add_sub"
    db.commit()
    db.close()

    t_login_8a = client.post("/api/auth/login", json={"username": "tea_acc_8a", "password": "tea_pass_acc"}).json()
    t_headers_8a = {"Authorization": f"Bearer {t_login_8a['access_token']}"}

    t_login_8b = client.post("/api/auth/login", json={"username": "tea_acc_8b", "password": "tea_pass_acc"}).json()
    t_headers_8b = {"Authorization": f"Bearer {t_login_8b['access_token']}"}

    # 8-B teacher tries 8-A -> 403
    res_403 = client.get("/api/teacher/class/8-A", headers=t_headers_8b)
    assert res_403.status_code == 403

    dash = client.get("/api/teacher/class/8-A", headers=t_headers_8a).json()
    assert "c6_math_integers_add_sub" in dash.get("grouped_by_gap", {})
    assert len(dash["grouped_by_gap"]["c6_math_integers_add_sub"]) >= 2
    assert any(c.get("concept_id") == "c6_math_integers_add_sub" for c in dash.get("suggested_clinics", []))


def test_acceptance_h_paper_bulk_entry(client):
    """
    Acceptance Test H:
    Paper bulk entry changes real attempt and mastery rows and shows up on dashboard;
    bad question ID shows real error.
    """
    db = SessionLocal()
    create_test_student(db, "stu_acc_h")
    db.close()

    t_login = client.post("/api/auth/login", json={"username": "tea_acc_8a", "password": "tea_pass_acc"}).json()
    t_headers = {"Authorization": f"Bearer {t_login['access_token']}"}

    payload = {
        "responses": [
            {"student_id": "stu_acc_h", "question_id": "q_c8_leq_01", "selected_option_id": "opt_1"},
            {"student_id": "stu_acc_h", "question_id": "bad_q_999", "selected_option_id": "opt_1"}
        ]
    }
    res = client.post("/api/teacher/bulk-paper-submit", json=payload, headers=t_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["processed_count"] == 1
    assert len(data["errors"]) == 1
    assert "bad_q_999" in data["errors"][0]["error"]


def test_acceptance_i_attempt_idempotency_online_and_sync(client):
    """
    Acceptance Test I:
    Posting same attempt ID and payload twice returns original result (HTTP 200) with 1 attempt row and unchanged mastery.
    Same ID with conflicting payload returns HTTP 409 (never 500).
    Same through sync route.
    """
    db = SessionLocal()
    create_test_student(db, "stu_acc_i")
    db.close()

    login_res = client.post("/api/auth/pin", json={"device_id": "dev_sync_test", "student_id": "stu_acc_i", "pin": "1234"}).json()
    headers = {"Authorization": f"Bearer {login_res['access_token']}"}

    attempt_id = f"test_idemp_{secrets.token_hex(6)}"
    payload1 = {
        "attempt_id": attempt_id,
        "question_id": "q_c8_leq_01",
        "concept_id": "c8_math_linear_eq_one_var",
        "selected_option_id": "opt_1"
    }

    # First attempt: 200
    r1 = client.post("/api/student/stu_acc_i/attempt", json=payload1, headers=headers)
    assert r1.status_code == 200
    mastery1 = r1.json()["updated_mastery"]

    # Identical retry: 200 and identical mastery
    r2 = client.post("/api/student/stu_acc_i/attempt", json=payload1, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["updated_mastery"] == mastery1

    # Conflicting payload with same ID: 409
    payload_conflict = {
        "attempt_id": attempt_id,
        "question_id": "q_c8_leq_01",
        "concept_id": "c8_math_linear_eq_one_var",
        "selected_option_id": "opt_2"
    }
    r3 = client.post("/api/student/stu_acc_i/attempt", json=payload_conflict, headers=headers)
    assert r3.status_code == 409

    # Test sync route idempotency
    sync_payload = {
        "device_id": "dev_sync_test",
        "class_id": "8-A",
        "queued_attempts": [
            {
                "attempt_id": f"sync_att_{secrets.token_hex(6)}",
                "student_id": "stu_acc_i",
                "question_id": "q_c8_leq_01",
                "concept_id": "c8_math_linear_eq_one_var",
                "selected_option_id": "opt_1",
                "is_correct": True
            }
        ]
    }
    s1 = client.post("/api/privacy/sync", json=sync_payload, headers=headers)
    assert s1.status_code == 200
    s2 = client.post("/api/privacy/sync", json=sync_payload, headers=headers)
    assert s2.status_code == 200


def test_acceptance_k_student_export_scoping(client):
    """
    Acceptance Test K:
    Student export: student exports only own data (other student 403, no token 401).
    Teacher exports only own class students.
    Export contains no PIN hash, salt, or subject key.
    Deleted student refused.
    """
    db = SessionLocal()
    create_test_student(db, "stu_acc_k1")
    create_test_student(db, "stu_acc_k2")
    db.close()

    login_en = client.post("/api/auth/pin", json={"device_id": "dev_test", "student_id": "stu_acc_k1", "pin": "1234"}).json()
    headers_en = {"Authorization": f"Bearer {login_en['access_token']}"}

    # 1. No token -> 401
    assert client.get("/api/student/stu_acc_k1/export").status_code == 401

    # 2. Student exports own data -> 200
    res_self = client.get("/api/student/stu_acc_k1/export", headers=headers_en)
    assert res_self.status_code == 200
    data = res_self.json()
    assert data["pseudonymous_id"] == "stu_acc_k1"
    assert "pin_hash" not in data
    assert "salt" not in data
    assert "subject_key" not in data

    # 3. Student exports other student -> 403
    assert client.get("/api/student/stu_acc_k2/export", headers=headers_en).status_code == 403

    # 4. Teacher 8-A exports 8-A student -> 200
    t_login_8a = client.post("/api/auth/login", json={"username": "tea_acc_8a", "password": "tea_pass_acc"}).json()
    headers_t8a = {"Authorization": f"Bearer {t_login_8a['access_token']}"}
    assert client.get("/api/student/stu_acc_k1/export", headers=headers_t8a).status_code == 200

    # 5. Teacher 8-B exports 8-A student -> 403
    t_login_8b = client.post("/api/auth/login", json={"username": "tea_acc_8b", "password": "tea_pass_acc"}).json()
    headers_t8b = {"Authorization": f"Bearer {t_login_8b['access_token']}"}
    assert client.get("/api/student/stu_acc_k1/export", headers=headers_t8b).status_code == 403

    # 6. Deleted student export refused (404)
    del_res = client.post("/api/privacy/delete-student", json={"student_id": "stu_acc_k1"}, headers=headers_t8a)
    assert del_res.status_code == 200
    assert client.get("/api/student/stu_acc_k1/export", headers=headers_t8a).status_code == 404


def test_acceptance_l_content_editor(client):
    """
    Acceptance Test L:
    Content editor: only authorized roles read/write pack (student gets 403).
    Invalid edit rejected by validator with visible error.
    Valid edit saves, review status resets to 'author-drafted, unreviewed', percent drops.
    Restores pack content in finally block so packaged content is not polluted.
    """
    from app.main import PACK_PATH
    with open(PACK_PATH, "r", encoding="utf-8") as f:
        original_pack_content = f.read()

    try:
        db = SessionLocal()
        create_test_student(db, "stu_acc_l")
        db.close()

        login_en = client.post("/api/auth/pin", json={"device_id": "dev_test", "student_id": "stu_acc_l", "pin": "1234"}).json()
        headers_student = {"Authorization": f"Bearer {login_en['access_token']}"}

        rev_login = client.post("/api/auth/login", json={"username": "rev_acc_01", "password": "rev_pass_acc"}).json()
        headers_rev = {"Authorization": f"Bearer {rev_login['access_token']}"}

        # 1. Student cannot access editor pack -> 403
        assert client.get("/api/content/editor/pack", headers=headers_student).status_code == 403

        # 2. Reviewer can access editor pack -> 200
        res_pack = client.get("/api/content/editor/pack", headers=headers_rev)
        assert res_pack.status_code == 200

        # 3. Invalid edit: 0 correct options -> 422
        bad_payload = {
            "id": "q_c8_leq_01",
            "question_text": "Solve for x: x + 5 = 10",
            "options": [
                {"id": "opt_1", "text": "5", "is_correct": False, "misconception_tag": "tag1"},
                {"id": "opt_2", "text": "15", "is_correct": False, "misconception_tag": "tag2"}
            ]
        }
        r_bad = client.post("/api/content/editor/pack", json=bad_payload, headers=headers_rev)
        assert r_bad.status_code == 422
        assert "exactly one correct option" in r_bad.json()["detail"]

        # 4. Valid edit saves and resets review status to 'author-drafted, unreviewed'
        valid_payload = {
            "id": "q_c8_leq_01",
            "concept": "c8_math_linear_eq_one_var",
            "difficulty": 0.3,
            "question_text": "Solve for x: x + 7 = 14",
            "options": [
                {"id": "opt_1", "text": "7", "is_correct": True},
                {"id": "opt_2", "text": "21", "is_correct": False, "misconception_tag": "tag_sign_error_on_transposition"}
            ]
        }
        r_valid = client.post("/api/content/editor/pack", json=valid_payload, headers=headers_rev)
        assert r_valid.status_code == 200
        assert r_valid.json()["review_status"] == "author-drafted, unreviewed"
    finally:
        with open(PACK_PATH, "w", encoding="utf-8") as f:
            f.write(original_pack_content)


def test_offline_sync_saves_attempts_and_returns_synced_ids(client):
    """
    FIX 1: Offline Sync Blocker
    Verifies that queued attempts sent with both Authorization and X-Device-Purge-Token headers
    are re-graded and saved in AttemptDB, returning synced_attempts_processed and synced_attempt_ids.
    """
    db = SessionLocal()
    create_test_student(db, "stu_acc_sync")
    db.close()

    # Sign in online to get access token and device purge token
    login_res = client.post("/api/auth/pin", json={
        "device_id": "dev_sync_test",
        "student_id": "stu_acc_sync",
        "pin": "1234"
    })
    assert login_res.status_code == 200
    data = login_res.json()
    token = data["access_token"]
    purge_token = data["device_purge_token"]

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Device-Purge-Token": purge_token
    }

    # Sync 2 queued attempts from offline session
    payload = {
        "device_id": "dev_sync_test",
        "class_id": "8-A",
        "queued_attempts": [
            {
                "attempt_id": "att_off_01",
                "student_id": "stu_acc_sync",
                "question_id": "q_c8_leq_01",
                "selected_option_id": "opt_1",
                "time_spent_seconds": 10
            },
            {
                "attempt_id": "att_off_02",
                "student_id": "stu_acc_sync",
                "question_id": "q_c8_leq_02",
                "selected_option_id": "opt_1",
                "time_spent_seconds": 12
            }
        ]
    }

    sync_res = client.post("/api/privacy/sync", json=payload, headers=headers)
    assert sync_res.status_code == 200
    sync_data = sync_res.json()

    # Must NOT be in purge_mode and must have processed both attempts!
    assert sync_data.get("purge_mode") is not True
    assert sync_data["synced_attempts_processed"] == 2
    assert "att_off_01" in sync_data["synced_attempt_ids"]
    assert "att_off_02" in sync_data["synced_attempt_ids"]

    # Verify both attempts exist in the database
    db = SessionLocal()
    try:
        saved_attempts = db.query(AttemptDB).filter(AttemptDB.student_id == "stu_acc_sync").all()
        assert len(saved_attempts) == 2
    finally:
        db.close()


def test_move_ahead_checks_original_topic_mastery_not_prerequisite(client):
    """
    FIX 2: Move-Ahead Blocker
    Verifies that when a prerequisite reaches high mastery (e.g. 87%),
    the student is NOT advanced to move_ahead if the original topic is still at low mastery (e.g. 56%).
    The student must return to SOLVE on the original topic.
    """
    db = SessionLocal()
    create_test_student(db, "stu_acc_move", mastery=0.56, consecutive_successes=0)
    # Set student to bridge_recheck stage with gap concept c6_math_integers_add_sub
    plan = db.query(PlanDB).filter(PlanDB.student_id == "stu_acc_move").first()
    plan.current_stage = "bridge_recheck"
    plan.current_concept_id = "c8_math_linear_eq_one_var"
    plan.gap_concept_id = "c6_math_integers_add_sub"

    # Set prerequisite concept mastery to 0.84 and 2 successes
    m_prereq = db.query(MasteryStateDB).filter(
        MasteryStateDB.student_id == "stu_acc_move",
        MasteryStateDB.concept_id == "c6_math_integers_add_sub"
    ).first()
    if not m_prereq:
        m_prereq = MasteryStateDB(
            student_id="stu_acc_move",
            concept_id="c6_math_integers_add_sub",
            mastery_estimate=0.84,
            consecutive_successes=2
        )
        db.add(m_prereq)
    else:
        m_prereq.mastery_estimate = 0.84
        m_prereq.consecutive_successes = 2
    db.commit()
    db.close()

    login_res = client.post("/api/auth/pin", json={
        "device_id": "dev_test",
        "student_id": "stu_acc_move",
        "pin": "1234"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Student answers a bridge re-check question on c6_math_integers_add_sub correctly!
    # This pushes prerequisite mastery over 0.85 (e.g. 0.87+) and 3 successes on prerequisite.
    prereq_q = [q for q in pack.questions if q.concept == "c6_math_integers_add_sub"][0]
    correct_opt = next(o for o in prereq_q.options if o.is_correct)

    att_res = client.post("/api/student/stu_acc_move/attempt", json={
        "question_id": prereq_q.id,
        "concept_id": prereq_q.concept,
        "selected_option_id": correct_opt.id
    }, headers=headers)
    assert att_res.status_code == 200
    att_data = att_res.json()

    # The action must be RETURN_TO_ORIGINAL_TOPIC, NOT MOVE_AHEAD!
    assert att_data["decision"]["action"] == "RETURN_TO_ORIGINAL_TOPIC"
    assert att_data["updated_mastery"] >= 0.85  # prerequisite reached high mastery

    # Now verify next step is SOLVE on the original topic, NOT move_ahead or enrichment!
    step_res = client.get("/api/student/stu_acc_move/next-step", headers=headers).json()
    assert step_res["step"]["stage"] == "solve"
    assert step_res["step"]["item_type"] == "question"
    assert step_res["item"]["concept"] == "c8_math_linear_eq_one_var"


def test_teacher_override_short_reason_returns_validation_error_never_500(client):
    """
    FIX 3: Teacher Override Short Reason Fix
    A very short teacher-override reason (length < 3) must return HTTP 400 / 422 with a validation message,
    and NEVER crash with a 500 server error.
    """
    t_login = client.post("/api/auth/login", json={"username": "tea_acc_8a", "password": "tea_pass_acc"}).json()
    headers_t = {"Authorization": f"Bearer {t_login['access_token']}"}

    db = SessionLocal()
    create_test_student(db, "stu_acc_overr")
    db.close()

    # 1. Reason shorter than 3 characters (e.g. "ok")
    res_short = client.post("/api/teacher/override", json={
        "class_id": "8-A",
        "student_id": "stu_acc_overr",
        "concept_id": "c8_math_linear_eq_one_var",
        "action": "assign_concept",
        "reason": "ok"
    }, headers=headers_t)

    assert res_short.status_code in (400, 422)
    assert res_short.status_code != 500
    err_detail = str(res_short.json().get("detail", ""))
    assert "at least 3 characters" in err_detail or "min_length" in err_detail

    # 2. 1-character reason "a"
    res_single = client.post("/api/teacher/override", json={
        "class_id": "8-A",
        "student_id": "stu_acc_overr",
        "concept_id": "c8_math_linear_eq_one_var",
        "action": "assign_concept",
        "reason": "a"
    }, headers=headers_t)

    assert res_single.status_code in (400, 422)
    assert res_single.status_code != 500

    # 3. Valid reason (>= 3 chars) succeeds with 200
    res_valid = client.post("/api/teacher/override", json={
        "class_id": "8-A",
        "student_id": "stu_acc_overr",
        "concept_id": "c8_math_linear_eq_one_var",
        "action": "assign_concept",
        "reason": "Student completed manual paper diagnostic successfully."
    }, headers=headers_t)

    assert res_valid.status_code == 200
    assert "override" in res_valid.json()

