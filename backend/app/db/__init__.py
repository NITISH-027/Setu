from app.db.database import engine, SessionLocal, Base, get_db
from app.db.models import (
    UserDB, SessionDB, StudentDB, PlanDB, MasteryStateDB,
    HypothesisDB, AttemptDB, DecisionDB, TeacherOverrideDB,
    TombstoneDB, DeviceDB, AuditEventDB, ReviewRecordDB, GapClosedRecordDB,
    PinProfileDB
)

def init_db(target_engine=None):
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)

__all__ = [
    "engine", "SessionLocal", "Base", "get_db", "init_db",
    "UserDB", "SessionDB", "StudentDB", "PlanDB", "MasteryStateDB",
    "HypothesisDB", "AttemptDB", "DecisionDB", "TeacherOverrideDB",
    "TombstoneDB", "DeviceDB", "AuditEventDB", "ReviewRecordDB", "GapClosedRecordDB",
    "PinProfileDB"
]
