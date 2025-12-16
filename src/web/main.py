"""
FastAPI Application Entry Point

Usage:
    uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.services.database import get_database_service
from src.services.notification import get_notification_service
from src.services.pipeline import get_pipeline_orchestrator, shutdown_pipeline_orchestrator
from src.web.dependencies import get_job_store, reset_job_store
from src.web.routes import api_router, pages_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Memory logging for web interface
from src.web.log_handler import setup_memory_logging

setup_memory_logging(max_entries=500)

# Application metadata
APP_NAME = "Scout"
APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")

    try:
        # Initialize database (demo data is auto-seeded by DatabaseService)
        await get_database_service()
        logger.info("Database initialized")

        await get_pipeline_orchestrator()
        logger.info("Pipeline orchestrator initialized")
        get_job_store()
        logger.info("Job store initialized")
        get_notification_service()
        logger.info("Notification service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

    logger.info(f"{APP_NAME} ready")
    yield

    logger.info(f"Shutting down {APP_NAME}")
    await shutdown_pipeline_orchestrator()
    reset_job_store()
    logger.info("Shutdown complete")


# Create application
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Intelligent Job Application System",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Future Vue dev server
        "http://localhost:8000",
        "http://192.168.1.21:3000",
        "http://192.168.1.21:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include routers
app.include_router(api_router)  # /api/v1/*
app.include_router(pages_router)  # HTML pages


# Legacy compatibility redirects (remove after frontend migration)
@app.get("/health", include_in_schema=False)
async def legacy_health() -> RedirectResponse:
    """Legacy health endpoint - redirects to /api/v1/health."""
    return RedirectResponse(url="/api/v1/health")


@app.get("/info", include_in_schema=False)
async def legacy_info() -> RedirectResponse:
    """Legacy info endpoint - redirects to /api/v1/info."""
    return RedirectResponse(url="/api/v1/info")
