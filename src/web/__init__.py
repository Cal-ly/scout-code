"""
Scout Web Package

FastAPI-based REST API for Scout job application processing.

Usage:
    uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000

Endpoints:
    POST /api/v1/jobs/apply - Start new job application
    GET /api/v1/jobs/{job_id} - Get pipeline status
    GET /api/v1/jobs/{job_id}/download/{file_type} - Download PDF
    GET /api/v1/jobs - List all jobs
    GET /api/v1/health - Health check
"""

from src.web.dependencies import (
    JobStore,
    get_job_store,
    get_orchestrator,
    get_store,
    reset_job_store,
)
from src.web.main import app
from src.web.routes import api_router
from src.web.routes.api.schemas import (
    ApplyRequest,
    ApplyResponse,
    ErrorResponse,
    JobListResponse,
    JobSummary,
    StatusResponse,
    StepInfo,
)

__all__ = [
    # Main app
    "app",
    "api_router",
    # Dependencies
    "JobStore",
    "get_job_store",
    "get_store",
    "get_orchestrator",
    "reset_job_store",
    # Schemas
    "ApplyRequest",
    "ApplyResponse",
    "StatusResponse",
    "JobSummary",
    "JobListResponse",
    "StepInfo",
    "ErrorResponse",
]
