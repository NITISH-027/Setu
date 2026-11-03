"""
Adaptive Test Engine.
Pure-Python.

Implements the third leg of the Learn - Solve - Test loop: an assessment
session whose item selection adapts to the student's CURRENT per-concept
BKT mastery estimate after every answer.

Honesty rules (consistent with the rest of Setu):
- Mastery estimates remain labelled 'uncalibrated, hand-set'.
- Selection reasons are plain language and persisted as DecisionDB rows.
- Diagnostic probe questions (probe_for_misconception set) are NEVER served
  as test items; they belong to the Solve-loop diagnostic path.
- No hints are served during a test. A test measures; Solve teaches.
- Content coverage limits are reported, not hidden: concepts with too few
  assessment questions are excluded and named in the session payload.
"""

from typing import Dict, List, Optional, Any, Tuple

from app.models.pack import ContentPack
from app.models.content import Question


class AdaptiveTestEngine:
    MIN_ITEMS_PER_CONCEPT = 2
    DEFAULT_LENGTH = 8
    MAX_LENGTH = 20

    def __init__(self, pack: ContentPack):
        self.pack = pack
        # Assessment items only: exclude diagnostic probes.
        self.questions_by_concept: Dict[str, List[Question]] = {}
        for q in pack.questions:
            if q.probe_for_misconception:
                continue
            if not q.options:
                continue
            self.questions_by_concept.setdefault(q.concept, []).append(q)
        for qs in self.questions_by_concept.values():
            qs.sort(key=lambda q: (q.difficulty, q.id))
        # Language-aware index with the same rule as the Solve loop:
        # English students NEVER receive non-English items; non-English
        # students fall back to English (labelled) when no draft exists.
        self.questions_by_concept_lang: Dict[tuple, List[Question]] = {}
        for q in pack.questions:
            if q.probe_for_misconception or not q.options:
                continue
            lang = getattr(q, "language", "en") or "en"
            self.questions_by_concept_lang.setdefault((q.concept, lang), []).append(q)
        for qs in self.questions_by_concept_lang.values():
            qs.sort(key=lambda q: (q.difficulty, q.id))

    def _items_for(self, concept_id: str, medium_language: str):
        """Returns (questions, is_fallback) for concept + medium, Solve-loop rules."""
        lang = medium_language or "en"
        qs = self.questions_by_concept_lang.get((concept_id, lang), [])
        if qs:
            return qs, False
        if lang != "en":
            en_qs = self.questions_by_concept_lang.get((concept_id, "en"), [])
            if en_qs:
                return en_qs, True
        return self.questions_by_concept.get(concept_id, []), False

    def eligible_concepts(self) -> List[str]:
        """Concepts with enough assessment questions to test meaningfully."""
        return sorted(
            cid for cid, qs in self.questions_by_concept.items()
            if len(qs) >= self.MIN_ITEMS_PER_CONCEPT
        )

    def excluded_concepts(self) -> List[str]:
        """Concepts in the pack that cannot be tested (too few items). Reported, not hidden."""
        all_concepts = {c.id for c in self.pack.concepts}
        return sorted(all_concepts - set(self.eligible_concepts()))

    def select_next(
        self,
        concept_ids: List[str],
        mastery_by_concept: Dict[str, float],
        served_by_concept: Dict[str, int],
        last_wrong_concepts: set,
        answered_qids: set,
        medium_language: str = "en"
    ) -> Tuple[Optional[str], Optional[Question], str, bool]:
        """
        Picks the next (concept, question) for the session.

        Concept choice: fewest items served so far (coverage); ties break toward
        concepts where the student's last answer was wrong (uncertain estimate).
        Item choice within the concept: the unseen question whose difficulty is
        closest to the student's current mastery estimate - the same
        'most informative item' rule the Solve loop uses. Answers update
        mastery for later picks; difficulty movement is bounded by the items
        available in the bank, so a harder or easier follow-up is not
        guaranteed.
        """
        candidates = []
        fallback_by_concept: Dict[str, bool] = {}
        for cid in concept_ids:
            items, is_fb = self._items_for(cid, medium_language)
            unseen = [q for q in items if q.id not in answered_qids]
            if unseen:
                candidates.append((cid, unseen))
                fallback_by_concept[cid] = is_fb
        if not candidates:
            return None, None, "All available test questions have been served.", False

        candidates.sort(key=lambda c: (
            served_by_concept.get(c[0], 0),
            0 if c[0] in last_wrong_concepts else 1,
            c[0]
        ))
        cid, unseen = candidates[0]
        mastery = mastery_by_concept.get(cid, 0.2)
        chosen = min(unseen, key=lambda q: (abs(q.difficulty - mastery), q.id))
        reason = (
            f"Adaptive selection: testing '{cid}' (fewest items served); "
            f"question difficulty {chosen.difficulty:.2f} is closest to the current "
            f"mastery estimate {mastery:.2f} (uncalibrated, hand-set)."
        )
        return cid, chosen, reason, fallback_by_concept.get(cid, False)

    def summarize(
        self,
        concept_ids: List[str],
        mastery_before: Dict[str, float],
        mastery_after: Dict[str, float],
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Builds the completion summary. Per-concept served/correct, mastery
        before/after (label stays 'uncalibrated, hand-set'), misconceptions
        encountered, weakest concept, and the recommended next step.
        """
        per_concept = []
        for cid in concept_ids:
            c_items = [it for it in items if it["concept_id"] == cid and it.get("is_correct") is not None]
            served = len(c_items)
            if served == 0:
                continue
            correct = sum(1 for it in c_items if it["is_correct"])
            tags = sorted({it["misconception_tag"] for it in c_items if not it["is_correct"] and it.get("misconception_tag")})
            per_concept.append({
                "concept_id": cid,
                "served": served,
                "correct": correct,
                "mastery_before": round(mastery_before.get(cid, 0.2), 3),
                "mastery_after": round(mastery_after.get(cid, 0.2), 3),
                "misconception_tags": tags
            })

        total_served = sum(c["served"] for c in per_concept)
        total_correct = sum(c["correct"] for c in per_concept)
        weakest = None
        if per_concept:
            weakest = min(per_concept, key=lambda c: (c["mastery_after"], c["correct"] / c["served"]))
        all_tags = sorted({t for c in per_concept for t in c["misconception_tags"]})

        concept_name = None
        if weakest:
            concept = self.pack.get_concept(weakest["concept_id"])
            concept_name = concept.name if concept else weakest["concept_id"]

        return {
            "total_served": total_served,
            "total_correct": total_correct,
            "per_concept": per_concept,
            "weakest_concept_id": weakest["concept_id"] if weakest else None,
            "weakest_concept_name": concept_name,
            "misconception_tags": all_tags,
            "mastery_label": "uncalibrated, hand-set",
            "recommendation": (
                f"Recommended next step: focused practice on '{concept_name}'. "
                "Setu will diagnose any prerequisite gap there with probes before teaching."
                if weakest else "No assessable items were served."
            )
        }
