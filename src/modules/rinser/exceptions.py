"""
M2 Rinser Exceptions

Custom exceptions for job processing operations.
"""


class RinserError(Exception):
    """Base exception for Rinser module."""

    pass


class ExtractionError(RinserError):
    """Failed to extract structured data from job posting."""

    pass


class SanitizationError(RinserError):
    """Failed to sanitize input text."""

    pass


class IndexingError(RinserError):
    """Failed to index job data in vector store."""

    pass


class ValidationError(RinserError):
    """Job data validation failed."""

    pass
