import sys
import os
import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.models.student import Student, ConsentStatus
from app.models.learning import Attempt, Plan, MasteryState
from app.models.security import Tombstone, TombstoneStatus, AuditEventType
from app.privacy.data_protection_manager import DataProtectionManager


def test_forbidden_fields_rejected():
    # Only minimal operational metadata allowed
    with pytest.raises(ValidationError):
        Student(pseudonymous_id="stu_1", class_id="8-A", pin_hash="h", name="Aarav Sharma")

    with pytest.raises(ValidationError):
        Student(pseudonymous_id="stu_1", class_id="8-A", pin_hash="h", phone="9988776655")

    with pytest.raises(ValidationError):
        Student(pseudonymous_id="stu_1", class_id="8-A", pin_hash="h", email="child@school.in")


def test_delete_student_purges_stores():
    """
    Test requirement:
    'After delete-student and the tombstone sync, a search of the server stores,
     local caches, sync queues, generated exports and the audit log finds no active
     student record, no learning payload and no student ID. The only allowed trace
     is the restricted tombstone key, which is not an ID and holds no payload.'
    """
    manager = DataProtectionManager()
    manager.register_device("8-A", "device_tablet_01")

    student_id = "stu_delete_target"
    student = Student(pseudonymous_id=student_id, class_id="8-A", pin_hash="h")
    manager.add_student(student, Plan(student_id=student_id, class_id="8-A", current_concept_id="c8_math_linear_eq_one_var"))

    # Seed attempts, hypotheses, mastery, and export
    manager.attempts[student_id] = [
        Attempt(student_id=student_id, question_id="q1", concept_id="c1", selected_option_id="o1", is_correct=False)
    ]
    manager.generated_exports["exp_001"] = {
        "export_id": "exp_001",
        "student_id": student_id,
        "contained_student_ids": [student_id]
    }

    # Execute deletion
    report = manager.delete_student(student_id, actor="tea_math_01")

    # 1. Search server stores -> must find NO active student, NO attempts, NO plan, NO export
    assert student_id not in manager.students
    assert student_id not in manager.attempts
    assert student_id not in manager.plans
    assert "exp_001" not in manager.generated_exports

    # 2. Before sync: pending state is visible
    assert report.pending_devices == 1
    assert report.is_fully_deleted_everywhere is False
    assert "Deletion pending, not yet applied on 1 device(s)" in report.status_message

    # 3. Tombstone sync: device syncs and purges local copy
    sync_result = manager.sync_device("device_tablet_01", "8-A")
    assert report.tombstone_key in sync_result["applied_tombstones"]
    assert student_id in sync_result["purge_student_ids"]

    # 4. Check audit log -> records event, class, count, tombstone key, but NO student ID and NO answers
    delete_audit = [e for e in manager.audit_events if e.event_type == AuditEventType.DELETE][0]
    assert delete_audit.opaque_tombstone_key == report.tombstone_key
    assert delete_audit.record_count == 1
    # Verify student_id is not in audit log event dictionary
    assert "stu_delete_target" not in str(delete_audit.model_dump())


def test_tombstone_lifecycle_and_pending_state():
    """
    Test requirement:
    'The pending state ("deletion pending, not yet applied on N devices") must be visible
     on the server and in the connected admin or teacher view.
     The app must never claim "all stores deleted" while any tombstone is pending.'
    """
    manager = DataProtectionManager()
    manager.register_device("8-A", "dev_1")
    manager.register_device("8-A", "dev_2")

    student = Student(pseudonymous_id="stu_two_devices", class_id="8-A", pin_hash="h")
    manager.add_student(student)

    report = manager.delete_student("stu_two_devices")
    assert report.pending_devices == 2
    assert report.is_fully_deleted_everywhere is False
    assert "not yet applied on 2 device(s)" in report.status_message

    # First device syncs
    manager.sync_device("dev_1", "8-A")
    tombstone = manager.tombstones[report.tombstone_key]
    assert tombstone.pending_devices == 1
    assert tombstone.status == TombstoneStatus.PENDING

    # Second device syncs
    manager.sync_device("dev_2", "8-A")
    assert tombstone.pending_devices == 0
    assert tombstone.status == TombstoneStatus.APPLIED


def test_late_sync_offline_no_resurrection():
    """
    Test requirement:
    'A late-syncing offline device does not resurrect deleted data.'
    """
    manager = DataProtectionManager()
    manager.register_device("8-A", "dev_late")

    student = Student(pseudonymous_id="stu_offline_victim", class_id="8-A", pin_hash="h")
    manager.add_student(student)

    # Server deletes student while device was offline
    report = manager.delete_student("stu_offline_victim")

    # Offline device wakes up late and attempts to sync queued attempts for the deleted student
    queued_attempts = [
        {"student_id": "stu_offline_victim", "question_id": "q1", "is_correct": True}
    ]
    sync_result = manager.sync_device("dev_late", "8-A", device_queued_attempts=queued_attempts)

    # Queued attempt was rejected!
    assert sync_result["rejected_deleted_attempts_count"] == 1
    assert sync_result["accepted_attempts_count"] == 0
    # Student is NOT resurrected in server database
    assert "stu_offline_victim" not in manager.students


