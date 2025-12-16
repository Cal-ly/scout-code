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
