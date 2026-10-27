"""
Hypothesis & Evidence Engine.
Rules:
1. Wrong answer opens a hypothesis with heuristic evidence score band 'Low'.
2. Heuristic evidence score = (supporting probes - contradicting probes).
   NOT a probability and NOT derived from BKT.
3. If probes are conflicting (e.g. supporting > 0 and contradicting > 0) or evidence is thin,
   yields 'not sure' and requests more probes. Never a forced gap.
4. When score >= 2 with no contradictions, band is High.
"""

from typing import List, Optional, Tuple
from app.models.learning import Hypothesis, EvidenceItem, EvidenceBand, HypothesisStatus


class HypothesisEngine:
    LABEL = "heuristic evidence score"

    def open_hypothesis(
        self,
        student_id: str,
        suspected_concept_id: str,
        misconception_tag: str
    ) -> Hypothesis:
        """
        After 1 wrong answer, opens hypothesis with score=0, band=Low, status=OPEN.
        No gap declared yet.
        """
        return Hypothesis(
            student_id=student_id,
            suspected_concept_id=suspected_concept_id,
            misconception_tag=misconception_tag,
            evidence_list=[],
            heuristic_score=0,
            evidence_band=EvidenceBand.LOW,
            status=HypothesisStatus.OPEN
        )

    def add_probe_result(
        self,
        hypothesis: Hypothesis,
        probe_question_id: str,
        probe_concept_id: str,
        is_supporting: bool,
        details: str = ""
    ) -> Hypothesis:
        """
        Adds a probe result to the hypothesis and updates heuristic evidence score and band.
        - is_supporting=True: student answered probe incorrectly with targeted misconception -> supports gap.
        - is_supporting=False: student answered probe correctly -> contradicts gap.
        """
        item = EvidenceItem(
            probe_question_id=probe_question_id,
            probe_concept_id=probe_concept_id,
            is_supporting=is_supporting,
            details=details or ("Student confirmed misconception on probe" if is_supporting else "Student answered probe correctly")
        )
        hypothesis.evidence_list.append(item)

        supporting_count = sum(1 for e in hypothesis.evidence_list if e.is_supporting)
        contradicting_count = sum(1 for e in hypothesis.evidence_list if not e.is_supporting)

        score = supporting_count - contradicting_count
        hypothesis.heuristic_score = score

        # Evaluate evidence band and status
        total_probes = len(hypothesis.evidence_list)

        if total_probes == 0:
            hypothesis.evidence_band = EvidenceBand.LOW
            hypothesis.status = HypothesisStatus.OPEN
        elif supporting_count > 0 and contradicting_count > 0:
            # Conflicting evidence: plant test expects "not sure"
            hypothesis.evidence_band = EvidenceBand.NOT_SURE
            hypothesis.status = HypothesisStatus.UNDECIDED
        elif contradicting_count >= 1 and supporting_count == 0:
            # Contradicted by probe
            hypothesis.evidence_band = EvidenceBand.LOW
            hypothesis.status = HypothesisStatus.REJECTED
        elif supporting_count == 1 and contradicting_count == 0:
            # Thin evidence (only 1 probe)
            hypothesis.evidence_band = EvidenceBand.MEDIUM
            hypothesis.status = HypothesisStatus.OPEN
        elif supporting_count >= 2 and contradicting_count == 0:
            # Strong supporting evidence
            hypothesis.evidence_band = EvidenceBand.HIGH
            hypothesis.status = HypothesisStatus.SUPPORTED
        else:
            hypothesis.evidence_band = EvidenceBand.NOT_SURE
            hypothesis.status = HypothesisStatus.UNDECIDED

        return hypothesis
