"""
Cache Service - Exceptions

Custom exceptions for cache operations.
"""


class CacheError(Exception):
    """
    Base exception for Cache operations.

    Raised when cache operations fail due to:
    - Service not initialized
    - File I/O errors
    - Configuration errors
    """

    pass


class CacheKeyError(CacheError):
    """
    Invalid or missing cache key.

    Raised when:
    - Key format is invalid
    - Key not found when required
    """

    pass
