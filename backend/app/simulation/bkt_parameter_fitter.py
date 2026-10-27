"""
BKT Parameter Fitting Module.
Fits BKT parameters (prior, learn, guess, slip) from synthetic student attempt sequences
using maximum likelihood estimation (log-likelihood optimization via scipy.optimize or grid search).
NOTICE: Demonstrates that the algorithmic parameter recovery path functions.
Real calibration requires empirical classroom datasets.
"""

import math
from typing import List, Dict, Tuple, Any, Optional
import numpy as np
from scipy.optimize import minimize
from app.models.learning import BKTParameters


class BKTParameterFitter:
    DISCLAIMER = (
        "PARAMETER FITTING HARNESS: Recovers parameters from synthetic sequences to demonstrate "
        "algorithmic path feasibility. Real calibration requires empirical classroom datasets."
    )

    @staticmethod
    def compute_log_likelihood(
        sequences: List[List[int]],
        prior: float,
        learn: float,
        guess: float,
        slip: float
    ) -> float:
        """
        Computes negative log-likelihood of observation sequences under given BKT parameters.
        """
        # Ensure parameters are within valid probabilities
        prior = max(0.01, min(0.99, prior))
        learn = max(0.01, min(0.99, learn))
        guess = max(0.01, min(0.50, guess))
        slip = max(0.01, min(0.50, slip))

        total_log_likelihood = 0.0

        for seq in sequences:
            p_l = prior
            for obs in seq:
                # Probability of observation: P(obs) = P(L)*P(obs|L) + (1-P(L))*P(obs|~L)
                if obs == 1:
                    p_obs_given_l = 1.0 - slip
                    p_obs_given_not_l = guess
                else:
                    p_obs_given_l = slip
                    p_obs_given_not_l = 1.0 - guess

                p_obs = p_l * p_obs_given_l + (1.0 - p_l) * p_obs_given_not_l
                p_obs = max(1e-9, p_obs)
                total_log_likelihood += math.log(p_obs)

                # Posterior update
                num = p_l * p_obs_given_l
                posterior = num / p_obs if p_obs > 0 else p_l

                # Transition
                p_l = posterior + (1.0 - posterior) * learn

        return -total_log_likelihood  # Negative for minimization

    def fit_parameters(
        self,
        observation_sequences: List[List[int]],
        initial_guess: Optional[Tuple[float, float, float, float]] = None
    ) -> Dict[str, Any]:
        """
        Fits BKT parameters to minimize negative log-likelihood.
        """
        x0 = initial_guess or (0.2, 0.15, 0.2, 0.1)
        bounds = [(0.01, 0.99), (0.01, 0.60), (0.01, 0.45), (0.01, 0.45)]

        def loss(params):
            p, l, g, s = params
            return self.compute_log_likelihood(observation_sequences, p, l, g, s)

        res = minimize(
            loss,
            x0,
            method="L-BFGS-B",
            bounds=bounds,
            options={"maxiter": 100}
        )

        fitted_prior, fitted_learn, fitted_guess, fitted_slip = res.x
        return {
            "disclaimer": self.DISCLAIMER,
            "fitted_parameters": {
                "prior": round(float(fitted_prior), 3),
                "learn": round(float(fitted_learn), 3),
                "guess": round(float(fitted_guess), 3),
                "slip": round(float(fitted_slip), 3)
            },
            "loss": round(float(res.fun), 3),
            "converged": bool(res.success)
        }

    @staticmethod
    def generate_synthetic_sequences(
        true_params: BKTParameters,
        num_students: int = 40,
        seq_length: int = 15,
        seed: int = 101
    ) -> List[List[int]]:
        """
        Generates synthetic sequences using known true parameters.
        """
        import random
        rng = random.Random(seed)
        sequences = []

        for _ in range(num_students):
            seq = []
            has_mastered = (rng.random() < true_params.prior)
            for _ in range(seq_length):
                if has_mastered:
                    obs = 0 if (rng.random() < true_params.slip) else 1
                else:
                    obs = 1 if (rng.random() < true_params.guess) else 0

                seq.append(obs)

                # Learning transition
                if not has_mastered and (rng.random() < true_params.learn):
                    has_mastered = True

            sequences.append(seq)
        return sequences
