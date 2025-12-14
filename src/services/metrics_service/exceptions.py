"""
Metrics Service - Exceptions

Custom exceptions for the Metrics Service.
"""


class MetricsServiceError(Exception):
    """Base exception for Metrics Service operations."""

    pass


class MetricsInitializationError(MetricsServiceError):
    """Raised when the Metrics Service fails to initialize."""

    pass


class MetricsCollectionError(MetricsServiceError):
    """Raised when metrics collection fails."""

    pass
