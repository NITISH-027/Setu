"""
Generates deterministic golden test vectors from the pure-Python Setu engine.
These vectors are asserted against the client-side JavaScript engine port
in frontend/test_parity.js to guarantee 100% mathematical and logic parity.
"""

import sys
import os
import json
from datetime import datetime

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.models.learning import BKTParameters, MasteryState, Hypothesis, EvidenceBand
from app.engine.bkt import BKTEngine
from app.engine.scheduler import SpacedRepetitionScheduler
from app.engine.hypothesis_engine import HypothesisEngine
from app.engine.sequencer import RuleSequencer


def generate():
    vectors = {}

    # 1. BKT Update Vectors
    bkt = BKTEngine(BKTParameters(prior=0.2, learn=0.15, guess=0.2, slip=0.1))
    
    # Sequence of 6 attempts: [1, 0, 1, 1, 1, 0]
    bkt_sequence = []
    current_m = 0.2
    for step_idx, is_corr in enumerate([True, False, True, True, True, False]):
        next_m = bkt.update(current_m, is_corr)
        bkt_sequence.append({
            "step": step_idx,
            "input_mastery": current_m,
            "is_correct": is_corr,
            "output_mastery": next_m
        })
        current_m = next_m

    vectors["bkt_sequence"] = bkt_sequence

    # 2. SM-2 Spaced Repetition Vectors
    scheduler = SpacedRepetitionScheduler()
    base_state = MasteryState(
        student_id="test_vec",
        concept_id="c8_leq",
        interval_days=1.0,
        ease_factor=2.5,
        consecutive_successes=0
    )
    
    sm2_sequence = []
    fixed_time = datetime(2026, 1, 1, 12, 0, 0)
    for q in [4, 5, 5, 2, 4]:
        base_state = scheduler.schedule_next_review(base_state, quality=q, current_time=fixed_time)
        sm2_sequence.append({
            "quality": q,
            "interval_days": base_state.interval_days,
            "ease_factor": base_state.ease_factor,
            "consecutive_successes": base_state.consecutive_successes
        })

    vectors["sm2_sequence"] = sm2_sequence

    # 3. Hypothesis & Evidence Band Vectors
    hyp_engine = HypothesisEngine()
    hyp = hyp_engine.open_hypothesis(
        student_id="test_vec",
        suspected_concept_id="c7_math_integers_add_sub",
        misconception_tag="tag_sign_error_on_transposition"
    )

    hyp_sequence = []
    # Probe 1: supporting
    hyp = hyp_engine.add_probe_result(hyp, "q_probe_01", "c7_math_integers_add_sub", is_supporting=True)
    hyp_sequence.append({
        "step": 1,
        "heuristic_score": hyp.heuristic_score,
        "evidence_band": hyp.evidence_band.value,
        "status": hyp.status.value
    })

    # Probe 2: supporting (now 2 supporting -> High / supported)
    hyp = hyp_engine.add_probe_result(hyp, "q_probe_02", "c7_math_integers_add_sub", is_supporting=True)
    hyp_sequence.append({
        "step": 2,
        "heuristic_score": hyp.heuristic_score,
        "evidence_band": hyp.evidence_band.value,
        "status": hyp.status.value
    })

    # Probe 3: contradicting (conflicting -> not sure / undecided)
    hyp = hyp_engine.add_probe_result(hyp, "q_probe_03", "c7_math_integers_add_sub", is_supporting=False)
    hyp_sequence.append({
        "step": 3,
        "heuristic_score": hyp.heuristic_score,
        "evidence_band": hyp.evidence_band.value,
        "status": hyp.status.value
    })

    vectors["hypothesis_sequence"] = hyp_sequence

    # 4. Rule Sequencer Vectors
    sequencer = RuleSequencer()
    rules_cases = [
        {"input": {"stuck_attempts": 2}, "expected_action": "FLAG_TEACHER_STUCK"},
        {"input": {"bridge_recheck_fails": 2, "current_stage": "bridge_recheck"}, "expected_action": "FLAG_TEACHER_REPEATED_FAIL"},
        {"input": {"bridge_recheck_passed": True, "current_stage": "bridge_recheck"}, "expected_action": "RETURN_TO_ORIGINAL_TOPIC"},
        {"input": {"bridge_recheck_passed": False, "current_stage": "bridge_recheck"}, "expected_action": "STAY_ON_GAP"},
        {"input": {"evidence_band": "not sure", "current_stage": "probe"}, "expected_action": "REQUEST_MORE_PROBES"}
    ]

    sequencer_results = []
    for c in rules_cases:
        dec = sequencer.evaluate(c["input"])
        sequencer_results.append({
            "input": c["input"],
            "action": dec.action,
            "rule_id": dec.rule_id,
            "reason": dec.reason
        })

    vectors["sequencer_results"] = sequencer_results

    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packs", "golden_test_vectors.json"))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(vectors, f, indent=2)

    print(f"Golden test vectors generated at {out_path}")


if __name__ == "__main__":
    generate()
