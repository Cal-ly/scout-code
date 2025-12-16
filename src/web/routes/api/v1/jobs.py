"""
Jobs API Routes

Job application pipeline endpoints.

Endpoints:
    POST /api/v1/jobs/apply - Start job application
    POST /api/v1/jobs/quick-score - Get quick compatibility score
    GET /api/v1/jobs - List all jobs
    GET /api/v1/jobs/{job_id} - Get job status
    GET /api/v1/jobs/{job_id}/download/{file_type} - Download PDF
"""

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse

from src.services.database import (
    get_database_service,
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationStatus,
)
from src.services.database.exceptions import ProfileNotFoundError
from src.services.pipeline import (
    PipelineInput,
    PipelineOrchestrator,
    PipelineResult,
    PipelineStatus,
)
from src.web.dependencies import JobStore, get_orchestrator, get_store
from src.web.routes.api.schemas import (
    ApplyRequest,
    ApplyResponse,
    ErrorResponse,
    JobListResponse,
    JobSummary,
    QuickScoreRequest,
    QuickScoreResponse,
    StatusResponse,
    StepInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Timeouts for local LLM inference
PIPELINE_TIMEOUT_SECONDS = 900  # 15 minutes
QUICK_SCORE_TIMEOUT_SECONDS = 300  # 5 minutes


def _result_to_status_response(result: PipelineResult) -> StatusResponse:
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


def _result_to_summary(result: PipelineResult) -> JobSummary:
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


async def _execute_pipeline(
    orchestrator: PipelineOrchestrator,
    store: JobStore,
    input_data: PipelineInput,
    job_id: str,
) -> None:
    """Execute pipeline in background with timeout and persist to database."""
    db = await get_database_service()

    try:
        logger.info(f"Starting pipeline for job {job_id}")

        # Mark as running in database
        await db.update_application(job_id, ApplicationUpdate(
            status=ApplicationStatus.RUNNING,
            started_at=datetime.now(),
        ))

        result = await asyncio.wait_for(
            orchestrator.execute(input_data),
            timeout=PIPELINE_TIMEOUT_SECONDS,
        )
        store.store(result)

        # Save to database
        await db.update_application(job_id, ApplicationUpdate(
            status=ApplicationStatus.COMPLETED if result.status == PipelineStatus.COMPLETED else ApplicationStatus.FAILED,
            job_title=result.job_title,
            company_name=result.company_name,
            compatibility_score=result.compatibility_score,
            cv_path=result.cv_path,
            cover_letter_path=result.cover_letter_path,
            analysis_data=result.analysis.model_dump() if hasattr(result, 'analysis') and result.analysis else None,
            pipeline_data={
                "steps": [{"step": s.step.value, "status": s.status.value, "duration_ms": s.duration_ms} for s in result.steps],
                "total_duration_ms": result.total_duration_ms,
            },
            completed_at=datetime.now(),
            error_message=result.error,
        ))
        logger.info(f"Pipeline completed for job {job_id}: {result.status.value}")

    except TimeoutError:
        logger.error(f"Pipeline timed out for job {job_id}")
        error_result = PipelineResult(
            pipeline_id=job_id,
            status=PipelineStatus.FAILED,
            started_at=datetime.now(),
            error=f"Pipeline timed out after {PIPELINE_TIMEOUT_SECONDS} seconds",
        )
        store.store(error_result)
        await db.update_application(job_id, ApplicationUpdate(
            status=ApplicationStatus.FAILED,
            error_message=f"Pipeline timed out after {PIPELINE_TIMEOUT_SECONDS} seconds",
            completed_at=datetime.now(),
        ))

    except Exception as e:
        logger.error(f"Pipeline failed for job {job_id}: {e}")
        error_result = PipelineResult(
            pipeline_id=job_id,
            status=PipelineStatus.FAILED,
            started_at=datetime.now(),
            error=str(e),
        )
        store.store(error_result)
        await db.update_application(job_id, ApplicationUpdate(
            status=ApplicationStatus.FAILED,
            error_message=str(e),
            completed_at=datetime.now(),
        ))


@router.post(
    "/apply",
    response_model=ApplyResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Start job application",
)
async def apply(
    request: ApplyRequest,
    background_tasks: BackgroundTasks,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
    store: JobStore = Depends(get_store),
) -> ApplyResponse:
    """Start a new job application pipeline."""
    job_id = str(uuid.uuid4())[:8]

    # Verify active profile exists
    db = await get_database_service()
    active_profile = await db.get_active_profile()
    if active_profile is None:
        raise HTTPException(
            status_code=400,
            detail="No active profile. Please activate a profile first."
        )

    logger.info(f"Apply request: job_id={job_id}, profile={active_profile.slug}, source={request.source}")

    # Create application record in database
    await db.create_application(ApplicationCreate(
        job_id=job_id,
        profile_id=active_profile.id,
        job_text=request.job_text,
    ))

    input_data = PipelineInput(
        raw_job_text=request.job_text,
        source=request.source,
    )

    background_tasks.add_task(
        _execute_pipeline, orchestrator, store, input_data, job_id
    )

    return ApplyResponse(job_id=job_id, status="running")


@router.post(
    "/quick-score",
    response_model=QuickScoreResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get quick compatibility score",
)
async def quick_score(request: QuickScoreRequest) -> QuickScoreResponse:
    """Get quick compatibility score without full pipeline."""
    from src.modules.analyzer import get_analyzer
    from src.modules.rinser import get_rinser

    job_text = request.job_text.strip()
    if len(job_text) < 100:
        raise HTTPException(status_code=400, detail="Job text must be at least 100 characters")

    try:
        rinser = await get_rinser()
        analyzer = await get_analyzer()

        processed_job = await asyncio.wait_for(
            rinser.process_job(job_text, index=False),
            timeout=QUICK_SCORE_TIMEOUT_SECONDS,
        )

        analysis = await asyncio.wait_for(
            analyzer.analyze(processed_job, generate_strategy=False),
            timeout=QUICK_SCORE_TIMEOUT_SECONDS,
        )

        top_matches = [
            sm.requirement_text
            for sm in analysis.skill_matches[:5]
            if sm.score >= 0.6
        ]

        key_gaps = [
            gap.requirement
            for gap in analysis.gaps[:3]
            if gap.importance in ["must_have", "should_have"]
        ]

        score = analysis.compatibility.overall
        if score >= 85:
            recommendation = "Excellent match! Strongly recommended to apply."
        elif score >= 70:
            recommendation = "Strong match. Good candidate for this role."
        elif score >= 50:
            recommendation = "Moderate match. Consider highlighting transferable skills."
        else:
            recommendation = "Weak match. May want to focus on other opportunities."

        return QuickScoreResponse(
            score=score,
            level=analysis.compatibility.level.value,
            job_title=processed_job.title,
            company_name=processed_job.company.name if processed_job.company else None,
            top_matches=top_matches,
            key_gaps=key_gaps,
            recommendation=recommendation,
        )

    except TimeoutError:
        raise HTTPException(status_code=500, detail="Analysis timed out")
    except Exception as e:
        logger.error(f"Quick score failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "",
    response_model=JobListResponse,
    summary="List all jobs",
)
async def list_jobs(
    skip: int = 0,
    limit: int = 20,
    profile_slug: str | None = None,
    store: JobStore = Depends(get_store),
) -> JobListResponse:
    """Get paginated list of job applications from database."""
    db = await get_database_service()

    # Get profile ID if slug provided
    profile_id = None
    if profile_slug:
        try:
            profile = await db.get_profile_by_slug(profile_slug)
            profile_id = profile.id
        except ProfileNotFoundError:
            pass

    # Query database
    applications, total = await db.list_applications(
        profile_id=profile_id,
        limit=limit,
        offset=skip,
    )

    # Convert to summaries
    summaries = [
        JobSummary(
            job_id=app.job_id,
            job_title=app.job_title,
            company_name=app.company_name,
            status=app.status.value,
            compatibility_score=app.compatibility_score,
            submitted_at=app.created_at,
            completed_at=app.completed_at,
        )
        for app in applications
    ]

    return JobListResponse(jobs=summaries, total=total, skip=skip, limit=limit)


@router.get(
    "/{job_id}",
    response_model=StatusResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get job status",
)
async def get_status(
    job_id: str,
    store: JobStore = Depends(get_store),
) -> StatusResponse:
    """Get status of a specific job."""
    # First check in-memory store for running jobs (has real-time updates)
    result = store.get(job_id)
    if result is not None:
        return _result_to_status_response(result)

    # Fall back to database for persisted results
    db = await get_database_service()
    app = await db.get_application_by_job_id(job_id)

    if app is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Convert database record to StatusResponse
    steps = []
    if app.pipeline_data and "steps" in app.pipeline_data:
        steps = [StepInfo(**s) for s in app.pipeline_data["steps"]]

    return StatusResponse(
        job_id=app.job_id,
        pipeline_id=app.job_id,
        status=app.status.value,
        current_step=None,
        job_title=app.job_title,
        company_name=app.company_name,
        compatibility_score=app.compatibility_score,
        cv_path=app.cv_path,
        cover_letter_path=app.cover_letter_path,
        steps=steps,
        error=app.error_message,
        started_at=app.started_at,
        completed_at=app.completed_at,
        total_duration_ms=app.pipeline_data.get("total_duration_ms", 0) if app.pipeline_data else 0,
    )


@router.get(
    "/{job_id}/download/{file_type}",
    responses={404: {"model": ErrorResponse}},
    summary="Download generated PDF",
)
async def download(
    job_id: str,
    file_type: Literal["cv", "cover_letter"],
    store: JobStore = Depends(get_store),
) -> FileResponse:
    """Download CV or cover letter PDF."""
    # First check in-memory store
    result = store.get(job_id)
    file_path = None

    if result is not None:
        file_path = result.cv_path if file_type == "cv" else result.cover_letter_path
    else:
        # Fall back to database
        db = await get_database_service()
        app = await db.get_application_by_job_id(job_id)
        if app is None:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        file_path = app.cv_path if file_type == "cv" else app.cover_letter_path

    filename = f"{file_type}_{job_id}.pdf"

    if file_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"{file_type} not available for job {job_id}",
        )

    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    return FileResponse(path=str(path), media_type="application/pdf", filename=filename)
