import sys
import os
import pytest

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.models.concept import Concept, PrerequisiteEdge
from app.models.content import Question, Option, ReviewRecord, ReviewStatus
from app.models.pack import ContentPack, PackMetadata
from app.validator.pack_validator import PackValidator


def test_validator_rejects_untagged_wrong_option():
    validator = PackValidator()

    # Question with an untagged wrong option
    q_bad = Question(
        id="q1",
        concept="c1",
        question_text="Solve: 2x = 6",
        options=[
            Option(id="o1", text="x = 3", is_correct=True),
            Option(id="o2", text="x = 4", is_correct=False, misconception_tag=None)  # Missing tag!
        ]
    )

    pack = ContentPack(
        metadata=PackMetadata(),
        concepts=[Concept(id="c1", name="Equations", class_level=8)],
        questions=[q_bad]
    )

    result = validator.validate(pack)
    assert not result.is_valid
    errors = result.errors()
    assert any(e.code == "UNTAGGED_WRONG_OPTION" for e in errors)


def test_validator_detects_cycles_and_dangling():
    validator = PackValidator()

    # Dangling prerequisite: c2 depends on non-existent c99
    pack_dangling = ContentPack(
        concepts=[Concept(id="c2", name="Fractions", class_level=7)],
        prerequisite_edges=[PrerequisiteEdge(concept="c2", depends_on="c99")]
    )
    result = validator.validate(pack_dangling)
    assert not result.is_valid
    assert any(e.code == "DANGLING_PREREQUISITE" for e in result.errors())

    # Cycle: c1 -> c2 -> c3 -> c1
    pack_cycle = ContentPack(
        concepts=[
            Concept(id="c1", name="One", class_level=8),
            Concept(id="c2", name="Two", class_level=8),
            Concept(id="c3", name="Three", class_level=8),
        ],
        prerequisite_edges=[
            PrerequisiteEdge(concept="c1", depends_on="c2"),
            PrerequisiteEdge(concept="c2", depends_on="c3"),
            PrerequisiteEdge(concept="c3", depends_on="c1"),
        ]
    )
    result_cycle = validator.validate(pack_cycle)
    assert not result_cycle.is_valid
    assert any(e.code == "GRAPH_CYCLE_DETECTED" for e in result_cycle.errors())


def test_validator_missing_probes():
    validator = PackValidator()

    # Question tags a misconception 'tag_sign_flip', but no question exists with probe_for_misconception='tag_sign_flip'
    q = Question(
        id="q1",
        concept="c1",
        question_text="Solve: -3x = 9",
        options=[
            Option(id="o1", text="x = -3", is_correct=True),
            Option(id="o2", text="x = 3", is_correct=False, misconception_tag="tag_sign_flip")
        ]
    )
    pack = ContentPack(
        concepts=[Concept(id="c1", name="Equations", class_level=8)],
        questions=[q]
    )

    result = validator.validate(pack)
    assert not result.is_valid
    assert any(e.code == "MISSING_PROBE_FOR_TAG" for e in result.errors())


def test_recompute_numeric_answers():
    validator = PackValidator()

    # Option text says "4" but numeric_value is set to 5.0 -> mismatch warning
    q = Question(
        id="q_num",
        concept="c1",
        question_text="What is 2 + 2?",
        options=[
            Option(id="o1", text="4", is_correct=True, numeric_value=5.0),  # Mismatch!
            Option(id="o2", text="3", is_correct=False, misconception_tag="tag_arithmetic", numeric_value=3.0)
        ],
        probe_for_misconception="tag_arithmetic"
    )
    pack = ContentPack(
        concepts=[Concept(id="c1", name="Addition", class_level=6)],
        questions=[q]
    )

    result = validator.validate(pack)
    warnings = result.warnings()
    assert any(w.code == "NUMERIC_VALUE_MISMATCH" for w in warnings)


def test_duplicate_options_flagged():
    validator = PackValidator()

    # Question has duplicate options
    q = Question(
        id="q_dup",
        concept="c1",
        question_text="Pick an option",
        options=[
            Option(id="o1", text="Option A", is_correct=True),
            Option(id="o2", text="Option A", is_correct=False, misconception_tag="tag_dup"),
        ],
        probe_for_misconception="tag_dup"
    )
    pack = ContentPack(
        concepts=[Concept(id="c1", name="Test", class_level=8)],
        questions=[q]
    )
    result = validator.validate(pack)
    assert any(w.code == "DUPLICATE_OPTION" for w in result.warnings())


def test_validator_validates_hints():
    from app.models.content import HintLadder
    validator = PackValidator()

    q = Question(
        id="q_hint_test",
        concept="c1",
        question_text="Solve: x + 7 = 14",
        options=[
            Option(id="o1", text="7", is_correct=True),
            Option(id="o2", text="21", is_correct=False, misconception_tag="tag_transposition")
        ],
        probe_for_misconception="tag_transposition"
    )

    bad_hint = HintLadder(
        question_id="q_hint_test",
        level_1_hint="Subtract 7",
        level_2_partial_step="x = 3 - 7",
        level_3_worked_step="Calculate 3 - 7: x = -4."  # Contradicts option '7'!
    )

    pack = ContentPack(
        concepts=[Concept(id="c1", name="Equations", class_level=8)],
        questions=[q],
        hints=[bad_hint]
    )

    result = validator.validate(pack)
    assert not result.is_valid
    errors = result.errors()
    assert any(e.code == "HINT_ANSWER_CONTRADICTION" for e in errors)

    # Now with valid hint
    good_hint = HintLadder(
        question_id="q_hint_test",
        level_1_hint="Subtract 7",
        level_2_partial_step="x = 14 - 7",
        level_3_worked_step="Calculate 14 - 7: x = 7."
    )
    pack_good = ContentPack(
        concepts=[Concept(id="c1", name="Equations", class_level=8)],
        questions=[q],
        hints=[good_hint]
    )
    result_good = validator.validate(pack_good)
    assert result_good.is_valid

