"""
Explicit E2E fixture setup script for browser-level Playwright tests (FIX 7).
Refuses to run unless SETU_TEST_ENV=1 is set and DATABASE_URL points to a dedicated test database.
Seeds stu_e2e_01 (bound to dev_demo_tablet) and stu_e2e_02 (bound to dev_tablet_02).
"""

import os
import sys
import secrets

# FIX 7: Refuse execution outside test environment or on production database
if os.environ.get("SETU_TEST_ENV") != "1":
    raise RuntimeError(
        "REFUSAL: scripts/seed_e2e_fixtures.py is strictly restricted to test environments!\n"
        "Set SETU_TEST_ENV=1 and point DATABASE_URL to an isolated test database (e.g. setu_test.db)."
    )

db_url = os.environ.get("DATABASE_URL", "")
if "test" not in db_url.lower():
    raise RuntimeError(
        f"REFUSAL: scripts/seed_e2e_fixtures.py refuses to run against non-test database: {db_url}!\n"
        "DATABASE_URL must explicitly point to a test database containing 'test' (e.g. setu_test.db)."
    )

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.db import init_db, SessionLocal
from app.db.models import UserDB, StudentDB, PlanDB, MasteryStateDB, DeviceDB, PinProfileDB, DeviceSubjectDB, AttemptDB, DecisionDB, TeacherOverrideDB, HypothesisDB
from app.auth.security import hash_password, hash_pin


