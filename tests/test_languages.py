import sys
import os
import pytest
from datetime import datetime

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.i18n.localization_manager import LocalizationManager
from app.models.content import Lesson, ReviewRecord, ReviewStatus


def test_unreviewed_language_fallback():
    """
    Test requirement:
    'Languages: Add Hindi and Telugu lesson and question text as drafts marked "unreviewed".
     Never present them as supported. A language counts as supported only for items reviewed
     by a fluent speaker and a subject reviewer (two attestations).
     The UI shows a visible fallback to English when a translation is missing.'
    """
    manager = LocalizationManager()

    # 1. Hindi draft string marked as unreviewed
    hi_result = manager.get_ui_string("submit_button", requested_lang="hi")
    assert hi_result.language == "hi"
    assert "उत्तर जमा करें" in hi_result.text
    assert "[HI Draft - unreviewed]" in hi_result.notice

    # 2. Telugu draft string marked as unreviewed
    te_result = manager.get_ui_string("submit_button", requested_lang="te")
    assert te_result.language == "te"
    assert "సమాధానం సమర్పించండి" in te_result.text
    assert "[TE Draft - unreviewed]" in te_result.notice

    # 3. Visible fallback to English when translation is missing
    missing_key = "non_existent_key"
    manager.catalog["en"]["custom_metric"] = "Mastery Level"
    # Not defined in Hindi
    fallback_result = manager.get_ui_string("custom_metric", requested_lang="hi")
    assert fallback_result.is_fallback is True
    assert fallback_result.language == "en"
    assert fallback_result.text == "Mastery Level"
    assert "[English Fallback - translation missing for hi]" in fallback_result.notice

    # 4. Lesson fallback test
    en_lesson = Lesson(
        id="les_en",
        concept="c1",
        language="en",
        content="Subtract 7 from both sides."
    )
    # Student requested Telugu, but only English lesson exists
    resolved, is_fb, notice = manager.resolve_lesson_content([en_lesson], requested_lang="te")
    assert is_fb is True
    assert resolved.language == "en"
    assert "[English Fallback" in notice

    # 5. Language support requires TWO human attestations (fluent speaker + subject reviewer)
    single_attestation = [
        ReviewRecord(
            status=ReviewStatus.REVIEWED,
            reviewer_name="Native Speaker",
            reviewer_role="Telugu Fluent Speaker (self-declared)",
            attestation_date=datetime.utcnow(),
            attestation_statement="Checked grammar"
        )
    ]
    # Single attestation cannot count as fully supported
    assert not LocalizationManager.verify_language_support_status(single_attestation)

    two_attestations = [
        ReviewRecord(
            status=ReviewStatus.REVIEWED,
            reviewer_name="Native Speaker",
            reviewer_role="Telugu Fluent Speaker (self-declared)",
            attestation_date=datetime.utcnow(),
            attestation_statement="Checked grammar"
        ),
        ReviewRecord(
            status=ReviewStatus.REVIEWED,
            reviewer_name="Math Teacher",
            reviewer_role="TGT Mathematics Subject Reviewer (self-declared)",
            attestation_date=datetime.utcnow(),
            attestation_statement="Checked mathematical correctness"
        )
    ]
    assert LocalizationManager.verify_language_support_status(two_attestations)
