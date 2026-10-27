import sys
import os
import pytest

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.simulation.held_out_manager import HeldOutQuestionManager
from app.models.content import Question, Option


def test_held_out_question_isolation():
    """
    Test requirement:
    'Held-out question set, reserved for evaluation once real data exists.'
    """
    manager = HeldOutQuestionManager()

    assert len(manager.held_out_questions) >= 2
    assert "HELD-OUT SET" in manager.DISCLAIMER

    # Held out ID check
    assert manager.is_held_out("held_out_c8_leq_01") is True
    assert manager.is_held_out("q_c8_leq_01") is False

    # Filtering from live pools
    mixed_questions = [
        Question(id="q1", concept="c1", question_text="q1", options=[Option(id="o1", text="a", is_correct=True)]),
        manager.held_out_questions[0]
    ]

    live_filtered = manager.filter_live_questions(mixed_questions)
    assert len(live_filtered) == 1
    assert live_filtered[0].id == "q1"
