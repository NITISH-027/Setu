"""
Explicit synthetic demo data seeding script.
Only run for local testing and demonstration when explicitly called.
NEVER automatically executed in production.
Refused if ENV=production.
"""

import os
import sys
import json
import secrets
from datetime import datetime

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db import init_db, SessionLocal
from app.db.models import UserDB, StudentDB, PlanDB, MasteryStateDB, DeviceDB
from app.auth.security import hash_password, hash_pin

def seed():
    env = os.getenv("ENV", "development").lower()
    if env == "production":
        print("ERROR: Refusing to seed demo credentials in production mode!")
        sys.exit(1)

    print("Running explicit synthetic seeding in development mode...")
    init_db()
    db = SessionLocal()

    try:
        # 1. Admin account
        if not db.query(UserDB).filter(UserDB.username == "admin").first():
            admin = UserDB(
                id="usr_admin_01",
                username="admin",
                password_hash=hash_password("admin_pass_123"),
                role="admin",
                assigned_classes="[]"
            )
            db.add(admin)

        # 2. Teacher 8-A account
        if not db.query(UserDB).filter(UserDB.username == "teacher_8a").first():
            t1 = UserDB(
                id="usr_tea_8a",
                username="teacher_8a",
                password_hash=hash_password("teacher_pass_123"),
                role="teacher",
                assigned_classes=json.dumps(["8-A"])
            )
            db.add(t1)

        # 3. Teacher 8-B account (for negative testing)
        if not db.query(UserDB).filter(UserDB.username == "teacher_8b").first():
            t2 = UserDB(
                id="usr_tea_8b",
                username="teacher_8b",
                password_hash=hash_password("teacher_pass_123"),
                role="teacher",
                assigned_classes=json.dumps(["8-B"])
            )
            db.add(t2)

        # 4. Reviewer account
        if not db.query(UserDB).filter(UserDB.username == "reviewer_sunita").first():
            rev = UserDB(
                id="usr_rev_01",
                username="reviewer_sunita",
                password_hash=hash_password("reviewer_pass_123"),
                role="reviewer",
                assigned_classes="[]"
            )
            db.add(rev)

        # 5. Synthetic student in Class 8-A
        stu_id = "stu_demo_01"
        if not db.query(StudentDB).filter(StudentDB.pseudonymous_id == stu_id).first():
            salt = secrets.token_hex(8)
            pin_h = hash_pin("1234", salt)
            subject_k = secrets.token_hex(16)

            stu = StudentDB(
                pseudonymous_id=stu_id,
                subject_key=subject_k,
                class_id="8-A",
                board="CBSE",
                medium_language="en",
                pin_hash=pin_h,
                salt=salt,
                consent_status="not requested"
            )
            db.add(stu)

            plan = PlanDB(
                student_id=stu_id,
                class_id="8-A",
                current_stage="solve",
                current_concept_id="c8_math_linear_eq_one_var",
                reason="Initial practice sequence"
            )
            db.add(plan)

            mastery = MasteryStateDB(
                student_id=stu_id,
                concept_id="c8_math_linear_eq_one_var",
                mastery_estimate=0.25,
                bkt_prior=0.2,
                bkt_learn=0.15,
                bkt_guess=0.2,
                bkt_slip=0.1,
                mastery_label="uncalibrated, hand-set"
            )
            db.add(mastery)

        # 6. Registered device for Class 8-A
        if not db.query(DeviceDB).filter(DeviceDB.device_id == "dev_demo_tablet").first():
            dev = DeviceDB(
                device_id="dev_demo_tablet",
                class_id="8-A"
            )
            db.add(dev)

        db.commit()
        print("Explicit synthetic demo data successfully seeded.")
        print("Demo Accounts:")
        print("  - Admin:    admin / admin_pass_123")
        print("  - Teacher:  teacher_8a / teacher_pass_123 (Class 8-A)")
        print("  - Teacher:  teacher_8b / teacher_pass_123 (Class 8-B)")
        print("  - Reviewer: reviewer_sunita / reviewer_pass_123")
        print("  - Student:  stu_demo_01 (PIN: 1234, Device: dev_demo_tablet)")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
