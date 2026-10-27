"""
SM-2 Spaced Repetition Scheduling Engine.
Pure-Python.
NOTICE: Default repetition intervals and ease factors are untuned and unvalidated
against real classroom retention data. They are designed to demonstrate spaced review.
"""

from datetime import datetime, timedelta
from typing import Tuple
from app.models.learning import MasteryState


class SpacedRepetitionScheduler:
    DISCLAIMER = "SM-2 intervals are untuned and unvalidated against classroom retention curves."

    def __init__(self, default_ease_factor: float = 2.5):
        self.default_ease = default_ease_factor

    def schedule_next_review(
        self,
        mastery_state: MasteryState,
        quality: int,  # 0 to 5 (e.g. 5=perfect, 4=correct with slight hesitation, 3=correct with difficulty, <3=fail)
        current_time: datetime = None
    ) -> MasteryState:
        now = current_time or datetime.utcnow()
        mastery_state.last_seen = now

        if quality >= 3:
            # Successful recall
            if mastery_state.consecutive_successes == 0:
                interval_days = 1.0
            elif mastery_state.consecutive_successes == 1:
                interval_days = 3.0
            else:
                interval_days = round(mastery_state.interval_days * mastery_state.ease_factor, 1)

            mastery_state.consecutive_successes += 1
        else:
            # Failed recall: reset repetitions
            mastery_state.consecutive_successes = 0
            interval_days = 1.0

        # Update ease factor using standard SM-2 formula:
        # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        q = max(0, min(5, quality))
        delta_ease = 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)
        new_ease = max(1.3, round(mastery_state.ease_factor + delta_ease, 2))

        mastery_state.ease_factor = new_ease
        mastery_state.interval_days = interval_days
        mastery_state.next_review = now + timedelta(days=interval_days)

        return mastery_state

    def is_due_for_review(self, mastery_state: MasteryState, current_time: datetime = None) -> bool:
        if not mastery_state.next_review:
            return False
        now = current_time or datetime.utcnow()
        return now >= mastery_state.next_review
