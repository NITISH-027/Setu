"""
Override learning (v4): teacher overrides refine the STARTING estimate.

What it does: every teacher override carries a target starting level
(mark_cleared/close_gap -> 0.70, reinforce -> 0.30, assign_concept -> 0.20).
When a mastery row is first created for a student on a concept that has logged
overrides, the prior is the override targets averaged with the base prior
(0.20, strength k=4) - a Beta-style shrinkage so one override nudges and many
converge. Rows are labelled "refined from N teacher overrides (hand-set)".

What it is NOT: it is not a fitted model and not deep learning. The targets
and k are hand-set design choices. The live BKT update after the first attempt
is unchanged. This makes the human-in-the-loop visible and honest: the class's
accumulated teacher judgement changes the next child's starting point.
"""

from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.db.models import TeacherOverrideDB

OVERRIDE_TARGETS = {
    "mark_cleared": 0.70,
    "close_gap": 0.70,
    "reinforce": 0.30,
    "assign_concept": 0.20,
}
BASE_PRIOR = 0.20
PRIOR_STRENGTH = 4.0  # pseudo-count of the base prior; higher = slower to move


def refined_prior(db: Session, concept_id: str) -> Optional[Tuple[float, int]]:
    """Return (prior, n_overrides) for a concept with logged overrides, else None."""
    rows = db.query(TeacherOverrideDB).filter(TeacherOverrideDB.concept_id == concept_id).all()
    if not rows:
        return None
    vals = [OVERRIDE_TARGETS.get(r.override_action, 0.20) for r in rows]
    prior = (PRIOR_STRENGTH * BASE_PRIOR + sum(vals)) / (PRIOR_STRENGTH + len(vals))
    return round(prior, 4), len(rows)


def override_stats(db: Session, class_id: Optional[str] = None) -> dict:
    """Per-concept counts for the 'learned from N overrides' counter."""
    q = db.query(TeacherOverrideDB)
    if class_id:
        q = q.filter(TeacherOverrideDB.class_id == class_id)
    rows = q.all()
    per_concept = {}
    for r in rows:
        per_concept.setdefault(r.concept_id, 0)
        per_concept[r.concept_id] += 1
    return {"total_overrides": len(rows), "per_concept": per_concept}
