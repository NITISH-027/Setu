"""
Content expansion module for CBSE Class 8 Mathematics.
Fulfills FIX 9:
- At least 8 questions and 2 probes per active Class 8 concept.
- At least 5 Hindi and 5 Telugu draft questions and lessons for c8_math_linear_eq_one_var.
- Every wrong option tagged with a misconception.
- Probes provided for all tagged misconceptions.
- Numeric values verified.
- All items marked 'author-drafted, unreviewed'.
"""

from typing import List, Tuple
from app.models.content import Question, Option, Lesson, HintLadder, ReviewRecord, ReviewStatus


def make_draft_rr():
    return ReviewRecord(status=ReviewStatus.AUTHOR_DRAFTED)


def get_expansion_items() -> Tuple[List[Question], List[Lesson], List[HintLadder]]:
    questions: List[Question] = []
    lessons: List[Lesson] = []
    hints: List[HintLadder] = []

    # =========================================================================
    # 1. c8_math_linear_eq_one_var (Expand to 8 English + 5 Hindi + 5 Telugu + 2 Probes)
    # =========================================================================
    # Additional English questions (Q4 to Q8)
    questions.append(Question(
        id="q_c8_leq_04",
        concept="c8_math_linear_eq_one_var",
        difficulty=0.3,
        question_text="Solve for x: x - 4 = 11",
        options=[
            Option(id="opt_1", text="x = 15", is_correct=True, numeric_value=15.0),
            Option(id="opt_2", text="x = 7", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=7.0),
            Option(id="opt_3", text="x = -7", is_correct=False, misconception_tag="tag_class6_integer_subtraction", numeric_value=-7.0),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_04",
        level_1_hint="To undo subtracting 4, perform the opposite operation.",
        level_2_partial_step="Add 4 to both sides: x = 11 + 4.",
        level_3_worked_step="11 + 4 = 15, so x = 15.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_leq_05",
        concept="c8_math_linear_eq_one_var",
        difficulty=0.4,
        question_text="Solve for z: 4z = 28",
        options=[
            Option(id="opt_1", text="z = 7", is_correct=True, numeric_value=7.0),
            Option(id="opt_2", text="z = 24", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=24.0),
            Option(id="opt_3", text="z = -7", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=-7.0),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_05",
        level_1_hint="4z means 4 multiplied by z. What undoes multiplication?",
        level_2_partial_step="Divide both sides by 4: z = 28 / 4.",
        level_3_worked_step="28 / 4 = 7, so z = 7.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_leq_06",
        concept="c8_math_linear_eq_one_var",
        difficulty=0.5,
        question_text="Solve for m: 5m + 3 = 18",
        options=[
            Option(id="opt_1", text="m = 3", is_correct=True, numeric_value=3.0),
            Option(id="opt_2", text="m = 4.2", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=4.2),
            Option(id="opt_3", text="m = 10", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=10.0),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_06",
        level_1_hint="Subtract 3 from both sides first to isolate 5m.",
        level_2_partial_step="5m = 18 - 3 => 5m = 15.",
        level_3_worked_step="Divide by 5: m = 15 / 5 = 3.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_leq_07",
        concept="c8_math_linear_eq_one_var",
        difficulty=0.6,
        question_text="Solve for p: p/3 + 1 = 6",
        options=[
            Option(id="opt_1", text="p = 15", is_correct=True, numeric_value=15.0),
            Option(id="opt_2", text="p = 21", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=21.0),
            Option(id="opt_3", text="p = 2", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=2.0),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_07",
        level_1_hint="Subtract 1 from both sides first: p/3 = 5.",
        level_2_partial_step="Multiply both sides by 3 to isolate p.",
        level_3_worked_step="p = 5 * 3 = 15.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_leq_08",
        concept="c8_math_linear_eq_one_var",
        difficulty=0.7,
        question_text="Solve for k: 7k - 2 = 5k + 8",
        options=[
            Option(id="opt_1", text="k = 5", is_correct=True, numeric_value=5.0),
            Option(id="opt_2", text="k = 3", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=3.0),
            Option(id="opt_3", text="k = -5", is_correct=False, misconception_tag="tag_grouping_variables_wrong_sign", numeric_value=-5.0),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_08",
        level_1_hint="Transpose 5k to left and -2 to right.",
        level_2_partial_step="7k - 5k = 8 + 2 => 2k = 10.",
        level_3_worked_step="Divide by 2: k = 5.",
        review_record=make_draft_rr()
    ))

    # Probe 2 for c8_math_linear_eq_one_var (direct concept probe)
    questions.append(Question(
        id="probe_c8_leq_direct_02",
        concept="c8_math_linear_eq_one_var",
        difficulty=0.3,
        question_text="To solve 'x - 9 = 2', what must you add to both sides?",
        options=[
            Option(id="p1", text="Add 9 to both sides", is_correct=True, numeric_value=9.0),
            Option(id="p2", text="Subtract 9 from both sides", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=-9.0)
        ],
        probe_for_misconception="tag_sign_error_on_transposition",
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="probe_c8_leq_direct_02",
        level_1_hint="Inverse operation of -9 is +9.",
        level_2_partial_step="Add 9: x - 9 + 9 = 2 + 9.",
        level_3_worked_step="Result is x = 11.",
        review_record=make_draft_rr()
    ))

    # 4 Additional Hindi draft questions (q_c8_leq_hi_02 to 05)
    questions.append(Question(
        id="q_c8_leq_hi_02",
        concept="c8_math_linear_eq_one_var",
        difficulty=0.4,
        language="hi",
        question_text="[ड्राफ्ट] हल कीजिए: 3x - 5 = 16",
        options=[
            Option(id="opt_hi_1", text="x = 7", is_correct=True, numeric_value=7.0),
            Option(id="opt_hi_2", text="x = 3.67", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=3.67),
            Option(id="opt_hi_3", text="x = 11", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=11.0)
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_hi_02",
        level_1_hint="[ड्राफ्ट] पहले दोनों पक्षों में 5 जोड़ें।",
        level_2_partial_step="[ड्राफ्ट] 3x = 16 + 5 => 3x = 21",
        level_3_worked_step="[ड्राफ्ट] x = 21 / 3 = 7",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_leq_hi_03",
        concept="c8_math_linear_eq_one_var",
        difficulty=0.5,
        language="hi",
        question_text="[ड्राफ्ट] हल कीजिए: 2y + 9 = 1",
        options=[
            Option(id="opt_hi_1", text="y = -4", is_correct=True, numeric_value=-4.0),
            Option(id="opt_hi_2", text="y = 5", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=5.0),
            Option(id="opt_hi_3", text="y = -8", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=-8.0)
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_hi_03",
        level_1_hint="[ड्राफ्ट] दोनों पक्षों से 9 घटाएं।",
        level_2_partial_step="[ड्राफ्ट] 2y = 1 - 9 => 2y = -8",
        level_3_worked_step="[ड्राफ्ट] y = -8 / 2 = -4",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_leq_hi_04",
        concept="c8_math_linear_eq_one_var",
        difficulty=0.3,
        language="hi",
        question_text="[ड्राफ्ट] हल कीजिए: x - 4 = 11",
        options=[
            Option(id="opt_hi_1", text="x = 15", is_correct=True, numeric_value=15.0),
            Option(id="opt_hi_2", text="x = 7", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=7.0),
            Option(id="opt_hi_3", text="x = -7", is_correct=False, misconception_tag="tag_class6_integer_subtraction", numeric_value=-7.0)
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_hi_04",
        level_1_hint="[ड्राफ्ट] दोनों पक्षों में 4 जोड़ें।",
        level_2_partial_step="[ड्राफ्ट] x = 11 + 4",
        level_3_worked_step="[ड्राफ्ट] x = 15",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_leq_hi_05",
        concept="c8_math_linear_eq_one_var",
        difficulty=0.4,
        language="hi",
        question_text="[ड्राफ्ट] हल कीजिए: 4z = 28",
        options=[
            Option(id="opt_hi_1", text="z = 7", is_correct=True, numeric_value=7.0),
            Option(id="opt_hi_2", text="z = 24", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=24.0),
            Option(id="opt_hi_3", text="z = -7", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=-7.0)
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_hi_05",
        level_1_hint="[ड्राफ्ट] दोनों पक्षों को 4 से विभाजित करें।",
        level_2_partial_step="[ड्राफ्ट] z = 28 / 4",
        level_3_worked_step="[ड्राफ्ट] z = 7",
        review_record=make_draft_rr()
    ))

    # 4 Additional Telugu draft questions (q_c8_leq_te_02 to 05)
    questions.append(Question(
        id="q_c8_leq_te_02",
        concept="c8_math_linear_eq_one_var",
        difficulty=0.4,
        language="te",
        question_text="[డ్రాఫ్ట్] సాధించండి: 3x - 5 = 16",
        options=[
            Option(id="opt_te_1", text="x = 7", is_correct=True, numeric_value=7.0),
            Option(id="opt_te_2", text="x = 3.67", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=3.67),
            Option(id="opt_te_3", text="x = 11", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=11.0)
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_te_02",
        level_1_hint="[డ్రాఫ్ట్] మొదట రెండు వైపులా 5 కలపండి.",
        level_2_partial_step="[డ్రాఫ్ట్] 3x = 16 + 5 => 3x = 21",
        level_3_worked_step="[డ్రాఫ్ట్] x = 21 / 3 = 7",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_leq_te_03",
        concept="c8_math_linear_eq_one_var",
        difficulty=0.5,
        language="te",
        question_text="[డ్రాఫ్ట్] సాధించండి: 2y + 9 = 1",
        options=[
            Option(id="opt_te_1", text="y = -4", is_correct=True, numeric_value=-4.0),
            Option(id="opt_te_2", text="y = 5", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=5.0),
            Option(id="opt_te_3", text="y = -8", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=-8.0)
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_te_03",
        level_1_hint="[డ్రాఫ్ట్] రెండు వైపుల నుండి 9 తీసివేయండి.",
        level_2_partial_step="[డ్రాఫ్ట్] 2y = 1 - 9 => 2y = -8",
        level_3_worked_step="[డ్రాఫ్ట్] y = -8 / 2 = -4",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_leq_te_04",
        concept="c8_math_linear_eq_one_var",
        difficulty=0.3,
        language="te",
        question_text="[డ్రాఫ్ట్] సాధించండి: x - 4 = 11",
        options=[
            Option(id="opt_te_1", text="x = 15", is_correct=True, numeric_value=15.0),
            Option(id="opt_te_2", text="x = 7", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=7.0),
            Option(id="opt_te_3", text="x = -7", is_correct=False, misconception_tag="tag_class6_integer_subtraction", numeric_value=-7.0)
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_te_04",
        level_1_hint="[డ్రాఫ్ట్] రెండు వైపులా 4 కలపండి.",
        level_2_partial_step="[డ్రాఫ్ట్] x = 11 + 4",
        level_3_worked_step="[డ్రాఫ్ట్] x = 15",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_leq_te_05",
        concept="c8_math_linear_eq_one_var",
        difficulty=0.4,
        language="te",
        question_text="[డ్రాఫ్ట్] సాధించండి: 4z = 28",
        options=[
            Option(id="opt_te_1", text="z = 7", is_correct=True, numeric_value=7.0),
            Option(id="opt_te_2", text="z = 24", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=24.0),
            Option(id="opt_te_3", text="z = -7", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=-7.0)
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_te_05",
        level_1_hint="[డ్రాఫ్ట్] రెండు వైపులా 4 తో భాగించండి.",
        level_2_partial_step="[డ్రాఫ్ట్] z = 28 / 4",
        level_3_worked_step="[డ్రాఫ్ట్] z = 7",
        review_record=make_draft_rr()
    ))

    # 4 Additional Hindi draft lessons
    lessons.append(Lesson(
        id="les_hi_draft_leq_02",
        concept="c8_math_linear_eq_one_var",
        misconception="tag_dividing_instead_of_subtracting",
        language="hi",
        content="[ड्राफ्ट - असमीक्षित] विपरीत संक्रिया: गुणा होने पर भाग करें (जैसे 4x = 20 में 4 से भाग)।",
        review_record=make_draft_rr()
    ))
    lessons.append(Lesson(
        id="les_hi_draft_leq_03",
        concept="c8_math_linear_eq_one_var",
        misconception="tag_class6_integer_subtraction",
        language="hi",
        content="[ड्राफ्ट - असमीक्षित] पूर्णांक घटाव: जब छोटी संख्या से बड़ी संख्या घटाते हैं, तो उत्तर ऋणात्मक होता है (3 - 7 = -4)।",
        review_record=make_draft_rr()
    ))
    lessons.append(Lesson(
        id="les_hi_draft_leq_04",
        concept="c8_math_linear_eq_one_var",
        language="hi",
        content="[ड्राफ्ट - असमीक्षित] आधारभूत नियम: समीकरण एक तराजू की तरह संतुलित रहता है।",
        review_record=make_draft_rr()
    ))
    lessons.append(Lesson(
        id="les_hi_draft_leq_05",
        concept="c8_math_linear_eq_one_var",
        language="hi",
        content="[ड्राफ्ट - असमीक्षित] चर को अलग करना: पहले जोड़/घटाव को हटाएं, फिर गुणा/भाग को।",
        review_record=make_draft_rr()
    ))

    # 4 Additional Telugu draft lessons
    lessons.append(Lesson(
        id="les_te_draft_leq_02",
        concept="c8_math_linear_eq_one_var",
        misconception="tag_dividing_instead_of_subtracting",
        language="te",
        content="[డ్రాఫ్ట్ - సమీక్షించబడలేదు] విలోమ ప్రక్రియ: గుణకారంగా ఉన్నప్పుడు భాగించండి (ఉదా. 4x = 20 లో 4 తో భాగించాలి).",
        review_record=make_draft_rr()
    ))
    lessons.append(Lesson(
        id="les_te_draft_leq_03",
        concept="c8_math_linear_eq_one_var",
        misconception="tag_class6_integer_subtraction",
        language="te",
        content="[డ్రాఫ్ట్ - సమీక్షించబడలేదు] పూర్ణాంకాల వ్యవకలనం: చిన్న సంఖ్య నుండి పెద్ద సంఖ్య తీసివేస్తే ఋణాత్మకం వస్తుంది (3 - 7 = -4).",
        review_record=make_draft_rr()
    ))
    lessons.append(Lesson(
        id="les_te_draft_leq_04",
        concept="c8_math_linear_eq_one_var",
        language="te",
        content="[డ్రాఫ్ట్ - సమీక్షించబడలేదు] ప్రాథమిక నియమం: సమీకరణం త్రాసు లాంటిది, రెండు వైపులా సమాన మార్పులు చేయాలి.",
        review_record=make_draft_rr()
    ))
    lessons.append(Lesson(
        id="les_te_draft_leq_05",
        concept="c8_math_linear_eq_one_var",
        language="te",
        content="[డ్రాఫ్ట్ - సమీక్షించబడలేదు] చరరాశి వేరుచేయడం: మొదట సంకలనం/వ్యవకలనం తొలగించి, తరువాత గుణకారం/భాగహారం చేయండి.",
        review_record=make_draft_rr()
    ))

    # =========================================================================
    # 2. c8_math_linear_eq_variables_both_sides (Expand to 8 questions + 2 probes)
    # =========================================================================
    questions.append(Question(
        id="q_c8_leq_both_04",
        concept="c8_math_linear_eq_variables_both_sides",
        difficulty=0.4,
        question_text="Solve: 6x + 2 = 4x + 10",
        options=[
            Option(id="opt_1", text="x = 4", is_correct=True, numeric_value=4.0),
            Option(id="opt_2", text="x = 6", is_correct=False, misconception_tag="tag_grouping_variables_wrong_sign", numeric_value=6.0),
            Option(id="opt_3", text="x = 1.2", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=1.2),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_both_04",
        level_1_hint="Subtract 4x from both sides.",
        level_2_partial_step="6x - 4x = 10 - 2 => 2x = 8.",
        level_3_worked_step="Divide by 2: x = 4.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_leq_both_05",
        concept="c8_math_linear_eq_variables_both_sides",
        difficulty=0.5,
        question_text="Solve: 3(x + 2) = 2x + 11",
        options=[
            Option(id="opt_1", text="x = 5", is_correct=True, numeric_value=5.0),
            Option(id="opt_2", text="x = 9", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=9.0),
            Option(id="opt_3", text="x = 3.4", is_correct=False, misconception_tag="tag_grouping_variables_wrong_sign", numeric_value=3.4),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_both_05",
        level_1_hint="Expand 3(x + 2) = 3x + 6 first.",
        level_2_partial_step="3x + 6 = 2x + 11 => 3x - 2x = 11 - 6.",
        level_3_worked_step="x = 5.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_leq_both_06",
        concept="c8_math_linear_eq_variables_both_sides",
        difficulty=0.6,
        question_text="Solve: 4y - 7 = y + 5",
        options=[
            Option(id="opt_1", text="y = 4", is_correct=True, numeric_value=4.0),
            Option(id="opt_2", text="y = -0.4", is_correct=False, misconception_tag="tag_grouping_variables_wrong_sign", numeric_value=-0.4),
            Option(id="opt_3", text="y = 2.4", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=2.4),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_both_06",
        level_1_hint="Subtract y from both sides, and add 7 to both sides.",
        level_2_partial_step="4y - y = 5 + 7 => 3y = 12.",
        level_3_worked_step="Divide by 3: y = 4.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_leq_both_07",
        concept="c8_math_linear_eq_variables_both_sides",
        difficulty=0.6,
        question_text="Solve: 7m - 5 = 2m + 15",
        options=[
            Option(id="opt_1", text="m = 4", is_correct=True, numeric_value=4.0),
            Option(id="opt_2", text="m = 2", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=2.0),
            Option(id="opt_3", text="m = 10", is_correct=False, misconception_tag="tag_grouping_variables_wrong_sign", numeric_value=10.0),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_both_07",
        level_1_hint="Transpose 2m to left and -5 to right.",
        level_2_partial_step="7m - 2m = 15 + 5 => 5m = 20.",
        level_3_worked_step="Divide by 5: m = 4.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_leq_both_08",
        concept="c8_math_linear_eq_variables_both_sides",
        difficulty=0.7,
        question_text="Solve: 9x - 12 = 4x + 13",
        options=[
            Option(id="opt_1", text="x = 5", is_correct=True, numeric_value=5.0),
            Option(id="opt_2", text="x = 0.2", is_correct=False, misconception_tag="tag_grouping_variables_wrong_sign", numeric_value=0.2),
            Option(id="opt_3", text="x = 1", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=1.0),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_both_08",
        level_1_hint="Group terms: 9x - 4x on left, 13 + 12 on right.",
        level_2_partial_step="5x = 25.",
        level_3_worked_step="Divide by 5: x = 5.",
        review_record=make_draft_rr()
    ))

    # Probe 2 for c8_math_linear_eq_variables_both_sides
    questions.append(Question(
        id="probe_c8_leq_both_02",
        concept="c8_math_linear_eq_variables_both_sides",
        difficulty=0.4,
        question_text="When transposing -4x across the '=' sign, it becomes:",
        options=[
            Option(id="p1", text="+4x (positive term)", is_correct=True),
            Option(id="p2", text="-4x (remains negative)", is_correct=False, misconception_tag="tag_grouping_variables_wrong_sign")
        ],
        probe_for_misconception="tag_grouping_variables_wrong_sign",
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="probe_c8_leq_both_02",
        level_1_hint="Transposition flips signs for variable terms just like constants.",
        level_2_partial_step="The opposite of subtracting 4x is adding 4x.",
        level_3_worked_step="Therefore -4x becomes +4x.",
        review_record=make_draft_rr()
    ))

    # =========================================================================
    # 3. c8_math_rational_ops (Expand to 8 questions + 2 probes)
    # =========================================================================
    questions.append(Question(
        id="q_c8_rat_04",
        concept="c8_math_rational_ops",
        difficulty=0.3,
        question_text="Find the sum: 2/5 + 1/5",
        options=[
            Option(id="opt_1", text="3/5", is_correct=True),
            Option(id="opt_2", text="3/10", is_correct=False, misconception_tag="tag_adding_denominators_directly"),
            Option(id="opt_3", text="1/5", is_correct=False, misconception_tag="tag_class6_integer_subtraction"),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_rat_04",
        level_1_hint="Denominators are identical (5).",
        level_2_partial_step="Add only the numerators: 2 + 1 = 3.",
        level_3_worked_step="Denominator stays 5, so 3/5.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_rat_05",
        concept="c8_math_rational_ops",
        difficulty=0.5,
        question_text="Calculate: (3/5) / (2/3)",
        options=[
            Option(id="opt_1", text="9/10", is_correct=True),
            Option(id="opt_2", text="6/15", is_correct=False, misconception_tag="tag_reciprocal_error_division"),
            Option(id="opt_3", text="5/8", is_correct=False, misconception_tag="tag_adding_denominators_directly"),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_rat_05",
        level_1_hint="Multiply by reciprocal of 2/3, which is 3/2.",
        level_2_partial_step="(3/5) * (3/2) = (3*3) / (5*2).",
        level_3_worked_step="9/10.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_rat_06",
        concept="c8_math_rational_ops",
        difficulty=0.5,
        question_text="Subtract: 5/7 - 2/7",
        options=[
            Option(id="opt_1", text="3/7", is_correct=True),
            Option(id="opt_2", text="3/0", is_correct=False, misconception_tag="tag_adding_denominators_directly"),
            Option(id="opt_3", text="7/7", is_correct=False, misconception_tag="tag_class6_integer_subtraction"),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_rat_06",
        level_1_hint="Denominator is 7. Subtract numerators: 5 - 2.",
        level_2_partial_step="5 - 2 = 3.",
        level_3_worked_step="3/7.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_rat_07",
        concept="c8_math_rational_ops",
        difficulty=0.6,
        question_text="Calculate: 1/4 + 2/3",
        options=[
            Option(id="opt_1", text="11/12", is_correct=True),
            Option(id="opt_2", text="3/7", is_correct=False, misconception_tag="tag_adding_denominators_directly"),
            Option(id="opt_3", text="2/12", is_correct=False, misconception_tag="tag_reciprocal_error_division"),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_rat_07",
        level_1_hint="Find LCM of 4 and 3: 12.",
        level_2_partial_step="Convert: 3/12 + 8/12.",
        level_3_worked_step="3 + 8 = 11, so 11/12.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_rat_08",
        concept="c8_math_rational_ops",
        difficulty=0.6,
        question_text="Calculate: (5/6) * (3/10)",
        options=[
            Option(id="opt_1", text="1/4", is_correct=True),
            Option(id="opt_2", text="8/16", is_correct=False, misconception_tag="tag_adding_denominators_directly"),
            Option(id="opt_3", text="25/18", is_correct=False, misconception_tag="tag_reciprocal_error_division"),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_rat_08",
        level_1_hint="Multiply numerators and multiply denominators: (5*3) / (6*10).",
        level_2_partial_step="15 / 60.",
        level_3_worked_step="Simplify: 15/60 = 1/4.",
        review_record=make_draft_rr()
    ))

    # Probe 2 for c8_math_rational_ops
    questions.append(Question(
        id="probe_c8_rat_ops_02",
        concept="c8_math_rational_ops",
        difficulty=0.3,
        question_text="What is the reciprocal of the rational number -4/9?",
        options=[
            Option(id="p1", text="-9/4", is_correct=True),
            Option(id="p2", text="4/9 (change sign without inverting)", is_correct=False, misconception_tag="tag_reciprocal_error_division")
        ],
        probe_for_misconception="tag_reciprocal_error_division",
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="probe_c8_rat_ops_02",
        level_1_hint="Reciprocal flips numerator and denominator; sign stays negative.",
        level_2_partial_step="Numerator becomes 9, denominator becomes 4.",
        level_3_worked_step="-9/4.",
        review_record=make_draft_rr()
    ))

    # =========================================================================
    # 4. c8_math_squares_square_roots (Expand to 8 questions + 2 probes)
    # =========================================================================
    questions.append(Question(
        id="q_c8_sqr_04",
        concept="c8_math_squares_square_roots",
        difficulty=0.3,
        question_text="What is 9 squared (9²)?",
        options=[
            Option(id="opt_1", text="81", is_correct=True, numeric_value=81.0),
            Option(id="opt_2", text="18", is_correct=False, misconception_tag="tag_squaring_as_doubling", numeric_value=18.0),
            Option(id="opt_3", text="27", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=27.0),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_sqr_04",
        level_1_hint="9 squared means 9 multiplied by 9.",
        level_2_partial_step="9 * 9.",
        level_3_worked_step="81.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_sqr_05",
        concept="c8_math_squares_square_roots",
        difficulty=0.4,
        question_text="What is the square root of 100 (√100)?",
        options=[
            Option(id="opt_1", text="10", is_correct=True, numeric_value=10.0),
            Option(id="opt_2", text="50", is_correct=False, misconception_tag="tag_squaring_as_doubling", numeric_value=50.0),
            Option(id="opt_3", text="25", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=25.0),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_sqr_05",
        level_1_hint="Which number multiplied by itself gives 100?",
        level_2_partial_step="10 * 10 = 100.",
        level_3_worked_step="Square root of 100 is 10.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_sqr_06",
        concept="c8_math_squares_square_roots",
        difficulty=0.5,
        question_text="What is 12²?",
        options=[
            Option(id="opt_1", text="144", is_correct=True, numeric_value=144.0),
            Option(id="opt_2", text="24", is_correct=False, misconception_tag="tag_squaring_as_doubling", numeric_value=24.0),
            Option(id="opt_3", text="36", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=36.0),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_sqr_06",
        level_1_hint="Multiply 12 by 12.",
        level_2_partial_step="12 * 10 = 120, plus 12 * 2 = 24.",
        level_3_worked_step="120 + 24 = 144.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_sqr_07",
        concept="c8_math_squares_square_roots",
        difficulty=0.5,
        question_text="What is the square root of 169 (√169)?",
        options=[
            Option(id="opt_1", text="13", is_correct=True, numeric_value=13.0),
            Option(id="opt_2", text="84.5", is_correct=False, misconception_tag="tag_squaring_as_doubling", numeric_value=84.5),
            Option(id="opt_3", text="19", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=19.0),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_sqr_07",
        level_1_hint="Test integer squares: 12² = 144, 13² = 169.",
        level_2_partial_step="13 * 13 = 169.",
        level_3_worked_step="√169 = 13.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_sqr_08",
        concept="c8_math_squares_square_roots",
        difficulty=0.6,
        question_text="How many natural numbers lie between 10² and 11²?",
        options=[
            Option(id="opt_1", text="20", is_correct=True, numeric_value=20.0),
            Option(id="opt_2", text="2", is_correct=False, misconception_tag="tag_squaring_as_doubling", numeric_value=2.0),
            Option(id="opt_3", text="21", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=21.0),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_sqr_08",
        level_1_hint="Formula between n² and (n+1)² is 2n.",
        level_2_partial_step="10² = 100, 11² = 121. Numbers between are 101 to 120.",
        level_3_worked_step="2 * 10 = 20 natural numbers.",
        review_record=make_draft_rr()
    ))

    # Probe 2 for c8_math_squares_square_roots
    questions.append(Question(
        id="probe_c8_sqr_02",
        concept="c8_math_squares_square_roots",
        difficulty=0.3,
        question_text="Does (5)² equal 5 + 5 or 5 × 5?",
        options=[
            Option(id="p1", text="5 × 5 = 25", is_correct=True, numeric_value=25.0),
            Option(id="p2", text="5 + 5 = 10", is_correct=False, misconception_tag="tag_squaring_as_doubling", numeric_value=10.0)
        ],
        probe_for_misconception="tag_squaring_as_doubling",
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="probe_c8_sqr_02",
        level_1_hint="Exponent 2 indicates repeated multiplication.",
        level_2_partial_step="Base 5 multiplied by itself.",
        level_3_worked_step="5 * 5 = 25.",
        review_record=make_draft_rr()
    ))

    # =========================================================================
    # 5. c8_math_exponents_powers (Expand to 8 questions + 2 probes)
    # =========================================================================
    questions.append(Question(
        id="q_c8_exp_04",
        concept="c8_math_exponents_powers",
        difficulty=0.3,
        question_text="Simplify: 2³ × 2⁴",
        options=[
            Option(id="opt_1", text="2⁷", is_correct=True),
            Option(id="opt_2", text="2¹²", is_correct=False, misconception_tag="tag_multiplying_bases_adding_exponents_wrong"),
            Option(id="opt_3", text="4⁷", is_correct=False, misconception_tag="tag_squaring_as_doubling"),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_exp_04",
        level_1_hint="Law of exponents: a^m * a^n = a^(m+n).",
        level_2_partial_step="Add exponents: 3 + 4 = 7.",
        level_3_worked_step="Base stays 2, result is 2⁷.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_exp_05",
        concept="c8_math_exponents_powers",
        difficulty=0.4,
        question_text="Simplify: 5⁶ / 5²",
        options=[
            Option(id="opt_1", text="5⁴", is_correct=True),
            Option(id="opt_2", text="5³", is_correct=False, misconception_tag="tag_multiplying_bases_adding_exponents_wrong"),
            Option(id="opt_3", text="1⁴", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting"),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_exp_05",
        level_1_hint="Quotient law: a^m / a^n = a^(m-n).",
        level_2_partial_step="Subtract exponents: 6 - 2 = 4.",
        level_3_worked_step="5⁴.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_exp_06",
        concept="c8_math_exponents_powers",
        difficulty=0.5,
        question_text="Simplify: (3²)³",
        options=[
            Option(id="opt_1", text="3⁶", is_correct=True),
            Option(id="opt_2", text="3⁵", is_correct=False, misconception_tag="tag_multiplying_bases_adding_exponents_wrong"),
            Option(id="opt_3", text="9³", is_correct=False, misconception_tag="tag_squaring_as_doubling"),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_exp_06",
        level_1_hint="Power of a power: (a^m)^n = a^(m*n).",
        level_2_partial_step="Multiply powers: 2 * 3 = 6.",
        level_3_worked_step="3⁶.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_exp_07",
        concept="c8_math_exponents_powers",
        difficulty=0.6,
        question_text="What is the value of 3⁻²?",
        options=[
            Option(id="opt_1", text="1/9", is_correct=True),
            Option(id="opt_2", text="-9", is_correct=False, misconception_tag="tag_multiplying_bases_adding_exponents_wrong"),
            Option(id="opt_3", text="-6", is_correct=False, misconception_tag="tag_squaring_as_doubling"),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_exp_07",
        level_1_hint="Negative exponent law: a^(-n) = 1 / (a^n).",
        level_2_partial_step="1 / (3²) = 1 / 9.",
        level_3_worked_step="1/9.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_exp_08",
        concept="c8_math_exponents_powers",
        difficulty=0.6,
        question_text="What is 7⁰?",
        options=[
            Option(id="opt_1", text="1", is_correct=True, numeric_value=1.0),
            Option(id="opt_2", text="0", is_correct=False, misconception_tag="tag_multiplying_bases_adding_exponents_wrong", numeric_value=0.0),
            Option(id="opt_3", text="7", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=7.0),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_exp_08",
        level_1_hint="Any non-zero number to power 0 equals 1.",
        level_2_partial_step="a⁰ = 1 for any a != 0.",
        level_3_worked_step="1.",
        review_record=make_draft_rr()
    ))

    # Probe 2 for c8_math_exponents_powers
    questions.append(Question(
        id="probe_c8_exp_powers_02",
        concept="c8_math_exponents_powers",
        difficulty=0.3,
        question_text="In 10² × 10³, what should you do with the exponents 2 and 3?",
        options=[
            Option(id="p1", text="Add them: 2 + 3 = 5", is_correct=True),
            Option(id="p2", text="Multiply them: 2 × 3 = 6", is_correct=False, misconception_tag="tag_multiplying_bases_adding_exponents_wrong")
        ],
        probe_for_misconception="tag_multiplying_bases_adding_exponents_wrong",
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="probe_c8_exp_powers_02",
        level_1_hint="When multiplying identical bases, powers add.",
        level_2_partial_step="2 + 3 = 5.",
        level_3_worked_step="Result is 10⁵.",
        review_record=make_draft_rr()
    ))

    # =========================================================================
    # 6. c8_math_algebraic_identities (Expand to 8 questions + 2 probes)
    # =========================================================================
    questions.append(Question(
        id="q_c8_ident_04",
        concept="c8_math_algebraic_identities",
        difficulty=0.4,
        question_text="Expand: (x + 5)²",
        options=[
            Option(id="opt_1", text="x² + 10x + 25", is_correct=True),
            Option(id="opt_2", text="x² + 25", is_correct=False, misconception_tag="tag_missing_middle_term_identity"),
            Option(id="opt_3", text="x² + 5x + 25", is_correct=False, misconception_tag="tag_sign_error_on_transposition"),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_ident_04",
        level_1_hint="Use (a + b)² = a² + 2ab + b².",
        level_2_partial_step="Here a = x, b = 5. Middle term is 2 * x * 5 = 10x.",
        level_3_worked_step="x² + 10x + 25.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_ident_05",
        concept="c8_math_algebraic_identities",
        difficulty=0.5,
        question_text="Expand: (2x + 3)²",
        options=[
            Option(id="opt_1", text="4x² + 12x + 9", is_correct=True),
            Option(id="opt_2", text="4x² + 9", is_correct=False, misconception_tag="tag_missing_middle_term_identity"),
            Option(id="opt_3", text="2x² + 6x + 9", is_correct=False, misconception_tag="tag_squaring_as_doubling"),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_ident_05",
        level_1_hint="Square the first term: (2x)² = 4x².",
        level_2_partial_step="Double the product: 2 * (2x) * 3 = 12x. Square the second: 3² = 9.",
        level_3_worked_step="4x² + 12x + 9.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_ident_06",
        concept="c8_math_algebraic_identities",
        difficulty=0.5,
        question_text="Expand: (y - 4)²",
        options=[
            Option(id="opt_1", text="y² - 8y + 16", is_correct=True),
            Option(id="opt_2", text="y² - 16", is_correct=False, misconception_tag="tag_missing_middle_term_identity"),
            Option(id="opt_3", text="y² + 8y + 16", is_correct=False, misconception_tag="tag_sign_error_on_transposition"),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_ident_06",
        level_1_hint="Identity: (a - b)² = a² - 2ab + b².",
        level_2_partial_step="Middle term is -2 * y * 4 = -8y. Last term is (-4)² = +16.",
        level_3_worked_step="y² - 8y + 16.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_ident_07",
        concept="c8_math_algebraic_identities",
        difficulty=0.6,
        question_text="Calculate 103 × 97 using an algebraic identity.",
        options=[
            Option(id="opt_1", text="9991", is_correct=True, numeric_value=9991.0),
            Option(id="opt_2", text="10009", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=10009.0),
            Option(id="opt_3", text="9982", is_correct=False, misconception_tag="tag_missing_middle_term_identity", numeric_value=9982.0),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_ident_07",
        level_1_hint="Write as (100 + 3)(100 - 3).",
        level_2_partial_step="Apply (a + b)(a - b) = a² - b² = 100² - 3².",
        level_3_worked_step="10000 - 9 = 9991.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_ident_08",
        concept="c8_math_algebraic_identities",
        difficulty=0.6,
        question_text="Factorize: 49x² - 36",
        options=[
            Option(id="opt_1", text="(7x + 6)(7x - 6)", is_correct=True),
            Option(id="opt_2", text="(7x - 6)²", is_correct=False, misconception_tag="tag_missing_middle_term_identity"),
            Option(id="opt_3", text="(49x - 6)(x + 6)", is_correct=False, misconception_tag="tag_squaring_as_doubling"),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_ident_08",
        level_1_hint="Notice both terms are perfect squares: (7x)² - 6².",
        level_2_partial_step="Difference of squares: a² - b² = (a + b)(a - b).",
        level_3_worked_step="(7x + 6)(7x - 6).",
        review_record=make_draft_rr()
    ))

    # Probe 2 for c8_math_algebraic_identities
    questions.append(Question(
        id="probe_c8_ident_02",
        concept="c8_math_algebraic_identities",
        difficulty=0.3,
        question_text="When expanding (x + 1)², how many terms are in the expanded expression?",
        options=[
            Option(id="p1", text="3 terms (x² + 2x + 1)", is_correct=True),
            Option(id="p2", text="2 terms (x² + 1)", is_correct=False, misconception_tag="tag_missing_middle_term_identity")
        ],
        probe_for_misconception="tag_missing_middle_term_identity",
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="probe_c8_ident_02",
        level_1_hint="(a + b)² produces three terms: a², 2ab, and b².",
        level_2_partial_step="Do not forget the middle term 2x.",
        level_3_worked_step="Total is 3 terms: x² + 2x + 1.",
        review_record=make_draft_rr()
    ))

    # =========================================================================
    # 7. c8_math_comparing_quantities_percentages (Expand to 8 questions + 2 probes)
    # =========================================================================
    questions.append(Question(
        id="q_c8_pct_04",
        concept="c8_math_comparing_quantities_percentages",
        difficulty=0.3,
        question_text="Convert 3/4 to a percentage.",
        options=[
            Option(id="opt_1", text="75%", is_correct=True, numeric_value=75.0),
            Option(id="opt_2", text="34%", is_correct=False, misconception_tag="tag_percent_as_raw_value", numeric_value=34.0),
            Option(id="opt_3", text="43%", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=43.0),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_pct_04",
        level_1_hint="To convert a fraction to percentage, multiply by 100.",
        level_2_partial_step="(3/4) * 100 = 300 / 4.",
        level_3_worked_step="75%.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_pct_05",
        concept="c8_math_comparing_quantities_percentages",
        difficulty=0.4,
        question_text="What is 15% of 200?",
        options=[
            Option(id="opt_1", text="30", is_correct=True, numeric_value=30.0),
            Option(id="opt_2", text="15", is_correct=False, misconception_tag="tag_percent_as_raw_value", numeric_value=15.0),
            Option(id="opt_3", text="20", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=20.0),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_pct_05",
        level_1_hint="15% means 15/100.",
        level_2_partial_step="(15/100) * 200 = 15 * 2.",
        level_3_worked_step="30.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_pct_06",
        concept="c8_math_comparing_quantities_percentages",
        difficulty=0.5,
        question_text="An item priced at Rs 500 is given a 10% discount. What is the sale price?",
        options=[
            Option(id="opt_1", text="Rs 450", is_correct=True, numeric_value=450.0),
            Option(id="opt_2", text="Rs 490", is_correct=False, misconception_tag="tag_percent_as_raw_value", numeric_value=490.0),
            Option(id="opt_3", text="Rs 400", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=400.0),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_pct_06",
        level_1_hint="Discount = 10% of 500 = (10/100) * 500 = 50.",
        level_2_partial_step="Sale price = Original price - Discount = 500 - 50.",
        level_3_worked_step="Rs 450.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_pct_07",
        concept="c8_math_comparing_quantities_percentages",
        difficulty=0.6,
        question_text="A shirt bought for Rs 400 is sold for Rs 480. Find the profit percentage.",
        options=[
            Option(id="opt_1", text="20%", is_correct=True, numeric_value=20.0),
            Option(id="opt_2", text="80%", is_correct=False, misconception_tag="tag_percent_as_raw_value", numeric_value=80.0),
            Option(id="opt_3", text="16.6%", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=16.6),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_pct_07",
        level_1_hint="Profit = Selling Price - Cost Price = 480 - 400 = 80.",
        level_2_partial_step="Profit % = (Profit / Cost Price) * 100 = (80 / 400) * 100.",
        level_3_worked_step="80 / 4 = 20%.",
        review_record=make_draft_rr()
    ))

    questions.append(Question(
        id="q_c8_pct_08",
        concept="c8_math_comparing_quantities_percentages",
        difficulty=0.6,
        question_text="What is the ratio of 5 m to 10 km?",
        options=[
            Option(id="opt_1", text="1 : 2000", is_correct=True),
            Option(id="opt_2", text="1 : 2", is_correct=False, misconception_tag="tag_percent_as_raw_value"),
            Option(id="opt_3", text="5 : 10", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting"),
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_pct_08",
        level_1_hint="Convert both quantities to same units: 1 km = 1000 m.",
        level_2_partial_step="10 km = 10,000 m. Ratio is 5 : 10,000.",
        level_3_worked_step="Divide by 5: 1 : 2000.",
        review_record=make_draft_rr()
    ))

    # Probe 2 for c8_math_comparing_quantities_percentages
    questions.append(Question(
        id="probe_c8_pct_02",
        concept="c8_math_comparing_quantities_percentages",
        difficulty=0.3,
        question_text="If a test has 50 marks and a student scores 40%, how many marks did they get?",
        options=[
            Option(id="p1", text="20 marks ((40/100) * 50)", is_correct=True, numeric_value=20.0),
            Option(id="p2", text="40 marks (treat 40% as 40 marks)", is_correct=False, misconception_tag="tag_percent_as_raw_value", numeric_value=40.0)
        ],
        probe_for_misconception="tag_percent_as_raw_value",
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="probe_c8_pct_02",
        level_1_hint="Percentage is a fraction of the total, not the raw count.",
        level_2_partial_step="40% of 50 = (40 * 50) / 100.",
        level_3_worked_step="20 marks.",
        review_record=make_draft_rr()
    ))

    # =========================================================================
    # FIX 6: Extended Hindi and Telugu Drafts across all Active Class 8 Concepts
    # Marked 'author-drafted, unreviewed'
    # =========================================================================

    # 1. c8_math_rational_ops (Hindi & Telugu drafts)
    questions.append(Question(
        id="q_c8_rat_hi_01",
        concept="c8_math_rational_ops",
        difficulty=0.3,
        language="hi",
        question_text="[ड्राफ्ट] हल कीजिए: (2/5) + (1/5)",
        options=[
            Option(id="opt_hi_1", text="3/5", is_correct=True, numeric_value=0.6),
            Option(id="opt_hi_2", text="3/10", is_correct=False, misconception_tag="tag_adding_denominators_directly", numeric_value=0.3),
            Option(id="opt_hi_3", text="2/25", is_correct=False, misconception_tag="tag_reciprocal_error_division", numeric_value=0.08)
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_rat_hi_01",
        level_1_hint="[ड्राफ्ट] जब हर समान हों, तो केवल अंशों को जोड़ें।",
        level_2_partial_step="[ड्राफ्ट] (2 + 1) / 5 = 3 / 5",
        level_3_worked_step="[ड्राफ्ट] उत्तर 3/5 है।",
        review_record=make_draft_rr()
    ))
    questions.append(Question(
        id="q_c8_rat_te_01",
        concept="c8_math_rational_ops",
        difficulty=0.3,
        language="te",
        question_text="[డ్రాఫ్ట్] సాధించండి: (2/5) + (1/5)",
        options=[
            Option(id="opt_te_1", text="3/5", is_correct=True, numeric_value=0.6),
            Option(id="opt_te_2", text="3/10", is_correct=False, misconception_tag="tag_adding_denominators_directly", numeric_value=0.3),
            Option(id="opt_te_3", text="2/25", is_correct=False, misconception_tag="tag_reciprocal_error_division", numeric_value=0.08)
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_rat_te_01",
        level_1_hint="[డ్రాఫ్ట్] హారాలు సమానంగా ఉన్నప్పుడు లవాలను మాత్రమే కూడండి.",
        level_2_partial_step="[డ్రాఫ్ట్] (2 + 1) / 5 = 3 / 5",
        level_3_worked_step="[డ్రాఫ్ట్] సమాధానం 3/5.",
        review_record=make_draft_rr()
    ))
    lessons.append(Lesson(
        id="les_hi_draft_rat_01",
        concept="c8_math_rational_ops",
        language="hi",
        content="[ड्राफ्ट - असमीक्षित] समान हर वाले परिमेय संख्याओं का जोड़: केवल अंशों को जोड़ें, हर अपरिवर्तित रहता है।",
        review_record=make_draft_rr()
    ))
    lessons.append(Lesson(
        id="les_te_draft_rat_01",
        concept="c8_math_rational_ops",
        language="te",
        content="[డ్రాఫ్ట్ - సమీక్షించబడలేదు] సమాన హారాలు గల అకరణీయ సంఖ్యల సంకలనం: లవాలను మాత్రమే కూడాలి, హారం మారదు.",
        review_record=make_draft_rr()
    ))

    # 2. c8_math_linear_eq_variables_both_sides (Hindi & Telugu drafts)
    questions.append(Question(
        id="q_c8_leq_both_hi_01",
        concept="c8_math_linear_eq_variables_both_sides",
        difficulty=0.4,
        language="hi",
        question_text="[ड्राफ्ट] हल कीजिए: 5x + 3 = 2x + 12",
        options=[
            Option(id="opt_hi_1", text="x = 3", is_correct=True, numeric_value=3.0),
            Option(id="opt_hi_2", text="x = 5", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=5.0),
            Option(id="opt_hi_3", text="x = 2", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=2.0)
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_both_hi_01",
        level_1_hint="[ड्राफ्ट] 2x को बाईं ओर और 3 को दाईं ओर ले जाएं।",
        level_2_partial_step="[ड्राफ्ट] 5x - 2x = 12 - 3 => 3x = 9",
        level_3_worked_step="[ड्राफ्ट] x = 9 / 3 = 3",
        review_record=make_draft_rr()
    ))
    questions.append(Question(
        id="q_c8_leq_both_te_01",
        concept="c8_math_linear_eq_variables_both_sides",
        difficulty=0.4,
        language="te",
        question_text="[డ్రాఫ్ట్] సాధించండి: 5x + 3 = 2x + 12",
        options=[
            Option(id="opt_te_1", text="x = 3", is_correct=True, numeric_value=3.0),
            Option(id="opt_te_2", text="x = 5", is_correct=False, misconception_tag="tag_sign_error_on_transposition", numeric_value=5.0),
            Option(id="opt_te_3", text="x = 2", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=2.0)
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_leq_both_te_01",
        level_1_hint="[డ్రాఫ్ట్] 2x ను ఎడమవైపునకు, 3 ను కుడివైపునకు బదిలీ చేయండి.",
        level_2_partial_step="[డ్రాఫ్ట్] 5x - 2x = 12 - 3 => 3x = 9",
        level_3_worked_step="[డ్రాఫ్ట్] x = 9 / 3 = 3",
        review_record=make_draft_rr()
    ))
    lessons.append(Lesson(
        id="les_hi_draft_leq_both_01",
        concept="c8_math_linear_eq_variables_both_sides",
        language="hi",
        content="[ड्राफ्ट - असमीक्षित] दोनों पक्षों में चर: चर पदों को एक पक्ष में और अचर पदों को दूसरे पक्ष में पक्षांतरित करें।",
        review_record=make_draft_rr()
    ))
    lessons.append(Lesson(
        id="les_te_draft_leq_both_01",
        concept="c8_math_linear_eq_variables_both_sides",
        language="te",
        content="[డ్రాఫ్ట్ - సమీక్షించబడలేదు] ఇరువైపులా చరరాశులు: చరరాశి పదాలను ఒకవైపు, స్థిరపదాలను మరొకవైపునకు తీసుకురండి.",
        review_record=make_draft_rr()
    ))

    # 3. c8_math_squares_square_roots (Hindi & Telugu drafts)
    questions.append(Question(
        id="q_c8_sq_hi_01",
        concept="c8_math_squares_square_roots",
        difficulty=0.3,
        language="hi",
        question_text="[ड्राफ्ट] हल कीजिए: √144 का मान क्या है?",
        options=[
            Option(id="opt_hi_1", text="12", is_correct=True, numeric_value=12.0),
            Option(id="opt_hi_2", text="72", is_correct=False, misconception_tag="tag_squaring_as_doubling", numeric_value=72.0),
            Option(id="opt_hi_3", text="14", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=14.0)
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_sq_hi_01",
        level_1_hint="[ड्राफ्ट] किस संख्या को स्वयं से गुणा करने पर 144 मिलता है?",
        level_2_partial_step="[ड्राफ्ट] 12 × 12 = 144",
        level_3_worked_step="[ड्राफ्ट] √144 = 12",
        review_record=make_draft_rr()
    ))
    questions.append(Question(
        id="q_c8_sq_te_01",
        concept="c8_math_squares_square_roots",
        difficulty=0.3,
        language="te",
        question_text="[డ్రాఫ్ట్] సాధించండి: √144 విలువ ఎంత?",
        options=[
            Option(id="opt_te_1", text="12", is_correct=True, numeric_value=12.0),
            Option(id="opt_te_2", text="72", is_correct=False, misconception_tag="tag_squaring_as_doubling", numeric_value=72.0),
            Option(id="opt_te_3", text="14", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=14.0)
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_sq_te_01",
        level_1_hint="[డ్రాఫ్ట్] ఏ సంఖ్యను అదే సంఖ్యతో గుణిస్తే 144 వస్తుంది?",
        level_2_partial_step="[డ్రాఫ్ట్] 12 × 12 = 144",
        level_3_worked_step="[డ్రాఫ్ట్] √144 = 12",
        review_record=make_draft_rr()
    ))
    lessons.append(Lesson(
        id="les_hi_draft_sq_01",
        concept="c8_math_squares_square_roots",
        language="hi",
        content="[ड्राफ्ट - असमीक्षित] वर्गमूल: वर्गमूल वह संख्या है जिसका वर्ग मूल संख्या के बराबर होता है (12² = 144 => √144 = 12)।",
        review_record=make_draft_rr()
    ))
    lessons.append(Lesson(
        id="les_te_draft_sq_01",
        concept="c8_math_squares_square_roots",
        language="te",
        content="[డ్రాఫ్ట్ - సమీక్షించబడలేదు] వర్గమూలం: ఒక సంఖ్యను అదే సంఖ్యతో గుణించినప్పుడు వచ్చే లబ్దమే వర్గం (12² = 144 => √144 = 12).",
        review_record=make_draft_rr()
    ))

    # 4. c8_math_exponents_powers (Hindi & Telugu drafts)
    questions.append(Question(
        id="q_c8_exp_hi_01",
        concept="c8_math_exponents_powers",
        difficulty=0.4,
        language="hi",
        question_text="[ड्राफ्ट] हल कीजिए: 3² × 3³ का मान घातांक रूप में क्या है?",
        options=[
            Option(id="opt_hi_1", text="3⁵", is_correct=True),
            Option(id="opt_hi_2", text="3⁶", is_correct=False, misconception_tag="tag_multiplying_bases_adding_exponents_wrong"),
            Option(id="opt_hi_3", text="9⁵", is_correct=False, misconception_tag="tag_multiplying_bases_adding_exponents_wrong")
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_exp_hi_01",
        level_1_hint="[ड्राफ्ट] जब आधार समान हो, तो गुणा में घातांक जुड़ते हैं।",
        level_2_partial_step="[ड्राफ्ट] 3^(2 + 3) = 3⁵",
        level_3_worked_step="[ड्राफ्ट] उत्तर 3⁵ है।",
        review_record=make_draft_rr()
    ))
    questions.append(Question(
        id="q_c8_exp_te_01",
        concept="c8_math_exponents_powers",
        difficulty=0.4,
        language="te",
        question_text="[డ్రాఫ్ట్] సాధించండి: 3² × 3³ విలువ ఘాతాంక రూపంలో ఎంత?",
        options=[
            Option(id="opt_te_1", text="3⁵", is_correct=True),
            Option(id="opt_te_2", text="3⁶", is_correct=False, misconception_tag="tag_multiplying_bases_adding_exponents_wrong"),
            Option(id="opt_te_3", text="9⁵", is_correct=False, misconception_tag="tag_multiplying_bases_adding_exponents_wrong")
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_exp_te_01",
        level_1_hint="[డ్రాఫ్ట్] భూములు సమానంగా ఉన్నప్పుడు గుణకారంలో ఘాతాలను కూడండి.",
        level_2_partial_step="[డ్రాఫ్ట్] 3^(2 + 3) = 3⁵",
        level_3_worked_step="[డ్రాఫ్ట్] సమాధానం 3⁵.",
        review_record=make_draft_rr()
    ))
    lessons.append(Lesson(
        id="les_hi_draft_exp_01",
        concept="c8_math_exponents_powers",
        language="hi",
        content="[ड्राफ्ट - असमीक्षित] घातांकों का नियम: aᵐ × aⁿ = aᵐ⁺ⁿ। समान आधार होने पर घातांक जुड़ जाते हैं।",
        review_record=make_draft_rr()
    ))
    lessons.append(Lesson(
        id="les_te_draft_exp_01",
        concept="c8_math_exponents_powers",
        language="te",
        content="[డ్రాఫ్ట్ - సమీక్షించబడలేదు] ఘాతాంకాల నియమం: aᵐ × aⁿ = aᵐ⁺ⁿ. భూములు సమానంగా ఉంటే ఘాతాలు కలుస్తాయి.",
        review_record=make_draft_rr()
    ))

    # 5. c8_math_algebraic_identities (Hindi & Telugu drafts)
    questions.append(Question(
        id="q_c8_alg_id_hi_01",
        concept="c8_math_algebraic_identities",
        difficulty=0.5,
        language="hi",
        question_text="[ड्राफ्ट] हल कीजिए: (x + 3)² का विस्तार क्या है?",
        options=[
            Option(id="opt_hi_1", text="x² + 6x + 9", is_correct=True),
            Option(id="opt_hi_2", text="x² + 9", is_correct=False, misconception_tag="tag_missing_middle_term_identity"),
            Option(id="opt_hi_3", text="x² + 6x + 6", is_correct=False, misconception_tag="tag_missing_middle_term_identity")
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_alg_id_hi_01",
        level_1_hint="[ड्राफ्ट] सर्वसमिका लागू करें: (a + b)² = a² + 2ab + b²।",
        level_2_partial_step="[ड्राफ्ट] x² + 2(x)(3) + 3²",
        level_3_worked_step="[ड्राफ्ट] x² + 6x + 9",
        review_record=make_draft_rr()
    ))
    questions.append(Question(
        id="q_c8_alg_id_te_01",
        concept="c8_math_algebraic_identities",
        difficulty=0.5,
        language="te",
        question_text="[డ్రాఫ్ట్] సాధించండి: (x + 3)² విస్తరణ ఏమిటి?",
        options=[
            Option(id="opt_te_1", text="x² + 6x + 9", is_correct=True),
            Option(id="opt_te_2", text="x² + 9", is_correct=False, misconception_tag="tag_missing_middle_term_identity"),
            Option(id="opt_te_3", text="x² + 6x + 6", is_correct=False, misconception_tag="tag_missing_middle_term_identity")
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_alg_id_te_01",
        level_1_hint="[డ్రాఫ్ట్] సర్వసమీకరణం ఉపయోగించండి: (a + b)² = a² + 2ab + b².",
        level_2_partial_step="[డ్రాఫ్ట్] x² + 2(x)(3) + 3²",
        level_3_worked_step="[డ్రాఫ్ట్] x² + 6x + 9",
        review_record=make_draft_rr()
    ))
    lessons.append(Lesson(
        id="les_hi_draft_alg_id_01",
        concept="c8_math_algebraic_identities",
        language="hi",
        content="[ड्राफ्ट - असमीक्षित] बीजीय सर्वसमिका: (a + b)² = a² + 2ab + b²। मध्य पद 2ab को कभी मत भूलें।",
        review_record=make_draft_rr()
    ))
    lessons.append(Lesson(
        id="les_te_draft_alg_id_01",
        concept="c8_math_algebraic_identities",
        language="te",
        content="[డ్రాఫ్ట్ - సమీక్షించబడలేదు] బీజీయ సర్వసమీకరణం: (a + b)² = a² + 2ab + b². మధ్య పదం 2ab ఎల్లప్పుడూ రాయాలి.",
        review_record=make_draft_rr()
    ))

    # 6. c8_math_comparing_quantities_percentages (Hindi & Telugu drafts)
    questions.append(Question(
        id="q_c8_pct_hi_01",
        concept="c8_math_comparing_quantities_percentages",
        difficulty=0.4,
        language="hi",
        question_text="[ड्राफ्ट] हल कीजिए: 200 का 25% कितना होगा?",
        options=[
            Option(id="opt_hi_1", text="50", is_correct=True, numeric_value=50.0),
            Option(id="opt_hi_2", text="25", is_correct=False, misconception_tag="tag_percent_as_raw_value", numeric_value=25.0),
            Option(id="opt_hi_3", text="8", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=8.0)
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_pct_hi_01",
        level_1_hint="[ड्राफ्ट] 25% का अर्थ है (25 / 100)।",
        level_2_partial_step="[ड्राफ्ट] (25 / 100) × 200",
        level_3_worked_step="[ड्राफ्ट] 25 × 2 = 50",
        review_record=make_draft_rr()
    ))
    questions.append(Question(
        id="q_c8_pct_te_01",
        concept="c8_math_comparing_quantities_percentages",
        difficulty=0.4,
        language="te",
        question_text="[డ్రాఫ్ట్] సాధించండి: 200 లో 25% ఎంత?",
        options=[
            Option(id="opt_te_1", text="50", is_correct=True, numeric_value=50.0),
            Option(id="opt_te_2", text="25", is_correct=False, misconception_tag="tag_percent_as_raw_value", numeric_value=25.0),
            Option(id="opt_te_3", text="8", is_correct=False, misconception_tag="tag_dividing_instead_of_subtracting", numeric_value=8.0)
        ],
        review_record=make_draft_rr()
    ))
    hints.append(HintLadder(
        question_id="q_c8_pct_te_01",
        level_1_hint="[డ్రాఫ్ట్] 25% అనగా (25 / 100).",
        level_2_partial_step="[డ్రాఫ్ట్] (25 / 100) × 200",
        level_3_worked_step="[డ్రాఫ్ట్] 25 × 2 = 50",
        review_record=make_draft_rr()
    ))
    lessons.append(Lesson(
        id="les_hi_draft_pct_01",
        concept="c8_math_comparing_quantities_percentages",
        language="hi",
        content="[ड्राफ्ट - असमीक्षित] प्रतिशत गणना: किसी संख्या का X% = (X / 100) × संख्या।",
        review_record=make_draft_rr()
    ))
    lessons.append(Lesson(
        id="les_te_draft_pct_01",
        concept="c8_math_comparing_quantities_percentages",
        language="te",
        content="[డ్రాఫ్ట్ - సమీక్షించబడలేదు] శాతం లెక్కించు విధానం: ఒక సంఖ్య యొక్క X% = (X / 100) × ఆ సంఖ్య.",
        review_record=make_draft_rr()
    ))

    return questions, lessons, hints
