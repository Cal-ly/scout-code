"""
Pipeline Data Models

Models for pipeline execution, tracking, and results.

Usage:
    from src.services.pipeline.models import (
        PipelineInput, PipelineResult, PipelineStatus
    )

    input_data = PipelineInput(raw_job_text="...")
    result = PipelineResult(pipeline_id="abc123", ...)
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PipelineStep(str, Enum):
    """Pipeline execution steps."""

    RINSER = "rinser"
    ANALYZER = "analyzer"
    CREATOR = "creator"
    FORMATTER = "formatter"


class StepStatus(str, Enum):
    """Status of a pipeline step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStatus(str, Enum):
    """Overall pipeline status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StepResult(BaseModel):
    """Result of a single pipeline step."""

    step: PipelineStep
    status: StepStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int = 0
    error: str | None = None
    output: dict[str, Any] | None = None


class PipelineInput(BaseModel):
    """Input for pipeline execution."""

    raw_job_text: str = Field(..., min_length=100)
    source: str | None = None  # e.g., "linkedin", "indeed"
    skip_formatting: bool = False  # Skip PDF generation


class PipelineResult(BaseModel):
    """Complete pipeline execution result."""

    # Identification
    pipeline_id: str

    # Status
    status: PipelineStatus
    current_step: PipelineStep | None = None

    # Timing
    started_at: datetime
    completed_at: datetime | None = None
    total_duration_ms: int = 0

    # Step results
    steps: list[StepResult] = Field(default_factory=list)

    # Outputs (references to actual data)
    job_id: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    compatibility_score: float | None = None

    # Output files
    cv_path: str | None = None
    cover_letter_path: str | None = None

    # Error info
    error: str | None = None
    failed_step: PipelineStep | None = None

    def get_step_result(self, step: PipelineStep) -> StepResult | None:
        """Get result for a specific step."""
        for result in self.steps:
            if result.step == step:
                return result
        return None

    @property
    def is_success(self) -> bool:
        """Check if pipeline completed successfully."""
        return self.status == PipelineStatus.COMPLETED


class PipelineProgress(BaseModel):
    """Real-time pipeline progress update."""

    pipeline_id: str
    status: PipelineStatus
    current_step: PipelineStep | None
    steps_completed: int
    steps_total: int
    progress_percent: float
    message: str
