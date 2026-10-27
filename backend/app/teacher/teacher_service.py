"""
Teacher System Service.
Handles:
1. Scoped class view (a teacher sees ONLY their own class; unauthorized access is blocked).
2. Grouped view by shared prerequisite gap with explicit uncertainty ("not sure" placed under Undecided).
3. Small-group clinic suggestions (~10 minutes).
4. Teacher overrides (approve, edit, reject plan, assign concept, mark gap closed) with mandatory logged reason.
5. Gap-closed records for remedial planning and parent communication.
6. Teacher override rate computation as a live quality signal.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.learning import (
    TeacherOverride, Plan, MasteryState, Hypothesis, EvidenceBand,
    HypothesisStatus, StageEnum
)
from app.models.security import AuditLogEvent, AuditEventType


class GapClosedRecord(BaseModel):
    id: str
    student_id: str
    class_id: str
    concept_id: str
    concept_name: str
    closed_at: datetime = Field(default_factory=datetime.utcnow)
    teacher_id: str
    closure_reason: str
    supporting_evidence_summary: str
    note_for_parents: str


class ClinicSuggestion(BaseModel):
    clinic_id: str
    concept_id: str
    concept_name: str
    recommended_duration_minutes: int = 10
    student_ids: List[str]
    suggested_micro_lesson_id: Optional[str] = None
    reason: str


class StudentClassCard(BaseModel):
    student_id: str
    class_id: str
    current_concept_id: str
    gap_concept_id: Optional[str] = None
    bkt_mastery_estimate: float
    bkt_label: str = "uncalibrated, hand-set"
    evidence_score: Optional[int] = None
    evidence_band: Optional[str] = None
    evidence_label: str = "heuristic evidence score"
    suggested_plan_reason: str
    evidence_details: List[str] = Field(default_factory=list)


class ClassDashboardView(BaseModel):
    class_id: str
    teacher_id: str
    grouped_by_gap: Dict[str, List[StudentClassCard]]
    undecided_students: List[StudentClassCard]
    suggested_clinics: List[ClinicSuggestion]
    override_rate: float
    total_decisions: int
    total_overrides: int


class TeacherService:
    def __init__(self, teacher_class_assignments: Optional[Dict[str, Set[str]]] = None):
        # Maps teacher_id -> set of assigned class_ids, e.g. {"tea_math_01": {"8-A", "8-B"}}
        self.teacher_class_assignments = teacher_class_assignments or {
            "tea_01": {"8-A"},
            "tea_02": {"8-B"}
        }
        self.overrides: List[TeacherOverride] = []
        self.gap_closed_records: List[GapClosedRecord] = []
        self.audit_log: List[AuditLogEvent] = []
        self.decision_counts: Dict[str, int] = {}  # class_id -> total decisions count

    def verify_class_access(self, teacher_id: str, class_id: str) -> bool:
        allowed = self.teacher_class_assignments.get(teacher_id, set())
        return class_id in allowed

    def record_decision(self, class_id: str):
        self.decision_counts[class_id] = self.decision_counts.get(class_id, 0) + 1

    def get_class_dashboard(
        self,
        teacher_id: str,
        class_id: str,
        students_data: List[Dict[str, Any]]
    ) -> ClassDashboardView:
        """
        Retrieves the scoped class dashboard.
        Raises PermissionError if teacher is not assigned to this class.
        Groups students by shared supported gap; places 'not sure' / undecided students
        in the undecided bucket, NOT grouped.
        """
        if not self.verify_class_access(teacher_id, class_id):
            raise PermissionError(f"Access Denied: Teacher '{teacher_id}' is not assigned to class '{class_id}'.")

        # Log read audit event
        self.audit_log.append(AuditLogEvent(
            event_type=AuditEventType.READ,
            actor=teacher_id,
            class_id=class_id,
            record_count=len(students_data)
        ))

        grouped_by_gap: Dict[str, List[StudentClassCard]] = {}
        undecided_students: List[StudentClassCard] = []

        for item in students_data:
            student_id = item["student_id"]
            hyp: Optional[Hypothesis] = item.get("hypothesis")
            plan: Plan = item["plan"]
            mastery: MasteryState = item["mastery"]

            evidence_items = [e.details for e in hyp.evidence_list] if hyp else []

            card = StudentClassCard(
                student_id=student_id,
                class_id=class_id,
                current_concept_id=plan.current_concept_id,
                gap_concept_id=plan.gap_concept_id,
                bkt_mastery_estimate=mastery.mastery_estimate,
                bkt_label=mastery.mastery_label,
                evidence_score=hyp.heuristic_score if hyp else None,
                evidence_band=hyp.evidence_band.value if hyp else None,
                evidence_label="heuristic evidence score",
                suggested_plan_reason=plan.reason,
                evidence_details=evidence_items
            )

            # Check if student is undecided / not sure
            if hyp and (hyp.evidence_band == EvidenceBand.NOT_SURE or hyp.status == HypothesisStatus.UNDECIDED):
                undecided_students.append(card)
            elif plan.gap_concept_id and hyp and hyp.status == HypothesisStatus.SUPPORTED:
                # Group by shared gap
                grouped_by_gap.setdefault(plan.gap_concept_id, []).append(card)
            else:
                undecided_students.append(card)

        # Generate small-group clinic suggestions (~10 minutes)
        suggested_clinics: List[ClinicSuggestion] = []
        for gap_cid, student_cards in grouped_by_gap.items():
            if len(student_cards) >= 1:
                suggested_clinics.append(ClinicSuggestion(
                    clinic_id=f"clinic_{gap_cid}",
                    concept_id=gap_cid,
                    concept_name=gap_cid.replace("_", " ").title(),
                    recommended_duration_minutes=10,
                    student_ids=[c.student_id for c in student_cards],
                    suggested_micro_lesson_id=f"les_{gap_cid}",
                    reason=f"{len(student_cards)} student(s) identified with supported gap on '{gap_cid}'."
                ))

        # Compute override rate
        total_decisions = max(self.decision_counts.get(class_id, 0), len(students_data))
        class_overrides = [o for o in self.overrides if o.class_id == class_id]
        override_rate = round(len(class_overrides) / total_decisions, 3) if total_decisions > 0 else 0.0

        return ClassDashboardView(
            class_id=class_id,
            teacher_id=teacher_id,
            grouped_by_gap=grouped_by_gap,
            undecided_students=undecided_students,
            suggested_clinics=suggested_clinics,
            override_rate=override_rate,
            total_decisions=total_decisions,
            total_overrides=len(class_overrides)
        )

    def apply_override(
        self,
        teacher_id: str,
        class_id: str,
        student_id: str,
        concept_id: str,
        action: str,
        reason: str,
        student_plan: Plan
    ) -> Tuple[Plan, TeacherOverride]:
        """
        Applies a teacher override with mandatory reason.
        Modifies plan and logs override.
        """
        if not self.verify_class_access(teacher_id, class_id):
            raise PermissionError(f"Teacher '{teacher_id}' cannot override plans for class '{class_id}'.")

        override = TeacherOverride(
            student_id=student_id,
            teacher_id=teacher_id,
            class_id=class_id,
            concept_id=concept_id,
            override_action=action,
            reason=reason
        )
        self.overrides.append(override)

        # Update student plan
        if action == "assign_concept":
            student_plan.current_concept_id = concept_id
            student_plan.current_stage = StageEnum.SOLVE
            student_plan.gap_concept_id = None
        elif action == "close_gap":
            student_plan.gap_concept_id = None
            student_plan.current_stage = StageEnum.SOLVE
        elif action == "skip_to_enrichment":
            student_plan.current_stage = StageEnum.ENRICHMENT

        student_plan.reason = f"Teacher override ({action}): {reason}"

        # Audit log entry (contains no answers, no PII, no student ID in audit payload)
        self.audit_log.append(AuditLogEvent(
            event_type=AuditEventType.OVERRIDE,
            actor=teacher_id,
            class_id=class_id,
            record_count=1
        ))

        return student_plan, override

    def mark_gap_closed(
        self,
        teacher_id: str,
        class_id: str,
        student_id: str,
        concept_id: str,
        concept_name: str,
        reason: str,
        evidence_summary: str
    ) -> GapClosedRecord:
        """
        Records a gap-closed milestone readable for parents and remedial planning.
        """
        if not self.verify_class_access(teacher_id, class_id):
            raise PermissionError("Unauthorized class access.")

        record = GapClosedRecord(
            id=f"gap_closed_{student_id}_{concept_id}_{int(datetime.utcnow().timestamp())}",
            student_id=student_id,
            class_id=class_id,
            concept_id=concept_id,
            concept_name=concept_name,
            teacher_id=teacher_id,
            closure_reason=reason,
            supporting_evidence_summary=evidence_summary,
            note_for_parents=f"Prerequisite gap in {concept_name} successfully resolved via teacher clinic."
        )
        self.gap_closed_records.append(record)
        return record

    def compute_override_rate(self, class_id: str) -> float:
        class_overrides = [o for o in self.overrides if o.class_id == class_id]
        total_decisions = max(1, self.decision_counts.get(class_id, 1))
        return round(len(class_overrides) / total_decisions, 4)
