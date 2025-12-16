# Task: API Hardening & Separation-Ready Architecture

## Overview

**Task ID:** SCOUT-API-HARDENING  
**Priority:** High  
**Estimated Effort:** 2-4 hours  
**Dependencies:** Tasks A, C, E must be complete

Refactor the Scout web API into a clean, versioned, domain-organized structure that is ready for future frontend separation (Vue SPA). This involves reorganizing endpoints, adding versioning, improving documentation, and ensuring clean separation between API routes and page routes.

---

## Context

### Current State

The web layer has grown organically with endpoints spread across multiple files:

```
src/web/
├── main.py                 # App setup, health/info endpoints
├── routes/
│   ├── api.py              # Mixed: jobs, logs, metrics, diagnostics (~600 lines)
│   ├── notifications.py    # Notification endpoints
│   ├── pages.py            # HTML page routes
│   └── profile.py          # Profile endpoints (Tasks C, E additions)
```

**Problems:**
- `api.py` is too large (600+ lines) with mixed domains
- No API versioning
- Endpoints scattered without clear organization
- Health/info endpoints in `main.py` instead of routes
- No clear separation between API (JSON) and Pages (HTML)
- Missing skill aliases endpoints from Task A

### Target Architecture

```
src/web/
├── main.py                 # App setup only (minimal)
├── routes/
│   ├── __init__.py         # Clean exports
│   ├── pages.py            # HTML pages (unchanged)
│   └── api/
│       ├── __init__.py     # API router aggregation
│       ├── v1/
│       │   ├── __init__.py # V1 router with all domains
│       │   ├── jobs.py     # /api/v1/jobs/*
│       │   ├── profile.py  # /api/v1/profile/*
│       │   ├── skills.py   # /api/v1/skills/* (NEW - Task A)
│       │   ├── notifications.py  # /api/v1/notifications/*
│       │   ├── metrics.py  # /api/v1/metrics/*
│       │   ├── diagnostics.py    # /api/v1/diagnostics/*
│       │   ├── logs.py     # /api/v1/logs/*
│       │   └── system.py   # /api/v1/health, /api/v1/info
│       └── schemas/        # Shared Pydantic models
│           ├── __init__.py
│           ├── jobs.py
│           ├── profile.py
│           ├── metrics.py
│           └── common.py
├── static/                 # Unchanged
└── templates/              # Unchanged
```

**Benefits:**
- Clear API versioning (`/api/v1/`)
- Domain-driven organization
- Easy to add `/api/v2/` later
- Clean separation for future Vue frontend
- Better OpenAPI documentation grouping
- Maintainable file sizes (~100-200 lines each)

---

## Implementation Requirements

### Phase 1: Create Directory Structure

```bash
# On Pi
cd /home/cally/projects/scout-code/src/web/routes
mkdir -p api/v1
mkdir -p api/schemas
touch api/__init__.py
touch api/v1/__init__.py
touch api/schemas/__init__.py
```

### Phase 2: Create Schema Files

#### 2.1 Common Schemas

**File:** `src/web/routes/api/schemas/common.py`

```python
"""Common API schemas used across multiple domains."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    detail: str
    code: str | None = None


class SuccessResponse(BaseModel):
    """Standard success response."""
    
    status: str = "success"
    message: str | None = None


class PaginationParams(BaseModel):
    """Pagination parameters."""
    
    skip: int = 0
    limit: int = 20


class PaginatedResponse(BaseModel):
    """Base paginated response."""
    
    total: int
    skip: int
    limit: int
```

#### 2.2 Job Schemas

**File:** `src/web/routes/api/schemas/jobs.py`

```python
"""Job-related API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class ApplyRequest(BaseModel):
    """Request to start job application pipeline."""
    
    job_text: str = Field(..., min_length=100, description="Raw job posting text")
    source: str = Field(default="web", description="Source of job posting")


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
    current_step: str | None
    job_title: str | None
    company_name: str | None
    compatibility_score: int | None
    cv_path: str | None
    cover_letter_path: str | None
    steps: list[StepInfo]
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
    total_duration_ms: int


class JobSummary(BaseModel):
    """Job summary for list views."""
    
    job_id: str
    job_title: str | None
    company_name: str | None
    status: str
    compatibility_score: int | None
    submitted_at: datetime | None
    completed_at: datetime | None


class JobListResponse(BaseModel):
    """Paginated job list response."""
    
    jobs: list[JobSummary]
    total: int
    skip: int
    limit: int
```

#### 2.3 Profile Schemas

**File:** `src/web/routes/api/schemas/profile.py`

```python
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
```

#### 2.4 Metrics Schemas

**File:** `src/web/routes/api/schemas/metrics.py`

```python
"""Metrics-related API schemas."""

from datetime import datetime

from pydantic import BaseModel


class MetricsStatusResponse(BaseModel):
    """Current metrics status."""
    
    calls_today: int
    success_rate_today: float
    avg_tokens_per_second: float
    avg_duration_seconds: float
    primary_model_success_rate: float
    fallback_usage_rate: float
    current_cpu_percent: float | None
    current_memory_percent: float | None
    current_temperature: float | None
    throttling_warning: bool
    performance_trend: str


class MetricsSummaryResponse(BaseModel):
    """Metrics summary for period."""
    
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
    """Paginated metrics entries."""
    
    entries: list[MetricsEntryResponse]
    total: int
    skip: int
    limit: int


class ModelStatsResponse(BaseModel):
    """Model statistics."""
    
    model_name: str
    total_calls: int
    success_count: int
    success_rate: float
    total_tokens: int
    total_duration_seconds: float
    avg_tokens_per_second: float
    avg_duration_seconds: float
    error_breakdown: dict[str, int]


class ModelComparisonResponse(BaseModel):
    """Model comparison data."""
    
    models: list[ModelStatsResponse]


class SystemMetricsPointResponse(BaseModel):
    """Single system metrics point."""
    
    timestamp: str
    cpu_percent: float | None
    memory_percent: float | None
    memory_mb: float | None
    temperature_c: float | None


class SystemMetricsHistoryResponse(BaseModel):
    """System metrics time-series."""
    
    points: list[SystemMetricsPointResponse]
    minutes: int
    count: int
```

