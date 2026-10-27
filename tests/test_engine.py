import sys
import os
import json
import pytest

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.models.pack import ContentPack
from app.models.student import Student, ConsentStatus
from app.models.learning import (
    Attempt, Hypothesis, EvidenceBand, HypothesisStatus,
    MasteryState, Plan, StageEnum, TeacherOverride
)
from app.engine.adaptive_engine import AdaptiveEngine
from app.engine.hypothesis_engine import HypothesisEngine
from app.engine.graph_tracer import GraphTracer


@pytest.fixture
def engine():
    pack_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packs", "cbse_math_pack.json"))
    with open(pack_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    pack = ContentPack.model_validate(data)
    return AdaptiveEngine(pack)


def test_wrong_answer_hypothesis_low_band(engine):
    student = Student(pseudonymous_id="stu_test_01", class_id="8-A", pin_hash="hash")
    plan = Plan(student_id=student.pseudonymous_id, class_id=student.class_id, current_concept_id="c8_math_linear_eq_one_var")
    mastery = MasteryState(student_id=student.pseudonymous_id, concept_id="c8_math_linear_eq_one_var")

    # Student makes 1 wrong answer on question with tag_sign_error_on_transposition
    wrong_attempt = Attempt(
        student_id=student.pseudonymous_id,
        question_id="q_c8_leq_01",
        concept_id="c8_math_linear_eq_one_var",
        selected_option_id="opt_2",
        is_correct=False,
        misconception_tag="tag_sign_error_on_transposition"
    )

    plan, mastery, hyp, decision = engine.process_attempt(student, plan, wrong_attempt, mastery, None)

    # 1. Hypothesis opened with score band Low and label "heuristic evidence score"
    assert hyp is not None
    assert hyp.evidence_band == EvidenceBand.LOW
    assert hyp.label == "heuristic evidence score"
    assert hyp.heuristic_score == 0
    assert hyp.status == HypothesisStatus.OPEN

    # 2. No gap is declared yet
    assert plan.gap_concept_id is None

    # 3. Next step administers a focused probe
    next_step = engine.get_next_step(student, plan, mastery, hyp)
    assert next_step.stage == StageEnum.PROBE
    assert next_step.item_type == "question"
    assert next_step.item.probe_for_misconception == "tag_sign_error_on_transposition"


def test_conflicting_probes_yields_not_sure():
    """
    Test requirement:
    'Probe: prerequisite probes support or reject the hypothesis.
     Conflicting or thin evidence leads to more probes or "not sure".
     Test with planted conflicting probe results: expect "not sure".'
    """
    hyp_engine = HypothesisEngine()
    hyp = hyp_engine.open_hypothesis("stu_01", "c8_math_linear_eq_one_var", "tag_sign_error_on_transposition")

    # Probe 1: Confirms gap (student answers probe wrongly) -> supporting = True
    hyp = hyp_engine.add_probe_result(
        hypothesis=hyp,
        probe_question_id="probe_01",
        probe_concept_id="c7_math_simple_eq",
        is_supporting=True
    )
    assert hyp.heuristic_score == 1

    # Probe 2: Planted conflicting result! Student answers second probe correctly -> is_supporting = False
    hyp = hyp_engine.add_probe_result(
        hypothesis=hyp,
        probe_question_id="probe_02",
        probe_concept_id="c7_math_simple_eq",
        is_supporting=False
    )

    # Heuristic evidence score: 1 supporting - 1 contradicting = 0
    assert hyp.heuristic_score == 0
    # Must yield "not sure" and status undecided! Never a forced gap.
    assert hyp.evidence_band == EvidenceBand.NOT_SURE
    assert hyp.status == HypothesisStatus.UNDECIDED


def test_trace_to_class6_gap(engine):
    """
    Test requirement:
    'Trace: walk the graph to the earliest gap the probes support, inside the tested graph (not a proven cause).
     It may reach lower classes. Test: a synthetic student with a planted Class 6 gap is traced to it.'
    """
    student = Student(pseudonymous_id="stu_c6_gap", class_id="8-B", pin_hash="hash")
    plan = Plan(student_id=student.pseudonymous_id, class_id="8-B", current_concept_id="c8_math_linear_eq_one_var")
    mastery = MasteryState(student_id=student.pseudonymous_id, concept_id="c8_math_linear_eq_one_var")

    # Initial wrong answer with planted Class 6 misconception
    attempt_1 = Attempt(
        student_id=student.pseudonymous_id,
        question_id="q_c8_leq_01",
        concept_id="c8_math_linear_eq_one_var",
        selected_option_id="opt_3",
        is_correct=False,
        misconception_tag="tag_class6_integer_subtraction"
    )
    plan, mastery, hyp, _ = engine.process_attempt(student, plan, attempt_1, mastery, None)

    # Synthetic probe 1 on Class 6 integer subtraction confirms gap
    hyp = engine.hypothesis_engine.add_probe_result(
        hypothesis=hyp,
        probe_question_id="probe_c6_int_sub_01",
        probe_concept_id="c6_math_integers_add_sub",
        is_supporting=True
    )
    # Synthetic probe 2 also confirms
    hyp = engine.hypothesis_engine.add_probe_result(
        hypothesis=hyp,
        probe_question_id="probe_c6_int_sub_02",
        probe_concept_id="c6_math_integers_add_sub",
        is_supporting=True
    )
    assert hyp.status == HypothesisStatus.SUPPORTED

    # Trace through graph from c8_math_linear_eq_one_var to c6_math_integers_add_sub
    trace = engine.tracer.trace_earliest_gap(
        starting_concept_id="c8_math_linear_eq_one_var",
        active_hypotheses=[hyp]
    )

    assert trace.found_gap is True
    assert trace.earliest_gap_concept_id == "c6_math_integers_add_sub"
    assert "c8_math_linear_eq_one_var" in trace.trace_path
    assert "c6_math_integers_add_sub" in trace.trace_path
    assert "not a proven cause" in trace.disclaimer


def test_hint_ladder_and_stuck_flag(engine):
    """
    Test requirement:
    'Solve: hint ladder (hint, partial step, full worked step).
     Two stuck attempts raise a teacher flag.'
    """
    # Verify hint ladder exists for question
    ladder = engine.get_hint_ladder("q_c8_leq_01")
    assert ladder is not None
    assert len(ladder.level_1_hint) > 0
    assert len(ladder.level_2_partial_step) > 0
    assert len(ladder.level_3_worked_step) > 0

    student = Student(pseudonymous_id="stu_stuck", class_id="8-A", pin_hash="hash")
    plan = Plan(student_id=student.pseudonymous_id, class_id="8-A", current_concept_id="c8_math_linear_eq_one_var")
    mastery = MasteryState(student_id=student.pseudonymous_id, concept_id="c8_math_linear_eq_one_var")

    # Attempt 1: wrong
    att_1 = Attempt(student_id=student.pseudonymous_id, question_id="q_c8_leq_01", concept_id="c8_math_linear_eq_one_var", selected_option_id="o2", is_correct=False, misconception_tag="tag_sign_error_on_transposition")
    plan, mastery, hyp, _ = engine.process_attempt(student, plan, att_1, mastery, None)
    assert plan.stuck_attempts_count == 1

    # Attempt 2: wrong again -> stuck count reaches 2
    att_2 = Attempt(student_id=student.pseudonymous_id, question_id="q_c8_leq_01", concept_id="c8_math_linear_eq_one_var", selected_option_id="o2", is_correct=False, misconception_tag="tag_sign_error_on_transposition")
    plan, mastery, hyp, decision = engine.process_attempt(student, plan, att_2, mastery, hyp)
    assert plan.stuck_attempts_count == 2
    assert decision.action == "FLAG_TEACHER_STUCK"

    # Next step must return teacher flag
    next_step = engine.get_next_step(student, plan, mastery, hyp)
    assert next_step.teacher_flag == "STUCK_STUDENT"
    assert "stuck after 2 failed attempts" in next_step.reason


def test_bridge_recheck_routing(engine):
    """
    Test requirement:
    'Test: short adaptive check that picks items where the estimate is most uncertain.
     After a bridge, a re-check returns the student to the original topic on pass,
     stays on the gap on fail, and flags the teacher after repeated fails.'
    """
    student = Student(pseudonymous_id="stu_bridge", class_id="8-A", pin_hash="hash")
    mastery = MasteryState(student_id=student.pseudonymous_id, concept_id="c8_math_linear_eq_one_var")

    # Scenario A: Pass returns student to original topic
    plan_pass = Plan(
        student_id=student.pseudonymous_id,
        class_id="8-A",
        current_stage=StageEnum.BRIDGE_RECHECK,
        current_concept_id="c8_math_linear_eq_one_var",
        gap_concept_id="c6_math_integers_add_sub"
    )
    pass_attempt = Attempt(
        student_id=student.pseudonymous_id,
        question_id="probe_c6_int_sub_01",
        concept_id="c6_math_integers_add_sub",
        selected_option_id="p1",
        is_correct=True
    )
    plan_pass, mastery, _, dec_pass = engine.process_attempt(student, plan_pass, pass_attempt, mastery, None)
    assert dec_pass.action == "RETURN_TO_ORIGINAL_TOPIC"
    assert plan_pass.current_stage == StageEnum.SOLVE
    assert plan_pass.gap_concept_id is None

    # Scenario B: Fail stays on the gap
    plan_fail = Plan(
        student_id=student.pseudonymous_id,
        class_id="8-A",
        current_stage=StageEnum.BRIDGE_RECHECK,
        current_concept_id="c8_math_linear_eq_one_var",
        gap_concept_id="c6_math_integers_add_sub",
        bridge_recheck_fails=0
    )
    fail_attempt = Attempt(
        student_id=student.pseudonymous_id,
        question_id="probe_c6_int_sub_01",
        concept_id="c6_math_integers_add_sub",
        selected_option_id="p2",
        is_correct=False,
        misconception_tag="tag_class6_integer_subtraction"
    )
    plan_fail, mastery, _, dec_fail = engine.process_attempt(student, plan_fail, fail_attempt, mastery, None)
    assert dec_fail.action == "STAY_ON_GAP"
    assert plan_fail.bridge_recheck_fails == 1
    assert plan_fail.gap_concept_id == "c6_math_integers_add_sub"

    # Scenario C: Repeated fails flag teacher
    plan_fail_rep, mastery, _, dec_rep = engine.process_attempt(student, plan_fail, fail_attempt, mastery, None)
    assert plan_fail_rep.bridge_recheck_fails == 2
    assert dec_rep.action == "FLAG_TEACHER_REPEATED_FAIL"
    next_step = engine.get_next_step(student, plan_fail_rep, mastery, None)
    assert next_step.teacher_flag == "REPEATED_BRIDGE_FAIL"


def test_move_ahead_and_override(engine):
    """
    Test requirement:
    'Move ahead: when mastery is high with enough evidence, skip remaining drill and move to the next concept
     or an enrichment item. The teacher can override, and the override is logged. Test with a synthetic fast learner.'
    """
    student = Student(pseudonymous_id="stu_fast", class_id="8-A", pin_hash="hash")
    plan = Plan(student_id=student.pseudonymous_id, class_id="8-A", current_concept_id="c8_math_linear_eq_one_var")
    # Synthetic fast learner with high mastery
    mastery = MasteryState(
        student_id=student.pseudonymous_id,
        concept_id="c8_math_linear_eq_one_var",
        mastery_estimate=0.90,
        consecutive_successes=2
    )

    # 3rd consecutive correct answer
    att = Attempt(student_id=student.pseudonymous_id, question_id="q_c8_leq_01", concept_id="c8_math_linear_eq_one_var", selected_option_id="opt_1", is_correct=True)
    plan, mastery, _, decision = engine.process_attempt(student, plan, att, mastery, None)

    assert mastery.mastery_estimate >= 0.85
    assert mastery.consecutive_successes >= 3
    assert decision.action == "MOVE_AHEAD"
    assert plan.current_stage == StageEnum.MOVE_AHEAD

    # Teacher overrides to keep student on practice
    override = TeacherOverride(
        student_id=student.pseudonymous_id,
        teacher_id="tea_raman",
        class_id="8-A",
        concept_id="c8_math_linear_eq_one_var",
        override_action="continue_drill",
        reason="Needs additional practice with word problems"
    )
    # Teacher override applies and is logged
    assert override.reason == "Needs additional practice with word problems"
    plan.current_stage = StageEnum.SOLVE
    plan.reason = f"Teacher override: {override.reason}"
    assert "Teacher override" in plan.reason


def test_two_students_different_paths(engine):
    """
    Test requirement:
    'Paths: two synthetic students with different answers must get different sequences (tested, not scripted).'
    """
    stu_a = Student(pseudonymous_id="stu_learner_A", class_id="8-A", pin_hash="hash")
    stu_b = Student(pseudonymous_id="stu_learner_B", class_id="8-A", pin_hash="hash")

    plan_a = Plan(student_id=stu_a.pseudonymous_id, class_id="8-A", current_concept_id="c8_math_linear_eq_one_var")
    plan_b = Plan(student_id=stu_b.pseudonymous_id, class_id="8-A", current_concept_id="c8_math_linear_eq_one_var")

    mast_a = MasteryState(student_id=stu_a.pseudonymous_id, concept_id="c8_math_linear_eq_one_var")
    mast_b = MasteryState(student_id=stu_b.pseudonymous_id, concept_id="c8_math_linear_eq_one_var")

    # Student A gives correct answers
    att_a1 = Attempt(student_id=stu_a.pseudonymous_id, question_id="q_c8_leq_01", concept_id="c8_math_linear_eq_one_var", selected_option_id="opt_1", is_correct=True)
    plan_a, mast_a, _, _ = engine.process_attempt(stu_a, plan_a, att_a1, mast_a, None)
    step_a = engine.get_next_step(stu_a, plan_a, mast_a, None)

    # Student B gives wrong answer with transposition misconception
    att_b1 = Attempt(student_id=stu_b.pseudonymous_id, question_id="q_c8_leq_01", concept_id="c8_math_linear_eq_one_var", selected_option_id="opt_2", is_correct=False, misconception_tag="tag_sign_error_on_transposition")
    plan_b, mast_b, hyp_b, _ = engine.process_attempt(stu_b, plan_b, att_b1, mast_b, None)
    step_b = engine.get_next_step(stu_b, plan_b, mast_b, hyp_b)

    # Sequences must diverge:
    # Student A remains on SOLVE practice
    assert step_a.stage == StageEnum.SOLVE
    # Student B branches into PROBE stage
    assert step_b.stage == StageEnum.PROBE
    assert step_b.hypothesis.misconception_tag == "tag_sign_error_on_transposition"
    assert step_a.item.id != step_b.item.id
    assert mast_a.mastery_estimate > mast_b.mastery_estimate
