"""
Page Routes

HTML page serving endpoints for Scout web interface.

Endpoints:
    GET / - Main application page
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