def seed_fixtures():
    init_db()
    db = SessionLocal()
    try:
        # Clean reset for e2e test students so each test run has pristine state
        e2e_sids = ["stu_e2e_01", "stu_e2e_02", "stu_e2e_te", "stu_e2e_fast"]
        db.query(AttemptDB).filter(AttemptDB.student_id.in_(e2e_sids)).delete(synchronize_session=False)
        db.query(DecisionDB).filter(DecisionDB.student_id.in_(e2e_sids)).delete(synchronize_session=False)
        db.query(TeacherOverrideDB).filter(TeacherOverrideDB.student_id.in_(e2e_sids)).delete(synchronize_session=False)
        db.query(HypothesisDB).filter(HypothesisDB.student_id.in_(e2e_sids)).delete(synchronize_session=False)
        db.query(PlanDB).filter(PlanDB.student_id.in_(e2e_sids)).delete(synchronize_session=False)
        db.query(MasteryStateDB).filter(MasteryStateDB.student_id.in_(e2e_sids)).delete(synchronize_session=False)
        db.query(StudentDB).filter(StudentDB.pseudonymous_id.in_(e2e_sids)).delete(synchronize_session=False)
        db.query(PinProfileDB).filter(PinProfileDB.student_id.in_(e2e_sids)).delete(synchronize_session=False)
        db.commit()

        # Teacher for Class 8-A
        t = db.query(UserDB).filter(UserDB.username == "tea_e2e_8a").first()
        if not t:
            db.add(UserDB(
                id="usr_tea_e2e_8a",
                username="tea_e2e_8a",
                password_hash=hash_password("tea_e2e_pass"),
                role="teacher",
                assigned_classes='["8-A"]'
            ))

        # Teacher for Class 8-B (for 403 cross-class testing)
        t_b = db.query(UserDB).filter(UserDB.username == "tea_e2e_8b").first()
        if not t_b:
            db.add(UserDB(
                id="usr_tea_e2e_8b",
                username="tea_e2e_8b",
                password_hash=hash_password("tea_e2e_pass"),
                role="teacher",
                assigned_classes='["8-B"]'
            ))

        # Content Reviewer
        rev = db.query(UserDB).filter(UserDB.username == "rev_e2e_01").first()
        if not rev:
            db.add(UserDB(
                id="usr_rev_e2e_01",
                username="rev_e2e_01",
                password_hash=hash_password("rev_e2e_pass"),
                role="reviewer",
                assigned_classes='[]'
            ))

        # Device 1: dev_demo_tablet (holds student 1)
        dev1 = db.query(DeviceDB).filter(DeviceDB.device_id == "dev_demo_tablet").first()
        if not dev1:
            dev1 = DeviceDB(
                device_id="dev_demo_tablet",
                class_id="8-A",
                device_purge_token=secrets.token_hex(24)
            )
            db.add(dev1)
        elif not dev1.device_purge_token:
            dev1.device_purge_token = secrets.token_hex(24)

        # Device 2: dev_tablet_02 (holds student 2 only; never held student 1)
        dev2 = db.query(DeviceDB).filter(DeviceDB.device_id == "dev_tablet_02").first()
        if not dev2:
            dev2 = DeviceDB(
                device_id="dev_tablet_02",
                class_id="8-A",
                device_purge_token=secrets.token_hex(24)
            )
            db.add(dev2)
        elif not dev2.device_purge_token:
            dev2.device_purge_token = secrets.token_hex(24)

        # Student 1: stu_e2e_01
        sid1 = "stu_e2e_01"
        salt1 = secrets.token_hex(8)
        pin_h1 = hash_pin("5678", salt1)

        stu1 = db.query(StudentDB).filter(StudentDB.pseudonymous_id == sid1).first()
        if not stu1:
            stu1 = StudentDB(
                pseudonymous_id=sid1,
                subject_key="subj_e2e_k1",
                class_id="8-A",
                board="CBSE",
                medium_language="en",
                pin_hash=pin_h1,
                salt=salt1,
                consent_status="not requested"
            )
            db.add(stu1)
            db.add(PlanDB(
                student_id=sid1,
                class_id="8-A",
                current_stage="solve",
                current_concept_id="c8_math_linear_eq_one_var",
                reason="Playwright offline flow test"
            ))
            db.add(MasteryStateDB(
                student_id=sid1,
                concept_id="c8_math_linear_eq_one_var",
                mastery_estimate=0.25
            ))
        else:
            stu1.pin_hash = pin_h1
            stu1.salt = salt1

        # Student 2: stu_e2e_02 (on device 2)
        sid2 = "stu_e2e_02"
        salt2 = secrets.token_hex(8)
        pin_h2 = hash_pin("9876", salt2)

        stu2 = db.query(StudentDB).filter(StudentDB.pseudonymous_id == sid2).first()
        if not stu2:
            stu2 = StudentDB(
                pseudonymous_id=sid2,
                subject_key="subj_e2e_k2",
                class_id="8-A",
                board="CBSE",
                medium_language="en",
                pin_hash=pin_h2,
                salt=salt2,
                consent_status="not requested"
            )
            db.add(stu2)
            db.add(PlanDB(
                student_id=sid2,
                class_id="8-A",
                current_stage="solve",
                current_concept_id="c8_math_linear_eq_one_var",
                reason="Multi-device isolation test"
            ))
            db.add(MasteryStateDB(
                student_id=sid2,
                concept_id="c8_math_linear_eq_one_var",
                mastery_estimate=0.25
            ))
        else:
            stu2.pin_hash = pin_h2
            stu2.salt = salt2

        # Pin profiles
        prof1 = db.query(PinProfileDB).filter(
            PinProfileDB.device_id == "dev_demo_tablet",
            PinProfileDB.student_id == sid1
        ).first()
        if not prof1:
            db.add(PinProfileDB(
                device_id="dev_demo_tablet",
                student_id=sid1,
                class_id="8-A",
                pin_hash=pin_h1,
                salt=salt1
            ))
        else:
            prof1.pin_hash = pin_h1
            prof1.salt = salt1

        prof2 = db.query(PinProfileDB).filter(
            PinProfileDB.device_id == "dev_tablet_02",
            PinProfileDB.student_id == sid2
        ).first()
        if not prof2:
            db.add(PinProfileDB(
                device_id="dev_tablet_02",
                student_id=sid2,
                class_id="8-A",
                pin_hash=pin_h2,
                salt=salt2
            ))
        else:
            prof2.pin_hash = pin_h2
            prof2.salt = salt2

        # Device 2 holds student 2 (subj_e2e_k2)
        dev_sub2 = db.query(DeviceSubjectDB).filter(
            DeviceSubjectDB.device_id == "dev_tablet_02",
            DeviceSubjectDB.subject_key == "subj_e2e_k2"
        ).first()
        if not dev_sub2:
            db.add(DeviceSubjectDB(device_id="dev_tablet_02", subject_key="subj_e2e_k2"))

        # Student 3 (Telugu medium): stu_e2e_te
        sid_te = "stu_e2e_te"
        salt_te = secrets.token_hex(8)
        pin_h_te = hash_pin("1111", salt_te)
        if not db.query(StudentDB).filter(StudentDB.pseudonymous_id == sid_te).first():
            db.add(StudentDB(
                pseudonymous_id=sid_te,
                subject_key="subj_e2e_te",
                class_id="8-A",
                board="CBSE",
                medium_language="te",
                pin_hash=pin_h_te,
                salt=salt_te,
                consent_status="not requested"
            ))
            db.add(PlanDB(
                student_id=sid_te,
                class_id="8-A",
                current_stage="solve",
                current_concept_id="c8_math_linear_eq_one_var"
            ))
            db.add(MasteryStateDB(
                student_id=sid_te,
                concept_id="c8_math_linear_eq_one_var",
                mastery_estimate=0.25
            ))
            db.add(PinProfileDB(
                device_id="dev_demo_tablet",
                student_id=sid_te,
                class_id="8-A",
                pin_hash=pin_h_te,
                salt=salt_te
            ))

        # Student 4 (Fast learner): stu_e2e_fast
        sid_fast = "stu_e2e_fast"
        salt_fast = secrets.token_hex(8)
        pin_h_fast = hash_pin("2222", salt_fast)
        if not db.query(StudentDB).filter(StudentDB.pseudonymous_id == sid_fast).first():
            db.add(StudentDB(
                pseudonymous_id=sid_fast,
                subject_key="subj_e2e_fast",
                class_id="8-A",
                board="CBSE",
                medium_language="en",
                pin_hash=pin_h_fast,
                salt=salt_fast,
                consent_status="not requested"
            ))
            db.add(PlanDB(
                student_id=sid_fast,
                class_id="8-A",
                current_stage="solve",
                current_concept_id="c8_math_linear_eq_one_var"
            ))
            db.add(MasteryStateDB(
                student_id=sid_fast,
                concept_id="c8_math_linear_eq_one_var",
                mastery_estimate=0.90,
                consecutive_successes=2
            ))
            db.add(PinProfileDB(
                device_id="dev_demo_tablet",
                student_id=sid_fast,
                class_id="8-A",
                pin_hash=pin_h_fast,
                salt=salt_fast
            ))

        db.commit()
        print("E2E fixtures successfully seeded into isolated test database.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_fixtures()
