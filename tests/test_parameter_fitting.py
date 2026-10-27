import sys
import os
import pytest

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.models.learning import BKTParameters
from app.simulation.bkt_parameter_fitter import BKTParameterFitter


def test_bkt_parameter_recovery():
    """
    Test requirement:
    'Parameter fitting: a module that fits BKT parameters from logs,
     verified by recovering known parameters from synthetic data within a stated tolerance.
     This shows the path works. Real calibration still needs real classroom data.'
    """
    fitter = BKTParameterFitter()

    # Known true synthetic parameters
    true_params = BKTParameters(
        prior=0.30,
        learn=0.15,
        guess=0.20,
        slip=0.10
    )

    # Generate synthetic response sequences using known parameters
    sequences = fitter.generate_synthetic_sequences(
        true_params=true_params,
        num_students=60,
        seq_length=20,
        seed=42
    )

    # Recover parameters using maximum likelihood
    fit_result = fitter.fit_parameters(sequences, initial_guess=(0.25, 0.12, 0.18, 0.12))

    # Verify honest disclaimer is present
    assert "Real calibration requires empirical classroom datasets" in fit_result["disclaimer"]

    recovered = fit_result["fitted_parameters"]
    # Verify recovered values are within tolerance (+/- 0.15 on finite synthetic data)
    tolerance = 0.15
    assert abs(recovered["prior"] - true_params.prior) <= tolerance, f"Prior recovery out of tolerance: {recovered['prior']}"
    assert abs(recovered["learn"] - true_params.learn) <= tolerance, f"Learn recovery out of tolerance: {recovered['learn']}"
    assert abs(recovered["guess"] - true_params.guess) <= tolerance, f"Guess recovery out of tolerance: {recovered['guess']}"
    assert abs(recovered["slip"] - true_params.slip) <= tolerance, f"Slip recovery out of tolerance: {recovered['slip']}"
