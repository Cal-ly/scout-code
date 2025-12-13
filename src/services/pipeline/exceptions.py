"""
Pipeline Exceptions

Custom exceptions for pipeline orchestration operations.

Usage:
    from src.services.pipeline.exceptions import PipelineError, StepError

    raise PipelineError("Pipeline execution failed")
    raise StepError("rinser", "Failed to process job")
"""


class PipelineError(Exception):
    """Base exception for Pipeline operations."""

    pass


class StepError(PipelineError):
    """Error during a specific pipeline step."""

    def __init__(self, step: str, message: str):
        """
        Initialize StepError.

        Args:
            step: The step that failed (e.g., "rinser", "analyzer").
            message: Error description.
        """
        self.step = step
        super().__init__(f"{step.capitalize()} step failed: {message}")


class PipelineNotInitializedError(PipelineError):
    """Pipeline service not initialized."""

    pass


class InvalidInputError(PipelineError):
    """Invalid input data for pipeline."""

    pass
