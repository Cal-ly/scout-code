"""
Page Routes

HTML page serving endpoints for Scout web interface.

Endpoints:
    GET / - Main application page
    GET /profile/create - Legacy profile creation page
    GET /profiles - Profile list page
    GET /profiles/create - Create new profile
    GET /profiles/{filename} - Profile detail page
    GET /profiles/{filename}/edit - Edit profile page
    GET /applications - Generated applications list page
    GET /metrics - Performance metrics dashboard
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """
    Render the main application page.

    Args:
        request: FastAPI request object (required for templates).

    Returns:
        Rendered HTML page.
    """
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@router.get("/profile/create", response_class=HTMLResponse)
async def profile_create_legacy(request: Request) -> HTMLResponse:
    """
    Render the legacy profile creation/edit page.

    This is kept for backward compatibility.
    New implementations should use /profiles/create.

    Args:
        request: FastAPI request object (required for templates).

    Returns:
        Rendered HTML page.
    """
    return templates.TemplateResponse(
        request=request,
        name="profile.html",
    )


@router.get("/profile/edit", response_class=HTMLResponse)
async def profile_editor(request: Request) -> HTMLResponse:
    """
    Render the form-based profile editor page.

    Provides a user-friendly multi-step form interface for creating
    and editing profiles without needing to write YAML manually.

    Args:
        request: FastAPI request object (required for templates).

    Returns:
        Rendered HTML page.
    """
    return templates.TemplateResponse(
        request=request,
        name="profile_editor.html",
    )


# =============================================================================
# MULTI-PROFILE MANAGEMENT PAGES
# =============================================================================


@router.get("/profiles", response_class=HTMLResponse)
async def profiles_list(request: Request) -> HTMLResponse:
    """
    Render the profiles list page.

    Shows all user profiles with statistics and management options.

    Args:
        request: FastAPI request object (required for templates).

    Returns:
        Rendered HTML page.
    """
    return templates.TemplateResponse(
        request=request,
        name="profiles_list.html",
    )


@router.get("/profiles/create", response_class=HTMLResponse)
async def profiles_create(request: Request) -> HTMLResponse:
    """
    Render the profile creation page with YAML editor.

    Args:
        request: FastAPI request object (required for templates).

    Returns:
        Rendered HTML page.
    """
    return templates.TemplateResponse(
        request=request,
        name="profile_edit.html",
    )


@router.get("/profiles/{filename}", response_class=HTMLResponse)
async def profile_detail(request: Request, filename: str) -> HTMLResponse:
    """
    Render the profile detail/view page.

    Shows detailed information about a specific profile including
    statistics, content in different view modes, and management actions.

    Args:
        request: FastAPI request object (required for templates).
        filename: The YAML filename of the profile.

    Returns:
        Rendered HTML page.
    """
    return templates.TemplateResponse(
        request=request,
        name="profile_detail.html",
    )


@router.get("/profiles/{filename}/edit", response_class=HTMLResponse)
async def profile_edit(request: Request, filename: str) -> HTMLResponse:
    """
    Render the profile edit page with YAML editor.

    Args:
        request: FastAPI request object (required for templates).
        filename: The YAML filename of the profile to edit.

    Returns:
        Rendered HTML page.
    """
    return templates.TemplateResponse(
        request=request,
        name="profile_edit.html",
    )


# =============================================================================
# APPLICATIONS / GENERATED DOCUMENTS
# =============================================================================


@router.get("/applications", response_class=HTMLResponse)
async def applications_list(request: Request) -> HTMLResponse:
    """
    Render the generated applications list page.

    Shows all generated job applications with stats, compatibility scores,
    and download links for CVs and cover letters.

    Args:
        request: FastAPI request object (required for templates).

    Returns:
        Rendered HTML page.
    """
    return templates.TemplateResponse(
        request=request,
        name="applications.html",
    )


# =============================================================================
# METRICS PAGE
# =============================================================================


@router.get("/metrics", response_class=HTMLResponse)
async def metrics_page(request: Request) -> HTMLResponse:
    """
    Render the performance metrics dashboard.

    Shows LLM inference performance metrics including tokens per second,
    success rates, model comparison, and system resource usage.

    Args:
        request: FastAPI request object (required for templates).

    Returns:
        Rendered HTML page.
    """
    return templates.TemplateResponse(
        request=request,
        name="metrics.html",
    )


# =============================================================================
# LOGS PAGE
# =============================================================================


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request) -> HTMLResponse:
    """
    Render the application logs page.

    Provides a dedicated page for viewing and monitoring application logs
    with filtering, search, and auto-refresh capabilities.

    Args:
        request: FastAPI request object (required for templates).

    Returns:
        Rendered HTML page.
    """
    return templates.TemplateResponse(
        request=request,
        name="logs.html",
    )
