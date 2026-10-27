from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class EvidenceBand(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    NOT_SURE = "not sure"


class HypothesisStatus(str, Enum):
    OPEN = "open"
    SUPPORTED = "supported"
    REJECTED = "rejected"
    UNDECIDED = "undecided"


class StageEnum(str, Enum):
    DIAGNOSE = "diagnose"
    PROBE = "probe"
    LEARN = "learn"
    SOLVE = "solve"
    TEST = "test"
    BRIDGE_RECHECK = "bridge_recheck"
    MOVE_AHEAD = "move_ahead"
    ENRICHMENT = "enrichment"


class Attempt(BaseModel):
    id: Optional[str] = None
    student_id: str
    question_id: str
    concept_id: str
    selected_option_id: str
    is_correct: bool
    misconception_tag: Optional[str] = None
    time_spent_seconds: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EvidenceItem(BaseModel):
    probe_question_id: str
    probe_concept_id: str
    is_supporting: bool  # True if wrong answer on probe confirms gap; False if correct contradicts gap
    details: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Hypothesis(BaseModel):
    id: Optional[str] = None
    student_id: str
    suspected_concept_id: str
    misconception_tag: str
    evidence_list: List[EvidenceItem] = Field(default_factory=list)
    heuristic_score: int = Field(
        default=0,
        description="Supporting probes minus contradicting probes. NOT a probability."
    )
    evidence_band: EvidenceBand = Field(
        default=EvidenceBand.LOW,
        description="Low / Medium / High / not sure. Labelled 'heuristic evidence score'."
    )
    status: HypothesisStatus = Field(default=HypothesisStatus.OPEN)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def label(self) -> str:
        return "heuristic evidence score"


class BKTParameters(BaseModel):
    prior: float = Field(default=0.2, ge=0.0, le=1.0)
    learn: float = Field(default=0.15, ge=0.0, le=1.0)
    guess: float = Field(default=0.2, ge=0.0, le=1.0)
    slip: float = Field(default=0.1, ge=0.0, le=1.0)
    label: str = Field(default="uncalibrated, hand-set")


class MasteryState(BaseModel):
    student_id: str
    concept_id: str
    mastery_estimate: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Per-concept BKT probability with hand-set parameters"
    )
    bkt_params: BKTParameters = Field(default_factory=BKTParameters)
    mastery_label: str = Field(default="uncalibrated, hand-set")
    last_seen: Optional[datetime] = None
    next_review: Optional[datetime] = None
    interval_days: float = Field(default=1.0, description="Untuned SM-2 interval")
    ease_factor: float = Field(default=2.5, description="SM-2 ease factor")
    consecutive_successes: int = 0


class TeacherOverride(BaseModel):
    id: Optional[str] = None
    student_id: str
    teacher_id: str
    class_id: str
    concept_id: str
    override_action: str = Field(..., description="e.g. 'assign_concept', 'close_gap', 'skip_to_enrichment', 'modify_plan'")
    reason: str = Field(..., min_length=3, description="Mandatory non-empty explanation of override")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("reason")
    def validate_reason_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Override reason is mandatory and cannot be empty")
        return v.strip()


class Plan(BaseModel):
    student_id: str
    class_id: str
    current_stage: StageEnum = Field(default=StageEnum.DIAGNOSE)
    current_concept_id: str
    gap_concept_id: Optional[str] = None
    items_queue: List[str] = Field(default_factory=list, description="IDs of questions or micro-lessons queued")
    reason: str = Field(default="Initial diagnosis", description="Plain-language reason for why this plan/item was chosen")
    stuck_attempts_count: int = 0
    bridge_recheck_fails: int = 0
    updated_at: datetime = Field(default_factory=datetime.utcnow)
