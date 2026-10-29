from app.db.database import engine, SessionLocal, Base, get_db
from app.db.models import (
    UserDB, SessionDB, StudentDB, PlanDB, MasteryStateDB,
    HypothesisDB, AttemptDB, DecisionDB, TeacherOverrideDB,
    TombstoneDB, DeviceDB, AuditEventDB, ReviewRecordDB, GapClosedRecordDB,
    PinProfileDB, DeviceSubjectDB, TombstoneDeliveryDB
)

def init_db(target_engine=None):
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)
    
    # Handle SQLite missing column additions dynamically
    try:
        from sqlalchemy import text
        with eng.connect() as conn:
            # Check devices.device_purge_token
            res = conn.execute(text("PRAGMA table_info(devices)"))
            cols = [row[1] for row in res.fetchall()]
            if cols and "device_purge_token" not in cols:
                conn.execute(text("ALTER TABLE devices ADD COLUMN device_purge_token VARCHAR"))
                conn.commit()
            
            # Check users.is_seeded
            res = conn.execute(text("PRAGMA table_info(users)"))
            cols = [row[1] for row in res.fetchall()]
            if cols and "is_seeded" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_seeded BOOLEAN DEFAULT 0"))
                conn.commit()

            # Check students.failed_attempts and locked_until
            res = conn.execute(text("PRAGMA table_info(students)"))
            cols = [row[1] for row in res.fetchall()]
            if cols and "failed_attempts" not in cols:
                conn.execute(text("ALTER TABLE students ADD COLUMN failed_attempts INTEGER DEFAULT 0"))
                conn.commit()
            if cols and "locked_until" not in cols:
                conn.execute(text("ALTER TABLE students ADD COLUMN locked_until DATETIME"))
                conn.commit()

            # Check tombstones.expires_at
            res = conn.execute(text("PRAGMA table_info(tombstones)"))
            cols = [row[1] for row in res.fetchall()]
            if cols and "expires_at" not in cols:
                conn.execute(text("ALTER TABLE tombstones ADD COLUMN expires_at DATETIME"))
                conn.commit()
    except Exception:
        pass

__all__ = [
    "engine", "SessionLocal", "Base", "get_db", "init_db",
    "UserDB", "SessionDB", "StudentDB", "PlanDB", "MasteryStateDB",
    "HypothesisDB", "AttemptDB", "DecisionDB", "TeacherOverrideDB",
    "TombstoneDB", "DeviceDB", "AuditEventDB", "ReviewRecordDB", "GapClosedRecordDB",
    "PinProfileDB", "DeviceSubjectDB", "TombstoneDeliveryDB"
]
