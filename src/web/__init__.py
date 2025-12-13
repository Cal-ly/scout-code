"""
Scout Web Package

FastAPI-based REST API for Scout job application processing.

Usage:
    uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000

Endpoints:
    POST /api/apply - Start new job application
    GET /api/status/{job_id} - Get pipeline status
    GET /api/download/{job_id}/{file_type} - Download PDF
    GET /api/jobs - List all jobs
    GET /health - Health check
"""

from src.web.dependencies import (
    JobStore,
    get_job_store,
    get_orchestrator,
    get_store,
    reset_job_store,
)
from src.web.main import app
from src.web.routes import router
from src.web.schemas import (
    ApplyRequest,
    ApplyResponse,
    ErrorResponse,
    HealthResponse,
    JobListResponse,
    JobSummary,
    StatusResponse,
    StepInfo,
)

__all__ = [
    # Main app
    "app",
    "router",
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
    "HealthResponse",
]
