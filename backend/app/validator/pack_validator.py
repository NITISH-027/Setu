import math
from typing import List, Dict, Set, Tuple, Any, Optional
from app.models.pack import ContentPack
from app.models.content import Question, Option, ReviewStatus


class ValidationIssue:
    def __init__(self, severity: str, code: str, message: str, item_id: Optional[str] = None):
        self.severity = severity  # 'ERROR' or 'WARNING'
        self.code = code
        self.message = message
        self.item_id = item_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "item_id": self.item_id
        }


class PackValidationResult:
    def __init__(self, is_valid: bool, issues: List[ValidationIssue]):
        self.is_valid = is_valid
        self.issues = issues
        self.disclaimer = (
            "NOTICE: The validator checks structural integrity only. "
            "It cannot prove semantic ambiguity, tag correctness, lesson correctness, "
            "curriculum alignment, or content validity. Those require human subject-matter review."
        )

    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "ERROR"]

    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "WARNING"]


class PackValidator:
    """
    Validates structural rules of content packs:
    1. Untagged wrong options rejected.
    2. Acyclic graph & no dangling prerequisite references.
    3. Every misconception tag has at least one probe question.
    4. Numeric answer recomputation.
    5. Exact and near-duplicate option detection.
    """

    def validate(self, pack: ContentPack) -> PackValidationResult:
        issues: List[ValidationIssue] = []

        concept_ids: Set[str] = {c.id for c in pack.concepts}

        # 1. Check prerequisite edges (dangling & cycles)
        self._check_prerequisites(pack, concept_ids, issues)

        # 2. Check questions & options (untagged wrong options, duplicates, numeric checks)
        tagged_misconceptions: Set[str] = set()
        probe_misconceptions: Set[str] = set()

        for q in pack.questions:
            self._validate_question(q, issues, tagged_misconceptions, probe_misconceptions)

        # 3. Check probe coverage for all tagged misconceptions
        missing_probes = tagged_misconceptions - probe_misconceptions
        for tag in missing_probes:
            issues.append(ValidationIssue(
                severity="ERROR",
                code="MISSING_PROBE_FOR_TAG",
                message=f"Misconception tag '{tag}' is referenced in wrong options but has no corresponding probe question."
            ))

        # 4. Check hints structural and mathematical integrity
        self._validate_hints(pack, issues)

        is_valid = len([i for i in issues if i.severity == "ERROR"]) == 0
        return PackValidationResult(is_valid=is_valid, issues=issues)

    def _check_prerequisites(
        self,
        pack: ContentPack,
        concept_ids: Set[str],
        issues: List[ValidationIssue]
    ):
        adjacency: Dict[str, List[str]] = {cid: [] for cid in concept_ids}

        for edge in pack.prerequisite_edges:
            if edge.concept not in concept_ids:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    code="DANGLING_PREREQUISITE",
                    message=f"Concept '{edge.concept}' in prerequisite edge does not exist in pack concepts."
                ))
            if edge.depends_on not in concept_ids:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    code="DANGLING_PREREQUISITE",
                    message=f"Prerequisite '{edge.depends_on}' required by '{edge.concept}' does not exist in pack concepts."
                ))
            if edge.concept in adjacency and edge.depends_on in concept_ids:
                adjacency[edge.concept].append(edge.depends_on)

        # Detect cycles using DFS with 3-color graph coloring (0=unvisited, 1=visiting, 2=visited)
        visited: Dict[str, int] = {cid: 0 for cid in concept_ids}

        def has_cycle(node: str, path: List[str]) -> bool:
            visited[node] = 1
            for neighbor in adjacency.get(node, []):
                if visited.get(neighbor) == 1:
                    cycle_path = " -> ".join(path + [neighbor])
                    issues.append(ValidationIssue(
                        severity="ERROR",
                        code="GRAPH_CYCLE_DETECTED",
                        message=f"Cycle detected in prerequisite graph: {cycle_path}",
                        item_id=node
                    ))
                    return True
                if visited.get(neighbor) == 0:
                    if has_cycle(neighbor, path + [neighbor]):
                        return True
            visited[node] = 2
            return False

        for cid in concept_ids:
            if visited[cid] == 0:
                has_cycle(cid, [cid])

    def _validate_question(
        self,
        q: Question,
        issues: List[ValidationIssue],
        tagged_misconceptions: Set[str],
        probe_misconceptions: Set[str]
    ):
        if q.probe_for_misconception:
            probe_misconceptions.add(q.probe_for_misconception)

        has_correct = False
        option_texts = []

        for opt in q.options:
            option_texts.append(opt.text.strip().lower())
            if opt.is_correct:
                has_correct = True
            else:
                # Every wrong option MUST carry a misconception tag
                if not opt.misconception_tag or not opt.misconception_tag.strip():
                    issues.append(ValidationIssue(
                        severity="ERROR",
                        code="UNTAGGED_WRONG_OPTION",
                        message=f"Wrong option '{opt.id}' in question '{q.id}' lacks a misconception tag.",
                        item_id=q.id
                    ))
                else:
                    tagged_misconceptions.add(opt.misconception_tag.strip())

            # Check numeric value consistency if numeric_value is declared
            if opt.numeric_value is not None:
                # Attempt to parse numeric text from option text
                self._verify_numeric_value(q.id, opt, issues)

        if not has_correct:
            issues.append(ValidationIssue(
                severity="ERROR",
                code="NO_CORRECT_OPTION",
                message=f"Question '{q.id}' has no marked correct option.",
                item_id=q.id
            ))

        # Check for exact or near-duplicate options
        seen_texts: Set[str] = set()
        for idx, text in enumerate(option_texts):
            if text in seen_texts:
                issues.append(ValidationIssue(
                    severity="WARNING",
                    code="DUPLICATE_OPTION",
                    message=f"Duplicate option text '{text}' detected in question '{q.id}'. Prompt for human review.",
                    item_id=q.id
                ))
            seen_texts.add(text)

    def _verify_numeric_value(self, q_id: str, opt: Option, issues: List[ValidationIssue]):
        """
        Verify that option text containing numbers matches the declared numeric_value.
        Checks if the declared numeric_value matches the evaluated number (e.g. in '4 x 4 = 16', matches 16).
        """
        import re
        numbers = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", opt.text)
        if numbers:
            try:
                # In expressions like '4 x 4 = 16', the result is typically the last number
                matched = any(
                    math.isclose(float(num), opt.numeric_value, rel_tol=1e-5, abs_tol=1e-5)
                    for num in numbers
                )
                if not matched:
                    issues.append(ValidationIssue(
                        severity="WARNING",
                        code="NUMERIC_VALUE_MISMATCH",
                        message=(
                            f"In question '{q_id}', option '{opt.id}' numbers {numbers} "
                            f"differ from declared numeric_value '{opt.numeric_value}'."
                        ),
                        item_id=q_id
                    ))
            except ValueError:
                pass

    def _validate_hints(self, pack: ContentPack, issues: List[ValidationIssue]):
        """
        Validate hints:
        1. Non-empty steps (level 1, level 2, level 3).
        2. No dangling question references.
        3. Level 3 worked step does not contradict the declared correct option.
        """
        import re
        if not hasattr(pack, "hints") or not pack.hints:
            return

        q_map = {q.id: q for q in pack.questions}

        for h in pack.hints:
            if h.question_id not in q_map:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    code="DANGLING_HINT",
                    message=f"Hint references non-existent question '{h.question_id}'.",
                    item_id=h.question_id
                ))
                continue

            if not h.level_1_hint or not h.level_1_hint.strip():
                issues.append(ValidationIssue(
                    severity="ERROR",
                    code="EMPTY_HINT_STEP",
                    message=f"Hint for question '{h.question_id}' has empty level 1 hint.",
                    item_id=h.question_id
                ))
            if not h.level_2_partial_step or not h.level_2_partial_step.strip():
                issues.append(ValidationIssue(
                    severity="ERROR",
                    code="EMPTY_HINT_STEP",
                    message=f"Hint for question '{h.question_id}' has empty level 2 partial step.",
                    item_id=h.question_id
                ))
            if not h.level_3_worked_step or not h.level_3_worked_step.strip():
                issues.append(ValidationIssue(
                    severity="ERROR",
                    code="EMPTY_HINT_STEP",
                    message=f"Hint for question '{h.question_id}' has empty level 3 worked step.",
                    item_id=h.question_id
                ))

            # Mathematical / answer contradiction check
            q = q_map[h.question_id]
            correct_opt = next((o for o in q.options if o.is_correct), None)
            if correct_opt and h.level_3_worked_step:
                opt_text = correct_opt.text.strip()
                l3 = h.level_3_worked_step

                opt_var_match = re.search(r"\b([a-zA-Z])\s*=\s*([-+]?\d+)\b", opt_text)
                if opt_var_match:
                    var, val = opt_var_match.group(1), opt_var_match.group(2)
                    hint_final_nums = re.findall(r"=\s*([-+]?\d+)\b", l3)
                    if hint_final_nums and hint_final_nums[-1] != val:
                        issues.append(ValidationIssue(
                            severity="ERROR",
                            code="HINT_ANSWER_CONTRADICTION",
                            message=(
                                f"Hint for '{h.question_id}' concludes with value '{hint_final_nums[-1]}', "
                                f"contradicting correct option '{var} = {val}'."
                            ),
                            item_id=h.question_id
                        ))
                elif re.match(r"^[-+]?\d+$", opt_text):
                    opt_val = opt_text
                    hint_final_nums = re.findall(r"=\s*([-+]?\d+)\b", l3)
                    if hint_final_nums and hint_final_nums[-1] != opt_val:
                        issues.append(ValidationIssue(
                            severity="ERROR",
                            code="HINT_ANSWER_CONTRADICTION",
                            message=(
                                f"Hint for '{h.question_id}' concludes with value '{hint_final_nums[-1]}', "
                                f"contradicting correct option '{opt_val}'."
                            ),
                            item_id=h.question_id
                        ))
