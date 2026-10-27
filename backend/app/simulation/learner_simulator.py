"""
Synthetic Learner Simulation Harness.
Simulates synthetic student learners with known parameters and planted misconceptions.
Reports gap identification recovery rates, deterministic seeds, and failure cases.
NOTICE: All outputs are labelled 'SIMULATION HARNESS - SYNTHETIC DATA ONLY'.
None of this represents a verified learning outcome or real classroom calibration.
"""

import random
from typing import Dict, List, Optional, Any, Tuple
from app.models.pack import ContentPack
from app.models.student import Student
from app.models.learning import Plan, MasteryState, Attempt, StageEnum, HypothesisStatus
from app.engine.adaptive_engine import AdaptiveEngine


class SyntheticLearnerProfile:
    def __init__(
        self,
        student_id: str,
        class_id: str = "8-A",
        planted_gap_concept: Optional[str] = None,
        planted_misconception: Optional[str] = None,
        true_mastery: float = 0.7,
        gap_mastery: float = 0.15,
        guess_prob: float = 0.2,
        slip_prob: float = 0.1
    ):
        self.student_id = student_id
        self.class_id = class_id
        self.planted_gap_concept = planted_gap_concept
        self.planted_misconception = planted_misconception
        self.true_mastery = true_mastery
        self.gap_mastery = gap_mastery
        self.guess_prob = guess_prob
        self.slip_prob = slip_prob

    def simulate_answer(self, question: Any, rng: random.Random) -> Tuple[str, bool, Optional[str]]:
        # If student has a planted misconception and question has an option tagged with it:
        if self.planted_misconception:
            for opt in question.options:
                if not opt.is_correct and opt.misconception_tag == self.planted_misconception:
                    # High probability of picking the planted misconception option
                    if rng.random() > self.slip_prob:
                        return opt.id, False, opt.misconception_tag

        # Otherwise answer based on concept mastery
        concept_mastery = (
            self.gap_mastery
            if (self.planted_gap_concept and question.concept == self.planted_gap_concept)
            else self.true_mastery
        )

        knows_answer = (rng.random() < concept_mastery)
        if knows_answer:
            is_correct = (rng.random() > self.slip_prob)
        else:
            is_correct = (rng.random() < self.guess_prob)

        if is_correct:
            correct_opt = next(o for o in question.options if o.is_correct)
            return correct_opt.id, True, None
        else:
            wrong_opts = [o for o in question.options if not o.is_correct]
            chosen = rng.choice(wrong_opts)
            return chosen.id, False, chosen.misconception_tag


class SimulationRunResult:
    def __init__(
        self,
        seed: int,
        student_id: str,
        planted_gap: Optional[str],
        identified_gap: Optional[str],
        success: bool,
        steps_taken: int
    ):
        self.seed = seed
        self.student_id = student_id
        self.planted_gap = planted_gap
        self.identified_gap = identified_gap
        self.success = success
        self.steps_taken = steps_taken


class SimulationHarness:
    DISCLAIMER = "SIMULATION HARNESS - SYNTHETIC DATA ONLY. Not an empirical learning outcome."

    def __init__(self, pack: ContentPack):
        self.pack = pack

    def run_simulation(
        self,
        num_students: int = 20,
        base_seed: int = 42,
        planted_gap: str = "c6_math_integers_add_sub",
        planted_misconception: str = "tag_class6_integer_subtraction"
    ) -> Dict[str, Any]:
        results: List[SimulationRunResult] = []
        failures: List[Dict[str, Any]] = []

        for i in range(num_students):
            seed = base_seed + i
            rng = random.Random(seed)

            learner = SyntheticLearnerProfile(
                student_id=f"syn_stu_{seed}",
                class_id="8-A",
                planted_gap_concept=planted_gap,
                planted_misconception=planted_misconception
            )

            engine = AdaptiveEngine(self.pack)
            student = Student(pseudonymous_id=learner.student_id, class_id=learner.class_id, pin_hash="h")
            plan = Plan(student_id=student.pseudonymous_id, class_id=student.class_id, current_concept_id="c8_math_linear_eq_one_var")
            mastery = MasteryState(student_id=student.pseudonymous_id, concept_id="c8_math_linear_eq_one_var")
            hyp = None

            identified_gap = None
            steps = 0

            # Run up to 6 adaptive interactions
            for step_idx in range(6):
                steps += 1
                next_step = engine.get_next_step(student, plan, mastery, hyp)

                if next_step.item_type != "question" or not next_step.item:
                    # Micro-lesson or flag reached
                    if plan.gap_concept_id:
                        identified_gap = plan.gap_concept_id
                    break

                q = next_step.item
                opt_id, is_correct, tag = learner.simulate_answer(q, rng)

                attempt = Attempt(
                    student_id=student.pseudonymous_id,
                    question_id=q.id,
                    concept_id=q.concept,
                    selected_option_id=opt_id,
                    is_correct=is_correct,
                    misconception_tag=tag
                )

                plan, mastery, hyp, dec = engine.process_attempt(student, plan, attempt, mastery, hyp)
                if plan.gap_concept_id:
                    identified_gap = plan.gap_concept_id

            is_success = (identified_gap == planted_gap)
            res = SimulationRunResult(
                seed=seed,
                student_id=learner.student_id,
                planted_gap=planted_gap,
                identified_gap=identified_gap,
                success=is_success,
                steps_taken=steps
            )
            results.append(res)
            if not is_success:
                failures.append({
                    "seed": seed,
                    "student_id": learner.student_id,
                    "planted_gap": planted_gap,
                    "identified_gap": identified_gap,
                    "steps_taken": steps
                })

        success_count = sum(1 for r in results if r.success)
        recovery_rate = round(success_count / num_students, 3)

        return {
            "disclaimer": self.DISCLAIMER,
            "total_runs": num_students,
            "successful_recoveries": success_count,
            "recovery_rate": recovery_rate,
            "planted_gap": planted_gap,
            "planted_misconception": planted_misconception,
            "failures_count": len(failures),
            "failures": failures
        }
