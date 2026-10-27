/**
 * Declarative Rule Sequencer JavaScript Port.
 * Matches Python implementation in backend/app/engine/sequencer.py.
 */

export const DEFAULT_RULES = [
  {
    id: "rule_stuck_attempts_flag",
    priority: 100,
    condition_key: "stuck_attempts",
    operator: ">=",
    threshold: 2,
    action: "FLAG_TEACHER_STUCK",
    reason: "Student is stuck after multiple attempts. Teacher assistance flagged."
  },
  {
    id: "rule_bridge_recheck_repeated_fail",
    priority: 110,
    condition_key: "bridge_recheck_fails",
    operator: ">=",
    threshold: 2,
    target_stage: "bridge_recheck",
    action: "FLAG_TEACHER_REPEATED_FAIL",
    reason: "Student failed the bridge check repeatedly. Flagging teacher for 10-minute clinic intervention."
  },
  {
    id: "rule_bridge_recheck_pass",
    priority: 85,
    condition_key: "bridge_recheck_passed",
    operator: "==",
    threshold: true,
    target_stage: "bridge_recheck",
    action: "RETURN_TO_ORIGINAL_TOPIC",
    reason: "Student passed the bridge re-check! Returning to original topic."
  },
  {
    id: "rule_bridge_recheck_fail",
    priority: 80,
    condition_key: "bridge_recheck_passed",
    operator: "==",
    threshold: false,
    target_stage: "bridge_recheck",
    action: "STAY_ON_GAP",
    reason: "Student did not pass the bridge check. Remaining on gap concept for reinforcement."
  },
  {
    id: "rule_probe_conflicting_evidence",
    priority: 75,
    condition_key: "evidence_band",
    operator: "==",
    threshold: "not sure",
    target_stage: "probe",
    action: "REQUEST_MORE_PROBES",
    reason: "Diagnostic probe evidence is thin or conflicting ('not sure'). Gathering additional probes before deciding."
  }
];

export class RuleSequencer {
  constructor(rules = null) {
    this.rules = [...(rules || DEFAULT_RULES)].sort((a, b) => (b.priority || 0) - (a.priority || 0));
  }

  evaluate(state) {
    for (const rule of this.rules) {
      if (rule.target_stage && state.current_stage && state.current_stage !== rule.target_stage) {
        continue;
      }
      const val = state[rule.condition_key];
      if (val === undefined) continue;

      if (this.checkCondition(val, rule.operator, rule.threshold)) {
        return {
          action: rule.action,
          rule_id: rule.id,
          reason: rule.reason
        };
      }
    }

    return {
      action: "CONTINUE_PRACTICE",
      rule_id: "fallback",
      reason: "Adaptive drill sequence continues."
    };
  }

  checkCondition(val, op, threshold) {
    if (val === undefined || val === null) return false;
    if (op === ">=") return Number(val) >= Number(threshold);
    if (op === "<=") return Number(val) <= Number(threshold);
    if (op === ">") return Number(val) > Number(threshold);
    if (op === "<") return Number(val) < Number(threshold);
    if (op === "==") return val === threshold;
    return false;
  }
}
