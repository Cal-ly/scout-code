"""
API Routes

REST API endpoints for Scout job application processing.

Endpoints:
    POST /api/apply - Start new job application
    GET /api/status/{job_id} - Get pipeline status
    GET /api/download/{job_id}/{file_type} - Download PDF
    GET /api/jobs - List all jobs
    GET /api/logs - Get recent application logs
    GET /api/metrics/status - Get current metrics status
    GET /api/metrics/summary - Get metrics summary for period
    GET /api/metrics/entries - Get paginated metrics entries
    GET /api/metrics/comparison - Get model comparison data
"""

import asyncio
import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

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


# =============================================================================
# LOG ENDPOINTS
# =============================================================================


class LogEntryResponse(BaseModel):
    """Single log entry."""

    timestamp: str
    level: str
    logger: str
    message: str


class LogsResponse(BaseModel):
    """Response containing log entries."""

    entries: list[LogEntryResponse]
    total: int


@router.get(
    "/logs",
    response_model=LogsResponse,
    summary="Get application logs",
    description="Retrieve recent application log entries for debugging.",
)
async def get_logs(
    limit: int = 100,
    level: str | None = None,
    logger_filter: str | None = None,
) -> LogsResponse:
    """
    Get recent application logs.

    Args:
        limit: Maximum number of entries (default 100, max 500).
        level: Filter by level (INFO, WARNING, ERROR, DEBUG).
        logger_filter: Filter by logger name (partial match).

    Returns:
        LogsResponse with recent log entries.
    """
    from src.web.log_handler import get_memory_log_handler

    handler = get_memory_log_handler()
    entries = handler.get_entries(
        limit=min(limit, 500),
        level=level,
        logger_filter=logger_filter,
    )

    return LogsResponse(
        entries=[
            LogEntryResponse(
                timestamp=e.timestamp,
                level=e.level,
                logger=e.logger,
                message=e.message,
            )
            for e in entries
        ],
        total=len(entries),
    )


@router.delete(
    "/logs",
    summary="Clear logs",
    description="Clear all log entries from the memory buffer.",
)
async def clear_logs() -> dict[str, str]:
    """Clear log buffer."""
    from src.web.log_handler import get_memory_log_handler

    handler = get_memory_log_handler()
    handler.clear()
    return {"status": "cleared"}


# =============================================================================
# DIAGNOSTIC ENDPOINTS
# =============================================================================


class ComponentStatus(BaseModel):
    """Status of a single component."""

    name: str
    status: str  # "ok", "error", "not_initialized"
    message: str | None = None
    details: dict | None = None


class DiagnosticsResponse(BaseModel):
    """Full diagnostics response."""

    overall: str
    profile_loaded: bool
    profile_name: str | None = None
    components: list[ComponentStatus]


class ProfileDiagnostics(BaseModel):
    """Profile diagnostic information."""

    loaded: bool
    name: str | None = None
    email: str | None = None
    title: str | None = None
    years_experience: float | None = None
    skill_count: int = 0
    experience_count: int = 0
    education_count: int = 0
    certification_count: int = 0


