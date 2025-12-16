"""
Page Routes

HTML page serving endpoints for Scout web interface.

Endpoints:
    GET / - Main application page
    GET /profiles - Profile list page
    GET /profiles/new - Create new profile
    GET /profiles/{slug}/edit - Edit profile page
    GET /applications - Generated applications list page
    GET /metrics - Performance metrics dashboard
    GET /logs - Application logs page
    GET /diagnostics - System diagnostics page
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


@router.get("/profiles/new", response_class=HTMLResponse)
async def profiles_create(request: Request) -> HTMLResponse:
    """
    Render the profile creation page.

    Args:
        request: FastAPI request object (required for templates).

    Returns:
        Rendered HTML page.
    """
    return templates.TemplateResponse(
        request=request,
        name="profile_edit.html",
    )


@router.get("/profiles/{slug}/edit", response_class=HTMLResponse)
async def profile_edit(request: Request, slug: str) -> HTMLResponse:
    """
    Render the profile edit page.

    Args:
        request: FastAPI request object (required for templates).
        slug: The URL slug of the profile to edit.

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


# =============================================================================
# DIAGNOSTICS PAGE
# =============================================================================


@router.get("/diagnostics", response_class=HTMLResponse)
async def diagnostics_page(request: Request) -> HTMLResponse:
    """
    Render the system diagnostics page.

    Shows component health status, profile info, and quick tests
    for verifying system operation.

    Args:
        request: FastAPI request object (required for templates).

    Returns:
        Rendered HTML page.
    """
    return templates.TemplateResponse(
        request=request,
        name="diagnostics.html",
    )
