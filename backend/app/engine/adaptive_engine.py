"""
Adaptive Engine Orchestrator.
Coordinates:
- Ask & Hypothesise (wrong answer opens hypothesis, low evidence band, no immediate gap)
- Probe (diagnostic probes gather heuristic evidence; conflicting probes -> 'not sure')
- Trace (walks prerequisite graph backwards to isolate earliest supported gap)
- Learn (delivers micro-lesson bridge)
- Solve (hint ladder; 2 stuck attempts raise teacher flag)
- Test & Bridge Recheck (pass returns to topic, fail stays on gap, repeated fails flag teacher)
- Move Ahead (fast learners skip drill on sufficient mastery)
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from app.models.pack import ContentPack
from app.models.content import Question, Lesson, HintLadder
from app.models.student import Student
from app.models.learning import (
    Attempt, Hypothesis, EvidenceBand, HypothesisStatus,
    MasteryState, Plan, StageEnum, TeacherOverride
)
from app.engine.bkt import BKTEngine
from app.engine.hypothesis_engine import HypothesisEngine
from app.engine.graph_tracer import GraphTracer
from app.engine.sequencer import RuleSequencer, DecisionResult
from app.engine.scheduler import SpacedRepetitionScheduler


class NextStepResult:
    def __init__(
        self,
        stage: StageEnum,
        item_type: str,  # 'question', 'lesson', 'flag'
        item: Optional[Any],
        reason: str,
        bkt_mastery: float,
        bkt_label: str,
        hypothesis: Optional[Hypothesis] = None,
        teacher_flag: Optional[str] = None
    ):
        self.stage = stage
        self.item_type = item_type
        self.item = item
        self.reason = reason
        self.bkt_mastery = bkt_mastery
        self.bkt_label = bkt_label
        self.hypothesis = hypothesis
        self.teacher_flag = teacher_flag

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "item_type": self.item_type,
            "item_id": self.item.id if hasattr(self.item, "id") else None,
            "reason": self.reason,
            "bkt_mastery": self.bkt_mastery,
            "bkt_label": self.bkt_label,
            "evidence_score": self.hypothesis.heuristic_score if self.hypothesis else None,
            "evidence_band": self.hypothesis.evidence_band.value if self.hypothesis else None,
            "evidence_label": "heuristic evidence score",
            "teacher_flag": self.teacher_flag
        }


class AdaptiveEngine:
    def __init__(self, pack: ContentPack, sequencer_rules: Optional[List[Dict[str, Any]]] = None):
        self.pack = pack
        self.bkt = BKTEngine()
        self.hypothesis_engine = HypothesisEngine()
        self.tracer = GraphTracer(pack)
        self.sequencer = RuleSequencer(sequencer_rules)
        self.scheduler = SpacedRepetitionScheduler()

        # Indexes for content
        self.questions_by_id = {q.id: q for q in pack.questions}
        self.questions_by_concept: Dict[str, List[Question]] = {}
        for q in pack.questions:
            self.questions_by_concept.setdefault(q.concept, []).append(q)

        self.probes_by_tag: Dict[str, List[Question]] = {}
        for q in pack.questions:
            if q.probe_for_misconception:
                self.probes_by_tag.setdefault(q.probe_for_misconception, []).append(q)

        self.lessons_by_concept: Dict[str, List[Lesson]] = {}
        self.lessons_by_tag: Dict[str, Lesson] = {}
        for l in pack.lessons:
            self.lessons_by_concept.setdefault(l.concept, []).append(l)
            if l.misconception:
                self.lessons_by_tag[l.misconception] = l

        self.hints_by_qid = {h.question_id: h for h in pack.hints}

    def process_attempt(
        self,
        student: Student,
        plan: Plan,
        attempt: Attempt,
        mastery_state: MasteryState,
        active_hypothesis: Optional[Hypothesis] = None
    ) -> Tuple[Plan, MasteryState, Optional[Hypothesis], DecisionResult]:
        """
        Processes an attempt, updates BKT mastery, updates hypothesis/evidence,
        and evaluates data sequencer rules for the next decision.
        """
        # 1. Update BKT mastery
        updated_mastery = self.bkt.update(mastery_state.mastery_estimate, attempt.is_correct)
        mastery_state.mastery_estimate = updated_mastery
        if attempt.is_correct:
            mastery_state.consecutive_successes += 1
            plan.stuck_attempts_count = 0
        else:
            mastery_state.consecutive_successes = 0
            plan.stuck_attempts_count += 1

        # 2. Handle hypothesis & probe outcomes
        if plan.current_stage == StageEnum.PROBE and active_hypothesis:
            # We just answered a diagnostic probe
            # A wrong answer on probe confirms the gap; correct contradicts it
            is_supporting = not attempt.is_correct
            active_hypothesis = self.hypothesis_engine.add_probe_result(
                hypothesis=active_hypothesis,
                probe_question_id=attempt.question_id,
                probe_concept_id=attempt.concept_id,
                is_supporting=is_supporting
            )
        elif not attempt.is_correct and attempt.misconception_tag:
            # First wrong answer: opens hypothesis with LOW score band, NO gap declared
            active_hypothesis = self.hypothesis_engine.open_hypothesis(
                student_id=student.pseudonymous_id,
                suspected_concept_id=attempt.concept_id,
                misconception_tag=attempt.misconception_tag
            )

        # 3. Handle bridge recheck outcomes
        recheck_passed = None
        if plan.current_stage == StageEnum.BRIDGE_RECHECK:
            recheck_passed = attempt.is_correct
            if not attempt.is_correct:
                plan.bridge_recheck_fails += 1
            else:
                plan.bridge_recheck_fails = 0

        # 4. Check if gap is supported by tracing
        gap_supported = False
        earliest_gap_id = None
        if active_hypothesis and (active_hypothesis.status == HypothesisStatus.SUPPORTED or active_hypothesis.heuristic_score >= 1):
            trace = self.tracer.trace_earliest_gap(
                starting_concept_id=plan.current_concept_id,
                active_hypotheses=[active_hypothesis]
            )
            if trace.found_gap:
                gap_supported = True
                earliest_gap_id = trace.earliest_gap_concept_id
                plan.gap_concept_id = earliest_gap_id

        # 5. Build state for RuleSequencer evaluation
        sequencer_state = {
            "current_stage": plan.current_stage,
            "stuck_attempts": plan.stuck_attempts_count,
            "bridge_recheck_fails": plan.bridge_recheck_fails,
            "bridge_recheck_passed": recheck_passed,
            "has_open_hypothesis": active_hypothesis is not None and active_hypothesis.status == HypothesisStatus.OPEN,
            "evidence_band": active_hypothesis.evidence_band.value if active_hypothesis else None,
            "gap_supported": gap_supported,
            "mastery_estimate": mastery_state.mastery_estimate,
            "consecutive_successes": mastery_state.consecutive_successes
        }

        decision = self.sequencer.evaluate(sequencer_state)

        # 6. Apply sequencer decision to Plan
        if decision.action == "FLAG_TEACHER_STUCK" or decision.action == "FLAG_TEACHER_REPEATED_FAIL":
            plan.reason = decision.reason
        elif decision.action == "ADMINISTER_PROBE":
            plan.current_stage = StageEnum.PROBE
            plan.reason = decision.reason
        elif decision.action == "START_MICRO_LESSON":
            plan.current_stage = StageEnum.LEARN
            plan.reason = decision.reason
        elif decision.action == "RETURN_TO_ORIGINAL_TOPIC":
            plan.current_stage = StageEnum.SOLVE
            plan.gap_concept_id = None
            plan.reason = decision.reason
            # Schedule spaced review for passed gap
            self.scheduler.schedule_next_review(mastery_state, quality=4)
        elif decision.action == "STAY_ON_GAP":
            plan.current_stage = StageEnum.BRIDGE_RECHECK
            plan.reason = decision.reason
        elif decision.action == "MOVE_AHEAD":
            plan.current_stage = StageEnum.MOVE_AHEAD
            plan.reason = decision.reason
        elif decision.action == "REQUEST_MORE_PROBES":
            plan.current_stage = StageEnum.PROBE
            plan.reason = decision.reason

        plan.updated_at = datetime.utcnow()
        return plan, mastery_state, active_hypothesis, decision

    def get_next_step(
        self,
        student: Student,
        plan: Plan,
        mastery_state: MasteryState,
        active_hypothesis: Optional[Hypothesis] = None
    ) -> NextStepResult:
        """
        Determines the next item to display to the student (Question, Lesson, or Flag)
        strictly adhering to honest labelling rules.
        """
        # Teacher flags
        if plan.bridge_recheck_fails >= 2:
            return NextStepResult(
                stage=plan.current_stage,
                item_type="flag",
                item=None,
                reason="Student failed bridge check repeatedly. Teacher flagged for small-group clinic.",
                bkt_mastery=mastery_state.mastery_estimate,
                bkt_label=mastery_state.mastery_label,
                hypothesis=active_hypothesis,
                teacher_flag="REPEATED_BRIDGE_FAIL"
            )

        if plan.stuck_attempts_count >= 2:
            return NextStepResult(
                stage=plan.current_stage,
                item_type="flag",
                item=None,
                reason="Student is stuck after 2 failed attempts. Teacher intervention flagged.",
                bkt_mastery=mastery_state.mastery_estimate,
                bkt_label=mastery_state.mastery_label,
                hypothesis=active_hypothesis,
                teacher_flag="STUCK_STUDENT"
            )

        # 1. Probe Stage
        if plan.current_stage == StageEnum.PROBE and active_hypothesis:
            probes = self.probes_by_tag.get(active_hypothesis.misconception_tag, [])
            # Pick unseen probe
            seen_probes = {e.probe_question_id for e in active_hypothesis.evidence_list}
            available_probes = [p for p in probes if p.id not in seen_probes]

            if available_probes:
                probe_q = available_probes[0]
                return NextStepResult(
                    stage=StageEnum.PROBE,
                    item_type="question",
                    item=probe_q,
                    reason=f"Administering diagnostic probe to test suspected misconception '{active_hypothesis.misconception_tag}'.",
                    bkt_mastery=mastery_state.mastery_estimate,
                    bkt_label=mastery_state.mastery_label,
                    hypothesis=active_hypothesis
                )
            else:
                # Out of probes: evaluate status
                if active_hypothesis.heuristic_score > 0 and active_hypothesis.evidence_band != EvidenceBand.NOT_SURE:
                    plan.current_stage = StageEnum.LEARN
                else:
                    active_hypothesis.evidence_band = EvidenceBand.NOT_SURE
                    plan.current_stage = StageEnum.SOLVE

        # 2. Learn Stage (Micro-lesson)
        if plan.current_stage == StageEnum.LEARN:
            tag = active_hypothesis.misconception_tag if active_hypothesis else None
            lesson = self.lessons_by_tag.get(tag) if tag else None
            if not lesson:
                # Foundational concept lesson fallback
                concept_id = plan.gap_concept_id or plan.current_concept_id
                lessons = self.lessons_by_concept.get(concept_id, [])
                lesson = lessons[0] if lessons else None

            # After serving micro-lesson, transition plan to bridge re-check
            plan.current_stage = StageEnum.BRIDGE_RECHECK

            return NextStepResult(
                stage=StageEnum.LEARN,
                item_type="lesson",
                item=lesson,
                reason=f"Delivering targeted micro-lesson bridge for '{tag or plan.current_concept_id}'.",
                bkt_mastery=mastery_state.mastery_estimate,
                bkt_label=mastery_state.mastery_label,
                hypothesis=active_hypothesis
            )

        # 3. Bridge Re-Check Stage
        if plan.current_stage == StageEnum.BRIDGE_RECHECK:
            # Deliver a diagnostic check question on the gap concept or current concept
            concept_to_test = plan.gap_concept_id or plan.current_concept_id
            qs = self.questions_by_concept.get(concept_to_test, [])
            q = qs[0] if qs else None
            return NextStepResult(
                stage=StageEnum.BRIDGE_RECHECK,
                item_type="question",
                item=q,
                reason="Bridge re-check: verifying understanding of foundational prerequisite.",
                bkt_mastery=mastery_state.mastery_estimate,
                bkt_label=mastery_state.mastery_label,
                hypothesis=active_hypothesis
            )

        # 4. Move Ahead Stage
        if plan.current_stage == StageEnum.MOVE_AHEAD:
            return NextStepResult(
                stage=StageEnum.MOVE_AHEAD,
                item_type="enrichment",
                item=None,
                reason="High mastery verified with sufficient evidence. Advancing ahead to next concept or enrichment.",
                bkt_mastery=mastery_state.mastery_estimate,
                bkt_label=mastery_state.mastery_label,
                hypothesis=active_hypothesis
            )

        # 5. Default Solve / Practice Stage
        # Difficulty matches BKT estimate
        qs = self.questions_by_concept.get(plan.current_concept_id, [])
        # Sort by distance to current mastery estimate to pick the most informative item
        sorted_qs = sorted(qs, key=lambda q: abs(q.difficulty - mastery_state.mastery_estimate))
        chosen_q = sorted_qs[0] if sorted_qs else None

        return NextStepResult(
            stage=StageEnum.SOLVE,
            item_type="question",
            item=chosen_q,
            reason="Adaptive practice question selected to calibrate to current mastery estimate.",
            bkt_mastery=mastery_state.mastery_estimate,
            bkt_label=mastery_state.mastery_label,
            hypothesis=active_hypothesis
        )

    def get_hint_ladder(self, question_id: str) -> Optional[HintLadder]:
        return self.hints_by_qid.get(question_id)
