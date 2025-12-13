"""
API Routes

REST API endpoints for Scout job application processing.

Endpoints:
    POST /api/apply - Start new job application
    GET /api/status/{job_id} - Get pipeline status
    GET /api/download/{job_id}/{file_type} - Download PDF
    GET /api/jobs - List all jobs
"""

import asyncio
import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse

from src.services.pipeline import (
    PipelineInput,
    PipelineOrchestrator,
    PipelineResult,
)
from src.web.dependencies import JobStore, get_orchestrator, get_store
from src.web.schemas import (
    ApplyRequest,
    ApplyResponse,
    ErrorResponse,
    JobListResponse,
    JobSummary,
    StatusResponse,
    StepInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])

# Pipeline timeout in seconds (15 minutes for local LLM inference)
# Local inference on Raspberry Pi 5 can take 15-30 min for full pipeline
PIPELINE_TIMEOUT_SECONDS = 900


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def result_to_status_response(result: PipelineResult) -> StatusResponse:
    """Convert PipelineResult to StatusResponse."""
    steps = [
        StepInfo(
            step=step.step.value,
            status=step.status.value,
            duration_ms=step.duration_ms,
            error=step.error,
        )
        for step in result.steps
    ]

    return StatusResponse(
        job_id=result.job_id or result.pipeline_id,
        pipeline_id=result.pipeline_id,
        status=result.status.value,
        current_step=result.current_step.value if result.current_step else None,
        job_title=result.job_title,
        company_name=result.company_name,
        compatibility_score=result.compatibility_score,
        cv_path=result.cv_path,
        cover_letter_path=result.cover_letter_path,
        steps=steps,
        error=result.error,
        started_at=result.started_at,
        completed_at=result.completed_at,
        total_duration_ms=result.total_duration_ms,
    )


def result_to_job_summary(result: PipelineResult) -> JobSummary:
    """Convert PipelineResult to JobSummary."""
    return JobSummary(
        job_id=result.job_id or result.pipeline_id,
        job_title=result.job_title,
        company_name=result.company_name,
        status=result.status.value,
        compatibility_score=result.compatibility_score,
        submitted_at=result.started_at,
        completed_at=result.completed_at,
    )


async def execute_pipeline(
    orchestrator: PipelineOrchestrator,
    store: JobStore,
    input_data: PipelineInput,
    job_id: str,
) -> None:
    """
    Execute pipeline in background with timeout and store result.

    Uses asyncio.wait_for() to enforce a timeout on pipeline execution.
    This is critical for local LLM inference which can be slow.

    Args:
        orchestrator: Pipeline orchestrator instance.
        store: Job store for storing results.
        input_data: Pipeline input data.
        job_id: Pre-generated job ID for tracking.
    """
    from datetime import datetime

    from src.services.pipeline import PipelineResult, PipelineStatus

    try:
        logger.info(
            f"Starting pipeline execution for job {job_id} "
            f"(timeout: {PIPELINE_TIMEOUT_SECONDS}s)"
        )
        result = await asyncio.wait_for(
            orchestrator.execute(input_data),
            timeout=PIPELINE_TIMEOUT_SECONDS,
        )
        store.store(result)
        logger.info(f"Pipeline completed for job {job_id}: {result.status.value}")

    except TimeoutError:
        logger.error(
            f"Pipeline timed out for job {job_id} "
            f"after {PIPELINE_TIMEOUT_SECONDS}s"
        )
        error_result = PipelineResult(
            pipeline_id=job_id,
            status=PipelineStatus.FAILED,
            started_at=datetime.now(),
            error=f"Pipeline timed out after {PIPELINE_TIMEOUT_SECONDS} seconds. "
            "Local LLM inference may be taking longer than expected.",
        )
        store.store(error_result)

    except Exception as e:
        logger.error(f"Pipeline execution failed for job {job_id}: {e}")
        error_result = PipelineResult(
            pipeline_id=job_id,
            status=PipelineStatus.FAILED,
            started_at=datetime.now(),
            error=str(e),
        )
        store.store(error_result)


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.post(
    "/apply",
    response_model=ApplyResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Start new job application",
    description="Submit a job posting text to start the application generation pipeline.",
)
async def apply(
    request: ApplyRequest,
    background_tasks: BackgroundTasks,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
    store: JobStore = Depends(get_store),
) -> ApplyResponse:
    """
    Start a new job application.

    The pipeline runs in the background. Use GET /api/status/{job_id}
    to poll for completion.

    Args:
        request: Job application request with job text.
        background_tasks: FastAPI background task manager.
        orchestrator: Pipeline orchestrator.
        store: Job storage.

    Returns:
        ApplyResponse with job_id for tracking.

    Raises:
        HTTPException: If request is invalid.
    """
    import uuid

    # Generate job ID for tracking
    job_id = str(uuid.uuid4())[:8]

    logger.info(f"Received apply request, job_id={job_id}, source={request.source}")

    # Create pipeline input
    input_data = PipelineInput(
        raw_job_text=request.job_text,
        source=request.source,
    )

    # Start pipeline in background
    background_tasks.add_task(
        execute_pipeline,
        orchestrator,
        store,
        input_data,
        job_id,
    )

    return ApplyResponse(job_id=job_id, status="running")


