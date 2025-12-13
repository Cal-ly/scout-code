"""
M4 Creator Exceptions

Custom exceptions for the Creator module.
"""


class CreatorError(Exception):
    """Base exception for Creator module operations."""

    pass


class GenerationError(CreatorError):
    """Error during content generation."""

    pass


class CVGenerationError(GenerationError):
    """Error during CV content generation."""

    pass


class CoverLetterGenerationError(GenerationError):
    """Error during cover letter generation."""

    pass


class ProfileNotAvailableError(CreatorError):
    """User profile not available for content generation."""

    pass


class AnalysisNotAvailableError(CreatorError):
    """Analysis result not available for content generation."""

    pass
