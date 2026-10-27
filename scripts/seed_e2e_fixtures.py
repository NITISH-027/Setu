"""
Explicit E2E fixture setup script for browser-level Playwright tests.
Seeds stu_e2e_01 with PIN 5678, teacher_8a, and dev_demo_tablet.
"""

import os
import sys
import secrets

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.db import init_db, SessionLocal
from app.db.models import UserDB, StudentDB, PlanDB, MasteryStateDB, DeviceDB, PinProfileDB
from app.auth.security import hash_password, hash_pin


def seed_fixtures():
    init_db()
    db = SessionLocal()
    try:
        # Teacher
        t = db.query(UserDB).filter(UserDB.username == "tea_e2e_8a").first()
        if not t:
            db.add(UserDB(
                id="usr_tea_e2e_8a",
                username="tea_e2e_8a",
                password_hash=hash_password("tea_e2e_pass"),
                role="teacher",
                assigned_classes='["8-A"]'
            ))

        # Device
        dev = db.query(DeviceDB).filter(DeviceDB.device_id == "dev_demo_tablet").first()
        if not dev:
            db.add(DeviceDB(
                device_id="dev_demo_tablet",
                class_id="8-A"
            ))

        # Student
        sid = "stu_e2e_01"
        salt = secrets.token_hex(8)
        pin_h = hash_pin("5678", salt)

        stu = db.query(StudentDB).filter(StudentDB.pseudonymous_id == sid).first()
        if not stu:
            stu = StudentDB(
                pseudonymous_id=sid,
                subject_key="subj_e2e_k1",
                class_id="8-A",
                board="CBSE",
                medium_language="en",
                pin_hash=pin_h,
                salt=salt,
                consent_status="not requested"
            )
            db.add(stu)
            db.add(PlanDB(
                student_id=sid,
                class_id="8-A",
                current_stage="solve",
                current_concept_id="c8_math_linear_eq_one_var",
                reason="Playwright offline flow test"
            ))
            db.add(MasteryStateDB(
                student_id=sid,
                concept_id="c8_math_linear_eq_one_var",
                mastery_estimate=0.25
            ))
        else:
            stu.pin_hash = pin_h
            stu.salt = salt

        prof = db.query(PinProfileDB).filter(
            PinProfileDB.device_id == "dev_demo_tablet",
            PinProfileDB.student_id == sid
        ).first()
        if not prof:
            db.add(PinProfileDB(
                device_id="dev_demo_tablet",
                student_id=sid,
                class_id="8-A",
                pin_hash=pin_h,
                salt=salt
            ))
        else:
            prof.pin_hash = pin_h
            prof.salt = salt

        db.commit()
        print("E2E fixtures successfully seeded: stu_e2e_01 / PIN: 5678")
    finally:
        db.close()


if __name__ == "__main__":
    seed_fixtures()