def test_stale_device_reset_after_tombstone_purge():
    """
    Test requirement:
    'A device that returns after the tombstone is purged must have its local store
     for that class reset rather than merged, so stale records cannot return.'
    """
    manager = DataProtectionManager()
    manager.register_device("8-A", "dev_normal")

    student = Student(pseudonymous_id="stu_purged", class_id="8-A", pin_hash="h")
    manager.add_student(student)
    report = manager.delete_student("stu_purged")

    # Sync normal device and purge tombstone
    manager.sync_device("dev_normal", "8-A")
    manager.purge_applied_tombstones()
    assert report.tombstone_key in manager.tombstones
    assert manager.tombstones[report.tombstone_key].status == TombstoneStatus.PURGED

    # An unregistered stale device connects months later after tombstone was purged
    stale_result = manager.sync_stale_device_after_purge(
        device_id="dev_stale_forgotten",
        class_id="8-A",
        last_sync_timestamp=datetime.utcnow() - timedelta(days=90)
    )
    assert stale_result["action"] == "RESET_LOCAL_STORE"
    assert "reset rather than merged" in stale_result["reason"]


def test_retention_purge_job():
    """
    Test requirement:
    'Configurable retention with automatic deletion of expired records,
     using the same tombstone path for offline devices.'
    """
    manager = DataProtectionManager()
    manager.register_device("8-A", "dev_1")

    old_time = datetime.utcnow() - timedelta(days=200)
    recent_time = datetime.utcnow() - timedelta(days=30)

    # Expired student (> 180 days)
    s_expired = Student(pseudonymous_id="stu_expired", class_id="8-A", pin_hash="h", created_at=old_time)
    # Active student (< 180 days)
    s_recent = Student(pseudonymous_id="stu_recent", class_id="8-A", pin_hash="h", created_at=recent_time)

    manager.add_student(s_expired)
    manager.add_student(s_recent)

    purged_count = manager.run_retention_purge(retention_days=180)
    assert purged_count == 1
    assert "stu_expired" not in manager.students
    assert "stu_recent" in manager.students

    # Verify retention event was logged in audit log
    retention_audit = [e for e in manager.audit_events if e.event_type == AuditEventType.RETENTION_RUN]
    assert len(retention_audit) == 1
    assert retention_audit[0].record_count == 1


def test_audit_log_privacy_and_structure():
    """
    Test requirement:
    'Audit log records event type (read, export, delete, retention_run, tombstone_applied),
     acting teacher or system, class, timestamp and a record count.
     It holds no answers, no lesson content, no student payload, and it does not keep the deleted student's ID.'
    """
    manager = DataProtectionManager()
    manager.register_device("8-A", "dev_1")

    stu = Student(pseudonymous_id="stu_audit_check", class_id="8-A", pin_hash="h")
    manager.add_student(stu)

    manager.delete_student("stu_audit_check", actor="tea_01")
    manager.sync_device("dev_1", "8-A")

    for event in manager.audit_events:
        dump = event.model_dump()
        assert "event_type" in dump
        assert "actor" in dump
        assert "class_id" in dump
        assert "timestamp" in dump
        assert "record_count" in dump
        # Strictly forbidden fields
        assert "student_id" not in dump
        assert "answers" not in dump
        assert "lesson_content" not in dump
        assert "stu_audit_check" not in str(dump)


def test_consent_workflow_states():
    """
    Test requirement:
    'Consent: a proposed workflow with status fields (not requested, requested, recorded)
     so a real pilot has somewhere to record consent.
     Nothing is ever marked "consent obtained" in the demo, and no code path may set it from a script.'
    """
    # Default is NOT_REQUESTED
    s = Student(pseudonymous_id="stu_c", class_id="8-A", pin_hash="h")
    assert s.consent_status == ConsentStatus.NOT_REQUESTED

    # Valid transitions
    s.consent_status = ConsentStatus.REQUESTED
    assert s.consent_status == ConsentStatus.REQUESTED

    s.consent_status = ConsentStatus.RECORDED
    assert s.consent_status == ConsentStatus.RECORDED

    # Any attempt to pass unapproved strings like "consent obtained" or "verified" must fail
    with pytest.raises(ValidationError):
        Student(pseudonymous_id="stu_c2", class_id="8-A", pin_hash="h", consent_status="consent obtained")
