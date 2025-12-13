"""
S6 Pipeline Orchestrator Service

Coordinates sequential execution of all Scout modules for job application processing.

Usage:
    from src.services.pipeline import PipelineOrchestrator, get_pipeline_orchestrator

    # Singleton access (for FastAPI)
    orchestrator = await get_pipeline_orchestrator()
    result = await orchestrator.execute(input_data)

    # Simple execution
    result = await orchestrator.execute_simple("Raw job text...")

    # With progress callback
    async def on_progress(progress):
        print(f"{progress.progress_percent}%: {progress.message}")

    result = await orchestrator.execute(input_data, progress_callback=on_progress)
"""

from src.services.pipeline.exceptions import (
    InvalidInputError,
    PipelineError,
    PipelineNotInitializedError,
    StepError,
)
from src.services.pipeline.models import (
    PipelineInput,
    PipelineProgress,
    PipelineResult,
    PipelineStatus,
    PipelineStep,
    StepResult,
    StepStatus,
)
from src.services.pipeline.pipeline import (
    PipelineOrchestrator,
    ProgressCallback,
    get_pipeline_orchestrator,
    reset_pipeline_orchestrator,
    shutdown_pipeline_orchestrator,
)

__all__ = [
    # Service
    "PipelineOrchestrator",
    "get_pipeline_orchestrator",
    "shutdown_pipeline_orchestrator",
    "reset_pipeline_orchestrator",
    "ProgressCallback",
    # Models
    "PipelineStep",
    "StepStatus",
    "PipelineStatus",
    "StepResult",
    "PipelineInput",
    "PipelineResult",
    "PipelineProgress",
    # Exceptions
    "PipelineError",
    "StepError",
    "PipelineNotInitializedError",
    "InvalidInputError",
]
