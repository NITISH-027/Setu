"""
Sensitivity Analysis Module.
Examines which diagnoses and sequencing decisions flip across plausible prior ranges.
NOTICE: Simulation and sensitivity profiling only. Not an empirical efficacy claim.
"""

from typing import Dict, List, Any, Optional
from app.engine.sequencer import RuleSequencer


class SensitivityAnalyzer:
    DISCLAIMER = "SENSITIVITY ANALYSIS: Evaluates parameter flip boundaries across synthetic prior ranges."

    def __init__(self, sequencer: Optional[RuleSequencer] = None):
        self.sequencer = sequencer or RuleSequencer()

    def run_prior_sweep(
        self,
        stuck_attempts: int = 0,
        consecutive_successes: int = 3,
        prior_min: float = 0.05,
        prior_max: float = 0.95,
        step: float = 0.05
    ) -> Dict[str, Any]:
        """
        Sweeps mastery estimates to determine decision boundary flips.
        """
        points = []
        priors = [round(prior_min + i * step, 2) for i in range(int((prior_max - prior_min) / step) + 1)]

        transitions = []
        prev_action = None

        for p in priors:
            state = {
                "mastery_estimate": p,
                "stuck_attempts": stuck_attempts,
                "consecutive_successes": consecutive_successes,
                "has_open_hypothesis": False,
                "gap_supported": False
            }
            dec = self.sequencer.evaluate(state)
            points.append({
                "prior_value": p,
                "decision_action": dec.action,
                "rule_id": dec.rule_id
            })

            if prev_action is not None and dec.action != prev_action:
                transitions.append({
                    "flip_boundary": p,
                    "from_action": prev_action,
                    "to_action": dec.action,
                    "triggered_rule": dec.rule_id
                })
            prev_action = dec.action

        return {
            "disclaimer": self.DISCLAIMER,
            "total_points": len(points),
            "decision_transitions": transitions,
            "sweep_points": points
        }
