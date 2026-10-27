from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


class ConsentStatus(str, Enum):
    NOT_REQUESTED = "not requested"
    REQUESTED = "requested"
    RECORDED = "recorded"


class Student(BaseModel):
    """
    Minimal operational metadata for a student.
    Strictly forbids direct identifiers (no names, phones, emails, addresses, school names, birth dates).
    """
    pseudonymous_id: str = Field(..., description="Opaque pseudonymous student ID, e.g. stu_a8f9c1")
    class_id: str = Field(..., description="Class and section, e.g. 8-A")
    board: str = Field(default="CBSE", description="Educational board")
    medium_language: str = Field(default="en", description="Medium of instruction, e.g. en, hi, te")
    pin_hash: str = Field(..., description="Secure hash of 4-digit PIN for device authentication")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    consent_status: ConsentStatus = Field(default=ConsentStatus.NOT_REQUESTED)

    @field_validator("consent_status", mode="before")
    def validate_consent_status(cls, v):
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower in [e.value for e in ConsentStatus]:
                return ConsentStatus(v_lower)
        return v

    model_config = {
        "extra": "forbid"  # Rejects any unexpected/direct identifier fields like 'name', 'phone', etc.
    }
