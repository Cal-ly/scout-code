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
