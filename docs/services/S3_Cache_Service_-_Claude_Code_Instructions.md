# S3 Cache Service - Claude Code Instructions

**Version:** 2.0 (PoC Aligned)  
**Updated:** November 26, 2025  
**Status:** Ready for Implementation  
**Priority:** Phase 1 - Foundation Service (Build Second)

---

## PoC Scope Summary

| Feature | Status | Notes |
|---------|--------|-------|
| Memory cache (L1) | ✅ In Scope | LRU dict, 100 entries max |
| File cache (L2) | ✅ In Scope | JSON files in data/cache/ |
| Global TTL | ✅ In Scope | Single TTL value (1 hour) |
| Exact-match lookup | ✅ In Scope | Hash-based cache keys |
| Basic hit/miss stats | ✅ In Scope | Simple counters |
| get/set/delete/clear | ✅ In Scope | Core operations |
| Redis (L2) | ❌ Deferred | Single-user doesn't need distributed cache |
| Semantic similarity cache | ❌ Deferred | Exact-match provides 80% value |
| Per-entry TTL | ❌ Deferred | Global TTL sufficient |
| Cache warming | ❌ Deferred | Not needed at PoC scale |
| Compression | ❌ Deferred | Files are small enough |
| Cache analytics | ❌ Deferred | Basic stats sufficient |

---

## Context & Objective

Build the **Cache Service** for Scout - a simple two-tier caching system that reduces LLM API costs by storing and reusing responses. Memory cache provides fast access, file cache provides persistence across restarts.

### Why This Service Exists

LLM API calls are expensive and slow (~1-3 seconds). Many requests are similar or identical:
- Same job posting processed multiple times
- Same analysis regenerated after page refresh
- Testing repeatedly with same inputs

The Cache Service avoids redundant API calls by storing responses keyed by request hash.

---

## Technical Requirements

### Dependencies

```toml
# No additional dependencies required beyond core
# Uses only: pydantic, json, hashlib, pathlib, datetime, collections.OrderedDict
```

### File Structure

```
scout/
├── app/
│   ├── models/
│   │   └── cache.py             # Cache data models
│   ├── services/
│   │   └── cache.py             # Cache Service
│   ├── config/
│   │   └── settings.py          # Add cache settings
│   └── utils/
│       └── exceptions.py        # Add cache exceptions
├── data/
│   └── cache/                   # File cache directory
│       └── *.json               # Cached entries
└── tests/
    └── unit/
        └── services/
            └── test_cache.py
```

---

## Data Models

Create `app/models/cache.py`:

```python
"""
Cache Service Data Models

Simple models for two-tier caching (memory + file).
"""

from pydantic import BaseModel, Field
from typing import Any, Optional, Dict
from datetime import datetime


class CacheEntry(BaseModel):
    """
    A single cached item.
    
    Stored in both memory and file cache.
    """
    key: str
    value: Any  # The cached data (must be JSON-serializable)
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime
    hit_count: int = 0
    
    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        return datetime.now() > self.expires_at
    
    class Config:
        # Allow arbitrary types for 'value' field
        arbitrary_types_allowed = True


class CacheStats(BaseModel):
    """
    Cache performance statistics.
    
    Tracks hit/miss rates for monitoring.
    """
    hits: int = 0
    misses: int = 0
    memory_entries: int = 0
    file_entries: int = 0
    
    @property
    def total_requests(self) -> int:
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
    """
    status: str = "healthy"  # "healthy", "degraded"
    memory_entries: int = 0
    memory_max: int = 100
    file_cache_accessible: bool = True
    stats: CacheStats = Field(default_factory=CacheStats)
    last_cleanup: Optional[datetime] = None
```

---

## Configuration

Add to `app/config/settings.py`:

```python
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # ... existing settings ...
    
    # Cache Settings
    cache_dir: Path = Path("data/cache")
    cache_memory_max_entries: int = 100
    cache_default_ttl: int = 3600  # 1 hour in seconds
    
    class Config:
        env_prefix = ""
        env_file = ".env"
```

---

## Exceptions

Add to `app/utils/exceptions.py`:

