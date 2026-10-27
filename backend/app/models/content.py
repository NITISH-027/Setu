from enum import Enum
from typing import Optional, List, Union
from datetime import datetime
from pydantic import BaseModel, Field, model_validator


class ReviewStatus(str, Enum):
    AUTHOR_DRAFTED = "author-drafted, unreviewed"
    FLAGGED = "flagged"
    REVIEWED = "reviewed"
    UNVERIFIED_IMPORT = "unverified import"
    CHANGED_SINCE_REVIEW = "changed since review"


class ReviewRecord(BaseModel):
    status: ReviewStatus = Field(default=ReviewStatus.AUTHOR_DRAFTED)
    reviewer_name: Optional[str] = Field(default=None)
    reviewer_role: Optional[str] = Field(
        default=None,
        description="Self-declared qualification or role, explicitly presented as such"
    )
    attestation_date: Optional[datetime] = Field(default=None)
    item_version: int = Field(default=1)
    attestation_statement: Optional[str] = Field(
        default=None,
        description="Mandatory statement like 'I checked this item' for status=reviewed"
    )

    def is_human_reviewed(self) -> bool:
        return (
            self.status == ReviewStatus.REVIEWED
            and bool(self.reviewer_name)
            and bool(self.attestation_statement)
            and self.attestation_date is not None
        )


class Option(BaseModel):
    id: str
    text: str
    is_correct: bool
    misconception_tag: Optional[str] = Field(
        default=None,
        description="Must be provided if is_correct is False; rejected by validator if missing"
    )
    numeric_value: Optional[float] = Field(
        default=None,
        description="Recomputed or verified numeric result where computable"
    )


class Question(BaseModel):
    id: str
    concept: str
    difficulty: float = Field(default=0.5, ge=0.0, le=1.0)
    language: str = Field(default="en")
    question_text: str
    options: List[Option]
    probe_for_misconception: Optional[str] = Field(
        default=None,
        description="Misconception tag this question acts as a diagnostic probe for"
    )
    review_record: ReviewRecord = Field(default_factory=ReviewRecord)


class Lesson(BaseModel):
    id: str
    concept: str
    misconception: Optional[str] = Field(
        default=None,
        description="Targeted misconception tag, or None if foundational micro-lesson"
    )
    language: str = Field(default="en")
    content: str
    review_record: ReviewRecord = Field(default_factory=ReviewRecord)


class HintLadder(BaseModel):
    question_id: str
    level_1_hint: str = Field(..., description="Gentle nudge / clue")
    level_2_partial_step: str = Field(..., description="Partial step / intermediate formula")
    level_3_worked_step: str = Field(..., description="Full worked step")
    review_record: ReviewRecord = Field(default_factory=ReviewRecord)
