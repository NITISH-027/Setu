/**
 * Hypothesis & Evidence Engine JavaScript Port.
 * Matches Python implementation in backend/app/engine/hypothesis_engine.py.
 * Heuristic evidence score (supporting - contradicting).
 * Labels: Low, Medium, High, not sure.
 */

export class HypothesisEngine {
  constructor() {
    this.label = "heuristic evidence score";
  }

  openHypothesis(studentId, suspectedConceptId, misconceptionTag) {
    return {
      student_id: studentId,
      suspected_concept_id: suspectedConceptId,
      misconception_tag: misconceptionTag,
      evidence_list: [],
      heuristic_score: 0,
      evidence_band: "Low",
      status: "open"
    };
  }

  addProbeResult(hypothesis, probeQuestionId, probeConceptId, isSupporting, details = "") {
    const updated = { ...hypothesis };
    updated.evidence_list = [...(updated.evidence_list || [])];
    updated.evidence_list.push({
      probe_question_id: probeQuestionId,
      probe_concept_id: probeConceptId,
      is_supporting: isSupporting,
      details: details || (isSupporting ? "Student confirmed misconception on probe" : "Student answered probe correctly")
    });

    const supportingCount = updated.evidence_list.filter(e => e.is_supporting).length;
    const contradictingCount = updated.evidence_list.filter(e => !e.is_supporting).length;

    const score = supportingCount - contradictingCount;
    updated.heuristic_score = score;

    const totalProbes = updated.evidence_list.length;
    if (totalProbes === 0) {
      updated.evidence_band = "Low";
      updated.status = "open";
    } else if (supportingCount > 0 && contradictingCount > 0) {
      updated.evidence_band = "not sure";
      updated.status = "undecided";
    } else if (contradictingCount >= 1 && supportingCount === 0) {
      updated.evidence_band = "Low";
      updated.status = "rejected";
    } else if (supportingCount === 1 && contradictingCount === 0) {
      updated.evidence_band = "Medium";
      updated.status = "open";
    } else if (supportingCount >= 2 && contradictingCount === 0) {
      updated.evidence_band = "High";
      updated.status = "supported";
    } else {
      updated.evidence_band = "not sure";
      updated.status = "undecided";
    }

    return updated;
  }
}
