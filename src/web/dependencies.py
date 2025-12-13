"""
FastAPI Dependencies

Dependency injection functions for API routes.
Provides singleton access to services and in-memory job storage.
"""

import logging

from src.services.pipeline import (
    PipelineOrchestrator,
    PipelineResult,
    get_pipeline_orchestrator,
)

logger = logging.getLogger(__name__)


# =============================================================================
# JOB STORE (In-Memory for PoC)
# =============================================================================


class JobStore:
    """
    In-memory storage for pipeline results.

    Simple dict-based storage for PoC scope.
    Production would use a database.

    Attributes:
        _jobs: Dict mapping job_id to PipelineResult.
    """

    def __init__(self) -> None:
        """Initialize empty job store."""
        self._jobs: dict[str, PipelineResult] = {}

    def store(self, result: PipelineResult) -> str:
        """
        Store a pipeline result.

        Args:
            result: Pipeline result to store.

        Returns:
            The job_id for retrieval.
        """
        # Use job_id if available, else pipeline_id
        job_id = result.job_id or result.pipeline_id
        self._jobs[job_id] = result
        logger.debug(f"Stored job {job_id}, total jobs: {len(self._jobs)}")
        return job_id

    def get(self, job_id: str) -> PipelineResult | None:
        """
        Get a pipeline result by job_id.

        Args:
            job_id: Job identifier.

        Returns:
            Pipeline result if found, None otherwise.
        """
        return self._jobs.get(job_id)

    def list_all(self) -> list[PipelineResult]:
        """
        Get all stored pipeline results.

        Returns:
            List of all pipeline results, newest first.
        """
        # Sort by started_at descending
        return sorted(
            self._jobs.values(),
            key=lambda r: r.started_at,
            reverse=True,
        )

    def count(self) -> int:
        """Get total number of stored jobs."""
        return len(self._jobs)

    def clear(self) -> None:
        """Clear all stored jobs (for testing)."""
        self._jobs.clear()


# =============================================================================
# SINGLETON INSTANCES
# =============================================================================

_job_store: JobStore | None = None


def get_job_store() -> JobStore:
    """
    Get the singleton JobStore instance.

    Returns:
        JobStore instance.
    """
    global _job_store
    if _job_store is None:
        _job_store = JobStore()
        logger.info("JobStore initialized")
    return _job_store


def reset_job_store() -> None:
    """Reset the JobStore singleton (for testing)."""
    global _job_store
    if _job_store is not None:
        _job_store.clear()
    _job_store = None


# =============================================================================
# FASTAPI DEPENDENCIES
# =============================================================================


async def get_orchestrator() -> PipelineOrchestrator:
    """
    FastAPI dependency for getting the pipeline orchestrator.

    Usage:
        @router.post("/apply")
        async def apply(
            orchestrator: PipelineOrchestrator = Depends(get_orchestrator)
        ):
            ...

    Returns:
        Initialized PipelineOrchestrator instance.
    """
    return await get_pipeline_orchestrator()


def get_store() -> JobStore:
    """
    FastAPI dependency for getting the job store.

    Usage:
        @router.get("/jobs")
        async def list_jobs(store: JobStore = Depends(get_store)):
            ...

    Returns:
        JobStore instance.
    """
    return get_job_store()