#### 2.5 Schema Package Init

**File:** `src/web/routes/api/schemas/__init__.py`

```python
"""API Schema exports."""

from src.web.routes.api.schemas.common import (
    ErrorResponse,
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
)
from src.web.routes.api.schemas.jobs import (
    ApplyRequest,
    ApplyResponse,
    JobListResponse,
    JobSummary,
    QuickScoreRequest,
    QuickScoreResponse,
    StatusResponse,
    StepInfo,
)
from src.web.routes.api.schemas.metrics import (
    MetricsEntriesResponse,
    MetricsEntryResponse,
    MetricsStatusResponse,
    MetricsSummaryResponse,
    ModelComparisonResponse,
    ModelStatsResponse,
    SystemMetricsHistoryResponse,
    SystemMetricsPointResponse,
)
from src.web.routes.api.schemas.profile import (
    ProfileAssessmentResponse,
    ProfileCreateRequest,
    ProfileCreateResponse,
    ProfileStatusResponse,
    ProfileSummaryResponse,
    SectionScoreResponse,
)

__all__ = [
    # Common
    "ErrorResponse",
    "SuccessResponse",
    "PaginationParams",
    "PaginatedResponse",
    # Jobs
    "ApplyRequest",
    "ApplyResponse",
    "QuickScoreRequest",
    "QuickScoreResponse",
    "StatusResponse",
    "StepInfo",
    "JobSummary",
    "JobListResponse",
    # Profile
    "ProfileStatusResponse",
    "ProfileCreateRequest",
    "ProfileCreateResponse",
    "ProfileAssessmentResponse",
    "ProfileSummaryResponse",
    "SectionScoreResponse",
    # Metrics
    "MetricsStatusResponse",
    "MetricsSummaryResponse",
    "MetricsEntryResponse",
    "MetricsEntriesResponse",
    "ModelStatsResponse",
    "ModelComparisonResponse",
    "SystemMetricsPointResponse",
    "SystemMetricsHistoryResponse",
]
```

### Phase 3: Create V1 Route Modules

#### 3.1 System Routes (Health/Info)

**File:** `src/web/routes/api/v1/system.py`

```python
"""
System API Routes

Health checks and application info.

Endpoints:
    GET /api/v1/health - Health check
    GET /api/v1/info - Application info
"""

import logging

from fastapi import APIRouter

from src.services.notification import get_notification_service
from src.services.pipeline import get_pipeline_orchestrator
from src.web.dependencies import get_job_store

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])

APP_NAME = "Scout"
APP_VERSION = "0.1.0"


@router.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint.
    
    Returns application health status with service checks.
    """
    services: dict[str, str] = {}
    overall_healthy = True

    # Check pipeline orchestrator
    try:
        orchestrator = await get_pipeline_orchestrator()
        if orchestrator._initialized:
            services["pipeline"] = "ok"
        else:
            services["pipeline"] = "not_initialized"
            overall_healthy = False
    except Exception as e:
        services["pipeline"] = f"error: {e}"
        overall_healthy = False

    # Check job store
    try:
        store = get_job_store()
        services["job_store"] = "ok" if store else "not_available"
        if not store:
            overall_healthy = False
    except Exception as e:
        services["job_store"] = f"error: {e}"
        overall_healthy = False

    # Check notification service
    try:
        notification_service = get_notification_service()
        services["notifications"] = "ok" if notification_service else "not_available"
        if not notification_service:
            overall_healthy = False
    except Exception as e:
        services["notifications"] = f"error: {e}"
        overall_healthy = False

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "version": APP_VERSION,
        "services": services,
    }


@router.get("/info")
async def app_info() -> dict:
    """
    Application info endpoint.
    
    Returns basic application metadata.
    """
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "ready",
        "docs": "/docs",
        "api_version": "v1",
    }
```

#### 3.2 Jobs Routes

**File:** `src/web/routes/api/v1/jobs.py`

```python
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
    """Execute pipeline in background with timeout."""
    try:
        logger.info(f"Starting pipeline for job {job_id}")
        result = await asyncio.wait_for(
            orchestrator.execute(input_data),
            timeout=PIPELINE_TIMEOUT_SECONDS,
        )
        store.store(result)
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

    except Exception as e:
        logger.error(f"Pipeline failed for job {job_id}: {e}")
        error_result = PipelineResult(
            pipeline_id=job_id,
            status=PipelineStatus.FAILED,
            started_at=datetime.now(),
            error=str(e),
        )
        store.store(error_result)


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
    logger.info(f"Apply request: job_id={job_id}, source={request.source}")

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
    store: JobStore = Depends(get_store),
) -> JobListResponse:
    """Get paginated list of job applications."""
    all_results = store.list_all()
    total = len(all_results)
    paginated = all_results[skip : skip + limit]
    summaries = [_result_to_summary(r) for r in paginated]

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
    result = store.get(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return _result_to_status_response(result)


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
    result = store.get(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    file_path = result.cv_path if file_type == "cv" else result.cover_letter_path
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
```

