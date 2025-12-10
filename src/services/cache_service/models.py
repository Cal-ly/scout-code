"""
Cache Service - Data Models

Simple models for two-tier caching (memory + file).
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CacheEntry(BaseModel):
    """
    A single cached item.

    Stored in both memory and file cache.

    Attributes:
        key: The cache key (usually an MD5 hash).
        value: The cached data (must be JSON-serializable).
        created_at: When the entry was created.
        expires_at: When the entry expires.
        hit_count: Number of times this entry has been accessed.
    """

    key: str
    value: Any  # The cached data (must be JSON-serializable)
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime
    hit_count: int = 0

    model_config = {"arbitrary_types_allowed": True}

    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        return datetime.now() > self.expires_at


class CacheStats(BaseModel):
    """
    Cache performance statistics.

    Tracks hit/miss rates for monitoring.

    Attributes:
        hits: Number of cache hits.
        misses: Number of cache misses.
        memory_entries: Current entries in memory cache.
        file_entries: Current entries in file cache.
    """

    hits: int = 0
    misses: int = 0
    memory_entries: int = 0
    file_entries: int = 0

    @property
    def total_requests(self) -> int:
        """Total number of cache requests (hits + misses)."""
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """Hit rate as percentage (0-100)."""
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100


class CacheHealth(BaseModel):
    """
    Health status for the Cache Service.

    Attributes:
        status: Health status ("healthy" or "degraded").
        memory_entries: Current entries in memory cache.
        memory_max: Maximum memory cache entries.
        file_cache_accessible: Whether file cache is accessible.
        stats: Cache performance statistics.
        last_cleanup: Last time expired entries were cleaned up.
    """

    status: str = "healthy"  # "healthy" or "degraded"
    memory_entries: int = 0
    memory_max: int = 100
    file_cache_accessible: bool = True
    stats: CacheStats = Field(default_factory=CacheStats)
    last_cleanup: datetime | None = None