@router.get(
    "/diagnostics",
    response_model=DiagnosticsResponse,
    summary="Pipeline diagnostics",
    description="Get diagnostic information about all pipeline components.",
)
async def get_diagnostics(
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> DiagnosticsResponse:
    """
    Get diagnostic status of all pipeline components.

    Returns status of each module and service.
    """
    components: list[ComponentStatus] = []
    overall_ok = True

    # Check Collector and Profile
    try:
        collector = orchestrator._collector
        profile = collector.get_profile()
        components.append(
            ComponentStatus(
                name="collector",
                status="ok",
                message=f"Profile loaded: {profile.full_name}",
                details={"profile_hash": collector._profile_hash},
            )
        )
        profile_loaded = True
        profile_name = profile.full_name
    except Exception as e:
        components.append(
            ComponentStatus(name="collector", status="error", message=str(e))
        )
        profile_loaded = False
        profile_name = None
        overall_ok = False

    # Check Rinser (LLM connection)
    try:
        rinser = orchestrator._rinser
        if rinser._initialized:
            components.append(
                ComponentStatus(name="rinser", status="ok", message="Initialized")
            )
        else:
            components.append(
                ComponentStatus(
                    name="rinser", status="not_initialized", message="Not initialized"
                )
            )
            overall_ok = False
    except Exception as e:
        components.append(
            ComponentStatus(name="rinser", status="error", message=str(e))
        )
        overall_ok = False

    # Check Analyzer
    try:
        analyzer = orchestrator._analyzer
        if analyzer._initialized:
            components.append(
                ComponentStatus(name="analyzer", status="ok", message="Initialized")
            )
        else:
            components.append(
                ComponentStatus(
                    name="analyzer", status="not_initialized", message="Not initialized"
                )
            )
            overall_ok = False
    except Exception as e:
        components.append(
            ComponentStatus(name="analyzer", status="error", message=str(e))
        )
        overall_ok = False

    # Check Creator
    try:
        creator = orchestrator._creator
        if creator._initialized:
            components.append(
                ComponentStatus(name="creator", status="ok", message="Initialized")
            )
        else:
            components.append(
                ComponentStatus(
                    name="creator", status="not_initialized", message="Not initialized"
                )
            )
            overall_ok = False
    except Exception as e:
        components.append(
            ComponentStatus(name="creator", status="error", message=str(e))
        )
        overall_ok = False

    # Check Formatter
    try:
        formatter = orchestrator._formatter
        if formatter._initialized:
            components.append(
                ComponentStatus(name="formatter", status="ok", message="Initialized")
            )
        else:
            components.append(
                ComponentStatus(
                    name="formatter",
                    status="not_initialized",
                    message="Not initialized",
                )
            )
            overall_ok = False
    except Exception as e:
        components.append(
            ComponentStatus(name="formatter", status="error", message=str(e))
        )
        overall_ok = False

    # Check LLM Service
    try:
        llm_service = orchestrator._rinser._llm
        health = await llm_service.health_check()
        if health.status == "healthy":
            components.append(
                ComponentStatus(
                    name="llm_service",
                    status="ok",
                    message=f"Ollama: {health.model_loaded or 'unknown'}",
                    details={
                        "status": health.status,
                        "ollama_connected": health.ollama_connected,
                        "model": health.model_loaded,
                    },
                )
            )
        else:
            components.append(
                ComponentStatus(
                    name="llm_service",
                    status="degraded",
                    message=health.last_error or "Unknown error",
                    details={
                        "status": health.status,
                        "ollama_connected": health.ollama_connected,
                    },
                )
            )
            overall_ok = False
    except Exception as e:
        components.append(
            ComponentStatus(name="llm_service", status="error", message=str(e))
        )
        overall_ok = False

    return DiagnosticsResponse(
        overall="ok" if overall_ok else "degraded",
        profile_loaded=profile_loaded,
        profile_name=profile_name,
        components=components,
    )


@router.get(
    "/diagnostics/profile",
    response_model=ProfileDiagnostics,
    summary="Profile diagnostics",
    description="Get detailed information about the loaded user profile.",
)
async def get_profile_diagnostics(
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> ProfileDiagnostics:
    """Get profile details for diagnostics."""
    try:
        collector = orchestrator._collector
        profile = collector.get_profile()
        return ProfileDiagnostics(
            loaded=True,
            name=profile.full_name,
            email=profile.email,
            title=profile.title,
            years_experience=profile.years_experience,
            skill_count=len(profile.skills),
            experience_count=len(profile.experiences),
            education_count=len(profile.education),
            certification_count=len(profile.certifications),
        )
    except Exception:
        return ProfileDiagnostics(loaded=False)


class QuickTestResult(BaseModel):
    """Result of quick component test."""

    component: str
    status: str
    duration_ms: int
    message: str | None = None
    error: str | None = None


class QuickTestResponse(BaseModel):
    """Response from quick test."""

    success: bool
    total_duration_ms: int
    results: list[QuickTestResult]


@router.post(
    "/diagnostics/quick-test",
    response_model=QuickTestResponse,
    summary="Quick pipeline test",
    description="Run a quick test through pipeline components (no LLM calls).",
)
async def run_quick_test(
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> QuickTestResponse:
    """
    Quick test of pipeline components without full LLM processing.

    Tests:
    1. Profile access
    2. Vector store query
    3. Template loading
    """
    import time

    results: list[QuickTestResult] = []
    total_start = time.time()
    all_success = True

    # Test 1: Profile Access
    start = time.time()
    try:
        collector = orchestrator._collector
        profile = collector.get_profile()
        results.append(
            QuickTestResult(
                component="profile_access",
                status="ok",
                duration_ms=int((time.time() - start) * 1000),
                message=f"Profile: {profile.full_name}",
            )
        )
    except Exception as e:
        results.append(
            QuickTestResult(
                component="profile_access",
                status="error",
                duration_ms=int((time.time() - start) * 1000),
                error=str(e),
            )
        )
        all_success = False

    # Test 2: Vector Store Query
    start = time.time()
    try:
        collector = orchestrator._collector
        # Quick semantic search
        matches = await collector.search_skills("Python programming", n_results=3)
        results.append(
            QuickTestResult(
                component="vector_search",
                status="ok",
                duration_ms=int((time.time() - start) * 1000),
                message=f"Found {len(matches)} skill matches",
            )
        )
    except Exception as e:
        results.append(
            QuickTestResult(
                component="vector_search",
                status="error",
                duration_ms=int((time.time() - start) * 1000),
                error=str(e),
            )
        )
        all_success = False

    # Test 3: LLM Connection (just health check, no generation)
    start = time.time()
    try:
        llm_service = orchestrator._rinser._llm
        health = await llm_service.health_check()
        if health.status == "healthy":
            results.append(
                QuickTestResult(
                    component="llm_connection",
                    status="ok",
                    duration_ms=int((time.time() - start) * 1000),
                    message=f"Ollama ready: {health.model_loaded}",
                )
            )
        else:
            results.append(
                QuickTestResult(
                    component="llm_connection",
                    status="warning",
                    duration_ms=int((time.time() - start) * 1000),
                    message=health.last_error or "Not healthy",
                )
            )
    except Exception as e:
        results.append(
            QuickTestResult(
                component="llm_connection",
                status="error",
                duration_ms=int((time.time() - start) * 1000),
                error=str(e),
            )
        )
        all_success = False

    # Test 4: Template Loading
    start = time.time()
    try:
        formatter = orchestrator._formatter
        # Check templates exist
        template_dir = formatter._templates_dir
        if template_dir.exists():
            templates = list(template_dir.glob("*.html"))
            results.append(
                QuickTestResult(
                    component="templates",
                    status="ok",
                    duration_ms=int((time.time() - start) * 1000),
                    message=f"Found {len(templates)} templates",
                )
            )
        else:
            results.append(
                QuickTestResult(
                    component="templates",
                    status="warning",
                    duration_ms=int((time.time() - start) * 1000),
                    message="Template directory not found",
                )
            )
    except Exception as e:
        results.append(
            QuickTestResult(
                component="templates",
                status="error",
                duration_ms=int((time.time() - start) * 1000),
                error=str(e),
            )
        )
        all_success = False

    total_duration = int((time.time() - total_start) * 1000)

    return QuickTestResponse(
        success=all_success,
        total_duration_ms=total_duration,
        results=results,
    )


# =============================================================================
# METRICS ENDPOINTS
# =============================================================================


class MetricsStatusResponse(BaseModel):
    """Current metrics status response."""

    calls_today: int
    success_rate_today: float
    avg_tokens_per_second: float
    avg_duration_seconds: float
    primary_model_success_rate: float
    fallback_usage_rate: float
    current_temperature: float | None
    throttling_warning: bool
    performance_trend: str


class MetricsEntryResponse(BaseModel):
    """Single metrics entry."""

    timestamp: str
    model: str
    module: str | None
    job_id: str | None
    duration_seconds: float
    prompt_tokens: int
    completion_tokens: int
    tokens_per_second: float
    success: bool
    error_type: str | None
    retry_count: int
    fallback_used: bool
    cpu_percent: float | None
    memory_mb: float | None
    temperature_c: float | None


class MetricsEntriesResponse(BaseModel):
    """Paginated metrics entries response."""

    entries: list[MetricsEntryResponse]
    total: int
    skip: int
    limit: int


class MetricsSummaryResponse(BaseModel):
    """Metrics summary response."""

    period_start: str
    period_end: str
    total_calls: int
    total_tokens: int
    successful_calls: int
    avg_tokens_per_second: float
    median_duration_seconds: float
    p95_duration_seconds: float
    success_rate: float
    error_breakdown: dict[str, int]
    fallback_rate: float
    avg_cpu_percent: float | None
    avg_memory_mb: float | None
    avg_temperature_c: float | None


class ModelStatsResponse(BaseModel):
    """Model statistics response."""

    model_name: str
    total_calls: int
    success_count: int
    success_rate: float
    total_tokens: int
    total_duration_seconds: float
    avg_tokens_per_second: float
    avg_duration_seconds: float
    error_breakdown: dict[str, int]


class MetricsComparisonResponse(BaseModel):
    """Model comparison response."""

    models: list[ModelStatsResponse]


@router.get(
    "/metrics/status",
    response_model=MetricsStatusResponse,
    summary="Get current metrics status",
    description="Get real-time performance status including today's statistics.",
)
async def get_metrics_status() -> MetricsStatusResponse:
    """Get current metrics status."""
    from src.services.metrics_service import get_metrics_service

    try:
        metrics = await get_metrics_service()
        status = await metrics.get_status()

        return MetricsStatusResponse(
            calls_today=status.calls_today,
            success_rate_today=status.success_rate_today,
            avg_tokens_per_second=status.avg_tokens_per_second,
            avg_duration_seconds=status.avg_duration_seconds,
            primary_model_success_rate=status.primary_model_success_rate,
            fallback_usage_rate=status.fallback_usage_rate,
            current_temperature=status.current_temperature,
            throttling_warning=status.throttling_warning,
            performance_trend=status.performance_trend,
        )
    except Exception as e:
        logger.error(f"Failed to get metrics status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/metrics/summary",
    response_model=MetricsSummaryResponse,
    summary="Get metrics summary",
    description="Get performance summary for a time period.",
)
async def get_metrics_summary(
    days: int = 7,
) -> MetricsSummaryResponse:
    """
    Get metrics summary for specified period.

    Args:
        days: Number of days to include (default 7, max 90).
    """
    from datetime import datetime, timedelta

    from src.services.metrics_service import get_metrics_service

    try:
        metrics = await get_metrics_service()

        # Calculate period
        end = datetime.now()
        start = end - timedelta(days=min(days, 90))

        summary = await metrics.get_summary(start=start, end=end)

        return MetricsSummaryResponse(
            period_start=summary.period_start.isoformat(),
            period_end=summary.period_end.isoformat(),
            total_calls=summary.total_calls,
            total_tokens=summary.total_tokens,
            successful_calls=summary.successful_calls,
            avg_tokens_per_second=summary.avg_tokens_per_second,
            median_duration_seconds=summary.median_duration_seconds,
            p95_duration_seconds=summary.p95_duration_seconds,
            success_rate=summary.success_rate,
            error_breakdown=summary.error_breakdown,
            fallback_rate=summary.fallback_rate,
            avg_cpu_percent=summary.avg_cpu_percent,
            avg_memory_mb=summary.avg_memory_mb,
            avg_temperature_c=summary.avg_temperature_c,
        )
    except Exception as e:
        logger.error(f"Failed to get metrics summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/metrics/entries",
    response_model=MetricsEntriesResponse,
    summary="Get metrics entries",
    description="Get paginated list of metrics entries with filtering.",
)
async def get_metrics_entries(
    skip: int = 0,
    limit: int = 50,
    model: str | None = None,
    module: str | None = None,
    success: bool | None = None,
    sort_by: str = "timestamp",
    sort_order: str = "desc",
) -> MetricsEntriesResponse:
    """
    Get paginated metrics entries with optional filtering.

    Args:
        skip: Number of entries to skip.
        limit: Maximum entries to return (max 100).
        model: Filter by model name.
        module: Filter by module name.
        success: Filter by success status.
        sort_by: Sort field (timestamp, duration, tokens_per_second).
        sort_order: Sort order (asc, desc).
    """
    from src.services.metrics_service import get_metrics_service

    try:
        metrics = await get_metrics_service()

        # Get all entries (we'll filter/sort in memory for simplicity)
        all_entries = metrics._entries.copy()

        # Apply filters
        if model:
            all_entries = [e for e in all_entries if e.model == model]
        if module:
            all_entries = [e for e in all_entries if e.module == module]
        if success is not None:
            all_entries = [e for e in all_entries if e.success == success]

        # Sort entries
        reverse = sort_order == "desc"
        if sort_by == "timestamp":
            all_entries.sort(key=lambda e: e.timestamp, reverse=reverse)
        elif sort_by == "duration":
            all_entries.sort(key=lambda e: e.duration_seconds, reverse=reverse)
        elif sort_by == "tokens_per_second":
            all_entries.sort(key=lambda e: e.tokens_per_second, reverse=reverse)

        # Paginate
        total = len(all_entries)
        limit = min(limit, 100)
        paginated = all_entries[skip : skip + limit]

        # Convert to response
        entries = [
            MetricsEntryResponse(
                timestamp=e.timestamp.isoformat(),
                model=e.model,
                module=e.module,
                job_id=e.job_id,
                duration_seconds=e.duration_seconds,
                prompt_tokens=e.prompt_tokens,
                completion_tokens=e.completion_tokens,
                tokens_per_second=e.tokens_per_second,
                success=e.success,
                error_type=e.error_type,
                retry_count=e.retry_count,
                fallback_used=e.fallback_used,
                cpu_percent=e.cpu_percent,
                memory_mb=e.memory_mb,
                temperature_c=e.temperature_c,
            )
            for e in paginated
        ]

        return MetricsEntriesResponse(
            entries=entries,
            total=total,
            skip=skip,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Failed to get metrics entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/metrics/comparison",
    response_model=MetricsComparisonResponse,
    summary="Get model comparison",
    description="Compare performance metrics between different models.",
)
async def get_metrics_comparison() -> MetricsComparisonResponse:
    """Get model comparison statistics."""
    from src.services.metrics_service import get_metrics_service

    try:
        metrics = await get_metrics_service()
        comparison = await metrics.get_model_comparison()

        models = [
            ModelStatsResponse(
                model_name=stats.model_name,
                total_calls=stats.total_calls,
                success_count=stats.success_count,
                success_rate=stats.success_rate,
                total_tokens=stats.total_tokens,
                total_duration_seconds=stats.total_duration_seconds,
                avg_tokens_per_second=stats.avg_tokens_per_second,
                avg_duration_seconds=stats.avg_duration_seconds,
                error_breakdown=stats.error_breakdown,
            )
            for stats in comparison.values()
        ]

        return MetricsComparisonResponse(models=models)
    except Exception as e:
        logger.error(f"Failed to get metrics comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))
