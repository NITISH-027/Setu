import sys
import os
import pytest

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.engine.sequencer import RuleSequencer, DEFAULT_RULES


def test_sequencer_data_rule_change():
    """
    PROVES requirement from Part 2:
    'Sequencer: rules stored as data, not hard-coded.
     Test: changing a rule in data changes behaviour with no code edit.'
    """
    sequencer = RuleSequencer()

    state = {
        "stuck_attempts": 2,
        "mastery_estimate": 0.4
    }

    # Under default data rules, stuck_attempts >= 2 triggers 'FLAG_TEACHER_STUCK'
    decision = sequencer.evaluate(state)
    assert decision.action == "FLAG_TEACHER_STUCK"
    assert "Teacher assistance flagged" in decision.reason

    # Now, change the rules purely in DATA without altering any Python code:
    # Change threshold from 2 to 4
    custom_rules_data = [
        {
            "id": "rule_stuck_attempts_flag",
            "priority": 100,
            "condition_key": "stuck_attempts",
            "operator": ">=",
            "threshold": 4,  # Changed in data from 2 to 4!
            "action": "FLAG_TEACHER_STUCK",
            "reason": "Teacher assistance flagged after 4 attempts."
        },
        {
            "id": "rule_default_solve",
            "priority": 10,
            "condition_key": "always_true",
            "operator": "==",
            "threshold": True,
            "action": "CONTINUE_PRACTICE",
            "reason": "Continuing practice questions."
        }
    ]

    sequencer.load_rules(custom_rules_data)

    # Re-evaluate the exact same student state (stuck_attempts = 2)
    new_decision = sequencer.evaluate(state)

    # Behavior has changed: it no longer flags teacher at 2, but continues practice!
    assert new_decision.action == "CONTINUE_PRACTICE"
    assert new_decision.rule_id == "rule_default_solve"

    # And with stuck_attempts = 4, it triggers the new data-configured rule
    state_4 = {"stuck_attempts": 4, "mastery_estimate": 0.4}
    decision_4 = sequencer.evaluate(state_4)
    assert decision_4.action == "FLAG_TEACHER_STUCK"
    assert "after 4 attempts" in decision_4.reason
