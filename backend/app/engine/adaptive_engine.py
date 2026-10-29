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

from typing import Dict, List, Optional, Any, Tuple, Set
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
        item_type: str,  # 'question', 'lesson', 'flag', 'enrichment'
        item: Optional[Any],
        reason: str,
        bkt_mastery: float,
        bkt_label: str,
        hypothesis: Optional[Hypothesis] = None,
        teacher_flag: Optional[str] = None,
        is_fallback: bool = False,
        fallback_label: Optional[str] = None,
        language_label: Optional[str] = None,
        target_concept_id: Optional[str] = None,
        gap_concept_id: Optional[str] = None,
        misconception_tag: Optional[str] = None,
        stuck_attempts: int = 0,
        bridge_recheck_fails: int = 0,
        consecutive_successes: int = 0
    ):
        self.stage = stage
        self.item_type = item_type
        self.item = item
        self.reason = reason
        self.bkt_mastery = bkt_mastery
        self.bkt_label = bkt_label
        self.hypothesis = hypothesis
        self.teacher_flag = teacher_flag
        self.is_fallback = is_fallback
        self.fallback_label = fallback_label
        self.language_label = language_label
        self.target_concept_id = target_concept_id
        self.gap_concept_id = gap_concept_id
        self.misconception_tag = misconception_tag
        self.stuck_attempts = stuck_attempts
        self.bridge_recheck_fails = bridge_recheck_fails
        self.consecutive_successes = consecutive_successes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value if hasattr(self.stage, "value") else str(self.stage),
            "item_type": self.item_type,
            "item_id": self.item.id if hasattr(self.item, "id") else None,
            "reason": self.reason,
            "bkt_mastery": self.bkt_mastery,
            "bkt_label": self.bkt_label,
            "evidence_score": self.hypothesis.heuristic_score if self.hypothesis else None,
            "evidence_band": self.hypothesis.evidence_band.value if (self.hypothesis and hasattr(self.hypothesis.evidence_band, "value")) else (self.hypothesis.evidence_band if self.hypothesis else None),
            "evidence_label": "heuristic evidence score",
            "teacher_flag": self.teacher_flag,
            "is_fallback": self.is_fallback,
            "fallback_label": self.fallback_label,
            "language_label": self.language_label,
            "target_concept_id": self.target_concept_id,
            "gap_concept_id": self.gap_concept_id,
            "misconception_tag": self.misconception_tag,
            "stuck_attempts": self.stuck_attempts,
            "bridge_recheck_fails": self.bridge_recheck_fails,
            "consecutive_successes": self.consecutive_successes
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
        self.questions_by_concept_lang: Dict[Tuple[str, str], List[Question]] = {}
        for q in pack.questions:
            if not getattr(q, "is_probe", False):
                self.questions_by_concept.setdefault(q.concept, []).append(q)
                lang = getattr(q, "language", "en") or "en"
                self.questions_by_concept_lang.setdefault((q.concept, lang), []).append(q)

        self.probes_by_tag: Dict[str, List[Question]] = {}
        self.probes_by_tag_lang: Dict[Tuple[str, str], List[Question]] = {}
        for q in pack.questions:
            if q.probe_for_misconception:
                self.probes_by_tag.setdefault(q.probe_for_misconception, []).append(q)
                lang = getattr(q, "language", "en") or "en"
                self.probes_by_tag_lang.setdefault((q.probe_for_misconception, lang), []).append(q)

        self.lessons_by_concept: Dict[str, List[Lesson]] = {}
        self.lessons_by_concept_lang: Dict[Tuple[str, str], List[Lesson]] = {}
        self.lessons_by_tag: Dict[str, Lesson] = {}
        self.lessons_by_tag_lang: Dict[Tuple[str, str], Lesson] = {}
        for l in pack.lessons:
            self.lessons_by_concept.setdefault(l.concept, []).append(l)
            lang = getattr(l, "language", "en") or "en"
            self.lessons_by_concept_lang.setdefault((l.concept, lang), []).append(l)
            if l.misconception:
                self.lessons_by_tag_lang[(l.misconception, lang)] = l
                # For backward compatibility, prefer English as default in legacy tag index
                if l.misconception not in self.lessons_by_tag or lang == "en":
                    self.lessons_by_tag[l.misconception] = l

        self.hints_by_qid = {h.question_id: h for h in pack.hints}

    def get_questions_for_student(self, concept_id: str, medium_language: str) -> Tuple[List[Question], bool]:
        """
        Selects questions for concept and medium_language.
        English students NEVER receive non-English questions.
        Non-English students fallback to English if no items exist in their medium.
        Returns (questions_list, is_fallback).
        """
        lang = medium_language or "en"
        qs = self.questions_by_concept_lang.get((concept_id, lang), [])
        if qs:
            return qs, False
        if lang != "en":
            en_qs = self.questions_by_concept_lang.get((concept_id, "en"), [])
            if en_qs:
                return en_qs, True
        return self.questions_by_concept.get(concept_id, []), False

    def get_probes_for_student(self, misconception_tag: str, medium_language: str) -> Tuple[List[Question], bool]:
        """
        Selects diagnostic probes for misconception_tag and medium_language.
        Returns (probes_list, is_fallback).
        """
        lang = medium_language or "en"
        probes = self.probes_by_tag_lang.get((misconception_tag, lang), [])
        if probes:
            return probes, False
        if lang != "en":
            en_probes = self.probes_by_tag_lang.get((misconception_tag, "en"), [])
            if en_probes:
                return en_probes, True
        return self.probes_by_tag.get(misconception_tag, []), False

    def get_lesson_for_student(
        self,
        misconception_tag: Optional[str],
        concept_id: str,
        medium_language: str
    ) -> Tuple[Optional[Lesson], bool]:
        """
        Selects a micro-lesson matching misconception tag and student medium language.
        Returns (lesson, is_fallback).
        """
        lang = medium_language or "en"
        if misconception_tag:
            les = self.lessons_by_tag_lang.get((misconception_tag, lang))
            if les:
                return les, False
            if lang != "en":
                en_les = self.lessons_by_tag_lang.get((misconception_tag, "en"))
                if en_les:
                    return en_les, True

        # Concept lesson fallback
        concept_lessons = self.lessons_by_concept_lang.get((concept_id, lang), [])
        if concept_lessons:
            return concept_lessons[0], False
        if lang != "en":
            en_concept_lessons = self.lessons_by_concept_lang.get((concept_id, "en"), [])
            if en_concept_lessons:
                return en_concept_lessons[0], True

        # Legacy fallback
        if misconception_tag and misconception_tag in self.lessons_by_tag:
            l = self.lessons_by_tag[misconception_tag]
            l_lang = getattr(l, "language", "en")
            return l, (l_lang != lang)
        cl = self.lessons_by_concept.get(concept_id, [])
        return (cl[0] if cl else None), False

    def process_attempt(
        self,
        student: Student,
        plan: Plan,
        attempt: Attempt,
        mastery_state: MasteryState,
        active_hypothesis: Optional[Hypothesis] = None,
        original_concept_mastery: Optional[MasteryState] = None
    ) -> Tuple[Plan, MasteryState, Optional[Hypothesis], DecisionResult]:
        """
        Processes an attempt, updates BKT mastery, updates hypothesis/evidence,
        and evaluates data sequencer rules for the next decision.
        Diagnostic probes DO NOT count toward the stuck counter.
        Stuck counts consecutive wrong answers in SOLVE or BRIDGE_RECHECK.
        """
        # 1. Update BKT mastery
        updated_mastery = self.bkt.update(mastery_state.mastery_estimate, attempt.is_correct)
        mastery_state.mastery_estimate = updated_mastery

        # Preserve lesson-Continue transition during offline replay/sync:
        # If student was in micro-lesson (LEARN) and submits a question attempt,
        # the lesson was continued offline into BRIDGE_RECHECK.
        if plan.current_stage == StageEnum.LEARN:
            plan.current_stage = StageEnum.BRIDGE_RECHECK

        # Stuck counter: diagnostic probes DO NOT increment stuck counter
        # Diagnostic probes are attempts served when plan is in PROBE stage for a probe question
        is_probe_attempt = (plan.current_stage == StageEnum.PROBE) and (
            attempt.question_id.startswith("probe_") or 
            (active_hypothesis and any(p.id == attempt.question_id for p in self.probes_by_tag.get(active_hypothesis.misconception_tag, [])))
        )

        if attempt.is_correct:
            mastery_state.consecutive_successes += 1
            if not is_probe_attempt:
                plan.stuck_attempts_count = 0
        else:
            mastery_state.consecutive_successes = 0
            if not is_probe_attempt:
                plan.stuck_attempts_count += 1

        # 2. Handle hypothesis & probe outcomes
        if plan.current_stage == StageEnum.PROBE and active_hypothesis and is_probe_attempt:
            # We just answered a diagnostic probe
            # A wrong answer on probe confirms the gap; correct contradicts it
            is_supporting = not attempt.is_correct
            active_hypothesis = self.hypothesis_engine.add_probe_result(
                hypothesis=active_hypothesis,
                probe_question_id=attempt.question_id,
                probe_concept_id=attempt.concept_id,
                is_supporting=is_supporting
            )
            if attempt.is_correct:
                # Contradicted by probe: student showed prerequisite competence
                active_hypothesis.status = HypothesisStatus.REJECTED
                plan.current_stage = StageEnum.SOLVE
                plan.reason = "Prerequisite diagnostic probe answered correctly, contradicting misconception hypothesis. Returning to practice."
        elif not attempt.is_correct and attempt.misconception_tag and not is_probe_attempt:
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
        probes, _ = self.get_probes_for_student(
            active_hypothesis.misconception_tag, student.medium_language
        ) if active_hypothesis else ([], False)
        seen_probes = {e.probe_question_id for e in active_hypothesis.evidence_list} if active_hypothesis else set()
        unseen_probes = [p for p in probes if p.id not in seen_probes]

        if active_hypothesis and (active_hypothesis.status == HypothesisStatus.SUPPORTED or (active_hypothesis.heuristic_score >= 1 and not unseen_probes)):
            trace = self.tracer.trace_earliest_gap(
                starting_concept_id=plan.current_concept_id,
                active_hypotheses=[active_hypothesis]
            )
            if trace.found_gap:
                gap_supported = True
                earliest_gap_id = trace.earliest_gap_concept_id
                plan.gap_concept_id = earliest_gap_id

        # 5. Build state for RuleSequencer evaluation
        # Note: Move-ahead must be evaluated on the ORIGINAL topic's mastery (plan.current_concept_id),
        # NOT on the prerequisite's mastery!
        if attempt.concept_id == plan.current_concept_id:
            eval_mastery_estimate = mastery_state.mastery_estimate
            eval_consecutive_successes = mastery_state.consecutive_successes
        else:
            orig_m = original_concept_mastery
            eval_mastery_estimate = orig_m.mastery_estimate if orig_m else 0.0
            eval_consecutive_successes = orig_m.consecutive_successes if orig_m else 0

        sequencer_state = {
            "current_stage": plan.current_stage,
            "stuck_attempts": plan.stuck_attempts_count,
            "bridge_recheck_fails": plan.bridge_recheck_fails,
            "bridge_recheck_passed": recheck_passed,
            "has_open_hypothesis": active_hypothesis is not None and active_hypothesis.status == HypothesisStatus.OPEN,
            "evidence_band": active_hypothesis.evidence_band.value if (active_hypothesis and hasattr(active_hypothesis.evidence_band, "value")) else (active_hypothesis.evidence_band if active_hypothesis else None),
            "gap_supported": gap_supported,
            "mastery_estimate": eval_mastery_estimate,
            "consecutive_successes": eval_consecutive_successes
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
            plan.stuck_attempts_count = 0
            plan.reason = decision.reason
        elif decision.action == "RETURN_TO_ORIGINAL_TOPIC":
            plan.current_stage = StageEnum.SOLVE
            plan.gap_concept_id = None
            plan.stuck_attempts_count = 0
            plan.bridge_recheck_fails = 0
            plan.reason = decision.reason
            if active_hypothesis:
                active_hypothesis.status = HypothesisStatus.REJECTED
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

    def _enrich_result(
        self,
        res: NextStepResult,
        plan: Plan,
        mastery_state: MasteryState,
        active_hypothesis: Optional[Hypothesis]
    ) -> NextStepResult:
        res.target_concept_id = plan.current_concept_id
        res.gap_concept_id = plan.gap_concept_id
        res.misconception_tag = active_hypothesis.misconception_tag if active_hypothesis else None
        res.stuck_attempts = plan.stuck_attempts_count
        res.bridge_recheck_fails = plan.bridge_recheck_fails
        res.consecutive_successes = mastery_state.consecutive_successes
        return res

    def get_next_step(
        self,
        student: Student,
        plan: Plan,
        mastery_state: MasteryState,
        active_hypothesis: Optional[Hypothesis] = None,
        seen_question_ids: Optional[Set[str]] = None
    ) -> NextStepResult:
        res = self._compute_next_step(
            student=student,
            plan=plan,
            mastery_state=mastery_state,
            active_hypothesis=active_hypothesis,
            seen_question_ids=seen_question_ids
        )
        return self._enrich_result(res, plan, mastery_state, active_hypothesis)

    def _compute_next_step(
        self,
        student: Student,
        plan: Plan,
        mastery_state: MasteryState,
        active_hypothesis: Optional[Hypothesis] = None,
        seen_question_ids: Optional[Set[str]] = None
    ) -> NextStepResult:
        """
        Determines the next item to display to the student (Question, Lesson, Flag, or Enrichment)
        strictly adhering to honest labelling rules and student medium language.
        Does NOT change or mutate plan stage in GET.
        """
        seen_ids = set(seen_question_ids or [])
        medium_lang = getattr(student, "medium_language", "en") or "en"

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
            probes, is_fallback = self.get_probes_for_student(
                active_hypothesis.misconception_tag, medium_lang
            )
            seen_probes = {e.probe_question_id for e in active_hypothesis.evidence_list}
            available_probes = [p for p in probes if p.id not in seen_probes]

            if available_probes:
                probe_q = available_probes[0]
                lang_label = "unreviewed draft" if getattr(probe_q, "language", "en") in ("hi", "te") else "supported"
                fb_label = "English fallback (No probe in your medium)" if is_fallback else None
                return NextStepResult(
                    stage=StageEnum.PROBE,
                    item_type="question",
                    item=probe_q,
                    reason=f"Administering diagnostic probe to test suspected misconception '{active_hypothesis.misconception_tag}'.",
                    bkt_mastery=mastery_state.mastery_estimate,
                    bkt_label=mastery_state.mastery_label,
                    hypothesis=active_hypothesis,
                    is_fallback=is_fallback,
                    fallback_label=fb_label,
                    language_label=lang_label
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
            concept_to_learn = plan.gap_concept_id or plan.current_concept_id
            lesson, is_fallback = self.get_lesson_for_student(tag, concept_to_learn, medium_lang)

            lang_label = "unreviewed draft" if (lesson and getattr(lesson, "language", "en") in ("hi", "te")) else "supported"
            fb_label = "English fallback (No lesson in your medium)" if is_fallback else None

            # Note: Do NOT mutate plan.current_stage in GET!
            # Stage transition to BRIDGE_RECHECK occurs when the student clicks 'Continue'.
            return NextStepResult(
                stage=StageEnum.LEARN,
                item_type="lesson",
                item=lesson,
                reason=f"Delivering targeted micro-lesson bridge for '{tag or concept_to_learn}'.",
                bkt_mastery=mastery_state.mastery_estimate,
                bkt_label=mastery_state.mastery_label,
                hypothesis=active_hypothesis,
                is_fallback=is_fallback,
                fallback_label=fb_label,
                language_label=lang_label
            )

        # 3. Bridge Re-Check Stage
        if plan.current_stage == StageEnum.BRIDGE_RECHECK:
            concept_to_test = plan.gap_concept_id or plan.current_concept_id
            qs, is_fallback = self.get_questions_for_student(concept_to_test, medium_lang)
            unseen = [q for q in qs if q.id not in seen_ids]
            chosen_q = unseen[0] if unseen else (qs[0] if qs else None)

            lang_label = "unreviewed draft" if (chosen_q and getattr(chosen_q, "language", "en") in ("hi", "te")) else "supported"
            fb_label = "English fallback (No question in your medium)" if is_fallback else None

            return NextStepResult(
                stage=StageEnum.BRIDGE_RECHECK,
                item_type="question",
                item=chosen_q,
                reason="Bridge re-check: verifying understanding of foundational prerequisite.",
                bkt_mastery=mastery_state.mastery_estimate,
                bkt_label=mastery_state.mastery_label,
                hypothesis=active_hypothesis,
                is_fallback=is_fallback,
                fallback_label=fb_label,
                language_label=lang_label
            )

        # 4. Move Ahead / Fast Learner Stage
        is_original_concept = (mastery_state.concept_id == plan.current_concept_id)
        if plan.current_stage == StageEnum.MOVE_AHEAD or (is_original_concept and mastery_state.mastery_estimate >= 0.85 and mastery_state.consecutive_successes >= 3):
            return NextStepResult(
                stage=StageEnum.MOVE_AHEAD,
                item_type="enrichment",
                item=None,
                reason="High mastery verified with consistent evidence. Advancing ahead to next concept or enrichment.",
                bkt_mastery=mastery_state.mastery_estimate,
                bkt_label=mastery_state.mastery_label,
                hypothesis=active_hypothesis
            )

        # 5. Default Solve / Adaptive Practice Stage
        qs, is_fallback = self.get_questions_for_student(plan.current_concept_id, medium_lang)
        unseen_qs = [q for q in qs if q.id not in seen_ids]
        candidate_qs = unseen_qs if unseen_qs else qs

        if candidate_qs and (mastery_state.mastery_estimate < 0.85 or mastery_state.consecutive_successes < 3):
            # Sort by distance to current mastery estimate to select the most informative item
            sorted_qs = sorted(candidate_qs, key=lambda q: abs(q.difficulty - mastery_state.mastery_estimate))
            chosen_q = sorted_qs[0]
            lang_label = "unreviewed draft" if getattr(chosen_q, "language", "en") in ("hi", "te") else "supported"
            fb_label = "English fallback (No question in your medium)" if is_fallback else None

            return NextStepResult(
                stage=StageEnum.SOLVE,
                item_type="question",
                item=chosen_q,
                reason="Adaptive practice question selected to calibrate to current mastery estimate.",
                bkt_mastery=mastery_state.mastery_estimate,
                bkt_label=mastery_state.mastery_label,
                hypothesis=active_hypothesis,
                is_fallback=is_fallback,
                fallback_label=fb_label,
                language_label=lang_label
            )
        elif qs and mastery_state.mastery_estimate >= 0.85 and mastery_state.consecutive_successes >= 3:
            plan.current_stage = StageEnum.MOVE_AHEAD
            return NextStepResult(
                stage=StageEnum.MOVE_AHEAD,
                item_type="enrichment",
                item=None,
                reason="High mastery verified with consistent evidence. Advancing ahead to next concept or enrichment.",
                bkt_mastery=mastery_state.mastery_estimate,
                bkt_label=mastery_state.mastery_label,
                hypothesis=active_hypothesis
            )

        return NextStepResult(
            stage=StageEnum.SOLVE,
            item_type="question",
            item=None,
            reason="No practice questions available for this concept.",
            bkt_mastery=mastery_state.mastery_estimate,
            bkt_label=mastery_state.mastery_label,
            hypothesis=active_hypothesis
        )

    def get_hint_ladder(self, question_id: str) -> Optional[HintLadder]:
        return self.hints_by_qid.get(question_id)
