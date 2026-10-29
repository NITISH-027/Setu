import json
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, UniqueConstraint
from app.db.database import Base


class UserDB(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'admin', 'teacher', 'reviewer'
    assigned_classes = Column(Text, default="[]")  # JSON list of class_ids, e.g. ["8-A"]
    is_seeded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def get_classes(self):
        try:
            return json.loads(self.assigned_classes)
        except Exception:
            return []


class SessionDB(Base):
    __tablename__ = "sessions"
    token = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=True)
    role = Column(String, nullable=False)  # 'admin', 'teacher', 'reviewer', 'student'
    student_id = Column(String, nullable=True)
    device_id = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class StudentDB(Base):
    __tablename__ = "students"
    pseudonymous_id = Column(String, primary_key=True)
    subject_key = Column(String, unique=True, index=True, nullable=False)
    class_id = Column(String, index=True, nullable=False)
    board = Column(String, default="CBSE")
    medium_language = Column(String, default="en")
    pin_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    consent_status = Column(String, default="not requested")


class PlanDB(Base):
    __tablename__ = "plans"
    student_id = Column(String, primary_key=True)
    class_id = Column(String, index=True, nullable=False)
    current_stage = Column(String, default="diagnose")
    current_concept_id = Column(String, nullable=False)
    gap_concept_id = Column(String, nullable=True)
    items_queue = Column(Text, default="[]")
    reason = Column(Text, default="Initial diagnosis")
    stuck_attempts_count = Column(Integer, default=0)
    bridge_recheck_fails = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)


class MasteryStateDB(Base):
    __tablename__ = "mastery_states"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, index=True, nullable=False)
    concept_id = Column(String, index=True, nullable=False)
    mastery_estimate = Column(Float, default=0.2)
    bkt_prior = Column(Float, default=0.2)
    bkt_learn = Column(Float, default=0.15)
    bkt_guess = Column(Float, default=0.2)
    bkt_slip = Column(Float, default=0.1)
    mastery_label = Column(String, default="uncalibrated, hand-set")
    last_seen = Column(DateTime, nullable=True)
    next_review = Column(DateTime, nullable=True)
    interval_days = Column(Float, default=1.0)
    ease_factor = Column(Float, default=2.5)
    consecutive_successes = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint('student_id', 'concept_id', name='uq_student_concept'),)


class HypothesisDB(Base):
    __tablename__ = "hypotheses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, index=True, nullable=False)
    suspected_concept_id = Column(String, nullable=False)
    misconception_tag = Column(String, nullable=False)
    evidence_list = Column(Text, default="[]")
    heuristic_score = Column(Integer, default=0)
    evidence_band = Column(String, default="Low")
    status = Column(String, default="open")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class AttemptDB(Base):
    __tablename__ = "attempts"
    id = Column(String, primary_key=True)
    student_id = Column(String, index=True, nullable=False)
    subject_key = Column(String, index=True, nullable=True)
    question_id = Column(String, nullable=False)
    concept_id = Column(String, nullable=False)
    selected_option_id = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    misconception_tag = Column(String, nullable=True)
    time_spent_seconds = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class DecisionDB(Base):
    __tablename__ = "decisions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, index=True, nullable=False)
    class_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    rule_id = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    stage = Column(String, nullable=False)
    metadata_json = Column(Text, default="{}")
    timestamp = Column(DateTime, default=datetime.utcnow)


class TeacherOverrideDB(Base):
    __tablename__ = "teacher_overrides"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, index=True, nullable=False)
    teacher_id = Column(String, nullable=False)
    class_id = Column(String, nullable=False)
    concept_id = Column(String, nullable=False)
    override_action = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class TombstoneDB(Base):
    __tablename__ = "tombstones"
    id = Column(Integer, primary_key=True, autoincrement=True)
    opaque_key = Column(String, unique=True, index=True, nullable=False)
    subject_key = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    status = Column(String, default="pending")  # 'pending', 'applied', 'purged'
    pending_devices = Column(Integer, default=0)
    purged_at = Column(DateTime, nullable=True)


class DeviceDB(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, unique=True, index=True, nullable=False)
    class_id = Column(String, index=True, nullable=False)
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_sync_at = Column(DateTime, default=datetime.utcnow)
    device_purge_token = Column(String, index=True, nullable=True)


class DeviceSubjectDB(Base):
    """
    FIX 1: Tracks per device which student subject_keys have been active on it.
    Opaque subject_key ONLY. Never stores student_id or any PII.
    """
    __tablename__ = "device_subjects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, index=True, nullable=False)
    subject_key = Column(String, index=True, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('device_id', 'subject_key', name='uq_device_subject'),)


class TombstoneDeliveryDB(Base):
    """
    FIX 1: Per-device, per-tombstone delivery and acknowledgment record.
    Tracks whether a device that held this subject_key has received and acknowledged the purge.
    Never stores student_id or reason text.
    """
    __tablename__ = "tombstone_deliveries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tombstone_id = Column(Integer, index=True, nullable=False)
    opaque_tombstone_key = Column(String, index=True, nullable=False)
    device_id = Column(String, index=True, nullable=False)
    subject_key = Column(String, index=True, nullable=False)
    status = Column(String, default="pending")  # 'pending', 'acknowledged'
    delivered_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('tombstone_id', 'device_id', name='uq_tombstone_device'),)



class AuditEventDB(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    class_id = Column(String, nullable=False)
    record_count = Column(Integer, default=1)
    opaque_tombstone_key = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class ReviewRecordDB(Base):
    __tablename__ = "review_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String, index=True, nullable=False)
    item_type = Column(String, nullable=False)  # 'question', 'lesson', 'hint'
    status = Column(String, default="author-drafted, unreviewed")
    reviewer_name = Column(String, nullable=True)
    reviewer_role = Column(String, nullable=True)
    attestation_date = Column(DateTime, nullable=True)
    item_version = Column(Integer, default=1)
    attestation_statement = Column(Text, nullable=True)


class GapClosedRecordDB(Base):
    __tablename__ = "gap_closed_records"
    id = Column(String, primary_key=True)
    student_id = Column(String, index=True, nullable=False)
    class_id = Column(String, nullable=False)
    concept_id = Column(String, nullable=False)
    concept_name = Column(String, nullable=False)
    closed_at = Column(DateTime, default=datetime.utcnow)
    teacher_id = Column(String, nullable=False)
    closure_reason = Column(Text, nullable=False)
    supporting_evidence_summary = Column(Text, nullable=False)
    note_for_parents = Column(Text, nullable=False)


class PinProfileDB(Base):
    __tablename__ = "pin_profiles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, index=True, nullable=False)
    student_id = Column(String, index=True, nullable=False)
    class_id = Column(String, nullable=False)
    pin_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    __table_args__ = (UniqueConstraint('device_id', 'student_id', name='uq_device_student'),)

