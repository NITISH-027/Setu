import sys
import os
import pytest

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.simulation.sensitivity_analyzer import SensitivityAnalyzer


def test_sensitivity_report_generation():
    """
    Test requirement:
    'Sensitivity report: which diagnoses and sequencing decisions flip across plausible prior ranges.'
    """
    analyzer = SensitivityAnalyzer()
    report = analyzer.run_prior_sweep(
        stuck_attempts=0,
        consecutive_successes=3,
        prior_min=0.10,
        prior_max=0.90,
        step=0.05
    )

    assert "SENSITIVITY ANALYSIS" in report["disclaimer"]
    assert report["total_points"] > 10

    # Decision transitions (flips) must be identified
    assert len(report["decision_transitions"]) >= 1
    flip = report["decision_transitions"][0]
    assert flip["flip_boundary"] == 0.85
    assert flip["from_action"] == "CONTINUE_PRACTICE"
    assert flip["to_action"] == "MOVE_AHEAD"
    assert flip["triggered_rule"] == "rule_move_ahead_fast_learner"