```python
class CacheError(ScoutError):
    """Error in Cache operations."""
    pass


class CacheKeyError(CacheError):
    """Invalid or missing cache key."""
    pass
```

---

## Service Implementation

Create `app/services/cache.py`:

```python
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
    key = cache.generate_key(prompt, model, temperature)
    cached = await cache.get(key)
    if cached is None:
        response = await llm.generate(...)
        await cache.set(key, response)
"""

import json
import hashlib
import logging
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Dict, List

from app.models.cache import CacheEntry, CacheStats, CacheHealth
from app.config.settings import settings
from app.utils.exceptions import CacheError

logger = logging.getLogger(__name__)


class CacheService:
    """
    Two-tier cache service with memory and file backends.
    
    Memory cache (L1):
    - Fast access, limited size (100 entries)
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
    
    def __init__(self):
        """Initialize the Cache Service."""
        self._initialized = False
        self._memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._memory_max = settings.cache_memory_max_entries
        self._default_ttl = settings.cache_default_ttl
        self._cache_dir = Path(settings.cache_dir)
        self._stats = CacheStats()
        self._last_cleanup: Optional[datetime] = None
    
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
    
    def generate_key(self, *args, **kwargs) -> str:
        """
        Generate a cache key from arguments.
        
        Creates MD5 hash of all arguments for consistent keying.
        
        Args:
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key
            
        Returns:
            32-character hexadecimal hash string
            
        Example:
            >>> key = cache.generate_key("prompt text", model="haiku", temp=0.3)
            >>> print(key)
            "a1b2c3d4e5f6..."
        """
        # Combine all arguments into a consistent string
        key_data = {
            "args": args,
            "kwargs": kwargs
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    # =========================================================================
    # MEMORY CACHE OPERATIONS
    # =========================================================================
    
    def _memory_get(self, key: str) -> Optional[CacheEntry]:
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
    
    async def _file_get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from file cache."""
        file_path = self._get_file_path(key)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            entry = CacheEntry(**data)
            
            # Check expiration
            if entry.is_expired():
                file_path.unlink(missing_ok=True)
                return None
            
            entry.hit_count += 1
            return entry
            
        except (json.JSONDecodeError, ValueError, IOError) as e:
            logger.warning(f"Failed to read cache file {file_path}: {e}")
            file_path.unlink(missing_ok=True)  # Remove corrupted file
            return None
    
    async def _file_set(self, key: str, entry: CacheEntry) -> None:
        """Set entry in file cache."""
        file_path = self._get_file_path(key)
        
        try:
            with open(file_path, 'w') as f:
                json.dump(entry.model_dump(mode='json'), f, default=str)
        except IOError as e:
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
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Checks memory cache first, then file cache.
        Promotes file cache hits to memory cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
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
        ttl: Optional[int] = None
    ) -> None:
        """
        Store value in cache.
        
        Writes to both memory and file cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (default: 1 hour)
        """
        self._ensure_initialized()
        
        if ttl is None:
            ttl = self._default_ttl
        
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        entry = CacheEntry(
            key=key,
            value=value,
            expires_at=expires_at
        )
        
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
            key: Cache key
            
        Returns:
            True if entry was found and deleted
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
            Number of entries cleared
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
            Number of expired entries removed
        """
        self._ensure_initialized()
        
        removed = 0
        
        for file_path in self._cache_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                entry = CacheEntry(**data)
                
                if entry.is_expired():
                    file_path.unlink()
                    removed += 1
                    
            except (json.JSONDecodeError, ValueError, IOError):
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
            CacheStats with hit/miss counts and entry counts
        """
        self._stats.memory_entries = len(self._memory_cache)
        return self._stats.model_copy()
    
    async def health_check(self) -> CacheHealth:
        """
        Check health of Cache Service.
        
        Returns:
            CacheHealth with status and diagnostics
        """
        # Check file cache accessibility
        file_ok = True
        try:
            test_file = self._cache_dir / ".health_check"
            test_file.write_text("ok")
            test_file.unlink()
        except IOError:
            file_ok = False
        
        status = "healthy" if file_ok else "degraded"
        
        return CacheHealth(
            status=status,
            memory_entries=len(self._memory_cache),
            memory_max=self._memory_max,
            file_cache_accessible=file_ok,
            stats=self.get_stats(),
            last_cleanup=self._last_cleanup
        )
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache (without retrieving).
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists and is not expired
        """
        # Check memory
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if not entry.is_expired():
                return True
        
        # Check file
        file_path = self._get_file_path(key)
        if file_path.exists():
            entry = await self._file_get(key)
            return entry is not None
        
        return False


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

_cache_instance: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """
    Get the Cache Service instance.
    
    Creates and initializes singleton on first call.
    Use as FastAPI dependency.
    
    Returns:
        Initialized CacheService
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
```

