"""
FastAPI Application Entry Point

Main application configuration and setup.

Usage:
    uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.services.notification import get_notification_service
from src.services.pipeline import (
    get_pipeline_orchestrator,
    shutdown_pipeline_orchestrator,
)
from src.web.dependencies import get_job_store, reset_job_store
from src.web.routes import notifications_router, pages_router, router
from src.web.schemas import HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Application metadata
APP_NAME = "Scout"
APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown tasks.
    """
    # Startup
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")

    # Initialize services
    try:
        await get_pipeline_orchestrator()
        logger.info("Pipeline orchestrator initialized")

        # Initialize job store
        get_job_store()
        logger.info("Job store initialized")

        # Initialize notification service
        get_notification_service()
        logger.info("Notification service initialized")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

    logger.info(f"{APP_NAME} ready to accept requests")

    yield

    # Shutdown
    logger.info(f"Shutting down {APP_NAME}")
    await shutdown_pipeline_orchestrator()
    reset_job_store()
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Intelligent Job Application System",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)
app.include_router(notifications_router)
app.include_router(pages_router)


@app.get("/info", tags=["info"])
async def info() -> dict[str, str]:
    """
    Application info endpoint.

    Returns basic application info as JSON.
    """
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "ready",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    """
    Health check endpoint.

    Returns application health status.
    """
    return HealthResponse(
        status="healthy",
        version=APP_VERSION,
        services={
            "pipeline": "ok",
            "job_store": "ok",
            "notifications": "ok",
        },
    )