#### 3.3 Skills Routes (NEW - Task A Integration)

**File:** `src/web/routes/api/v1/skills.py`

```python
"""
Skills API Routes

Skill alias and normalization endpoints.

Endpoints:
    GET /api/v1/skills/aliases - Get all skill aliases
    GET /api/v1/skills/normalize - Normalize a skill name
    GET /api/v1/skills/expand - Expand skill to include aliases
    GET /api/v1/skills/search - Search skills (semantic)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from src.modules.collector import (
    SKILL_ALIASES,
    expand_skill_query,
    get_all_canonical_skills,
    get_collector,
    is_known_skill,
    normalize_skill_name,
)
from src.modules.collector.collector import Collector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skills", tags=["skills"])


async def get_collector_dep() -> Collector:
    """Get collector dependency."""
    return await get_collector()


@router.get(
    "/aliases",
    summary="Get all skill aliases",
    description="Returns the complete skill alias mapping.",
)
async def get_aliases() -> dict:
    """Get all skill aliases."""
    return {
        "aliases": SKILL_ALIASES,
        "canonical_skills": get_all_canonical_skills(),
        "total_canonical": len(SKILL_ALIASES),
    }


@router.get(
    "/normalize",
    summary="Normalize skill name",
    description="Convert a skill name or alias to its canonical form.",
)
async def normalize(
    skill: str = Query(..., description="Skill name to normalize"),
) -> dict:
    """Normalize a skill name to canonical form."""
    canonical = normalize_skill_name(skill)
    return {
        "input": skill,
        "canonical": canonical,
        "is_known": is_known_skill(skill),
    }


@router.get(
    "/expand",
    summary="Expand skill to aliases",
    description="Get all known aliases for a skill.",
)
async def expand(
    skill: str = Query(..., description="Skill to expand"),
) -> dict:
    """Expand skill name to include all aliases."""
    expanded = expand_skill_query(skill)
    return {
        "input": skill,
        "canonical": normalize_skill_name(skill),
        "expanded": expanded,
        "count": len(expanded),
    }


@router.get(
    "/search",
    summary="Search skills semantically",
    description="Search for skills matching a query using semantic similarity.",
)
async def search_skills(
    query: str = Query(..., description="Search query"),
    top_k: int = Query(default=5, ge=1, le=20, description="Number of results"),
    min_score: float = Query(default=0.3, ge=0, le=1, description="Minimum similarity score"),
    collector: Collector = Depends(get_collector_dep),
) -> dict:
    """Search for matching skills."""
    try:
        # Ensure profile is loaded
        try:
            collector.get_profile()
        except Exception:
            await collector.load_profile()

        matches = await collector.search_skills(query, n_results=top_k)
        
        # Filter by minimum score
        filtered = [m for m in matches if m.score >= min_score]

        return {
            "query": query,
            "expanded_query": expand_skill_query(query),
            "matches": [
                {
                    "skill": m.metadata.get("name", ""),
                    "canonical": m.metadata.get("canonical_name", ""),
                    "level": m.metadata.get("level", ""),
                    "years": m.metadata.get("years", 0),
                    "score": round(m.score, 3),
                }
                for m in filtered
            ],
            "count": len(filtered),
        }

    except Exception as e:
        logger.error(f"Skill search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

#### 3.4 Profile Routes

**File:** `src/web/routes/api/v1/profile.py`

```python
"""
Profile API Routes

User profile management endpoints.

Endpoints:
    GET /api/v1/profile/status - Check profile status
    GET /api/v1/profile - Get profile data
    POST /api/v1/profile - Create/update profile (text-based)
    POST /api/v1/profile/index - Re-index profile
    GET /api/v1/profile/assessment - Get completeness assessment
    GET /api/v1/profile/summary - Get quick summary with score
    GET /api/v1/profile/editor-data - Get data for form editor
    POST /api/v1/profile/editor-save - Save from form editor
    POST /api/v1/profile/assess - Assess without saving
    POST /api/v1/profile/export-yaml - Export as YAML download
"""

import logging
from datetime import datetime
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import ValidationError

from src.modules.collector import (
    Collector,
    ProfileAssessment,
    assess_profile,
    get_collector,
)
from src.modules.collector.models import (
    Certification,
    Education,
    Experience,
    Skill,
    SkillLevel,
    UserProfile,
)
from src.services.profile import (
    ProfileCreateRequest,
    ProfileCreateResponse,
    ProfileData,
    ProfileIndexRequest,
    ProfileIndexResponse,
    ProfileNotFoundError,
    ProfileService,
    ProfileStatus,
    ProfileValidationError,
    get_profile_service,
)
from src.web.routes.api.schemas import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["profile"])

DEFAULT_PROFILE_PATH = Path("data/profile.yaml")


# Dependencies
async def get_profile_svc() -> ProfileService:
    """Get profile service."""
    return await get_profile_service()


async def get_collector_dep() -> Collector:
    """Get collector module."""
    return await get_collector()


# =============================================================================
# TEXT-BASED PROFILE (ProfileService)
# =============================================================================


@router.get("/status", response_model=ProfileStatus)
async def get_status(service: ProfileService = Depends(get_profile_svc)) -> ProfileStatus:
    """Check if profile exists and is indexed."""
    return await service.get_status()


@router.get("/retrieve", response_model=ProfileData)
async def get_profile(service: ProfileService = Depends(get_profile_svc)) -> ProfileData:
    """Get current profile data (text-based)."""
    try:
        return await service.get_profile()
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail="No profile found")