---

## Test Implementation

Create `tests/unit/services/test_cache.py`:

```python
"""
Unit tests for Cache Service.

Run with: pytest tests/unit/services/test_cache.py -v
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from app.services.cache import (
    CacheService, get_cache_service, shutdown_cache_service, reset_cache_service
)
from app.models.cache import CacheEntry, CacheStats, CacheHealth
from app.utils.exceptions import CacheError


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_cache_dir(tmp_path):
    """Provide temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def mock_settings(temp_cache_dir):
    """Mock settings with test values."""
    with patch("app.services.cache.settings") as mock:
        mock.cache_dir = temp_cache_dir
        mock.cache_memory_max_entries = 5  # Small for testing eviction
        mock.cache_default_ttl = 3600
        yield mock


@pytest.fixture
async def cache(mock_settings):
    """Create initialized Cache Service for testing."""
    reset_cache_service()
    service = CacheService()
    await service.initialize()
    yield service
    await service.shutdown()


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================

class TestInitialization:
    """Tests for service initialization."""
    
    @pytest.mark.asyncio
    async def test_initialize_creates_directory(self, mock_settings, temp_cache_dir):
        """Should create cache directory if needed."""
        # Remove directory
        import shutil
        shutil.rmtree(temp_cache_dir)
        assert not temp_cache_dir.exists()
        
        cache = CacheService()
        await cache.initialize()
        
        assert temp_cache_dir.exists()
    
    @pytest.mark.asyncio
    async def test_double_initialize_warning(self, cache, caplog):
        """Should warn on double initialization."""
        await cache.initialize()
        assert "already initialized" in caplog.text.lower()
    
    @pytest.mark.asyncio
    async def test_operation_before_init_raises(self, mock_settings):
        """Should raise error if not initialized."""
        cache = CacheService()
        
        with pytest.raises(CacheError, match="not initialized"):
            await cache.get("key")


# =============================================================================
# KEY GENERATION TESTS
# =============================================================================

class TestKeyGeneration:
    """Tests for cache key generation."""
    
    @pytest.mark.asyncio
    async def test_generate_key(self, cache):
        """Should generate consistent hash keys."""
        key1 = cache.generate_key("prompt", model="haiku", temp=0.3)
        key2 = cache.generate_key("prompt", model="haiku", temp=0.3)
        
        assert key1 == key2
        assert len(key1) == 32  # MD5 hex length
    
    @pytest.mark.asyncio
    async def test_different_inputs_different_keys(self, cache):
        """Should generate different keys for different inputs."""
        key1 = cache.generate_key("prompt1")
        key2 = cache.generate_key("prompt2")
        
        assert key1 != key2


# =============================================================================
# MEMORY CACHE TESTS
# =============================================================================

class TestMemoryCache:
    """Tests for memory cache tier."""
    
    @pytest.mark.asyncio
    async def test_memory_set_get(self, cache):
        """Should store and retrieve from memory."""
        await cache.set("key1", {"data": "value"})
        result = await cache.get("key1")
        
        assert result == {"data": "value"}
        assert cache._stats.hits == 1
    
    @pytest.mark.asyncio
    async def test_memory_lru_eviction(self, cache):
        """Should evict oldest entry when full."""
        # Fill cache (max 5)
        for i in range(5):
            await cache.set(f"key{i}", f"value{i}")
        
        assert len(cache._memory_cache) == 5
        
        # Add one more - should evict key0
        await cache.set("key5", "value5")
        
        assert len(cache._memory_cache) == 5
        assert "key0" not in cache._memory_cache
        assert "key5" in cache._memory_cache
    
    @pytest.mark.asyncio
    async def test_memory_lru_access_updates_order(self, cache):
        """Should update LRU order on access."""
        await cache.set("key0", "value0")
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        # Access key0 - moves to end
        await cache.get("key0")
        
        # Fill to trigger eviction
        await cache.set("key3", "value3")
        await cache.set("key4", "value4")
        await cache.set("key5", "value5")  # Should evict key1
        
        assert "key0" in cache._memory_cache  # Still there (was accessed)
        assert "key1" not in cache._memory_cache  # Evicted


# =============================================================================
# FILE CACHE TESTS
# =============================================================================

class TestFileCache:
    """Tests for file cache tier."""
    
    @pytest.mark.asyncio
    async def test_file_persistence(self, cache, temp_cache_dir):
        """Should persist to file."""
        await cache.set("persist_key", {"saved": True})
        
        # Check file exists
        file_path = temp_cache_dir / "persist_key.json"
        assert file_path.exists()
        
        # Verify content
        with open(file_path) as f:
            data = json.load(f)
        assert data["value"]["saved"] is True
    
    @pytest.mark.asyncio
    async def test_file_cache_recovery(self, mock_settings, temp_cache_dir):
        """Should recover from file after memory cleared."""
        # Create and populate cache
        cache1 = CacheService()
        await cache1.initialize()
        await cache1.set("recover_key", {"recovered": True})
        
        # Simulate restart - clear memory but files remain
        cache1._memory_cache.clear()
        
        # Get should recover from file
        result = await cache1.get("recover_key")
        
        assert result == {"recovered": True}
    
    @pytest.mark.asyncio
    async def test_corrupted_file_handling(self, cache, temp_cache_dir):
        """Should handle corrupted cache files."""
        # Create corrupted file
        bad_file = temp_cache_dir / "bad_key.json"
        bad_file.write_text("not valid json {{{")
        
        # Should return None, not raise
        result = await cache.get("bad_key")
        
        assert result is None
        assert not bad_file.exists()  # Should be removed


# =============================================================================
# EXPIRATION TESTS
# =============================================================================

class TestExpiration:
    """Tests for TTL and expiration."""
    
    @pytest.mark.asyncio
    async def test_entry_expires(self, cache):
        """Should return None for expired entries."""
        # Set with very short TTL
        await cache.set("expire_key", "value", ttl=1)
        
        # Should exist initially
        assert await cache.get("expire_key") == "value"
        
        # Wait for expiration
        import asyncio
        await asyncio.sleep(1.1)
        
        # Should be None now
        assert await cache.get("expire_key") is None
    
    @pytest.mark.asyncio
    async def test_cleanup_expired(self, cache, temp_cache_dir):
        """Should remove expired entries on cleanup."""
        # Create entry with past expiration
        expired_entry = CacheEntry(
            key="old_key",
            value="old_value",
            expires_at=datetime.now() - timedelta(hours=1)
        )
        
        file_path = temp_cache_dir / "old_key.json"
        with open(file_path, 'w') as f:
            json.dump(expired_entry.model_dump(mode='json'), f, default=str)
        
        assert file_path.exists()
        
        # Run cleanup
        removed = await cache.cleanup_expired()
        
        assert removed >= 1
        assert not file_path.exists()


# =============================================================================
# PUBLIC API TESTS
# =============================================================================

class TestPublicAPI:
    """Tests for public API methods."""
    
    @pytest.mark.asyncio
    async def test_get_miss(self, cache):
        """Should return None for missing key."""
        result = await cache.get("nonexistent")
        
        assert result is None
        assert cache._stats.misses == 1
    
    @pytest.mark.asyncio
    async def test_delete(self, cache):
        """Should delete from both tiers."""
        await cache.set("delete_key", "value")
        
        # Verify exists
        assert await cache.get("delete_key") == "value"
        
        # Delete
        deleted = await cache.delete("delete_key")
        
        assert deleted is True
        assert await cache.get("delete_key") is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, cache):
        """Should return False for missing key."""
        deleted = await cache.delete("nonexistent")
        assert deleted is False
    
    @pytest.mark.asyncio
    async def test_clear(self, cache, temp_cache_dir):
        """Should clear all entries."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        count = await cache.clear()
        
        assert count >= 2
        assert len(cache._memory_cache) == 0
        assert len(list(temp_cache_dir.glob("*.json"))) == 0
    
    @pytest.mark.asyncio
    async def test_exists(self, cache):
        """Should check existence without retrieving."""
        await cache.set("exist_key", "value")
        
        assert await cache.exists("exist_key") is True
        assert await cache.exists("nonexistent") is False


# =============================================================================
# STATS & HEALTH TESTS
# =============================================================================

class TestStatsAndHealth:
    """Tests for statistics and health checks."""
    
    @pytest.mark.asyncio
    async def test_get_stats(self, cache):
        """Should return accurate statistics."""
        await cache.set("key1", "value1")
        await cache.get("key1")  # Hit
        await cache.get("key2")  # Miss
        
        stats = cache.get_stats()
        
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.hit_rate == 50.0
    
    @pytest.mark.asyncio
    async def test_health_check(self, cache):
        """Should return health status."""
        health = await cache.health_check()
        
        assert health.status == "healthy"
        assert health.file_cache_accessible is True


# =============================================================================
# DEPENDENCY INJECTION TESTS
# =============================================================================

class TestDependencyInjection:
    """Tests for singleton pattern."""
    
    @pytest.mark.asyncio
    async def test_get_cache_service_singleton(self, mock_settings):
        """Should return same instance."""
        reset_cache_service()
        
        cache1 = await get_cache_service()
        cache2 = await get_cache_service()
        
        assert cache1 is cache2
        
        await shutdown_cache_service()
```

