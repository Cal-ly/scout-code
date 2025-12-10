"""
M1 Collector Exceptions

Custom exceptions for profile management and search operations.
"""


class CollectorError(Exception):
    """Base exception for Collector module."""

    pass


class ProfileNotFoundError(CollectorError):
    """Profile file not found at specified path."""

    pass


class ProfileValidationError(CollectorError):
    """Profile data failed validation."""

    pass


class ProfileLoadError(CollectorError):
    """Failed to load profile from file."""

    pass


class IndexingError(CollectorError):
    """Failed to index profile content in vector store."""

    pass


class SearchError(CollectorError):
    """Failed to perform search operation."""

    pass
