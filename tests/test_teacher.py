import sys
import os
import pytest

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.teacher.teacher_service import TeacherService
from app.models.learning import (
    Plan, MasteryState, Hypothesis, EvidenceBand, HypothesisStatus,
    StageEnum, TeacherOverride
)


@pytest.fixture
def teacher_service():
    return TeacherService(
        teacher_class_assignments={
            "tea_math_8A": {"8-A"},
            "tea_math_8B": {"8-B"}
        }
    )


def test_teacher_class_isolation(teacher_service):
    """
    Negative test requirement:
    'A teacher sees only their own class.
     Tests: a teacher cannot read another class (negative test).'
    """
    # Teacher of 8-A tries to access 8-B data
    with pytest.raises(PermissionError) as excinfo:
        teacher_service.get_class_dashboard(
            teacher_id="tea_math_8A",
            class_id="8-B",
            students_data=[]
        )
    assert "Access Denied" in str(excinfo.value)
    assert "not assigned to class '8-B'" in str(excinfo.value)


def test_teacher_grouped_view_and_undecided(teacher_service):
    """
    Test requirement:
    'Class view grouped by shared gap, with each student's evidence: answers, probes,
     evidence score band, BKT estimate, and the reason the system suggests a plan.
     Show uncertainty. A student with "not sure" appears as undecided, not grouped.'
    """
    # Student 1: Supported Class 6 integer subtraction gap
    hyp_1 = Hypothesis(
        student_id="stu_1",
        suspected_concept_id="c6_math_integers_add_sub",
        misconception_tag="tag_class6_integer_subtraction",
        heuristic_score=2,
        evidence_band=EvidenceBand.HIGH,
        status=HypothesisStatus.SUPPORTED
    )
    plan_1 = Plan(
        student_id="stu_1",
        class_id="8-A",
        current_concept_id="c8_math_linear_eq_one_var",
        gap_concept_id="c6_math_integers_add_sub",
        reason="Supported prerequisite gap on Class 6 Integers"
    )
    mastery_1 = MasteryState(student_id="stu_1", concept_id="c8_math_linear_eq_one_var", mastery_estimate=0.35)

    # Student 2: Shares the exact same Class 6 gap
    hyp_2 = Hypothesis(
        student_id="stu_2",
        suspected_concept_id="c6_math_integers_add_sub",
        misconception_tag="tag_class6_integer_subtraction",
        heuristic_score=2,
        evidence_band=EvidenceBand.HIGH,
        status=HypothesisStatus.SUPPORTED
    )
    plan_2 = Plan(
        student_id="stu_2",
        class_id="8-A",
        current_concept_id="c8_math_linear_eq_one_var",
        gap_concept_id="c6_math_integers_add_sub",
        reason="Supported prerequisite gap on Class 6 Integers"
    )
    mastery_2 = MasteryState(student_id="stu_2", concept_id="c8_math_linear_eq_one_var", mastery_estimate=0.40)

    # Student 3: Thin or conflicting probe evidence -> 'not sure'
    hyp_3 = Hypothesis(
        student_id="stu_3",
        suspected_concept_id="c6_math_integers_add_sub",
        misconception_tag="tag_class6_integer_subtraction",
        heuristic_score=0,
        evidence_band=EvidenceBand.NOT_SURE,
        status=HypothesisStatus.UNDECIDED
    )
    plan_3 = Plan(
        student_id="stu_3",
        class_id="8-A",
        current_concept_id="c8_math_linear_eq_one_var",
        reason="Evidence thin/conflicting. Gathering more probes."
    )
    mastery_3 = MasteryState(student_id="stu_3", concept_id="c8_math_linear_eq_one_var", mastery_estimate=0.50)

    students_data = [
        {"student_id": "stu_1", "hypothesis": hyp_1, "plan": plan_1, "mastery": mastery_1},
        {"student_id": "stu_2", "hypothesis": hyp_2, "plan": plan_2, "mastery": mastery_2},
        {"student_id": "stu_3", "hypothesis": hyp_3, "plan": plan_3, "mastery": mastery_3},
    ]

    dashboard = teacher_service.get_class_dashboard("tea_math_8A", "8-A", students_data)

    # Students 1 & 2 must be grouped together under c6_math_integers_add_sub
    assert "c6_math_integers_add_sub" in dashboard.grouped_by_gap
    grouped_stus = [c.student_id for c in dashboard.grouped_by_gap["c6_math_integers_add_sub"]]
    assert "stu_1" in grouped_stus
    assert "stu_2" in grouped_stus

    # Student 3 ('not sure') must NOT be grouped into the gap! Must be in undecided_students!
    assert "stu_3" not in grouped_stus
    undecided_stus = [c.student_id for c in dashboard.undecided_students]
    assert "stu_3" in undecided_stus


