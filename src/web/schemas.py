"""
API Request/Response Schemas

Pydantic models for API validation and serialization.
"""

from datetime import datetime

from pydantic import BaseModel, Field

# =============================================================================
# REQUEST MODELS
# =============================================================================


class ApplyRequest(BaseModel):
    """Request body for starting a job application.

    Attributes:
        job_text: Raw job posting text (min 100, max 50000 chars).
        source: Optional source identifier (e.g., "linkedin", max 100 chars).
    """

    job_text: str = Field(
        ...,
        min_length=100,
        max_length=50000,
        description="Raw job posting text (100-50000 chars)",
    )
    source: str | None = Field(
        None,
        max_length=100,
        description="Source of job posting",
    )


# =============================================================================
# RESPONSE MODELS
# =============================================================================


class ApplyResponse(BaseModel):
    """Response for job application submission.

    Attributes:
        job_id: Unique identifier for the job application.
        status: Current status of the pipeline.
    """

    job_id: str
    status: str


class JobSummary(BaseModel):
    """Summary of a job application for listing.

    Attributes:
        job_id: Unique identifier for the job.
        job_title: Job title extracted from posting.
        company_name: Company name extracted from posting.
        status: Current status of the pipeline.
        compatibility_score: Match score (0-100) if available.
        submitted_at: When the application was submitted.
        completed_at: When processing completed (if done).
    """

    job_id: str
    job_title: str | None = None
    company_name: str | None = None
    status: str
    compatibility_score: float | None = None
    submitted_at: datetime
    completed_at: datetime | None = None


class JobListResponse(BaseModel):
    """Response for listing all jobs.

    Attributes:
        jobs: List of job summaries.
        total: Total number of jobs in store.
        skip: Number of jobs skipped (offset).
        limit: Maximum number of jobs returned.
    """

    jobs: list[JobSummary]
    total: int
    skip: int = 0
    limit: int = 20


class StepInfo(BaseModel):
    """Information about a pipeline step.

    Attributes:
        step: Step name.
        status: Step status.
        duration_ms: Time taken for this step.
        error: Error message if step failed.
    """

    step: str
    status: str
    duration_ms: int = 0
    error: str | None = None


class StatusResponse(BaseModel):
    """Response for job status query.

    Attributes:
        job_id: Unique identifier for the job.
        pipeline_id: Pipeline execution identifier.
        status: Current pipeline status.
        current_step: Currently executing step (if running).
        job_title: Job title extracted from posting.
        company_name: Company name extracted from posting.
        compatibility_score: Match score (0-100) if available.
        cv_path: Path to generated CV PDF.
        cover_letter_path: Path to generated cover letter PDF.
        steps: List of step execution info.
        error: Error message if pipeline failed.
        started_at: When pipeline started.
        completed_at: When pipeline completed.
        total_duration_ms: Total execution time.
    """

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
    started_at: datetime
    completed_at: datetime | None = None
    total_duration_ms: int = 0


class ErrorResponse(BaseModel):
    """Standard error response.

    Attributes:
        error: Error type.
        message: Human-readable error message.
        detail: Additional error details.
    """

    error: str
    message: str
    detail: str | None = None


class HealthResponse(BaseModel):
    """Health check response.

    Attributes:
        status: Health status.
        version: API version.
        services: Status of dependent services.
    """

    status: str
    version: str
    services: dict[str, str] = Field(default_factory=dict)
