"""
Teacher authoring (v5): teachers add or edit a question with its misconception
tags from the dashboard - no code, no JSON file editing.

Every authored question is validated with the same structural rules as the
shipped pack (untagged wrong options rejected, exactly one correct option,
numeric consistency) and is stored and served as "author-drafted, unreviewed":
it enters the child-facing flow as a DRAFT until a human reviewer changes its
review record. The validator checks structure only; it cannot prove the maths
or the tag choice is right - that still needs a subject-matter teacher.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import Session

from app.db.models import Base
from app.models.content import Question, Option, ReviewRecord, ReviewStatus
from app.models.pack import ContentPack
from app.validator.pack_validator import PackValidator, ValidationIssue


class AuthoredQuestionDB(Base):
    __tablename__ = "authored_questions"
    id = Column(String, primary_key=True)          # question id, e.g. q_teacher_ab12cd34
    payload = Column(Text, nullable=False)          # full Question JSON
    created_by = Column(String, nullable=False)     # teacher user id
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1)


def existing_probe_tags(pack: ContentPack) -> Set[str]:
    tags = set()
    for q in pack.questions:
        if q.probe_for_misconception:
            tags.add(q.probe_for_misconception)
    return tags


def validate_teacher_question(
    pack: ContentPack,
    data: Dict[str, Any],
    question_id: str,
    editing: bool = False,
) -> Tuple[Optional[Question], List[Dict[str, Any]]]:
    """Build and structurally validate a teacher-authored question.

    Returns (question_or_None, issues). Any ERROR issue means the question is
    rejected. WARNINGs are returned but the question can be stored.
    """
    issues: List[ValidationIssue] = []

    concept = (data.get("concept") or "").strip()
    if pack.get_concept(concept) is None:
        issues.append(ValidationIssue(
            severity="ERROR", code="UNKNOWN_CONCEPT",
            message=f"Concept '{concept}' is not in the pack. Authoring cannot create new concepts yet.",
            item_id=question_id,
        ))

    text = (data.get("question_text") or "").strip()
    if len(text) < 5:
        issues.append(ValidationIssue(
            severity="ERROR", code="TEXT_TOO_SHORT",
            message="Question text must be at least 5 characters.",
            item_id=question_id,
        ))

    raw_options = data.get("options") or []
    if not (2 <= len(raw_options) <= 6):
        issues.append(ValidationIssue(
            severity="ERROR", code="OPTION_COUNT",
            message="Provide 2 to 6 options.",
            item_id=question_id,
        ))

    correct_count = sum(1 for o in raw_options if o.get("is_correct"))
    if correct_count != 1:
        issues.append(ValidationIssue(
            severity="ERROR", code="CORRECT_COUNT",
            message=f"Exactly one option must be marked correct (got {correct_count}).",
            item_id=question_id,
        ))

    language = (data.get("language") or "en").strip() or "en"
    supported = set(pack.metadata.supported_languages) | set(pack.metadata.draft_unreviewed_languages) | {"en", "hi", "te", "ta"}
    if language not in supported:
        issues.append(ValidationIssue(
            severity="ERROR", code="UNKNOWN_LANGUAGE",
            message=f"Language '{language}' is not one of {sorted(supported)}.",
            item_id=question_id,
        ))

    if any(i.severity == "ERROR" for i in issues):
        return None, [i.to_dict() for i in issues]

    options = [
        Option(
            id=f"opt_{i + 1}",
            text=str(o.get("text", "")).strip(),
            is_correct=bool(o.get("is_correct")),
            misconception_tag=(o.get("misconception_tag") or None),
        )
        for i, o in enumerate(raw_options)
    ]

    probe_for = (data.get("probe_for_misconception") or None)
    if probe_for:
        probe_for = probe_for.strip() or None

    try:
        difficulty = float(data.get("difficulty", 0.5))
    except (TypeError, ValueError):
        difficulty = 0.5
    difficulty = max(0.0, min(1.0, difficulty))

    question = Question(
        id=question_id,
        concept=concept,
        difficulty=difficulty,
        language=language,
        question_text=text,
        options=options,
        probe_for_misconception=probe_for,
        item_type="diagnostic",
        review_record=ReviewRecord(status=ReviewStatus.AUTHOR_DRAFTED),
    )

    if not editing and pack.get_question(question_id) is not None:
        return None, [{"severity": "ERROR", "code": "DUPLICATE_ID",
                       "message": f"Question id '{question_id}' already exists.", "item_id": question_id}]

    # Reuse the shipped pack validator's per-question structural rules.
    validator = PackValidator()
    tagged: Set[str] = set()
    probes: Set[str] = set()
    validator._validate_question(question, issues, tagged, probes)

    # Pack-level honesty: a brand-new misconception tag needs a probe somewhere,
    # otherwise the diagnostic loop cannot confirm it. Warn, don't block.
    new_tags = {t for t in tagged if t != probe_for}
    covered = existing_probe_tags(pack)
    for t in sorted(new_tags):
        if t not in covered:
            issues.append(ValidationIssue(
                severity="WARNING", code="NEW_TAG_WITHOUT_PROBE",
                message=f"Misconception tag '{t}' is new: no probe question exists for it yet. "
                        f"Add a probe question (set 'probe_for_misconception') so the engine can confirm this gap.",
                item_id=question_id,
            ))

    if any(i.severity == "ERROR" for i in issues):
        return None, [i.to_dict() for i in issues]
    return question, [i.to_dict() for i in issues]


def store_question(db: Session, question: Question, teacher_id: str, editing: bool = False) -> AuthoredQuestionDB:
    row = db.query(AuthoredQuestionDB).filter(AuthoredQuestionDB.id == question.id).first()
    payload = question.model_dump_json()
    if row is None:
        row = AuthoredQuestionDB(
            id=question.id, payload=payload, created_by=teacher_id,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(), version=1,
        )
        db.add(row)
    else:
        row.payload = payload
        row.updated_at = datetime.utcnow()
        row.version = (row.version or 1) + 1
        # Any edit keeps the item in unreviewed draft state, version bumped.
        q = Question.model_validate_json(payload)
        q.review_record = ReviewRecord(status=ReviewStatus.AUTHOR_DRAFTED, item_version=row.version)
        row.payload = q.model_dump_json()
    db.commit()
    return row


def load_authored_into_pack(db: Session, pack: ContentPack) -> int:
    """Append REVIEWED teacher-authored questions to the in-memory pack (startup).
    Drafts and flagged items are stored but never served to students."""
    n = 0
    for row in db.query(AuthoredQuestionDB).all():
        try:
            q = Question.model_validate_json(row.payload)
        except Exception:
            continue
        if q.review_record.status != ReviewStatus.REVIEWED:
            continue
        if pack.get_question(q.id) is None:
            pack.questions.append(q)
            n += 1
    return n


def upsert_into_pack(pack: ContentPack, question: Question) -> None:
    existing = pack.get_question(question.id)
    if existing is None:
        pack.questions.append(question)
    else:
        idx = pack.questions.index(existing)
        pack.questions[idx] = question
