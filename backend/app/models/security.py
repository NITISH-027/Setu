import secrets
from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class TombstoneStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    PURGED = "purged"


class Tombstone(BaseModel):
    """
    Opaque tombstone record.
    Holds only an opaque deletion key (random token, NOT student ID, NOT name, NOT learning payload),
    a timestamp, status, and pending device count.
    """
    opaque_key: str = Field(default_factory=lambda: secrets.token_hex(16))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: TombstoneStatus = Field(default=TombstoneStatus.PENDING)
    pending_devices: int = Field(default=0, ge=0)
    purged_at: Optional[datetime] = None


class AuditEventType(str, Enum):
    READ = "read"
    EXPORT = "export"
    DELETE = "delete"
    RETENTION_RUN = "retention_run"
    TOMBSTONE_APPLIED = "tombstone_applied"
    OVERRIDE = "override"


class AuditLogEvent(BaseModel):
    """
    Privacy-safe audit log event.
    Holds ONLY event type, actor, class, timestamp, and record count.
    Does NOT keep student IDs, answers, lesson content, or student payload.
    May reference the opaque tombstone key.
    """
    id: Optional[str] = None
    event_type: AuditEventType
    actor: str = Field(..., description="Teacher ID or 'system'")
    class_id: str = Field(..., description="Class identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    record_count: int = Field(default=1, ge=0)
    opaque_tombstone_key: Optional[str] = None

    model_config = {
        "extra": "forbid"
    }
