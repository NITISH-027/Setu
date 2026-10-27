"""
Round 3 Hold-Out Test:
Validates that the system seamlessly accepts and adapts to unseen questions,
edge cases, and rules added strictly through data (JSON/dict), with ZERO code modifications.
"""

import sys
import os
import json
import pytest

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.models.pack import ContentPack
from app.models.content import Question, Option, ReviewRecord, ReviewStatus
from app.models.student import Student
from app.models.learning import Plan, MasteryState, Attempt, StageEnum
from app.engine.adaptive_engine import AdaptiveEngine
from app.engine.sequencer import DEFAULT_RULES
from app.validator.pack_validator import PackValidator


def test_round3_data_only_adaptation():
    # 1. Load base shipped pack
    pack_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packs", "cbse_math_pack.json"))
    with open(pack_path, "r", encoding="utf-8") as f:
        pack_data = json.load(f)

    # 2. Add UNSEEN question and probe strictly via data (no code change)
    unseen_tag = "tag_round3_unseen_edge_case"
    unseen_question = {
        "id": "q_round3_unseen_01",
        "concept": "c8_math_linear_eq_one_var",
        "difficulty": 0.8,
        "language": "en",
        "question_text": "[ROUND 3 UNSEEN] Solve for z: (z/2) + (z/3) = 10",
        "options": [
            {"id": "uo_1", "text": "z = 12", "is_correct": True, "numeric_value": 12.0},
            {"id": "uo_2", "text": "z = 20", "is_correct": False, "misconception_tag": unseen_tag, "numeric_value": 20.0}
        ],
        "review_record": {"status": "author-drafted, unreviewed"}
    }
    unseen_probe = {
        "id": "probe_round3_unseen_01",
        "concept": "c6_math_fractions_basic",
        "difficulty": 0.4,
        "language": "en",
        "question_text": "[ROUND 3 UNSEEN PROBE] What is 1/2 + 1/3?",
        "options": [
            {"id": "po_1", "text": "5/6", "is_correct": True},
            {"id": "po_2", "text": "2/5", "is_correct": False, "misconception_tag": unseen_tag}
        ],
        "probe_for_misconception": unseen_tag,
        "review_record": {"status": "author-drafted, unreviewed"}
    }

    pack_data["questions"].append(unseen_question)
    pack_data["questions"].append(unseen_probe)

    augmented_pack = ContentPack.model_validate(pack_data)

    # Verify validator accepts augmented data without errors
    validator = PackValidator()
    val_res = validator.validate(augmented_pack)
    assert val_res.is_valid is True

    # 3. Add a NEW RULE strictly via data (priority 105: Challenge Mode for 5 successes)
    custom_rules = [
        {
            "id": "rule_round3_challenge_mode",
            "priority": 105,
            "condition_key": "consecutive_successes",
            "operator": ">=",
            "threshold": 5,
            "action": "TRIGGER_CHALLENGE_MODE",
            "reason": "[ROUND 3 DATA RULE] Student answered 5 in a row. Unlocking Olympiad challenge question."
        }
    ]

    # Initialize engine with augmented pack and new data rule
    engine = AdaptiveEngine(augmented_pack, sequencer_rules=DEFAULT_RULES + custom_rules)

    # 4. Prove unseen question behaves correctly in engine
    student = Student(pseudonymous_id="stu_round3_tester", class_id="8-A", pin_hash="h")
    plan = Plan(student_id="stu_round3_tester", class_id="8-A", current_concept_id="c8_math_linear_eq_one_var")
    mastery = MasteryState(student_id="stu_round3_tester", concept_id="c8_math_linear_eq_one_var")

    # Student encounters the unseen question and makes the unseen error
    attempt_unseen = Attempt(
        student_id="stu_round3_tester",
        question_id="q_round3_unseen_01",
        concept_id="c8_math_linear_eq_one_var",
        selected_option_id="uo_2",
        is_correct=False,
        misconception_tag=unseen_tag
    )

    plan, mastery, hyp, dec = engine.process_attempt(student, plan, attempt_unseen, mastery, None)
    assert hyp.misconception_tag == unseen_tag
    assert hyp.evidence_band.value == "Low"

    # Engine automatically serves the unseen probe question!
    next_step = engine.get_next_step(student, plan, mastery, hyp)
    assert next_step.item.id == "probe_round3_unseen_01"

    # 5. Prove custom Round 3 data rule fires when condition is met
    mastery.consecutive_successes = 5
    challenge_dec = engine.sequencer.evaluate({"consecutive_successes": 5})
    assert challenge_dec.action == "TRIGGER_CHALLENGE_MODE"
    assert "Unlocking Olympiad challenge" in challenge_dec.reason
