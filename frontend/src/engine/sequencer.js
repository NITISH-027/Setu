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
  },
  {
    id: "rule_supported_gap_learn",
    priority: 70,
    condition_key: "gap_supported",
    operator: "==",
    threshold: true,
    action: "START_MICRO_LESSON",
    reason: "Prerequisite diagnostic probes supported a foundational gap. Delivering targeted micro-lesson."
  },
  {
    id: "rule_open_hypothesis_probe",
    priority: 60,
    condition_key: "has_open_hypothesis",
    operator: "==",
    threshold: true,
    action: "ADMINISTER_PROBE",
    reason: "Wrong answer opened a gap hypothesis. Administering prerequisite probe to test hypothesis."
  },
  {
    id: "rule_move_ahead_fast_learner",
    priority: 50,
    condition_key: "mastery_estimate",
    operator: ">=",
    threshold: 0.85,
    extra_condition_key: "consecutive_successes",
    extra_operator: ">=",
    extra_threshold: 3,
    action: "MOVE_AHEAD",
    reason: "Student demonstrates high mastery with consistent evidence. Skipping drill to advance ahead."
  },
  {
    id: "rule_default_solve",
    priority: 10,
    condition_key: "always_true",
    operator: "==",
    threshold: true,
    action: "CONTINUE_PRACTICE",
    reason: "Continuing practice questions calibrated to current mastery level."
  }
];

export class RuleSequencer {
  constructor(rules = null) {
    this.rules = [...(rules || DEFAULT_RULES)].sort((a, b) => (b.priority || 0) - (a.priority || 0));
  }

  evaluate(state) {
    const stateWithAlwaysTrue = { ...state, always_true: true };

    for (const rule of this.rules) {
      if (rule.target_stage && state.current_stage && state.current_stage !== rule.target_stage) {
        continue;
      }
      const val = stateWithAlwaysTrue[rule.condition_key];
      if (val === undefined) continue;

      let matches = this.checkCondition(val, rule.operator, rule.threshold);

      if (matches && rule.extra_condition_key) {
        const extraVal = stateWithAlwaysTrue[rule.extra_condition_key];
        matches = this.checkCondition(extraVal, rule.extra_operator, rule.extra_threshold);
      }

      if (matches) {
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
    if (op === "!=") return val !== threshold;
    return false;
  }
}
