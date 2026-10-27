import sys
import os
from datetime import datetime, timedelta
import pytest

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.engine.scheduler import SpacedRepetitionScheduler
from app.models.learning import MasteryState


def test_sm2_intervals():
    scheduler = SpacedRepetitionScheduler()
    state = MasteryState(student_id="stu_01", concept_id="c8_math_linear_eq_one_var")

    now = datetime(2026, 1, 1, 10, 0, 0)

    # First successful recall -> interval is 1 day
    state = scheduler.schedule_next_review(state, quality=4, current_time=now)
    assert state.consecutive_successes == 1
    assert state.interval_days == 1.0
    assert state.next_review == now + timedelta(days=1.0)
    assert not scheduler.is_due_for_review(state, current_time=now)
    assert scheduler.is_due_for_review(state, current_time=now + timedelta(days=1.1))

    # Second successful recall -> interval is 3 days
    second_time = now + timedelta(days=1.1)
    state = scheduler.schedule_next_review(state, quality=4, current_time=second_time)
    assert state.consecutive_successes == 2
    assert state.interval_days == 3.0
    assert state.next_review == second_time + timedelta(days=3.0)

    # Third successful recall -> interval is 3.0 * ease_factor
    third_time = second_time + timedelta(days=3.1)
    prev_interval = state.interval_days
    ease = state.ease_factor
    state = scheduler.schedule_next_review(state, quality=5, current_time=third_time)
    assert state.consecutive_successes == 3
    assert state.interval_days == round(prev_interval * ease, 1)

    # Failed recall -> resets repetitions and interval to 1 day
    fourth_time = third_time + timedelta(days=10)
    state = scheduler.schedule_next_review(state, quality=1, current_time=fourth_time)
    assert state.consecutive_successes == 0
    assert state.interval_days == 1.0
