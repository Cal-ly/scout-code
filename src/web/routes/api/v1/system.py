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
