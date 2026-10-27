"""
Graph Tracer for Setu Prerequisite Discovery.
Traverses the concept graph backwards along prerequisite edges to identify
the earliest supported gap within the tested graph.
NOTICE: Traces indicate likely prerequisite gaps inside the authored graph, NOT proven causes.
"""

from typing import List, Dict, Set, Optional, Tuple, Any
from app.models.pack import ContentPack
from app.models.learning import Hypothesis, HypothesisStatus, EvidenceBand


class TraceResult:
    def __init__(
        self,
        found_gap: bool,
        target_concept_id: str,
        earliest_gap_concept_id: Optional[str],
        trace_path: List[str],
        evidence_summary: str,
        disclaimer: str = "Earliest gap identified inside the authored graph. This is a working hypothesis, not a proven cause."
    ):
        self.found_gap = found_gap
        self.target_concept_id = target_concept_id
        self.earliest_gap_concept_id = earliest_gap_concept_id
        self.trace_path = trace_path
        self.evidence_summary = evidence_summary
        self.disclaimer = disclaimer

    def to_dict(self) -> Dict[str, Any]:
        return {
            "found_gap": self.found_gap,
            "target_concept_id": self.target_concept_id,
            "earliest_gap_concept_id": self.earliest_gap_concept_id,
            "trace_path": self.trace_path,
            "evidence_summary": self.evidence_summary,
            "disclaimer": self.disclaimer
        }


class GraphTracer:
    def __init__(self, pack: ContentPack):
        self.pack = pack
        self.concepts_by_id = {c.id: c for c in pack.concepts}
        # prerequisite map: concept -> list of prerequisites (depends_on)
        self.prereqs: Dict[str, List[str]] = {}
        for edge in pack.prerequisite_edges:
            self.prereqs.setdefault(edge.concept, []).append(edge.depends_on)

    def trace_earliest_gap(
        self,
        starting_concept_id: str,
        active_hypotheses: List[Hypothesis]
    ) -> TraceResult:
        """
        Walks backwards along prerequisite edges from starting_concept_id to find
        the earliest concept with supported probe evidence.
        """
        # Build map of concept_id -> supported status
        supported_concepts: Set[str] = set()
        hyp_details: Dict[str, str] = {}

        for h in active_hypotheses:
            # Check if hypothesis has supporting evidence or High/Medium band
            if h.status == HypothesisStatus.SUPPORTED or h.heuristic_score > 0:
                supported_concepts.add(h.suspected_concept_id)
                hyp_details[h.suspected_concept_id] = (
                    f"Misconception '{h.misconception_tag}', score={h.heuristic_score}, band={h.evidence_band.value}"
                )
            # Check evidence items directly
            for ev in h.evidence_list:
                if ev.is_supporting:
                    supported_concepts.add(ev.probe_concept_id)

        # BFS / DFS backwards from starting concept
        trace_path = [starting_concept_id]
        earliest_gap = None

        queue = [(starting_concept_id, [starting_concept_id])]
        visited = {starting_concept_id}

        deepest_level = -1
        candidate_gap = None
        best_path = [starting_concept_id]

        while queue:
            curr, path = queue.pop(0)

            # Check if this node is supported as a gap
            if curr in supported_concepts:
                curr_concept = self.concepts_by_id.get(curr)
                class_lvl = curr_concept.class_level if curr_concept else 8
                # Deeper in lower classes has priority
                level_rank = 10 - class_lvl  # Class 6 gives 4, Class 7 gives 3, Class 8 gives 2
                if level_rank > deepest_level:
                    deepest_level = level_rank
                    candidate_gap = curr
                    best_path = list(path)

            for prereq in self.prereqs.get(curr, []):
                if prereq not in visited:
                    visited.add(prereq)
                    queue.append((prereq, path + [prereq]))

        if candidate_gap:
            return TraceResult(
                found_gap=True,
                target_concept_id=starting_concept_id,
                earliest_gap_concept_id=candidate_gap,
                trace_path=best_path,
                evidence_summary=hyp_details.get(candidate_gap, "Supported by prerequisite diagnostic probes")
            )
        else:
            return TraceResult(
                found_gap=False,
                target_concept_id=starting_concept_id,
                earliest_gap_concept_id=None,
                trace_path=[starting_concept_id],
                evidence_summary="No prerequisite gap supported by probe evidence"
            )
