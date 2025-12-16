"""
Routes Package

Exports routers for the FastAPI application.
"""

from src.web.routes.api import router as api_router
from src.web.routes.pages import router as pages_router

__all__ = ["api_router", "pages_router"]
