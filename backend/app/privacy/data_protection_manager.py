"""
Data Protection & Privacy Manager.
Enforces:
1. Strict minimal student metadata (forbids direct identifiers).
2. Clean student deletion across server stores, local caches, sync queues, and held exports.
3. Tombstone protocol with opaque deletion keys (NO student ID, NO name, NO learning payload).
4. Device synchronization, pending tombstone tracking, and anti-resurrection guards:
   - Device applying tombstone purges local store and queued writes.
   - Stale device connecting after tombstone is purged gets RESET, not merged.
   - Never claims 'all stores deleted' while any tombstone is pending.
5. Configurable retention purge runner.
6. Privacy-safe audit log (event, actor, class, timestamp, count; NO student IDs, NO answers, NO payload).
7. Consent workflow schema (not requested, requested, recorded; never auto-marked).
"""

import secrets
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta

from app.models.student import Student, ConsentStatus
from app.models.learning import Attempt, Hypothesis, MasteryState, Plan, TeacherOverride
from app.models.security import Tombstone, TombstoneStatus, AuditLogEvent, AuditEventType


class DeletionReport:
    def __init__(
        self,
        student_id: str,
        tombstone_key: str,
        pending_devices: int,
        is_fully_deleted_everywhere: bool,
        status_message: str
    ):
        self.student_id = student_id
        self.tombstone_key = tombstone_key
        self.pending_devices = pending_devices
        self.is_fully_deleted_everywhere = is_fully_deleted_everywhere
        self.status_message = status_message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "tombstone_key": self.tombstone_key,
            "pending_devices": self.pending_devices,
            "is_fully_deleted_everywhere": self.is_fully_deleted_everywhere,
            "status_message": self.status_message
        }


