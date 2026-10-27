import sys
import os
import pytest
from datetime import datetime
from pydantic import ValidationError

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.models.student import Student, ConsentStatus
from app.models.concept import Concept, PrerequisiteEdge
from app.models.content import Question, Option, Lesson, HintLadder, ReviewRecord, ReviewStatus
from app.models.learning import (
    Attempt, Hypothesis, EvidenceItem, EvidenceBand, HypothesisStatus,
    BKTParameters, MasteryState, TeacherOverride, Plan, StageEnum
)
from app.models.security import Tombstone, TombstoneStatus, AuditLogEvent, AuditEventType
from app.models.pack import ContentPack, PackMetadata


def test_student_minimal_metadata():
    # Valid minimal student record
    student = Student(
        pseudonymous_id="stu_99f2b1",
        class_id="8-B",
        board="CBSE",
        medium_language="en",
        pin_hash="sha256$hashed_pin",
        consent_status=ConsentStatus.REQUESTED
    )
    assert student.pseudonymous_id == "stu_99f2b1"
    assert student.class_id == "8-B"
    assert student.consent_status == ConsentStatus.REQUESTED


def test_student_rejects_direct_identifiers():
    # Attempting to supply forbidden direct identifiers must raise a validation error
    forbidden_payloads = [
        {"pseudonymous_id": "stu_01", "class_id": "8-A", "pin_hash": "h", "first_name": "Aarav"},
        {"pseudonymous_id": "stu_01", "class_id": "8-A", "pin_hash": "h", "name": "Priya Sharma"},
        {"pseudonymous_id": "stu_01", "class_id": "8-A", "pin_hash": "h", "phone": "9876543210"},
        {"pseudonymous_id": "stu_01", "class_id": "8-A", "pin_hash": "h", "email": "child@school.edu"},
        {"pseudonymous_id": "stu_01", "class_id": "8-A", "pin_hash": "h", "school": "Kendriya Vidyalaya"},
        {"pseudonymous_id": "stu_01", "class_id": "8-A", "pin_hash": "h", "birth_date": "2012-05-15"}
    ]
    for payload in forbidden_payloads:
        with pytest.raises(ValidationError):
            Student(**payload)


def test_concept_ncert_and_graph_only():
    c8 = Concept(
        id="c8_math_linear_eq",
        name="Linear Equations in One Variable",
        class_level=8,
        ncert_chapter_reference="Chapter 2: Linear Equations in One Variable",
        reference_verified=False,
        graph_only=False
    )
    assert c8.reference_verified is False
    assert not c8.graph_only

    # Graph-only concept for lower class
    c6 = Concept(
        id="c6_math_basic_algebra",
        name="Algebra Introduction",
        class_level=6,
        graph_only=True
    )
    assert c6.graph_only is True
    assert c6.ncert_chapter_reference == "to verify against the official NCERT list"
    assert c6.reference_verified is False


def test_review_record_human_provenance():
    # Default is unreviewed
    rr = ReviewRecord()
    assert rr.status == ReviewStatus.AUTHOR_DRAFTED
    assert not rr.is_human_reviewed()

    # Valid human review requires reviewer name, statement, date
    reviewed_rr = ReviewRecord(
        status=ReviewStatus.REVIEWED,
        reviewer_name="Sunita Rao",
        reviewer_role="Senior Secondary Math Teacher (self-declared)",
        attestation_date=datetime.utcnow(),
        item_version=1,
        attestation_statement="I checked this item"
    )
    assert reviewed_rr.is_human_reviewed()

    # If reviewer name is missing, cannot count as reviewed
    faked_rr = ReviewRecord(
        status=ReviewStatus.REVIEWED,
        reviewer_name="",
        attestation_statement=""
    )
    assert not faked_rr.is_human_reviewed()


def test_honest_labels_and_overrides():
    bkt = BKTParameters()
    assert bkt.label == "uncalibrated, hand-set"

    hyp = Hypothesis(
        student_id="stu_123",
        suspected_concept_id="c7_math_integers",
        misconception_tag="tag_sign_error",
        evidence_band=EvidenceBand.LOW
    )
    assert hyp.label == "heuristic evidence score"
    assert hyp.evidence_band == EvidenceBand.LOW

    # Teacher override requires a non-empty reason
    with pytest.raises(ValueError):
        TeacherOverride(
            student_id="stu_123",
            teacher_id="tea_01",
            class_id="8-A",
            concept_id="c8_math_linear_eq",
            override_action="close_gap",
            reason="   "  # Empty / whitespace reason rejected
        )


def test_tombstone_and_audit_privacy():
    tombstone = Tombstone(pending_devices=2)
    assert len(tombstone.opaque_key) >= 16
    assert tombstone.status == TombstoneStatus.PENDING

    # Audit event must not accept student identifiers or learning payloads
    event = AuditLogEvent(
        event_type=AuditEventType.DELETE,
        actor="tea_math_01",
        class_id="8-A",
        record_count=1,
        opaque_tombstone_key=tombstone.opaque_key
    )
    assert event.record_count == 1
    assert event.opaque_tombstone_key == tombstone.opaque_key

    with pytest.raises(ValidationError):
        # Extra payload like student_id or answer should be rejected by model_config forbid
        AuditLogEvent(
            event_type=AuditEventType.DELETE,
            actor="tea_01",
            class_id="8-A",
            student_id="stu_leak"
        )
