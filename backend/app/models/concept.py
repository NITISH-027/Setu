from typing import Optional
from pydantic import BaseModel, Field


class Concept(BaseModel):
    id: str = Field(..., description="Unique concept ID, e.g. 'c8_math_linear_eq_one_var'")
    name: str = Field(..., description="Concept title")
    class_level: int = Field(..., description="Class level, e.g. 6, 7, 8, 9, 10")
    board: str = Field(default="CBSE", description="Curriculum board")
    subject: str = Field(default="Maths", description="Subject name")
    ncert_chapter_reference: str = Field(
        default="to verify against the official NCERT list",
        description="Intended NCERT chapter reference"
    )
    reference_verified: bool = Field(
        default=False,
        description="Flag indicating if NCERT chapter reference was checked against official list"
    )
    graph_only: bool = Field(
        default=False,
        description="True for concepts outside Class 8 that exist only in the graph spine without shipped questions"
    )


class PrerequisiteEdge(BaseModel):
    concept: str = Field(..., description="Dependent concept ID")
    depends_on: str = Field(..., description="Prerequisite concept ID that 'concept' depends on")
