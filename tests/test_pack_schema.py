import sys
import os
import json
import pytest

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.models.pack import ContentPack
from app.validator.pack_validator import PackValidator
from app.validator.coverage_reporter import CoverageReporter


@pytest.fixture
def shipped_pack():
    pack_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packs", "cbse_math_pack.json"))
    with open(pack_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ContentPack.model_validate(data)


def test_pack_serialization(shipped_pack):
    assert shipped_pack.metadata.board == "CBSE"
    assert shipped_pack.metadata.class_level == 8
    assert "intended NCERT alignment, unverified" in shipped_pack.metadata.alignment_disclaimer
    assert len(shipped_pack.concepts) >= 20
    assert len(shipped_pack.questions) >= 30


def test_shipped_pack_structural_validity(shipped_pack):
    validator = PackValidator()
    result = validator.validate(shipped_pack)
    # The shipped pack must have zero structural errors
    errors = result.errors()
    assert len(errors) == 0, f"Shipped pack has validation errors: {[e.to_dict() for e in errors]}"
    assert result.is_valid is True


def test_spine_coverage(shipped_pack):
    # Verify graph spine spans classes 6 to 10
    classes_present = {c.class_level for c in shipped_pack.concepts}
    assert {6, 7, 8, 9, 10}.issubset(classes_present)

    # Class 8 concepts are active; classes 6, 7, 9, 10 are graph-only
    for c in shipped_pack.concepts:
        if c.class_level != 8:
            assert c.graph_only is True, f"Concept {c.id} of class {c.class_level} must be marked graph_only"
        else:
            assert c.graph_only is False

    # Intended NCERT references are unverified by default
    for c in shipped_pack.concepts:
        assert c.reference_verified is False


def test_shipped_pack_coverage_report(shipped_pack):
    reporter = CoverageReporter()
    report = reporter.generate_report(shipped_pack)

    data = report.data
    assert data["total_concepts"] == 20
    assert data["active_concepts"] == 7
    assert data["graph_only_concepts"] == 13
    assert data["total_questions"] >= 30
    assert len(data["tags_without_probes"]) == 0  # Every tagged misconception has a probe!
    assert data["percent_human_reviewed"] == 0.0  # Honest review count (starts unreviewed)
