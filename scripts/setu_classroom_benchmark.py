#!/usr/bin/env python3
"""
SETU v5 - Simulated-classroom benchmark: steps-to-correct-gap, Setu vs fixed-order quiz.
=====================================================================================
WHAT THIS DOES:
  Simulates N synthetic students, each with a KNOWN planted prerequisite gap and
  a planted misconception, and measures how many questions each system needs to
  find the correct gap:

    ARM A (Setu):  the real AdaptiveEngine - wrong answer -> hypothesis ->
                   diagnostic probe -> gap identified (plan.gap_concept_id).
    ARM B (fixed): the same students take a fixed-order quiz (the pack's authored
                   question sequence, no adaptivity). The gap counts as found
                   when the student answers a question on the planted gap
                   concept incorrectly (i.e. the quiz happens to reach and
                   expose the gap).

  Reports mean, median, standard deviation and p10/p90 for both arms, plus the
  share of students whose gap is found at all within the step cap.

HONESTY CONTRACT (do not remove):
  - Every student is SIMULATED from hand-set parameters (true mastery 0.70,
    gap mastery 0.15, guess 0.20, slip 0.10). These are modelling choices,
    not measurements of real children.
  - This measures gap-DISCOVERY speed inside Setu's own authored graph. It
    says nothing about learning gains, real classroom accuracy, or Tamil Nadu.
  - The synthetic learner is written to cooperate with the hypothesis mechanism
    (its wrong answers carry the planted tag), so treat ARM A's advantage as
    "the mechanism works end-to-end", not as a measured real-world effect size.

Run:      python setu_classroom_benchmark.py [--students 200] [--seed 42]
Quick:    python setu_classroom_benchmark.py --students 20   (for tests)
Requires: the repo's backend/ on the path (this script adds it).
"""

import argparse
import json
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.models.pack import ContentPack
from app.models.student import Student
from app.models.learning import Plan, MasteryState, Attempt
from app.engine.adaptive_engine import AdaptiveEngine
from app.simulation.learner_simulator import SyntheticLearnerProfile

LABEL = "SIMULATED STUDENTS - NOT REAL CHILDREN. Hand-set parameters, gap-discovery speed only."
STEP_CAP_SETU = 12


def load_pack():
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packs", "cbse_math_pack.json"))
    with open(path, "r", encoding="utf-8") as f:
        import json as _json
        return ContentPack.model_validate(_json.load(f))


def percentile(sorted_vals, p):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = k - lo
    return round(sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac, 2)


def run_setu_arm(pack, learner, rng, start_concept):
    """Real engine. Returns (steps, found)."""
    engine = AdaptiveEngine(pack)
    student = Student(pseudonymous_id=learner.student_id, class_id=learner.class_id, pin_hash="h")
    plan = Plan(student_id=student.pseudonymous_id, class_id=student.class_id, current_concept_id=start_concept)
    mastery = MasteryState(student_id=student.pseudonymous_id, concept_id=start_concept)
    hyp = None
    identified = None
    steps = 0
    for _ in range(STEP_CAP_SETU):
        steps += 1
        nxt = engine.get_next_step(student, plan, mastery, hyp)
        if nxt.item_type != "question" or not nxt.item:
            if plan.gap_concept_id:
                identified = plan.gap_concept_id
            break
        q = nxt.item
        opt_id, is_correct, tag = learner.simulate_answer(q, rng)
        attempt = Attempt(
            student_id=student.pseudonymous_id, question_id=q.id, concept_id=q.concept,
            selected_option_id=opt_id, is_correct=is_correct, misconception_tag=tag,
        )
        plan, mastery, hyp, _ = engine.process_attempt(student, plan, attempt, mastery, hyp)
        if plan.gap_concept_id:
            identified = plan.gap_concept_id
    return steps, (identified == learner.planted_gap_concept)


def run_fixed_arm(pack, learner, rng, quiz):
    """Fixed-order quiz. Gap found when a gap-concept question is answered wrong."""
    for i, q in enumerate(quiz, start=1):
        opt_id, is_correct, tag = learner.simulate_answer(q, rng)
        if q.concept == learner.planted_gap_concept and not is_correct:
            return i, True
    return len(quiz), False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--students", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--start", default="c8_math_linear_eq_one_var",
                    help="Concept the simulated Class 8 student starts on.")
    ap.add_argument("--gap", default="c6_math_integers_add_sub")
    ap.add_argument("--misconception", default="tag_class6_integer_subtraction")
    args = ap.parse_args()

    pack = load_pack()

    if pack.get_concept(args.start) is None:
        print(f"Start concept {args.start} not in pack."); sys.exit(1)
    # The planted misconception must be exercisable from the start concept:
    # at least one served (non-probe) question there must carry the tag on a
    # wrong option, or the simulation is testing a path the engine never sees.
    exercisable = any(
        q.concept == args.start and not q.probe_for_misconception and any(
            (not o.is_correct) and o.misconception_tag == args.misconception for o in q.options
        ) for q in pack.questions
    )
    if not exercisable:
        print(f"No question on {args.start} carries wrong-option tag {args.misconception}; "
              "choose a start concept whose questions can expose the planted misconception.")
        sys.exit(1)
    start_concept = args.start

    # Fixed-order quiz: a realistic "quiz what we taught, in order" baseline -
    # current-class questions first, prerequisites only at the end, in the
    # pack's file order within each class level. No adaptivity.
    level = {c.id: c.class_level for c in pack.concepts}
    en_questions = [q for q in pack.questions if q.language == "en"]
    quiz = sorted(en_questions, key=lambda q: (-level.get(q.concept, 8), en_questions.index(q)))

    setu_steps, fixed_steps = [], []
    setu_found = fixed_found = 0

    for i in range(args.students):
        seed = args.seed + i
        learner = SyntheticLearnerProfile(
            student_id=f"syn_{seed}", planted_gap_concept=args.gap,
            planted_misconception=args.misconception,
        )
        s_steps, s_ok = run_setu_arm(pack, learner, random.Random(seed), start_concept)
        f_steps, f_ok = run_fixed_arm(pack, learner, random.Random(seed), quiz)
        setu_steps.append(s_steps); fixed_steps.append(f_steps)
        setu_found += 1 if s_ok else 0
        fixed_found += 1 if f_ok else 0

    def stats(vals, found, n):
        sv = sorted(vals)
        return {
            "mean": round(statistics.mean(vals), 2),
            "median": statistics.median(vals),
            "stdev": round(statistics.stdev(vals), 2) if len(vals) > 1 else 0.0,
            "p10": percentile(sv, 0.10),
            "p90": percentile(sv, 0.90),
            "gap_found_rate": round(found / n, 3),
        }

    report = {
        "label": LABEL,
        "students": args.students,
        "base_seed": args.seed,
        "planted_gap": args.gap,
        "planted_misconception": args.misconception,
        "start_concept": start_concept,
        "fixed_quiz_length": len(quiz),
        "setu_step_cap": STEP_CAP_SETU,
        "arm_setu_adaptive": stats(setu_steps, setu_found, args.students),
        "arm_fixed_order_quiz": stats(fixed_steps, fixed_found, args.students),
        "parameters": {"true_mastery": 0.7, "gap_mastery": 0.15, "guess": 0.2, "slip": 0.1},
    }
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
