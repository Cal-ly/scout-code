"""
API Routes Package

Exports routers for inclusion in the main FastAPI application.
"""

from src.web.routes.api import router
from src.web.routes.notifications import router as notifications_router
from src.web.routes.pages import router as pages_router

__all__ = ["router", "notifications_router", "pages_router"]
