"""Job-related API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class ApplyRequest(BaseModel):
    """Request to start job application pipeline."""

    job_text: str = Field(..., min_length=100, description="Raw job posting text")
    source: str | None = Field(default="web", description="Source of job posting")


class ApplyResponse(BaseModel):
    """Response from job application submission."""

    job_id: str
    status: str


class QuickScoreRequest(BaseModel):
    """Request for quick compatibility score."""

    job_text: str = Field(..., min_length=100)


class QuickScoreResponse(BaseModel):
    """Quick compatibility score response."""

    score: int = Field(ge=0, le=100)
    level: str
    job_title: str | None
    company_name: str | None
    top_matches: list[str]
    key_gaps: list[str]
    recommendation: str


class StepInfo(BaseModel):
    """Pipeline step information."""

    step: str
    status: str
    duration_ms: int
    error: str | None = None


class StatusResponse(BaseModel):
    """Job pipeline status response."""

    job_id: str
    pipeline_id: str
    status: str
    current_step: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    compatibility_score: float | None = None
    cv_path: str | None = None
    cover_letter_path: str | None = None
    steps: list[StepInfo] = Field(default_factory=list)
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_duration_ms: int = 0


class JobSummary(BaseModel):
    """Job summary for list views."""

    job_id: str
    job_title: str | None = None
    company_name: str | None = None
    status: str
    compatibility_score: float | None = None
    submitted_at: datetime | None = None
    completed_at: datetime | None = None


class JobListResponse(BaseModel):
    """Paginated job list response."""

    jobs: list[JobSummary]
    total: int
    skip: int = 0
    limit: int = 20
