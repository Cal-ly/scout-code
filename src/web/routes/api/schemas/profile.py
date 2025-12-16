"""Profile-related API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class ProfileStatusResponse(BaseModel):
    """Profile status response."""

    exists: bool
    is_indexed: bool
    chunk_count: int
    last_updated: datetime | None


class ProfileCreateRequest(BaseModel):
    """Request to create profile from text."""

    profile_text: str = Field(..., min_length=100, max_length=10000)


class ProfileCreateResponse(BaseModel):
    """Response from profile creation."""

    profile_id: int
    status: str
    is_indexed: bool
    chunk_count: int


class SectionScoreResponse(BaseModel):
    """Profile section score."""

    section: str
    score: int
    max_score: int
    weight: float
    issues: list[str]
    suggestions: list[str]


class ProfileAssessmentResponse(BaseModel):
    """Profile completeness assessment."""

    overall_score: int
    grade: str
    section_scores: list[SectionScoreResponse]
    top_suggestions: list[str]
    strengths: list[str]
    is_job_ready: bool


class ProfileSummaryResponse(BaseModel):
    """Quick profile summary."""

    name: str
    title: str
    completeness_score: int
    grade: str
    is_job_ready: bool
    top_suggestion: str | None
