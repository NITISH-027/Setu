import sys
import os
import json
import pytest

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.models.pack import ContentPack
from app.simulation.learner_simulator import SimulationHarness


@pytest.fixture
def pack():
    pack_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packs", "cbse_math_pack.json"))
    with open(pack_path, "r", encoding="utf-8") as f:
        return ContentPack.model_validate(json.load(f))


def test_simulation_gap_recovery_and_seeds(pack):
    """
    Test requirement:
    'Simulation harness: synthetic learners with known parameters and planted misconceptions.
     Report how often the engine finds the planted gap and list the failure cases, with seeds.'
    """
    harness = SimulationHarness(pack)

    # Run simulation with 15 synthetic learners with planted Class 6 subtraction gap
    sim_report = harness.run_simulation(
        num_students=15,
        base_seed=100,
        planted_gap="c6_math_integers_add_sub",
        planted_misconception="tag_class6_integer_subtraction"
    )

    # 1. Output clearly labelled synthetic
    assert "SYNTHETIC DATA ONLY" in sim_report["disclaimer"]

    # 2. Tracks total runs and recoveries
    assert sim_report["total_runs"] == 15
    assert sim_report["successful_recoveries"] > 0
    assert sim_report["recovery_rate"] > 0.5  # High recovery rate for planted misconception

    # 3. Failures are reported with deterministic seeds
    assert "failures" in sim_report
    for failure in sim_report["failures"]:
        assert "seed" in failure
        assert "planted_gap" in failure
        assert "identified_gap" in failure
