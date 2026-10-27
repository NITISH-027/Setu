"""
Declarative Data-Driven Rule Sequencer.
Rules are stored as data structures (JSON / dict), not hard-coded in logic.
Every decision returns a plain-language reason ('why this question').
A test proves that changing rules in data alters execution behaviour without code modifications.
"""

from typing import Dict, Any, List, Optional
from app.models.learning import StageEnum


DEFAULT_RULES: List[Dict[str, Any]] = [
    {
        "id": "rule_stuck_attempts_flag",
        "priority": 100,
        "condition_key": "stuck_attempts",
        "operator": ">=",
        "threshold": 2,
        "action": "FLAG_TEACHER_STUCK",
        "reason": "Student is stuck after multiple attempts. Teacher assistance flagged."
    },
    {
        "id": "rule_bridge_recheck_repeated_fail",
        "priority": 110,
        "condition_key": "bridge_recheck_fails",
        "operator": ">=",
        "threshold": 2,
        "target_stage": StageEnum.BRIDGE_RECHECK,
        "action": "FLAG_TEACHER_REPEATED_FAIL",
        "reason": "Student failed the bridge check repeatedly. Flagging teacher for 10-minute clinic intervention."
    },
    {
        "id": "rule_bridge_recheck_pass",
        "priority": 85,
        "condition_key": "bridge_recheck_passed",
        "operator": "==",
        "threshold": True,
        "target_stage": StageEnum.BRIDGE_RECHECK,
        "action": "RETURN_TO_ORIGINAL_TOPIC",
        "reason": "Student passed the bridge re-check! Returning to original topic."
    },
    {
        "id": "rule_bridge_recheck_fail",
        "priority": 80,
        "condition_key": "bridge_recheck_passed",
        "operator": "==",
        "threshold": False,
        "target_stage": StageEnum.BRIDGE_RECHECK,
        "action": "STAY_ON_GAP",
        "reason": "Student did not pass the bridge check. Remaining on gap concept for reinforcement."
    },
    {
        "id": "rule_probe_conflicting_evidence",
        "priority": 75,
        "condition_key": "evidence_band",
        "operator": "==",
        "threshold": "not sure",
        "target_stage": StageEnum.PROBE,
        "action": "REQUEST_MORE_PROBES",
        "reason": "Diagnostic probe evidence is thin or conflicting ('not sure'). Gathering additional probes before deciding."
    },
    {
        "id": "rule_supported_gap_learn",
        "priority": 70,
        "condition_key": "gap_supported",
        "operator": "==",
        "threshold": True,
        "action": "START_MICRO_LESSON",
        "reason": "Prerequisite diagnostic probes supported a foundational gap. Delivering targeted micro-lesson."
    },
    {
        "id": "rule_open_hypothesis_probe",
        "priority": 60,
        "condition_key": "has_open_hypothesis",
        "operator": "==",
        "threshold": True,
        "action": "ADMINISTER_PROBE",
        "reason": "Wrong answer opened a gap hypothesis. Administering prerequisite probe to test hypothesis."
    },
    {
        "id": "rule_move_ahead_fast_learner",
        "priority": 50,
        "condition_key": "mastery_estimate",
        "operator": ">=",
        "threshold": 0.85,
        "extra_condition_key": "consecutive_successes",
        "extra_operator": ">=",
        "extra_threshold": 3,
        "action": "MOVE_AHEAD",
        "reason": "Student demonstrates high mastery with consistent evidence. Skipping drill to advance ahead."
    },
    {
        "id": "rule_default_solve",
        "priority": 10,
        "condition_key": "always_true",
        "operator": "==",
        "threshold": True,
        "action": "CONTINUE_PRACTICE",
        "reason": "Continuing practice questions calibrated to current mastery level."
    }
]


class DecisionResult:
    def __init__(self, action: str, rule_id: str, reason: str, metadata: Optional[Dict[str, Any]] = None):
        self.action = action
        self.rule_id = rule_id
        self.reason = reason
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "rule_id": self.rule_id,
            "reason": self.reason,
            "metadata": self.metadata
        }


class RuleSequencer:
    """
    Evaluates data rules against student state.
    Rules can be loaded, replaced, or modified at runtime from JSON/dict data.
    """

    def __init__(self, rules: Optional[List[Dict[str, Any]]] = None):
        self.rules = sorted(
            list(rules or DEFAULT_RULES),
            key=lambda r: r.get("priority", 0),
            reverse=True
        )

    def load_rules(self, rules: List[Dict[str, Any]]):
        self.rules = sorted(
            list(rules),
            key=lambda r: r.get("priority", 0),
            reverse=True
        )

    def evaluate(self, state: Dict[str, Any]) -> DecisionResult:
        state_with_always_true = dict(state)
        state_with_always_true["always_true"] = True

        for rule in self.rules:
            # Check target stage restriction if present
            target_stage = rule.get("target_stage")
            current_stage = state.get("current_stage")
            if target_stage and current_stage and current_stage != target_stage:
                continue

            cond_key = rule.get("condition_key")
            op = rule.get("operator")
            threshold = rule.get("threshold")

            if cond_key not in state_with_always_true:
                continue

            val = state_with_always_true[cond_key]
            matches = self._check_condition(val, op, threshold)

            # Check extra condition if present
            extra_key = rule.get("extra_condition_key")
            if matches and extra_key:
                extra_val = state_with_always_true.get(extra_key)
                extra_op = rule.get("extra_operator")
                extra_threshold = rule.get("extra_threshold")
                matches = self._check_condition(extra_val, extra_op, extra_threshold)

            if matches:
                return DecisionResult(
                    action=rule.get("action", "CONTINUE"),
                    rule_id=rule.get("id", "unknown_rule"),
                    reason=rule.get("reason", "Rule condition matched"),
                    metadata={"matched_condition": f"{cond_key} {op} {threshold}"}
                )

        # Fallback
        return DecisionResult(
            action="CONTINUE_PRACTICE",
            rule_id="fallback",
            reason="Adaptive drill sequence continues."
        )

    def _check_condition(self, val: Any, op: str, threshold: Any) -> bool:
        if val is None:
            return False
        if op == ">=":
            return float(val) >= float(threshold)
        elif op == "<=":
            return float(val) <= float(threshold)
        elif op == ">":
            return float(val) > float(threshold)
        elif op == "<":
            return float(val) < float(threshold)
        elif op == "==":
            return val == threshold
        elif op == "!=":
            return val != threshold
        return False
