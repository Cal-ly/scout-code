"""
Cache Service

Two-tier caching: Memory (L1) → File (L2)
Reduces LLM costs by caching responses.

Usage:
    cache = CacheService()
    await cache.initialize()

    # Store
    await cache.set("my_key", {"data": "value"})

    # Retrieve
    result = await cache.get("my_key")

    # For LLM responses, use request hash as key
    key = cache.generate_key(prompt, model="qwen2.5:3b", temperature=0.3)
    cached = await cache.get(key)
    if cached is None:
        response = await llm.generate(...)
        await cache.set(key, response)
"""

import hashlib
import json
import logging
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.services.cache_service.exceptions import CacheError
from src.services.cache_service.models import CacheEntry, CacheHealth, CacheStats

logger = logging.getLogger(__name__)

# Default configuration values (can be overridden via constructor)
DEFAULT_CACHE_DIR = Path("data/cache")
DEFAULT_MEMORY_MAX_ENTRIES = 100
DEFAULT_TTL_SECONDS = 3600  # 1 hour


class CacheService:
    """
    Two-tier cache service with memory and file backends.

    Memory cache (L1):
    - Fast access, limited size (100 entries by default)
    - LRU eviction when full
    - Lost on restart

    File cache (L2):
    - Slower access, unlimited size
    - Persists across restarts
    - Automatic cleanup of expired entries

    Attributes:
        stats: Cache performance statistics

    Example:
        >>> cache = CacheService()
        >>> await cache.initialize()
        >>> await cache.set("user_123", {"name": "John"}, ttl=3600)
        >>> data = await cache.get("user_123")
        >>> print(data)
        {"name": "John"}
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        memory_max_entries: int = DEFAULT_MEMORY_MAX_ENTRIES,
        default_ttl: int = DEFAULT_TTL_SECONDS,
    ):
        """
        Initialize the Cache Service.

        Args:
            cache_dir: Directory for file cache (default: data/cache).
            memory_max_entries: Maximum entries in memory cache (default: 100).
            default_ttl: Default TTL in seconds (default: 3600 / 1 hour).
        """
        self._initialized = False
        self._memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._memory_max = memory_max_entries
        self._default_ttl = default_ttl
        self._cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self._stats = CacheStats()
        self._last_cleanup: datetime | None = None

    async def initialize(self) -> None:
        """
        Initialize the Cache Service.

        Creates cache directory if needed.
        """
        if self._initialized:
            logger.warning("Cache Service already initialized")
            return

        # Create cache directory
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Cache directory: {self._cache_dir}")

        # Count existing file cache entries
        self._stats.file_entries = len(list(self._cache_dir.glob("*.json")))

        self._initialized = True
        logger.info(
            f"Cache Service initialized: "
            f"memory=0/{self._memory_max}, "
            f"file={self._stats.file_entries}"
        )

    async def shutdown(self) -> None:
        """Gracefully shutdown the Cache Service."""
        if not self._initialized:
            return

        # Clear memory cache
        self._memory_cache.clear()
        self._initialized = False
        logger.info("Cache Service shutdown complete")

    def _ensure_initialized(self) -> None:
        """Raise error if service not initialized."""
        if not self._initialized:
            raise CacheError("Cache Service not initialized. Call initialize() first.")

    # =========================================================================
    # KEY GENERATION
    # =========================================================================

    def generate_key(self, *args: Any, **kwargs: Any) -> str:
        """
        Generate a cache key from arguments.

        Creates MD5 hash of all arguments for consistent keying.

        Args:
            *args: Positional arguments to include in key.
            **kwargs: Keyword arguments to include in key.

        Returns:
            32-character hexadecimal hash string.

        Example:
            >>> key = cache.generate_key("prompt text", model="qwen2.5:3b", temp=0.3)
            >>> print(key)
            "a1b2c3d4e5f6..."
        """
        # Combine all arguments into a consistent string
        key_data = {"args": args, "kwargs": kwargs}
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()

    # =========================================================================
    # MEMORY CACHE OPERATIONS
    # =========================================================================

    def _memory_get(self, key: str) -> CacheEntry | None:
        """Get entry from memory cache."""
        entry = self._memory_cache.get(key)
        if entry is None:
            return None

        # Check expiration
        if entry.is_expired():
            del self._memory_cache[key]
            return None

        # Move to end (most recently used)
        self._memory_cache.move_to_end(key)
        entry.hit_count += 1
        return entry

    def _memory_set(self, key: str, entry: CacheEntry) -> None:
        """Set entry in memory cache with LRU eviction."""
        # Evict oldest if at capacity
        while len(self._memory_cache) >= self._memory_max:
            oldest_key = next(iter(self._memory_cache))
            del self._memory_cache[oldest_key]
            logger.debug(f"Evicted from memory cache: {oldest_key[:16]}...")

        self._memory_cache[key] = entry
        self._memory_cache.move_to_end(key)

    def _memory_delete(self, key: str) -> bool:
        """Delete entry from memory cache."""
        if key in self._memory_cache:
            del self._memory_cache[key]
            return True
        return False

    # =========================================================================
    # FILE CACHE OPERATIONS
    # =========================================================================

    def _get_file_path(self, key: str) -> Path:
        """Get file path for a cache key."""
        return self._cache_dir / f"{key}.json"

    async def _file_get(self, key: str) -> CacheEntry | None:
        """Get entry from file cache."""
        file_path = self._get_file_path(key)

        if not file_path.exists():
            return None

        try:
            with open(file_path) as f:
                data = json.load(f)

            entry = CacheEntry(**data)

            # Check expiration
            if entry.is_expired():
                file_path.unlink(missing_ok=True)
                return None

            entry.hit_count += 1
            return entry

        except (json.JSONDecodeError, ValueError, OSError) as e:
            logger.warning(f"Failed to read cache file {file_path}: {e}")
            file_path.unlink(missing_ok=True)  # Remove corrupted file
            return None

    async def _file_set(self, key: str, entry: CacheEntry) -> None:
        """Set entry in file cache."""
        file_path = self._get_file_path(key)

        try:
            with open(file_path, "w") as f:
                json.dump(entry.model_dump(mode="json"), f, default=str)
        except OSError as e:
            logger.error(f"Failed to write cache file {file_path}: {e}")

    async def _file_delete(self, key: str) -> bool:
        """Delete entry from file cache."""
        file_path = self._get_file_path(key)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    async def get(self, key: str) -> Any | None:
        """
        Get value from cache.

        Checks memory cache first, then file cache.
        Promotes file cache hits to memory cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found/expired.
        """
        self._ensure_initialized()

        # Try memory cache first (L1)
        entry = self._memory_get(key)
        if entry is not None:
            self._stats.hits += 1
            logger.debug(f"Cache HIT (memory): {key[:16]}...")
            return entry.value

        # Try file cache (L2)
        entry = await self._file_get(key)
        if entry is not None:
            # Promote to memory cache
            self._memory_set(key, entry)
            self._stats.hits += 1
            logger.debug(f"Cache HIT (file): {key[:16]}...")
            return entry.value

        # Cache miss
        self._stats.misses += 1
        logger.debug(f"Cache MISS: {key[:16]}...")
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """
        Store value in cache.

        Writes to both memory and file cache.

        Args:
            key: Cache key.
            value: Value to cache (must be JSON-serializable).
            ttl: Time-to-live in seconds (default: 1 hour).
        """
        self._ensure_initialized()

        if ttl is None:
            ttl = self._default_ttl

        expires_at = datetime.now() + timedelta(seconds=ttl)

        entry = CacheEntry(key=key, value=value, expires_at=expires_at)

        # Write to both tiers
        self._memory_set(key, entry)
        await self._file_set(key, entry)

        # Update stats
        self._stats.memory_entries = len(self._memory_cache)
        self._stats.file_entries += 1  # Approximate

        logger.debug(f"Cache SET: {key[:16]}... (TTL: {ttl}s)")

    async def delete(self, key: str) -> bool:
        """
        Delete entry from cache.

        Removes from both memory and file cache.

        Args:
            key: Cache key.

        Returns:
            True if entry was found and deleted.
        """
        self._ensure_initialized()

        memory_deleted = self._memory_delete(key)
        file_deleted = await self._file_delete(key)

        deleted = memory_deleted or file_deleted

        if deleted:
            logger.debug(f"Cache DELETE: {key[:16]}...")
            self._stats.memory_entries = len(self._memory_cache)

        return deleted

    async def clear(self) -> int:
        """
        Clear all cache entries.

        Clears both memory and file cache.

        Returns:
            Number of entries cleared.
        """
        self._ensure_initialized()

        # Count entries
        memory_count = len(self._memory_cache)
        file_count = len(list(self._cache_dir.glob("*.json")))
        total = memory_count + file_count

        # Clear memory
        self._memory_cache.clear()

        # Clear files
        for file_path in self._cache_dir.glob("*.json"):
            file_path.unlink(missing_ok=True)

        # Reset stats
        self._stats = CacheStats()

        logger.info(f"Cache CLEARED: {total} entries removed")
        return total

    async def cleanup_expired(self) -> int:
        """
        Remove expired entries from file cache.

        Memory cache cleans up on access; file cache needs explicit cleanup.

        Returns:
            Number of expired entries removed.
        """
        self._ensure_initialized()

        removed = 0

        for file_path in self._cache_dir.glob("*.json"):
            try:
                with open(file_path) as f:
                    data = json.load(f)

                entry = CacheEntry(**data)

                if entry.is_expired():
                    file_path.unlink()
                    removed += 1

            except (json.JSONDecodeError, ValueError, OSError):
                # Remove corrupted files too
                file_path.unlink(missing_ok=True)
                removed += 1

        self._last_cleanup = datetime.now()
        self._stats.file_entries = len(list(self._cache_dir.glob("*.json")))

        if removed > 0:
            logger.info(f"Cache cleanup: {removed} expired entries removed")

        return removed

    # =========================================================================
    # STATS & HEALTH
    # =========================================================================

    def get_stats(self) -> CacheStats:
        """
        Get cache statistics.

        Returns:
            CacheStats with hit/miss counts and entry counts.
        """
        self._stats.memory_entries = len(self._memory_cache)
        return self._stats.model_copy()

    async def health_check(self) -> CacheHealth:
        """
        Check health of Cache Service.

        Returns:
            CacheHealth with status and diagnostics.
        """
        # Check file cache accessibility
        file_ok = True
        try:
            test_file = self._cache_dir / ".health_check"
            test_file.write_text("ok")
            test_file.unlink()
        except OSError:
            file_ok = False

        status = "healthy" if file_ok else "degraded"

        return CacheHealth(
            status=status,
            memory_entries=len(self._memory_cache),
            memory_max=self._memory_max,
            file_cache_accessible=file_ok,
            stats=self.get_stats(),
            last_cleanup=self._last_cleanup,
        )

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache (without retrieving).

        Args:
            key: Cache key.

        Returns:
            True if key exists and is not expired.
        """
        self._ensure_initialized()

        # Check memory
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if not entry.is_expired():
                return True

        # Check file
        file_path = self._get_file_path(key)
        if file_path.exists():
            file_entry = await self._file_get(key)
            return file_entry is not None

        return False


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

_cache_instance: CacheService | None = None


async def get_cache_service() -> CacheService:
    """
    Get the Cache Service instance.

    Creates and initializes singleton on first call.
    Use as FastAPI dependency.

    Returns:
        Initialized CacheService.
    """
    global _cache_instance

    if _cache_instance is None:
        _cache_instance = CacheService()
        await _cache_instance.initialize()

    return _cache_instance


async def shutdown_cache_service() -> None:
    """Shutdown the global Cache Service instance."""
    global _cache_instance

    if _cache_instance is not None:
        await _cache_instance.shutdown()
        _cache_instance = None


def reset_cache_service() -> None:
    """Reset the global instance (for testing)."""
    global _cache_instance
    _cache_instance = None
