"""
Cache Service

Two-tier caching system (Memory + File) for LLM response caching.
Reduces API costs by storing and reusing responses.

Usage:
    from src.services.cache_service import CacheService, get_cache_service

    # Using dependency injection (recommended)
    cache = await get_cache_service()
    await cache.set("key", {"data": "value"})
    result = await cache.get("key")

    # Direct instantiation
    cache = CacheService()
    await cache.initialize()
    await cache.set("key", {"data": "value"})
"""

from src.services.cache_service.exceptions import (
    CacheError,
    CacheKeyError,
)
from src.services.cache_service.models import (
    CacheEntry,
    CacheHealth,
    CacheStats,
)
from src.services.cache_service.service import (
    CacheService,
    get_cache_service,
    reset_cache_service,
    shutdown_cache_service,
)

__all__ = [
    # Models
    "CacheEntry",
    "CacheStats",
    "CacheHealth",
    # Exceptions
    "CacheError",
    "CacheKeyError",
    # Service
    "CacheService",
    "get_cache_service",
    "shutdown_cache_service",
    "reset_cache_service",
]
