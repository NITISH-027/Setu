"""
Demo-mode profile reset (Round 3 judge-demo hygiene).

Goal: on the public demo deployment, every judge should experience the seeded
starting state. When a demo profile (one-tap student entry or one-tap teacher
entry) logs out or its session expires, the profile's learning data is restored
to the state captured at server startup (i.e. right after the seed script ran).

Design (chosen for safety under concurrency):
- Snapshot at startup: in SETU_DEMO_MODE=true only, the rows of every student
  present in the DB at startup are captured in memory. This is the reset
  baseline. Students created AFTER startup are never in the snapshot and are
  therefore never reset.
- Demo-session markers: logins via /api/auth/demo-login insert a row into the
  demo_sessions table. A profile is only ever reset if it carries at least one
  demo marker, i.e. it was actually used through the demo entry. Profiles only
  ever used via real PIN sign-in are never wiped, even in demo mode.
- Concurrency guard: a profile is reset only when it has NO live (unexpired)
  session of any kind. Two judges on the same demo profile: the first logout
  does not wipe the second judge's live session; the wipe happens when the
  last live session ends (logout or expiry).
- Triggers: (1) /api/auth/logout of a demo session, (2) an expired demo session
  observed during token validation. In demo mode EVERY session (demo or PIN) is
  capped at 2 hours (vs 24h normal), so an abandoned session stops blocking the
  reset after at most 2 hours and cleans up on the next trigger.

Hard guarantees:
- Nothing in this module runs when SETU_DEMO_MODE is not exactly "true".
- AuditEventDB is never touched (append-only audit log is a privacy feature).
- Content packs and class-level content are not student data and are untouched.

Known limits (stated plainly):
- The reset baseline is the DB state at server startup. On Render free tier the
  sqlite file is ephemeral and re-seeded each boot, so the baseline is exactly
  the seeded state. With a persistent local DB, the baseline is whatever the DB
  held at startup (not necessarily the original factory seed).
- A judge who closes the browser without logging out leaves a live session for
  up to 2 hours; the profile resets only after that session expires and the
  next logout/validation event triggers the sweep. There is no background
  timer (keeps the free-tier single-process deployment simple).
- The device-side IndexedDB copy is cleared by the frontend on demo logout; a
  browser closed without logout keeps its local copy until the next visit.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import (
    SessionDB, StudentDB, PlanDB, MasteryStateDB, HypothesisDB,
    AttemptDB, DecisionDB, TeacherOverrideDB, GapClosedRecordDB,
    TestSessionDB, TestItemDB, DemoSessionDB,
)

DEMO_MODE = os.getenv("SETU_DEMO_MODE", "false").lower() == "true"

# Per-student tables wiped and restored on reset. AuditEventDB, DeviceDB,
# TombstoneDB and PinProfileDB are deliberately excluded (audit/privacy/device
# records are not demo progress data).
STUDENT_TABLES = [
    PlanDB, MasteryStateDB, HypothesisDB, AttemptDB, DecisionDB,
    TeacherOverrideDB, GapClosedRecordDB, TestSessionDB, TestItemDB,
]

# Mutable StudentDB fields restored on reset (progress-adjacent state only;
# pin_hash/salt/subject_key/class_id are identity, never rewritten).
STUDENT_FIELDS = ["failed_attempts", "locked_until", "consent_status", "medium_language"]

_snapshot_rows: Dict[str, Dict[str, List[dict]]] = {}
_snapshot_student_fields: Dict[str, dict] = {}
_snapshot_active = False


def _row_dict(row) -> dict:
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def capture_snapshot(db: Session) -> int:
    """Capture the reset baseline: all students currently in the DB.

    Demo mode only. Returns the number of snapshotted profiles.
    """
    global _snapshot_active
    if not DEMO_MODE:
        return 0
    _snapshot_rows.clear()
    _snapshot_student_fields.clear()
    students = db.query(StudentDB).all()
    for student in students:
        sid = student.pseudonymous_id
        _snapshot_student_fields[sid] = {f: getattr(student, f) for f in STUDENT_FIELDS}
        rows = {}
        for model in STUDENT_TABLES:
            rows[model.__tablename__] = [
                _row_dict(r) for r in db.query(model).filter(model.student_id == sid).all()
            ]
        _snapshot_rows[sid] = rows
    _snapshot_active = True
    return len(students)


def mark_demo_session(db: Session, token: str, student_id: Optional[str] = None) -> None:
    if not DEMO_MODE:
        return
    db.add(DemoSessionDB(token=token, student_id=student_id))
    db.commit()


def is_demo_session(db: Session, token: str) -> bool:
    if not DEMO_MODE:
        return False
    return db.query(DemoSessionDB).filter(DemoSessionDB.token == token).first() is not None


def reset_student(db: Session, student_id: str) -> bool:
    """Restore one snapshotted profile to the startup baseline. False if not snapshotted."""
    if student_id not in _snapshot_rows:
        return False
    for model in STUDENT_TABLES:
        db.query(model).filter(model.student_id == student_id).delete()
    for model in STUDENT_TABLES:
        for rd in _snapshot_rows[student_id][model.__tablename__]:
            db.add(model(**rd))
    student = db.query(StudentDB).filter(StudentDB.pseudonymous_id == student_id).first()
    if student:
        for f, v in _snapshot_student_fields[student_id].items():
            setattr(student, f, v)
    db.commit()
    return True


def sweep_idle_demo_profiles(db: Session) -> List[str]:
    """Reset every marked demo profile that has no live session.

    A profile is eligible only if (a) it is in the startup snapshot, (b) it
    carries at least one demo-session marker, and (c) it has no unexpired
    session (demo or real) right now. Markers whose sessions are gone or
    expired are cleaned up. Returns the list of reset profile ids.
    """
    if not DEMO_MODE or not _snapshot_active:
        return []
    now = datetime.utcnow()
    markers = db.query(DemoSessionDB).all()
    used_student_ids = set()
    for m in markers:
        if m.student_id:
            used_student_ids.add(m.student_id)
        sess = db.query(SessionDB).filter(SessionDB.token == m.token).first()
        if sess is not None and sess.expires_at < now:
            db.delete(sess)  # tidy expired session rows
    db.commit()

    reset_ids = []
    for sid in sorted(used_student_ids):
        live = (
            db.query(SessionDB)
            .filter(SessionDB.student_id == sid, SessionDB.expires_at > now)
            .count()
        )
        if live > 0:
            continue  # another judge is mid-demo on this profile
        if reset_student(db, sid):
            reset_ids.append(sid)
        # Profile is clean now; clear all its markers.
        db.query(DemoSessionDB).filter(DemoSessionDB.student_id == sid).delete()
        db.commit()
    # Clean teacher markers (student_id NULL) whose sessions are gone/expired.
    for m in db.query(DemoSessionDB).filter(DemoSessionDB.student_id == None).all():  # noqa: E711
        sess = db.query(SessionDB).filter(SessionDB.token == m.token).first()
        if sess is None or sess.expires_at < now:
            db.delete(m)
    db.commit()
    return reset_ids
