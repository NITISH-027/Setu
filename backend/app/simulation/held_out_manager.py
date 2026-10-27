"""
Held-Out Question Manager.
Maintains an isolated set of evaluation questions reserved exclusively for future evaluation
once real empirical student data exists. Held-out questions are strictly excluded from the
live adaptive drill loop.
"""

from typing import List, Set, Dict, Any, Optional
from app.models.content import Question, Option, ReviewRecord, ReviewStatus


class HeldOutQuestionManager:
    DISCLAIMER = "HELD-OUT SET: Reserved for post-pilot empirical validation. Strictly excluded from live drill."

    def __init__(self, held_out_questions: Optional[List[Question]] = None):
        self.held_out_questions = held_out_questions or self._default_held_out_set()
        self.held_out_ids: Set[str] = {q.id for q in self.held_out_questions}

    def _default_held_out_set(self) -> List[Question]:
        return [
            Question(
                id="held_out_c8_leq_01",
                concept="c8_math_linear_eq_one_var",
                difficulty=0.6,
                question_text="[HELD-OUT EVALUATION] Solve for p: 4p - 7 = 2p + 5",
                options=[
                    Option(id="ho_1", text="p = 6", is_correct=True, numeric_value=6.0),
                    Option(id="ho_2", text="p = -1", is_correct=False, misconception_tag="tag_grouping_variables_wrong_sign", numeric_value=-1.0),
                    Option(id="ho_3", text="p = 1", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=1.0)
                ],
                review_record=ReviewRecord(status=ReviewStatus.AUTHOR_DRAFTED)
            ),
            Question(
                id="held_out_c8_rat_01",
                concept="c8_math_rational_ops",
                difficulty=0.5,
                question_text="[HELD-OUT EVALUATION] Find the product: (-4/9) × (3/8)",
                options=[
                    Option(id="ho_1", text="-1/6", is_correct=True),
                    Option(id="ho_2", text="1/6", is_correct=False, misconception_tag="tag_class6_integer_subtraction"),
                    Option(id="ho_3", text="-7/17", is_correct=False, misconception_tag="tag_adding_denominators_directly")
                ],
                review_record=ReviewRecord(status=ReviewStatus.AUTHOR_DRAFTED)
            )
        ]

    def is_held_out(self, question_id: str) -> bool:
        return question_id in self.held_out_ids

    def filter_live_questions(self, questions: List[Question]) -> List[Question]:
        """Filters out held-out evaluation questions from live training/practice pools."""
        return [q for q in questions if q.id not in self.held_out_ids]
