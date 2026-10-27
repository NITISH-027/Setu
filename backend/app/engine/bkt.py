"""
Bayesian Knowledge Tracing (BKT) implementation.
Pure-Python.
NOTICE: All parameters (prior, learn, guess, slip) are hand-set and uncalibrated.
Outputs are labelled 'uncalibrated, hand-set'.
"""

from typing import Dict, Any, Tuple
from app.models.learning import BKTParameters, MasteryState


class BKTEngine:
    """
    Standard Corbett & Anderson Bayesian Knowledge Tracing algorithm:
    P(L_0) = prior
    P(T)   = learn (probability of transitioning from unmastered to mastered)
    P(G)   = guess (probability of answering correctly if unmastered)
    P(S)   = slip (probability of answering incorrectly if mastered)
    """

    LABEL = "uncalibrated, hand-set"

    def __init__(self, default_params: BKTParameters = None):
        self.params = default_params or BKTParameters()

    def update(
        self,
        current_mastery: float,
        is_correct: bool,
        custom_params: BKTParameters = None
    ) -> float:
        """
        Updates mastery probability given an attempt outcome.
        """
        p = custom_params or self.params
        prior_mastery = max(0.001, min(0.999, current_mastery))

        if is_correct:
            # P(L | Correct) = P(L) * (1 - S) / [ P(L)*(1 - S) + (1 - P(L))*G ]
            num = prior_mastery * (1.0 - p.slip)
            denom = num + (1.0 - prior_mastery) * p.guess
            posterior = num / denom if denom > 0 else prior_mastery
        else:
            # P(L | Incorrect) = P(L) * S / [ P(L)*S + (1 - P(L))*(1 - G) ]
            num = prior_mastery * p.slip
            denom = num + (1.0 - prior_mastery) * (1.0 - p.guess)
            posterior = num / denom if denom > 0 else prior_mastery

        # Transition: P(L_next) = posterior + (1 - posterior) * P(T)
        next_mastery = posterior + (1.0 - posterior) * p.learn
        return max(0.0, min(1.0, round(next_mastery, 4)))

    def initialize_mastery(self, student_id: str, concept_id: str) -> MasteryState:
        return MasteryState(
            student_id=student_id,
            concept_id=concept_id,
            mastery_estimate=self.params.prior,
            bkt_params=self.params,
            mastery_label=self.LABEL
        )