@router.get(
    "/status/{job_id}",
    response_model=StatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
    summary="Get pipeline status",
    description="Get the current status and results of a job application pipeline.",
)
async def get_status(
    job_id: str,
    store: JobStore = Depends(get_store),
) -> StatusResponse:
    """
    Get status of a job application.

    Args:
        job_id: Job identifier from /apply response.
        store: Job storage.

    Returns:
        StatusResponse with current pipeline status and results.

    Raises:
        HTTPException: If job_id not found.
    """
    result = store.get(job_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found",
        )

    return result_to_status_response(result)


@router.get(
    "/download/{job_id}/{file_type}",
    responses={
        404: {"model": ErrorResponse, "description": "File not found"},
        400: {"model": ErrorResponse, "description": "Invalid file type"},
    },
    summary="Download generated PDF",
    description="Download the generated CV or cover letter PDF.",
)
async def download(
    job_id: str,
    file_type: Literal["cv", "cover_letter"],
    store: JobStore = Depends(get_store),
) -> FileResponse:
    """
    Download a generated PDF file.

    Args:
        job_id: Job identifier.
        file_type: Either "cv" or "cover_letter".
        store: Job storage.

    Returns:
        PDF file download.

    Raises:
        HTTPException: If job not found or file not ready.
    """
    result = store.get(job_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found",
        )

    # Get the appropriate path
    if file_type == "cv":
        file_path = result.cv_path
        filename = f"cv_{job_id}.pdf"
    else:
        file_path = result.cover_letter_path
        filename = f"cover_letter_{job_id}.pdf"

    if file_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"{file_type} not available for job {job_id}. "
            f"Status: {result.status.value}",
        )

    # Verify file exists
    path = Path(file_path)
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {file_path}",
        )

    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=filename,
    )


@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="List all jobs",
    description="Get a paginated list of submitted job applications.",
)
async def list_jobs(
    skip: int = 0,
    limit: int = 20,
    store: JobStore = Depends(get_store),
) -> JobListResponse:
    """
    List all job applications with pagination.

    Args:
        skip: Number of jobs to skip (offset).
        limit: Maximum number of jobs to return.
        store: Job storage.

    Returns:
        JobListResponse with paginated list of job summaries.
    """
    # Get all results (already sorted by date descending)
    all_results = store.list_all()
    total = len(all_results)

    # Apply pagination
    paginated_results = all_results[skip : skip + limit]
    summaries = [result_to_job_summary(r) for r in paginated_results]

    return JobListResponse(
        jobs=summaries,
        total=total,
        skip=skip,
        limit=limit,
    )
