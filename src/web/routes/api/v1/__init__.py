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