def test_clinic_suggestions(teacher_service):
    # Two students share c6_math_integers_add_sub gap
    hyp = Hypothesis(
        student_id="stu_1",
        suspected_concept_id="c6_math_integers_add_sub",
        misconception_tag="tag_class6_integer_subtraction",
        evidence_band=EvidenceBand.HIGH,
        status=HypothesisStatus.SUPPORTED
    )
    plan = Plan(
        student_id="stu_1",
        class_id="8-A",
        current_concept_id="c8_math_linear_eq_one_var",
        gap_concept_id="c6_math_integers_add_sub"
    )
    mastery = MasteryState(student_id="stu_1", concept_id="c8_math_linear_eq_one_var")

    dashboard = teacher_service.get_class_dashboard(
        "tea_math_8A", "8-A",
        [{"student_id": "stu_1", "hypothesis": hyp, "plan": plan, "mastery": mastery}]
    )

    assert len(dashboard.suggested_clinics) >= 1
    clinic = dashboard.suggested_clinics[0]
    assert clinic.recommended_duration_minutes == 10
    assert clinic.concept_id == "c6_math_integers_add_sub"
    assert "stu_1" in clinic.student_ids


def test_teacher_override_logging(teacher_service):
    """
    Test requirement:
    'An override changes the student's plan and is logged with a reason.'
    """
    plan = Plan(
        student_id="stu_1",
        class_id="8-A",
        current_concept_id="c8_math_linear_eq_one_var",
        gap_concept_id="c6_math_integers_add_sub",
        current_stage=StageEnum.LEARN
    )

    updated_plan, override = teacher_service.apply_override(
        teacher_id="tea_math_8A",
        class_id="8-A",
        student_id="stu_1",
        concept_id="c8_math_rational_ops",
        action="assign_concept",
        reason="Student already mastered linear equations in tutoring.",
        student_plan=plan
    )

    # Plan changed
    assert updated_plan.current_concept_id == "c8_math_rational_ops"
    assert updated_plan.gap_concept_id is None
    assert "Teacher override" in updated_plan.reason

    # Override logged with reason
    assert len(teacher_service.overrides) == 1
    assert override.reason == "Student already mastered linear equations in tutoring."
    assert override.teacher_id == "tea_math_8A"


def test_gap_closed_record(teacher_service):
    record = teacher_service.mark_gap_closed(
        teacher_id="tea_math_8A",
        class_id="8-A",
        student_id="stu_1",
        concept_id="c6_math_integers_add_sub",
        concept_name="Addition and Subtraction of Integers",
        reason="Completed 10-minute small group clinic and passed exit ticket.",
        evidence_summary="Answered 3/3 integer subtraction probe questions correctly."
    )
    assert record.student_id == "stu_1"
    assert record.concept_id == "c6_math_integers_add_sub"
    assert "Prerequisite gap" in record.note_for_parents
    assert len(teacher_service.gap_closed_records) == 1


def test_teacher_override_rate_computation(teacher_service):
    teacher_service.record_decision("8-A")
    teacher_service.record_decision("8-A")
    teacher_service.record_decision("8-A")
    teacher_service.record_decision("8-A")  # 4 decisions

    plan = Plan(student_id="stu_1", class_id="8-A", current_concept_id="c8_math_linear_eq_one_var")
    teacher_service.apply_override(
        teacher_id="tea_math_8A",
        class_id="8-A",
        student_id="stu_1",
        concept_id="c8_math_linear_eq_one_var",
        action="close_gap",
        reason="Demonstrated mastery on blackboard",
        student_plan=plan
    )

    rate = teacher_service.compute_override_rate("8-A")
    # 1 override out of 4 decisions = 0.25
    assert rate == 0.25
