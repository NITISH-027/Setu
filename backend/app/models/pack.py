from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.concept import Concept, PrerequisiteEdge
from app.models.content import Question, Lesson, HintLadder, ReviewRecord, ReviewStatus


class PackMetadata(BaseModel):
    board: str = "CBSE"
    class_level: int = 8
    subject: str = "Maths"
    language: str = "en"
    version: str = "1.0.0"
    alignment_disclaimer: str = (
        "intended NCERT alignment, unverified until references and content are checked"
    )
    supported_languages: List[str] = Field(default_factory=lambda: ["en"])
    draft_unreviewed_languages: List[str] = Field(default_factory=lambda: ["hi", "te"])
    author: str = "Setu Authoring Engine"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ContentPack(BaseModel):
    metadata: PackMetadata = Field(default_factory=PackMetadata)
    concepts: List[Concept] = Field(default_factory=list)
    prerequisite_edges: List[PrerequisiteEdge] = Field(default_factory=list)
    questions: List[Question] = Field(default_factory=list)
    lessons: List[Lesson] = Field(default_factory=list)
    hints: List[HintLadder] = Field(default_factory=list)