---

## Implementation Steps

Follow these steps in order, verifying each before proceeding:

### Step 3.1: Exceptions
```bash
# Add CacheError to app/utils/exceptions.py
# Verify:
python -c "from app.utils.exceptions import CacheError; print('OK')"
```

### Step 3.2: Configuration
```bash
# Add settings to app/config/settings.py
# Verify:
python -c "from app.config.settings import settings; print(settings.cache_dir)"
```

### Step 3.3: Data Models
```bash
# Create app/models/cache.py
# Verify:
python -c "from app.models.cache import CacheEntry, CacheStats; print('OK')"
```

### Step 3.4: Service Implementation
```bash
# Create app/services/cache.py
# Verify:
python -c "from app.services.cache import CacheService; print('OK')"
```

### Step 3.5: Unit Tests
```bash
# Create tests/unit/services/test_cache.py
# Verify:
pytest tests/unit/services/test_cache.py -v
```

### Step 3.6: Integration Verification
```bash
# Verify full integration:
python -c "
import asyncio
from app.services.cache import CacheService

async def test():
    cache = CacheService()
    await cache.initialize()
    
    key = cache.generate_key('test prompt', model='haiku')
    await cache.set(key, {'response': 'cached'})
    
    result = await cache.get(key)
    print(f'Cached: {result}')
    
    stats = cache.get_stats()
    print(f'Hit rate: {stats.hit_rate}%')

asyncio.run(test())
"
```

---

## Success Criteria

| Metric | Target | Verification |
|--------|--------|--------------|
| Memory LRU eviction | Works at capacity | Fill beyond max, verify oldest removed |
| File persistence | Survives restart | Set, clear memory, get returns value |
| TTL expiration | Automatic | Set with 1s TTL, wait, verify None |
| Hit rate tracking | Accurate | Compare hits/(hits+misses) |
| Test coverage | >90% | `pytest --cov=app/services/cache` |

---

## Edge Cases Handled

| Edge Case | Handling |
|-----------|----------|
| Missing cache directory | Create on initialize |
| Corrupted JSON files | Log warning, delete file, return None |
| Expired entries | Return None, clean up on access |
| Non-serializable values | Let JSON raise, caller handles |
| Concurrent access | Single-threaded PoC, not an issue |
| Disk full | Log error, continue with memory-only |

---

*This specification is aligned with Scout PoC Scope Document v1.0*
