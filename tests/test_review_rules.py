import sys
import os
import pytest

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.models.content import ReviewRecord, ReviewStatus, Question, Option, Lesson
from app.models.concept import Concept
from app.models.pack import ContentPack
from app.validator.review_manager import ReviewManager
from app.validator.coverage_reporter import CoverageReporter


def test_seed_cannot_set_reviewed():
    manager = ReviewManager()
    draft = manager.create_draft_record(version=1)
    assert draft.status == ReviewStatus.AUTHOR_DRAFTED
    assert not draft.is_human_reviewed()


def test_imported_reviewed_downgraded():
    manager = ReviewManager()  # No registered external reviewers

    # External record claiming 'reviewed' without recognized provenance
    untrusted_import = {
        "status": "reviewed",
        "reviewer_name": "Random Third Party",
        "attestation_statement": "Looks good",
        "item_version": 1
    }

    processed = manager.import_external_record(untrusted_import)
    # Must be downgraded to unverified import
    assert processed.status == ReviewStatus.UNVERIFIED_IMPORT
    assert not processed.is_human_reviewed()


def test_edit_resets_review_status():
    manager = ReviewManager()
    manager.register_human_reviewer("K. Raman", "Mathematics Head (self-declared)")

    initial = manager.create_draft_record()
    reviewed = manager.human_attest(
        initial,
        reviewer_name="K. Raman",
        reviewer_role="Mathematics Head",
        attestation_statement="I checked this item"
    )
    assert reviewed.status == ReviewStatus.REVIEWED
    assert reviewed.is_human_reviewed()

    # When item is modified, status is reset
    modified = manager.on_item_modified(reviewed)
    assert modified.status == ReviewStatus.CHANGED_SINCE_REVIEW
    assert modified.item_version == reviewed.item_version + 1
    assert not modified.is_human_reviewed()


def test_coverage_reporter_percentage():
    reporter = CoverageReporter()

    # Create a pack with 1 reviewed question and 1 unreviewed question
    manager = ReviewManager()
    q1 = Question(
        id="q1",
        concept="c1",
        question_text="2+2=?",
        options=[
            Option(id="o1", text="4", is_correct=True),
            Option(id="o2", text="5", is_correct=False, misconception_tag="tag_add")
        ],
        probe_for_misconception="tag_add",
        review_record=manager.human_attest(
            manager.create_draft_record(),
            reviewer_name="Teacher A",
            reviewer_role="TGT Math",
            attestation_statement="I checked this item"
        )
    )
    q2 = Question(
        id="q2",
        concept="c1",
        question_text="3+3=?",
        options=[
            Option(id="o1", text="6", is_correct=True),
            Option(id="o2", text="7", is_correct=False, misconception_tag="tag_add")
        ],
        probe_for_misconception="tag_add",
        review_record=manager.create_draft_record()
    )

    pack = ContentPack(
        concepts=[Concept(id="c1", name="Addition", class_level=8)],
        questions=[q1, q2]
    )

    report = reporter.generate_report(pack)
    assert report.data["total_items"] == 2
    assert report.data["human_reviewed_items"] == 1
    assert report.data["percent_human_reviewed"] == 50.0