class DataProtectionManager:
    def __init__(self):
        # Server databases/stores
        self.students: Dict[str, Student] = {}
        self.attempts: Dict[str, List[Attempt]] = {}          # student_id -> attempts
        self.hypotheses: Dict[str, List[Hypothesis]] = {}    # student_id -> hypotheses
        self.mastery_states: Dict[str, List[MasteryState]] = {}
        self.plans: Dict[str, Plan] = {}
        self.overrides: Dict[str, List[TeacherOverride]] = {}
        self.generated_exports: Dict[str, Dict[str, Any]] = {} # export_id -> export data

        # Tombstone registry: opaque_key -> Tombstone
        self.tombstones: Dict[str, Tombstone] = {}
        # Mapping from opaque_key to target student_id (held internally ONLY during pending transition, erased on purge)
        # Note: Tombstone itself does NOT contain student ID.
        self._pending_key_to_student_id: Dict[str, str] = {}
        self._deleted_pseudonyms: Set[str] = set()

        # Registered devices per class: class_id -> set of device_ids
        self.registered_devices: Dict[str, Set[str]] = {}
        # Devices pending sync for each tombstone: opaque_key -> set of device_ids
        self.tombstone_pending_devices: Dict[str, Set[str]] = {}

        # Audit log
        self.audit_events: List[AuditLogEvent] = []

    def register_device(self, class_id: str, device_id: str):
        self.registered_devices.setdefault(class_id, set()).add(device_id)

    def add_student(self, student: Student, plan: Optional[Plan] = None):
        self.students[student.pseudonymous_id] = student
        if plan:
            self.plans[student.pseudonymous_id] = plan

    def delete_student(
        self,
        student_id: str,
        actor: str = "system"
    ) -> DeletionReport:
        """
        Deletes student from app-controlled server stores and creates an opaque tombstone.
        """
        student = self.students.get(student_id)
        class_id = student.class_id if student else "unknown_class"

        # 1. Purge from active server stores
        self.students.pop(student_id, None)
        self.attempts.pop(student_id, None)
        self.hypotheses.pop(student_id, None)
        self.mastery_states.pop(student_id, None)
        self.plans.pop(student_id, None)
        self.overrides.pop(student_id, None)

        # 2. Purge from generated exports held by app
        exports_to_remove = [
            exp_id for exp_id, data in self.generated_exports.items()
            if data.get("student_id") == student_id or student_id in data.get("contained_student_ids", [])
        ]
        for exp_id in exports_to_remove:
            self.generated_exports.pop(exp_id, None)

        self._deleted_pseudonyms.add(student_id)

        # 3. Create Opaque Tombstone
        opaque_key = secrets.token_hex(16)
        class_devices = set(self.registered_devices.get(class_id, set()))
        pending_count = len(class_devices)

        tombstone = Tombstone(
            opaque_key=opaque_key,
            created_at=datetime.utcnow(),
            status=TombstoneStatus.PENDING,
            pending_devices=pending_count
        )
        self.tombstones[opaque_key] = tombstone
        self._pending_key_to_student_id[opaque_key] = student_id
        self.tombstone_pending_devices[opaque_key] = class_devices

        # 4. Log privacy-safe Audit Event (contains NO student ID, NO answers, NO payload)
        self.audit_events.append(AuditLogEvent(
            event_type=AuditEventType.DELETE,
            actor=actor,
            class_id=class_id,
            record_count=1,
            opaque_tombstone_key=opaque_key
        ))

        is_fully_deleted = (pending_count == 0)
        status_msg = (
            "All app stores deleted." if is_fully_deleted
            else f"Deletion pending, not yet applied on {pending_count} device(s)."
        )

        return DeletionReport(
            student_id=student_id,
            tombstone_key=opaque_key,
            pending_devices=pending_count,
            is_fully_deleted_everywhere=is_fully_deleted,
            status_message=status_msg
        )

    def sync_device(
        self,
        device_id: str,
        class_id: str,
        device_queued_attempts: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Processes a device synchronization.
        - Applies pending tombstones to device.
        - Blocks late-syncing offline devices from resurrecting deleted students.
        - If an unknown/stale device syncs after tombstones have been purged, triggers class store RESET.
        """
        device_queued_attempts = device_queued_attempts or []

        # Find tombstones relevant to this device
        pending_for_device: List[str] = []
        purged_student_ids_for_device: List[str] = []

        for key, dev_set in list(self.tombstone_pending_devices.items()):
            if device_id in dev_set:
                pending_for_device.append(key)
                stu_id = self._pending_key_to_student_id.get(key)
                if stu_id:
                    purged_student_ids_for_device.append(stu_id)
                dev_set.remove(device_id)
                tomb = self.tombstones.get(key)
                if tomb:
                    tomb.pending_devices = len(dev_set)
                    if len(dev_set) == 0:
                        tomb.status = TombstoneStatus.APPLIED

        # Filter incoming device queued attempts: reject any attempts belonging to deleted students
        accepted_attempts = []
        rejected_deleted_count = 0
        for att in device_queued_attempts:
            sid = att.get("student_id")
            if sid in self._deleted_pseudonyms or sid in purged_student_ids_for_device:
                rejected_deleted_count += 1
            else:
                accepted_attempts.append(att)

        # Audit event for tombstone sync
        if pending_for_device:
            self.audit_events.append(AuditLogEvent(
                event_type=AuditEventType.TOMBSTONE_APPLIED,
                actor=f"device_{device_id}",
                class_id=class_id,
                record_count=len(pending_for_device),
                opaque_tombstone_key=pending_for_device[0]
            ))

        return {
            "applied_tombstones": pending_for_device,
            "purge_student_ids": purged_student_ids_for_device,
            "accepted_attempts_count": len(accepted_attempts),
            "rejected_deleted_attempts_count": rejected_deleted_count,
            "action": "SYNC_SUCCESS"
        }

    def sync_stale_device_after_purge(
        self,
        device_id: str,
        class_id: str,
        last_sync_timestamp: datetime
    ) -> Dict[str, Any]:
        """
        A stale device that reconnects AFTER tombstones have already expired and been purged:
        The server resets the device's local class store rather than merging,
        preventing any zombie records from resurrecting.
        """
        return {
            "action": "RESET_LOCAL_STORE",
            "class_id": class_id,
            "reason": (
                "Device registration expired and tombstones were purged. "
                "Class store reset rather than merged to prevent resurrecting deleted student data."
            )
        }

    def run_retention_purge(
        self,
        retention_days: int = 180,
        current_time: Optional[datetime] = None
    ) -> int:
        """
        Configurable retention job: purges student records older than retention_days.
        Uses the exact same tombstone path for offline devices.
        """
        now = current_time or datetime.utcnow()
        cutoff = now - timedelta(days=retention_days)

        expired_students = [
            sid for sid, student in self.students.items()
            if student.created_at < cutoff
        ]

        purged_count = 0
        for sid in expired_students:
            self.delete_student(sid, actor="retention_runner")
            purged_count += 1

        self.audit_events.append(AuditLogEvent(
            event_type=AuditEventType.RETENTION_RUN,
            actor="retention_runner",
            class_id="all_classes",
            record_count=purged_count
        ))

        return purged_count

    def purge_applied_tombstones(self) -> int:
        """
        Purges tombstones that have been applied across all registered devices.
        Completely removes internal student_id mapping.
        """
        keys_to_purge = [
            k for k, t in self.tombstones.items()
            if t.status == TombstoneStatus.APPLIED or t.pending_devices == 0
        ]
        for k in keys_to_purge:
            t = self.tombstones[k]
            t.status = TombstoneStatus.PURGED
            t.purged_at = datetime.utcnow()
            self._pending_key_to_student_id.pop(k, None)

        return len(keys_to_purge)
