from app.db.database import engine, SessionLocal, Base, get_db
from app.db.models import (
    UserDB, SessionDB, StudentDB, PlanDB, MasteryStateDB,
    HypothesisDB, AttemptDB, DecisionDB, TeacherOverrideDB,
    TombstoneDB, DeviceDB, AuditEventDB, ReviewRecordDB, GapClosedRecordDB,
    PinProfileDB, DeviceSubjectDB, TombstoneDeliveryDB,
    TestSessionDB, TestItemDB, DemoSessionDB
)

def _ensure_schema_columns(eng):
    """Add model columns missing from an existing database.

    create_all() creates missing TABLES but never alters existing ones, so a
    DB file created by an older build (e.g. a v3 setu.db, or a deployed DB
    from before a column was added) breaks the new code. For every table that
    already exists, add any column the models declare but the DB lacks.
    Only ever ADD COLUMN - never drops, renames or rewrites data. Works on
    SQLite and Postgres via the SQLAlchemy inspector.
    """
    from sqlalchemy import inspect, text
    insp = inspect(eng)
    existing_tables = set(insp.get_table_names())
    with eng.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue  # create_all handles brand-new tables
            present = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in present:
                    continue
                col_type = col.type.compile(eng.dialect)
                default = ""
                if col.default is not None and getattr(col.default, "is_scalar", False):
                    val = col.default.arg
                    if isinstance(val, bool):
                        default = " DEFAULT %d" % (1 if val else 0)
                    elif isinstance(val, (int, float)):
                        default = " DEFAULT %s" % val
                    elif isinstance(val, str):
                        default = " DEFAULT '%s'" % val.replace("'", "''")
                conn.execute(text(
                    "ALTER TABLE %s ADD COLUMN %s %s%s" % (table.name, col.name, col_type, default)
                ))
                print("DB migration: added missing column %s.%s (%s)" % (table.name, col.name, col_type))


def init_db(target_engine=None):
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)
    _ensure_schema_columns(eng)

__all__ = [
    "engine", "SessionLocal", "Base", "get_db", "init_db",
    "UserDB", "SessionDB", "StudentDB", "PlanDB", "MasteryStateDB",
    "HypothesisDB", "AttemptDB", "DecisionDB", "TeacherOverrideDB",
    "TombstoneDB", "DeviceDB", "AuditEventDB", "ReviewRecordDB", "GapClosedRecordDB",
    "PinProfileDB", "DeviceSubjectDB", "TombstoneDeliveryDB",
    "TestSessionDB", "TestItemDB", "DemoSessionDB"
]
