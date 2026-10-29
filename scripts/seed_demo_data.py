"""
Explicit synthetic demo data seeding script.
Only run for local testing and demonstration when explicitly called.
NEVER automatically executed in production.
Refused if ENV=production.
Generates cryptographically random passwords and PINs per run, printed ONCE to console.
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
from app.db.models import UserDB, StudentDB, PlanDB, MasteryStateDB, DeviceDB, PinProfileDB
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
        # Generate random credentials per run
        admin_pass = os.getenv("SETU_DEMO_ADMIN_PASS") or secrets.token_urlsafe(12)
        teacher_8a_pass = os.getenv("SETU_DEMO_TEACHER_8A_PASS") or secrets.token_urlsafe(12)
        teacher_8b_pass = os.getenv("SETU_DEMO_TEACHER_8B_PASS") or secrets.token_urlsafe(12)
        reviewer_pass = os.getenv("SETU_DEMO_REVIEWER_PASS") or secrets.token_urlsafe(12)
        student_pin = os.getenv("SETU_DEMO_STUDENT_PIN") or f"{secrets.randbelow(9000) + 1000}"

        # 1. Admin account
        admin = db.query(UserDB).filter(UserDB.username == "admin").first()
        if not admin:
            admin = UserDB(
                id="usr_admin_01",
                username="admin",
                password_hash=hash_password(admin_pass),
                role="admin",
                assigned_classes="[]",
                is_seeded=True
            )
            db.add(admin)
        else:
            admin.password_hash = hash_password(admin_pass)
            admin.is_seeded = True

        # 2. Teacher 8-A account
        t1 = db.query(UserDB).filter(UserDB.username == "teacher_8a").first()
        if not t1:
            t1 = UserDB(
                id="usr_tea_8a",
                username="teacher_8a",
                password_hash=hash_password(teacher_8a_pass),
                role="teacher",
                assigned_classes=json.dumps(["8-A"]),
                is_seeded=True
            )
            db.add(t1)
        else:
            t1.password_hash = hash_password(teacher_8a_pass)
            t1.is_seeded = True

        # 3. Teacher 8-B account
        t2 = db.query(UserDB).filter(UserDB.username == "teacher_8b").first()
        if not t2:
            t2 = UserDB(
                id="usr_tea_8b",
                username="teacher_8b",
                password_hash=hash_password(teacher_8b_pass),
                role="teacher",
                assigned_classes=json.dumps(["8-B"]),
                is_seeded=True
            )
            db.add(t2)
        else:
            t2.password_hash = hash_password(teacher_8b_pass)
            t2.is_seeded = True

        # 4. Reviewer account
        rev = db.query(UserDB).filter(UserDB.username == "reviewer_sunita").first()
        if not rev:
            rev = UserDB(
                id="usr_rev_01",
                username="reviewer_sunita",
                password_hash=hash_password(reviewer_pass),
                role="reviewer",
                assigned_classes="[]",
                is_seeded=True
            )
            db.add(rev)
        else:
            rev.password_hash = hash_password(reviewer_pass)
            rev.is_seeded = True

        # 5. Synthetic student in Class 8-A
        stu_id = "stu_demo_01"
        salt = secrets.token_hex(8)
        pin_h = hash_pin(student_pin, salt)
        subject_k = secrets.token_hex(16)

        stu = db.query(StudentDB).filter(StudentDB.pseudonymous_id == stu_id).first()
        if not stu:
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
        else:
            stu.pin_hash = pin_h
            stu.salt = salt

        plan = db.query(PlanDB).filter(PlanDB.student_id == stu_id).first()
        if not plan:
            plan = PlanDB(
                student_id=stu_id,
                class_id="8-A",
                current_stage="solve",
                current_concept_id="c8_math_linear_eq_one_var",
                reason="Initial practice sequence"
            )
            db.add(plan)

        mastery = db.query(MasteryStateDB).filter(MasteryStateDB.student_id == stu_id).first()
        if not mastery:
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
        dev = db.query(DeviceDB).filter(DeviceDB.device_id == "dev_demo_tablet").first()
        if not dev:
            dev = DeviceDB(
                device_id="dev_demo_tablet",
                class_id="8-A"
            )
            db.add(dev)

        # Pin Profile on device
        prof = db.query(PinProfileDB).filter(
            PinProfileDB.device_id == "dev_demo_tablet",
            PinProfileDB.student_id == stu_id
        ).first()
        if not prof:
            prof = PinProfileDB(
                device_id="dev_demo_tablet",
                student_id=stu_id,
                class_id="8-A",
                pin_hash=pin_h,
                salt=salt
            )
            db.add(prof)
        else:
            prof.pin_hash = pin_h
            prof.salt = salt

        db.commit()

        if os.getenv("RENDER", "").lower() == "true":
            # Hosted run: never write demo credentials to cloud logs.
            print("Synthetic demo seed complete. Credentials are managed via SETU_DEMO_* env vars.")
        else:
            print("=" * 60)
            print("EXPLICIT SYNTHETIC DEMO CREDENTIALS (GENERATED ONCE)")
            print("=" * 60)
            print(f"Admin:    username: admin           password: {admin_pass}")
            print(f"Teacher:  username: teacher_8a      password: {teacher_8a_pass} (Class 8-A)")
            print(f"Teacher:  username: teacher_8b      password: {teacher_8b_pass} (Class 8-B)")
            print(f"Reviewer: username: reviewer_sunita password: {reviewer_pass}")
            print(f"Student:  student_id: {stu_id}      PIN: {student_pin} (Device: dev_demo_tablet)")
            print("=" * 60)
            print("These credentials are NOT stored in source code or docs.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