@router.post("/create", response_model=ProfileCreateResponse)
async def create_profile(
    request: ProfileCreateRequest,
    service: ProfileService = Depends(get_profile_svc),
) -> ProfileCreateResponse:
    """Create or update profile from text."""
    try:
        return await service.create_profile(request.profile_text)
    except ProfileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/index", response_model=ProfileIndexResponse)
async def index_profile(
    request: ProfileIndexRequest,
    service: ProfileService = Depends(get_profile_svc),
) -> ProfileIndexResponse:
    """Re-index profile for semantic search."""
    try:
        return await service.index_profile(request.profile_id)
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail="Profile not found")


# =============================================================================
# YAML-BASED PROFILE (Collector)
# =============================================================================


@router.get("/assessment", response_model=ProfileAssessment)
async def get_assessment(collector: Collector = Depends(get_collector_dep)) -> ProfileAssessment:
    """Get profile completeness assessment with scores and suggestions."""
    try:
        try:
            collector.get_profile()
        except Exception:
            await collector.load_profile()
        return collector.assess_profile_completeness()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_summary(collector: Collector = Depends(get_collector_dep)) -> dict:
    """Get quick profile summary with score."""
    try:
        try:
            profile = collector.get_profile()
        except Exception:
            await collector.load_profile()
            profile = collector.get_profile()

        assessment = collector.assess_profile_completeness()
        return {
            "name": profile.full_name,
            "title": profile.title,
            "completeness_score": assessment.overall_score,
            "grade": assessment.grade.value,
            "is_job_ready": assessment.is_job_ready,
            "top_suggestion": assessment.top_suggestions[0] if assessment.top_suggestions else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# FORM EDITOR ENDPOINTS
# =============================================================================


@router.get("/editor-data")
async def get_editor_data(collector: Collector = Depends(get_collector_dep)) -> dict:
    """Get profile data for form editor."""
    try:
        try:
            profile = collector.get_profile()
        except Exception:
            await collector.load_profile()
            profile = collector.get_profile()
        return profile.model_dump(mode="json")
    except Exception:
        raise HTTPException(status_code=404, detail="No profile found")


@router.post("/editor-save")
async def save_editor_data(
    profile_data: dict,
    collector: Collector = Depends(get_collector_dep),
) -> dict:
    """Save profile from form editor."""
    try:
        profile = _parse_profile_data(profile_data)
        DEFAULT_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(DEFAULT_PROFILE_PATH, "w") as f:
            yaml.dump(
                profile.model_dump(mode="json"),
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        await collector.load_profile(DEFAULT_PROFILE_PATH)
        await collector.clear_index()
        chunk_count = await collector.index_profile()

        return {"status": "saved", "message": "Profile saved successfully", "chunk_count": chunk_count}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assess", response_model=ProfileAssessment)
async def assess_profile_data(profile_data: dict) -> ProfileAssessment:
    """Assess profile without saving."""
    try:
        profile = _parse_profile_data(profile_data)
        return assess_profile(profile)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/export-yaml")
async def export_yaml(profile_data: dict) -> Response:
    """Export profile as YAML file."""
    try:
        profile = _parse_profile_data(profile_data)
        yaml_content = yaml.dump(
            profile.model_dump(mode="json"),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        return Response(
            content=yaml_content,
            media_type="application/x-yaml",
            headers={"Content-Disposition": "attachment; filename=profile.yaml"},
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _parse_profile_data(data: dict) -> UserProfile:
    """Parse profile data from editor form."""
    skills = []
    for s in data.get("skills", []):
        if s.get("name"):
            try:
                level = SkillLevel(s.get("level", "intermediate"))
            except ValueError:
                level = SkillLevel.INTERMEDIATE
            skills.append(Skill(
                name=s["name"], level=level, years=s.get("years"), keywords=s.get("keywords", [])
            ))

    experiences = []
    for e in data.get("experiences", []):
        if e.get("company") and e.get("role"):
            experiences.append(Experience(
                company=e["company"],
                role=e["role"],
                start_date=_parse_date(e.get("start_date")),
                end_date=_parse_date(e.get("end_date")),
                current=e.get("current", False),
                description=e.get("description", ""),
                achievements=e.get("achievements", []),
                technologies=e.get("technologies", []),
            ))

    education = []
    for ed in data.get("education", []):
        if ed.get("institution"):
            education.append(Education(
                institution=ed["institution"],
                degree=ed.get("degree", ""),
                field=ed.get("field", ""),
                start_date=_parse_date(ed.get("start_date")),
                end_date=_parse_date(ed.get("end_date")),
                gpa=ed.get("gpa"),
                relevant_courses=ed.get("relevant_courses", []),
            ))

    certifications = []
    for c in data.get("certifications", []):
        if c.get("name"):
            certifications.append(Certification(
                name=c["name"],
                issuer=c.get("issuer", ""),
                date_obtained=_parse_date(c.get("date_obtained")),
                expiry_date=_parse_date(c.get("expiry_date")),
                credential_id=c.get("credential_id"),
            ))

    return UserProfile(
        full_name=data.get("full_name", ""),
        email=data.get("email", ""),
        phone=data.get("phone"),
        location=data.get("location", ""),
        linkedin_url=data.get("linkedin_url"),
        github_url=data.get("github_url"),
        title=data.get("title", ""),
        years_experience=data.get("years_experience", 0.0),
        summary=data.get("summary", ""),
        skills=skills,
        experiences=experiences,
        education=education,
        certifications=certifications,
        last_updated=datetime.now(),
    )


def _parse_date(date_str: str | None) -> datetime | None:
    """Parse date string."""
    if not date_str:
        return None
    try:
        if "T" in date_str:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m")
        except ValueError:
            return None
```

#### 3.5 Notifications Routes

**File:** `src/web/routes/api/v1/notifications.py`

```python
"""
Notifications API Routes

Notification management endpoints.

Endpoints:
    GET /api/v1/notifications - Get notifications
    POST /api/v1/notifications/{id}/read - Mark as read
    POST /api/v1/notifications/read-all - Mark all as read
    DELETE /api/v1/notifications - Clear all
"""

import logging

from fastapi import APIRouter, Depends

from src.services.notification import (
    NotificationList,
    NotificationService,
    get_notification_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_service() -> NotificationService:
    """Get notification service."""
    return get_notification_service()


@router.get("", response_model=NotificationList)
async def get_notifications(
    unread_only: bool = False,
    limit: int = 20,
    service: NotificationService = Depends(get_service),
) -> NotificationList:
    """Get notifications."""
    return service.get_unread() if unread_only else service.get_all(limit=limit)


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    service: NotificationService = Depends(get_service),
) -> dict:
    """Mark notification as read."""
    return {"success": service.mark_read(notification_id)}


@router.post("/read-all")
async def mark_all_read(service: NotificationService = Depends(get_service)) -> dict:
    """Mark all as read."""
    return {"marked_read": service.mark_all_read()}


@router.delete("")
async def clear_all(service: NotificationService = Depends(get_service)) -> dict:
    """Clear all notifications."""
    return {"cleared": service.clear_all()}
```

#### 3.6 Logs Routes

**File:** `src/web/routes/api/v1/logs.py`

```python
"""
Logs API Routes

Application log endpoints.

Endpoints:
    GET /api/v1/logs - Get log entries
    DELETE /api/v1/logs - Clear logs
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["logs"])


class LogEntry(BaseModel):
    """Single log entry."""
    timestamp: str
    level: str
    logger: str
    message: str


class LogsResponse(BaseModel):
    """Logs response."""
    entries: list[LogEntry]
    total: int


@router.get("", response_model=LogsResponse)
async def get_logs(
    limit: int = 100,
    level: str | None = None,
    logger_filter: str | None = None,
) -> LogsResponse:
    """Get application logs."""
    from src.web.log_handler import get_memory_log_handler

    handler = get_memory_log_handler()
    entries = handler.get_entries(
        limit=min(limit, 500),
        level=level,
        logger_filter=logger_filter,
    )

    return LogsResponse(
        entries=[
            LogEntry(
                timestamp=e.timestamp,
                level=e.level,
                logger=e.logger,
                message=e.message,
            )
            for e in entries
        ],
        total=len(entries),
    )


@router.delete("")
async def clear_logs() -> dict:
    """Clear log buffer."""
    from src.web.log_handler import get_memory_log_handler

    handler = get_memory_log_handler()
    handler.clear()
    return {"status": "cleared"}
```

#### 3.7 Metrics Routes

**File:** `src/web/routes/api/v1/metrics.py`

```python
"""
Metrics API Routes

Performance metrics endpoints.

Endpoints:
    GET /api/v1/metrics/status - Current status
    GET /api/v1/metrics/summary - Summary for period
    GET /api/v1/metrics/entries - Paginated entries
    GET /api/v1/metrics/comparison - Model comparison
    GET /api/v1/metrics/system-history - System metrics history
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException

from src.web.routes.api.schemas import (
    MetricsEntriesResponse,
    MetricsEntryResponse,
    MetricsStatusResponse,
    MetricsSummaryResponse,
    ModelComparisonResponse,
    ModelStatsResponse,
    SystemMetricsHistoryResponse,
    SystemMetricsPointResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/status", response_model=MetricsStatusResponse)
async def get_status() -> MetricsStatusResponse:
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
            current_cpu_percent=status.current_cpu_percent,
            current_memory_percent=status.current_memory_percent,
            current_temperature=status.current_temperature,
            throttling_warning=status.throttling_warning,
            performance_trend=status.performance_trend,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", response_model=MetricsSummaryResponse)
async def get_summary(days: int = 7) -> MetricsSummaryResponse:
    """Get metrics summary for period."""
    from src.services.metrics_service import get_metrics_service

    try:
        metrics = await get_metrics_service()
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entries", response_model=MetricsEntriesResponse)
async def get_entries(
    skip: int = 0,
    limit: int = 50,
    model: str | None = None,
    module: str | None = None,
    success: bool | None = None,
    sort_by: str = "timestamp",
    sort_order: str = "desc",
) -> MetricsEntriesResponse:
    """Get paginated metrics entries."""
    from src.services.metrics_service import get_metrics_service

    try:
        metrics = await get_metrics_service()
        entries = metrics._entries.copy()

        # Filter
        if model:
            entries = [e for e in entries if e.model == model]
        if module:
            entries = [e for e in entries if e.module == module]
        if success is not None:
            entries = [e for e in entries if e.success == success]

        # Sort
        reverse = sort_order == "desc"
        if sort_by == "timestamp":
            entries.sort(key=lambda e: e.timestamp, reverse=reverse)
        elif sort_by == "duration":
            entries.sort(key=lambda e: e.duration_seconds, reverse=reverse)
        elif sort_by == "tokens_per_second":
            entries.sort(key=lambda e: e.tokens_per_second, reverse=reverse)

        # Paginate
        total = len(entries)
        limit = min(limit, 100)
        paginated = entries[skip : skip + limit]

        return MetricsEntriesResponse(
            entries=[
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
            ],
            total=total,
            skip=skip,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comparison", response_model=ModelComparisonResponse)
async def get_comparison() -> ModelComparisonResponse:
    """Get model comparison data."""
    from src.services.metrics_service import get_metrics_service

    try:
        metrics = await get_metrics_service()
        comparison = await metrics.get_model_comparison()

        return ModelComparisonResponse(
            models=[
                ModelStatsResponse(
                    model_name=s.model_name,
                    total_calls=s.total_calls,
                    success_count=s.success_count,
                    success_rate=s.success_rate,
                    total_tokens=s.total_tokens,
                    total_duration_seconds=s.total_duration_seconds,
                    avg_tokens_per_second=s.avg_tokens_per_second,
                    avg_duration_seconds=s.avg_duration_seconds,
                    error_breakdown=s.error_breakdown,
                )
                for s in comparison.values()
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system-history", response_model=SystemMetricsHistoryResponse)
async def get_system_history(minutes: int = 15) -> SystemMetricsHistoryResponse:
    """Get system metrics time-series."""
    from src.services.metrics_service import get_metrics_service

    try:
        metrics = await get_metrics_service()
        points = await metrics.get_system_metrics_history(minutes=minutes)

        return SystemMetricsHistoryResponse(
            points=[
                SystemMetricsPointResponse(
                    timestamp=p.timestamp.isoformat(),
                    cpu_percent=p.cpu_percent,
                    memory_percent=p.memory_percent,
                    memory_mb=p.memory_mb,
                    temperature_c=p.temperature_c,
                )
                for p in points
            ],
            minutes=minutes,
            count=len(points),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### 3.8 Diagnostics Routes

**File:** `src/web/routes/api/v1/diagnostics.py`

```python
"""
Diagnostics API Routes

Pipeline diagnostics and health endpoints.

Endpoints:
    GET /api/v1/diagnostics - Full diagnostics
    GET /api/v1/diagnostics/profile - Profile diagnostics
    POST /api/v1/diagnostics/quick-test - Quick component test
"""

import logging
import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.services.pipeline import PipelineOrchestrator
from src.web.dependencies import get_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


class ComponentStatus(BaseModel):
    """Component status."""
    name: str
    status: str
    message: str | None = None
    details: dict | None = None


class DiagnosticsResponse(BaseModel):
    """Full diagnostics response."""
    overall: str
    profile_loaded: bool
    profile_name: str | None = None
    components: list[ComponentStatus]


class ProfileDiagnostics(BaseModel):
    """Profile diagnostics."""
    loaded: bool
    name: str | None = None
    email: str | None = None
    title: str | None = None
    years_experience: float | None = None
    skill_count: int = 0
    experience_count: int = 0
    education_count: int = 0
    certification_count: int = 0


class QuickTestResult(BaseModel):
    """Quick test result."""
    component: str
    status: str
    duration_ms: int
    message: str | None = None
    error: str | None = None


class QuickTestResponse(BaseModel):
    """Quick test response."""
    success: bool
    total_duration_ms: int
    results: list[QuickTestResult]


@router.get("", response_model=DiagnosticsResponse)
async def get_diagnostics(
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> DiagnosticsResponse:
    """Get full pipeline diagnostics."""
    components: list[ComponentStatus] = []
    overall_ok = True
    profile_loaded = False
    profile_name = None

    # Check Collector
    try:
        collector = orchestrator._collector
        profile = collector.get_profile()
        components.append(ComponentStatus(
            name="collector",
            status="ok",
            message=f"Profile: {profile.full_name}",
            details={"profile_hash": collector._profile_hash},
        ))
        profile_loaded = True
        profile_name = profile.full_name
    except Exception as e:
        components.append(ComponentStatus(name="collector", status="error", message=str(e)))
        overall_ok = False

    # Check other modules
    for name, module in [
        ("rinser", orchestrator._rinser),
        ("analyzer", orchestrator._analyzer),
        ("creator", orchestrator._creator),
        ("formatter", orchestrator._formatter),
    ]:
        try:
            if module._initialized:
                components.append(ComponentStatus(name=name, status="ok", message="Initialized"))
            else:
                components.append(ComponentStatus(name=name, status="not_initialized"))
                overall_ok = False
        except Exception as e:
            components.append(ComponentStatus(name=name, status="error", message=str(e)))
            overall_ok = False

    # Check LLM
    try:
        llm = orchestrator._rinser._llm
        health = await llm.health_check()
        if health.status == "healthy":
            components.append(ComponentStatus(
                name="llm_service",
                status="ok",
                message=f"Ollama: {health.model_loaded}",
            ))
        else:
            components.append(ComponentStatus(
                name="llm_service",
                status="degraded",
                message=health.last_error,
            ))
            overall_ok = False
    except Exception as e:
        components.append(ComponentStatus(name="llm_service", status="error", message=str(e)))
        overall_ok = False

    return DiagnosticsResponse(
        overall="ok" if overall_ok else "degraded",
        profile_loaded=profile_loaded,
        profile_name=profile_name,
        components=components,
    )


@router.get("/profile", response_model=ProfileDiagnostics)
async def get_profile_diagnostics(
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> ProfileDiagnostics:
    """Get profile details."""
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


@router.post("/quick-test", response_model=QuickTestResponse)
async def quick_test(
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> QuickTestResponse:
    """Quick test of pipeline components."""
    results: list[QuickTestResult] = []
    total_start = time.time()
    all_success = True

    # Test profile
    start = time.time()
    try:
        profile = orchestrator._collector.get_profile()
        results.append(QuickTestResult(
            component="profile_access",
            status="ok",
            duration_ms=int((time.time() - start) * 1000),
            message=f"Profile: {profile.full_name}",
        ))
    except Exception as e:
        results.append(QuickTestResult(
            component="profile_access",
            status="error",
            duration_ms=int((time.time() - start) * 1000),
            error=str(e),
        ))
        all_success = False

    # Test vector search
    start = time.time()
    try:
        matches = await orchestrator._collector.search_skills("Python", n_results=3)
        results.append(QuickTestResult(
            component="vector_search",
            status="ok",
            duration_ms=int((time.time() - start) * 1000),
            message=f"Found {len(matches)} matches",
        ))
    except Exception as e:
        results.append(QuickTestResult(
            component="vector_search",
            status="error",
            duration_ms=int((time.time() - start) * 1000),
            error=str(e),
        ))
        all_success = False

    # Test LLM connection
    start = time.time()
    try:
        health = await orchestrator._rinser._llm.health_check()
        results.append(QuickTestResult(
            component="llm_connection",
            status="ok" if health.status == "healthy" else "warning",
            duration_ms=int((time.time() - start) * 1000),
            message=f"Ollama: {health.model_loaded}",
        ))
    except Exception as e:
        results.append(QuickTestResult(
            component="llm_connection",
            status="error",
            duration_ms=int((time.time() - start) * 1000),
            error=str(e),
        ))
        all_success = False

    # Test templates
    start = time.time()
    try:
        template_dir = orchestrator._formatter._templates_dir
        if template_dir.exists():
            templates = list(template_dir.glob("*.html"))
            results.append(QuickTestResult(
                component="templates",
                status="ok",
                duration_ms=int((time.time() - start) * 1000),
                message=f"Found {len(templates)} templates",
            ))
        else:
            results.append(QuickTestResult(
                component="templates",
                status="warning",
                duration_ms=int((time.time() - start) * 1000),
                message="Template dir not found",
            ))
    except Exception as e:
        results.append(QuickTestResult(
            component="templates",
            status="error",
            duration_ms=int((time.time() - start) * 1000),
            error=str(e),
        ))
        all_success = False

    return QuickTestResponse(
        success=all_success,
        total_duration_ms=int((time.time() - total_start) * 1000),
        results=results,
    )
```

#### 3.9 V1 Router Aggregation

**File:** `src/web/routes/api/v1/__init__.py`

```python
"""
API V1 Router

Aggregates all v1 endpoint routers.
"""

from fastapi import APIRouter

from src.web.routes.api.v1.diagnostics import router as diagnostics_router
from src.web.routes.api.v1.jobs import router as jobs_router
from src.web.routes.api.v1.logs import router as logs_router
from src.web.routes.api.v1.metrics import router as metrics_router
from src.web.routes.api.v1.notifications import router as notifications_router
from src.web.routes.api.v1.profile import router as profile_router
from src.web.routes.api.v1.skills import router as skills_router
from src.web.routes.api.v1.system import router as system_router

# Create v1 router
router = APIRouter(prefix="/v1")

# Include all domain routers
router.include_router(system_router)
router.include_router(jobs_router)
router.include_router(skills_router)
router.include_router(profile_router)
router.include_router(notifications_router)
router.include_router(logs_router)
router.include_router(metrics_router)
router.include_router(diagnostics_router)

__all__ = ["router"]
```

#### 3.10 API Router Aggregation

**File:** `src/web/routes/api/__init__.py`

```python
"""
API Router

Aggregates all API versions and provides the main API router.
"""

from fastapi import APIRouter

from src.web.routes.api.v1 import router as v1_router

# Create main API router
router = APIRouter(prefix="/api")

# Include version routers
router.include_router(v1_router)

__all__ = ["router"]
```

### Phase 4: Update Main Routes Init

**File:** `src/web/routes/__init__.py`

```python
"""
Routes Package

Exports routers for the FastAPI application.
"""

from src.web.routes.api import router as api_router
from src.web.routes.pages import router as pages_router

__all__ = ["api_router", "pages_router"]
```

### Phase 5: Update Main Application

**File:** `src/web/main.py`

```python
"""
FastAPI Application Entry Point

Usage:
    uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.services.notification import get_notification_service
from src.services.pipeline import get_pipeline_orchestrator, shutdown_pipeline_orchestrator
from src.web.dependencies import get_job_store, reset_job_store
from src.web.routes import api_router, pages_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Memory logging for web interface
from src.web.log_handler import setup_memory_logging
setup_memory_logging(max_entries=500)

# Application metadata
APP_NAME = "Scout"
APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")

    try:
        await get_pipeline_orchestrator()
        logger.info("Pipeline orchestrator initialized")
        get_job_store()
        logger.info("Job store initialized")
        get_notification_service()
        logger.info("Notification service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

    logger.info(f"{APP_NAME} ready")
    yield

    logger.info(f"Shutting down {APP_NAME}")
    await shutdown_pipeline_orchestrator()
    reset_job_store()
    logger.info("Shutdown complete")


# Create application
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Intelligent Job Application System",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Future Vue dev server
        "http://localhost:8000",
        "http://192.168.1.21:3000",
        "http://192.168.1.21:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include routers
app.include_router(api_router)  # /api/v1/*
app.include_router(pages_router)  # HTML pages


# Legacy compatibility redirects (optional - remove after frontend migration)
@app.get("/health", include_in_schema=False)
async def legacy_health():
    """Legacy health endpoint - redirects to /api/v1/health."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/v1/health")


@app.get("/info", include_in_schema=False)
async def legacy_info():
    """Legacy info endpoint - redirects to /api/v1/info."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/v1/info")
```

### Phase 6: Update Frontend JavaScript

Update the JavaScript to use new API paths:

**File:** `src/web/static/js/common.js`

Find and replace all API calls:
- `/api/notifications` → `/api/v1/notifications`
- `/api/jobs` → `/api/v1/jobs`
- `/api/apply` → `/api/v1/jobs/apply`
- `/api/status/` → `/api/v1/jobs/`
- `/api/diagnostics` → `/api/v1/diagnostics`
- `/api/logs` → `/api/v1/logs`
- `/api/metrics` → `/api/v1/metrics`

**File:** `src/web/static/js/profile-editor.js`

Find and replace:
- `/api/profile/editor-data` → `/api/v1/profile/editor-data`
- `/api/profile/editor-save` → `/api/v1/profile/editor-save`
- `/api/profile/assess` → `/api/v1/profile/assess`
- `/api/profile/export-yaml` → `/api/v1/profile/export-yaml`

---

## Endpoint Migration Map

| Old Endpoint | New Endpoint | Notes |
|--------------|--------------|-------|
| `GET /health` | `GET /api/v1/health` | Redirect added |
| `GET /info` | `GET /api/v1/info` | Redirect added |
| `POST /api/apply` | `POST /api/v1/jobs/apply` | |
| `POST /api/quick-score` | `POST /api/v1/jobs/quick-score` | |
| `GET /api/status/{id}` | `GET /api/v1/jobs/{id}` | |
| `GET /api/jobs` | `GET /api/v1/jobs` | |
| `GET /api/download/{id}/{type}` | `GET /api/v1/jobs/{id}/download/{type}` | |
| `GET /api/logs` | `GET /api/v1/logs` | |
| `DELETE /api/logs` | `DELETE /api/v1/logs` | |
| `GET /api/metrics/*` | `GET /api/v1/metrics/*` | |
| `GET /api/diagnostics` | `GET /api/v1/diagnostics` | |
| `GET /api/notifications` | `GET /api/v1/notifications` | |
| `GET /api/profile/*` | `GET /api/v1/profile/*` | |
| **NEW** | `GET /api/v1/skills/aliases` | Task A |
| **NEW** | `GET /api/v1/skills/normalize` | Task A |
| **NEW** | `GET /api/v1/skills/expand` | Task A |
| **NEW** | `GET /api/v1/skills/search` | Task A |

---

## Files to Create

| File | Description |
|------|-------------|
| `src/web/routes/api/__init__.py` | API router aggregation |
| `src/web/routes/api/v1/__init__.py` | V1 router aggregation |
| `src/web/routes/api/v1/system.py` | Health/info endpoints |
| `src/web/routes/api/v1/jobs.py` | Job pipeline endpoints |
| `src/web/routes/api/v1/skills.py` | **NEW** Skill alias endpoints |
| `src/web/routes/api/v1/profile.py` | Profile endpoints |
| `src/web/routes/api/v1/notifications.py` | Notification endpoints |
| `src/web/routes/api/v1/logs.py` | Log endpoints |
| `src/web/routes/api/v1/metrics.py` | Metrics endpoints |
| `src/web/routes/api/v1/diagnostics.py` | Diagnostics endpoints |
| `src/web/routes/api/schemas/__init__.py` | Schema exports |
| `src/web/routes/api/schemas/common.py` | Common schemas |
| `src/web/routes/api/schemas/jobs.py` | Job schemas |
| `src/web/routes/api/schemas/profile.py` | Profile schemas |
| `src/web/routes/api/schemas/metrics.py` | Metrics schemas |

## Files to Modify

| File | Changes |
|------|---------|
| `src/web/routes/__init__.py` | Update exports |
| `src/web/main.py` | Simplify, use new routers |
| `src/web/static/js/common.js` | Update API paths |
| `src/web/static/js/profile-editor.js` | Update API paths |

## Files to Delete (After Verification)

| File | Reason |
|------|--------|
| `src/web/routes/api.py` | Split into domain modules |
| `src/web/routes/notifications.py` | Moved to api/v1/ |
| `src/web/routes/profile.py` | Moved to api/v1/ |
| `src/web/schemas.py` | Moved to api/schemas/ |

---

## Testing Instructions

```bash
cd /home/cally/projects/scout-code
source venv/bin/activate

# Run existing tests (should still pass)
pytest tests/ -v --tb=short

# Start server
uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000

# Test new endpoints
curl http://localhost:8000/api/v1/health | jq
curl http://localhost:8000/api/v1/info | jq
curl http://localhost:8000/api/v1/skills/aliases | jq
curl http://localhost:8000/api/v1/skills/normalize?skill=k8s | jq
curl http://localhost:8000/api/v1/profile/summary | jq
curl http://localhost:8000/api/v1/diagnostics | jq

# Test legacy redirects
curl -L http://localhost:8000/health | jq

# Check OpenAPI docs
# Navigate to: http://192.168.1.21:8000/docs
```

---

## Success Criteria

1. ✅ All endpoints accessible under `/api/v1/`
2. ✅ OpenAPI docs show organized groups (jobs, profile, skills, etc.)
3. ✅ Legacy redirects work for `/health` and `/info`
4. ✅ All existing tests pass
5. ✅ Frontend continues to work (updated JS paths)
6. ✅ New `/api/v1/skills/*` endpoints functional
7. ✅ CORS configured for future Vue dev server

---

## Constraints

- Maintain backward compatibility during transition
- Keep page routes unchanged (`/`, `/profile/edit`, etc.)
- No breaking changes to response schemas
- Preserve all existing functionality

---

## Environment

- SSH: `ssh cally@192.168.1.21`
- Project: `/home/cally/projects/scout-code`
- Venv: `source venv/bin/activate`
- Server: `uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000`
