import sys
import os
import pytest

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.engine.bkt import BKTEngine
from app.models.learning import BKTParameters


def test_bkt_uncalibrated_label_and_update():
    engine = BKTEngine()
    assert engine.LABEL == "uncalibrated, hand-set"

    # Default prior = 0.2
    prior = 0.2
    state = engine.initialize_mastery("stu_1", "c1")
    assert state.mastery_estimate == prior
    assert state.mastery_label == "uncalibrated, hand-set"

    # A correct answer must increase mastery estimate
    post_correct = engine.update(prior, is_correct=True)
    assert post_correct > prior

    # A subsequent incorrect answer must decrease mastery estimate
    post_incorrect = engine.update(post_correct, is_correct=False)
    assert post_incorrect < post_correct
