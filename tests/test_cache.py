"""
Unit tests for Cache Service.

Run with: pytest tests/test_cache.py -v
"""

import asyncio
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.services.cache_service import (
    CacheEntry,
    CacheError,
    CacheHealth,
    CacheService,
    CacheStats,
    get_cache_service,
    reset_cache_service,
    shutdown_cache_service,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    """Provide temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
async def cache(temp_cache_dir: Path) -> CacheService:
    """Create initialized Cache Service for testing."""
    reset_cache_service()
    service = CacheService(
        cache_dir=temp_cache_dir,
        memory_max_entries=5,  # Small for testing eviction
        default_ttl=3600,
    )
    await service.initialize()
    yield service
    await service.shutdown()


@pytest.fixture
def uninitialized_cache(temp_cache_dir: Path) -> CacheService:
    """Create uninitialized Cache Service for testing."""
    return CacheService(cache_dir=temp_cache_dir)


# =============================================================================
# MODEL TESTS
# =============================================================================


class TestCacheEntryModel:
    """Tests for CacheEntry model."""

    def test_cache_entry_creation(self) -> None:
        """Should create a valid cache entry."""
        entry = CacheEntry(
            key="test_key",
            value={"data": "test"},
            expires_at=datetime.now() + timedelta(hours=1),
        )

        assert entry.key == "test_key"
        assert entry.value == {"data": "test"}
        assert entry.hit_count == 0
        assert not entry.is_expired()

    def test_cache_entry_expiration(self) -> None:
        """Should correctly detect expired entries."""
        expired_entry = CacheEntry(
            key="old_key",
            value="old",
            expires_at=datetime.now() - timedelta(hours=1),
        )

        assert expired_entry.is_expired()

    def test_cache_entry_not_expired(self) -> None:
        """Should correctly detect non-expired entries."""
        valid_entry = CacheEntry(
            key="new_key",
            value="new",
            expires_at=datetime.now() + timedelta(hours=1),
        )

        assert not valid_entry.is_expired()


class TestCacheStatsModel:
    """Tests for CacheStats model."""

    def test_stats_default_values(self) -> None:
        """Should have correct default values."""
        stats = CacheStats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.total_requests == 0
        assert stats.hit_rate == 0.0

    def test_stats_hit_rate_calculation(self) -> None:
        """Should calculate hit rate correctly."""
        stats = CacheStats(hits=7, misses=3)

        assert stats.total_requests == 10
        assert stats.hit_rate == 70.0

    def test_stats_zero_division_protection(self) -> None:
        """Should handle zero requests without division error."""
        stats = CacheStats(hits=0, misses=0)

        assert stats.hit_rate == 0.0


class TestCacheHealthModel:
    """Tests for CacheHealth model."""

    def test_health_default_values(self) -> None:
        """Should have correct default values."""
        health = CacheHealth()

        assert health.status == "healthy"
        assert health.memory_entries == 0
        assert health.memory_max == 100
        assert health.file_cache_accessible is True
        assert health.last_cleanup is None

    def test_health_with_stats(self) -> None:
        """Should include stats correctly."""
        stats = CacheStats(hits=5, misses=2)
        health = CacheHealth(
            status="healthy",
            memory_entries=10,
            stats=stats,
        )

        assert health.stats.hits == 5
        assert health.stats.hit_rate == pytest.approx(71.43, rel=0.01)


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


class TestInitialization:
    """Tests for service initialization."""

    @pytest.mark.asyncio
    async def test_initialize_creates_directory(self, tmp_path: Path) -> None:
        """Should create cache directory if needed."""
        cache_dir = tmp_path / "new_cache"
        assert not cache_dir.exists()

        cache = CacheService(cache_dir=cache_dir)
        await cache.initialize()

        assert cache_dir.exists()
        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_double_initialize_warning(
        self, cache: CacheService, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Should warn on double initialization."""
        await cache.initialize()
        assert "already initialized" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_operation_before_init_raises(
        self, uninitialized_cache: CacheService
    ) -> None:
        """Should raise error if not initialized."""
        with pytest.raises(CacheError, match="not initialized"):
            await uninitialized_cache.get("key")

    @pytest.mark.asyncio
    async def test_shutdown_clears_memory(self, cache: CacheService) -> None:
        """Should clear memory cache on shutdown."""
        await cache.set("key", "value")
        assert len(cache._memory_cache) == 1

        await cache.shutdown()
        assert len(cache._memory_cache) == 0

    @pytest.mark.asyncio
    async def test_shutdown_when_not_initialized(
        self, uninitialized_cache: CacheService
    ) -> None:
        """Should handle shutdown when not initialized."""
        # Should not raise
        await uninitialized_cache.shutdown()


# =============================================================================
# KEY GENERATION TESTS
# =============================================================================


class TestKeyGeneration:
    """Tests for cache key generation."""

    @pytest.mark.asyncio
    async def test_generate_key_consistency(self, cache: CacheService) -> None:
        """Should generate consistent hash keys."""
        key1 = cache.generate_key("prompt", model="haiku", temp=0.3)
        key2 = cache.generate_key("prompt", model="haiku", temp=0.3)

        assert key1 == key2
        assert len(key1) == 32  # MD5 hex length

    @pytest.mark.asyncio
    async def test_different_inputs_different_keys(self, cache: CacheService) -> None:
        """Should generate different keys for different inputs."""
        key1 = cache.generate_key("prompt1")
        key2 = cache.generate_key("prompt2")

        assert key1 != key2

    @pytest.mark.asyncio
    async def test_key_with_complex_data(self, cache: CacheService) -> None:
        """Should handle complex data in key generation."""
        key = cache.generate_key(
            "prompt",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.7,
            max_tokens=1000,
        )

        assert len(key) == 32

    @pytest.mark.asyncio
    async def test_key_order_independence(self, cache: CacheService) -> None:
        """Kwargs order should not affect key generation."""
        key1 = cache.generate_key("p", a=1, b=2)
        key2 = cache.generate_key("p", b=2, a=1)

        assert key1 == key2


# =============================================================================
# MEMORY CACHE TESTS
# =============================================================================


class TestMemoryCache:
    """Tests for memory cache tier."""

    @pytest.mark.asyncio
    async def test_memory_set_get(self, cache: CacheService) -> None:
        """Should store and retrieve from memory."""
        await cache.set("key1", {"data": "value"})
        result = await cache.get("key1")

        assert result == {"data": "value"}
        assert cache._stats.hits == 1

    @pytest.mark.asyncio
    async def test_memory_lru_eviction(self, cache: CacheService) -> None:
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
    async def test_memory_lru_access_updates_order(self, cache: CacheService) -> None:
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

    @pytest.mark.asyncio
    async def test_memory_expired_entry_removed_on_access(
        self, temp_cache_dir: Path
    ) -> None:
        """Should remove expired entries on access."""
        cache = CacheService(
            cache_dir=temp_cache_dir,
            memory_max_entries=5,
            default_ttl=1,  # 1 second TTL
        )
        await cache.initialize()

        await cache.set("expire_key", "value")

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Access should return None and remove entry
        result = await cache.get("expire_key")
        assert result is None

        await cache.shutdown()


# =============================================================================
# FILE CACHE TESTS
# =============================================================================


class TestFileCache:
    """Tests for file cache tier."""

    @pytest.mark.asyncio
    async def test_file_persistence(
        self, cache: CacheService, temp_cache_dir: Path
    ) -> None:
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
    async def test_file_cache_recovery(self, temp_cache_dir: Path) -> None:
        """Should recover from file after memory cleared."""
        # Create and populate cache
        cache1 = CacheService(cache_dir=temp_cache_dir)
        await cache1.initialize()
        await cache1.set("recover_key", {"recovered": True})

        # Simulate restart - clear memory but files remain
        cache1._memory_cache.clear()

        # Get should recover from file
        result = await cache1.get("recover_key")

        assert result == {"recovered": True}
        await cache1.shutdown()

    @pytest.mark.asyncio
    async def test_corrupted_file_handling(
        self, cache: CacheService, temp_cache_dir: Path
    ) -> None:
        """Should handle corrupted cache files."""
        # Create corrupted file
        bad_file = temp_cache_dir / "bad_key.json"
        bad_file.write_text("not valid json {{{")

        # Should return None, not raise
        result = await cache.get("bad_key")

        assert result is None
        assert not bad_file.exists()  # Should be removed

    @pytest.mark.asyncio
    async def test_file_promotes_to_memory(
        self, cache: CacheService, temp_cache_dir: Path
    ) -> None:
        """Should promote file cache hits to memory."""
        await cache.set("promote_key", "value")

        # Clear memory only
        cache._memory_cache.clear()
        assert "promote_key" not in cache._memory_cache

        # Get from file should promote to memory
        await cache.get("promote_key")

        assert "promote_key" in cache._memory_cache


# =============================================================================
# EXPIRATION TESTS
# =============================================================================


class TestExpiration:
    """Tests for TTL and expiration."""

    @pytest.mark.asyncio
    async def test_entry_expires(self, temp_cache_dir: Path) -> None:
        """Should return None for expired entries."""
        cache = CacheService(cache_dir=temp_cache_dir, default_ttl=1)
        await cache.initialize()

        # Set with very short TTL
        await cache.set("expire_key", "value", ttl=1)

        # Should exist initially
        assert await cache.get("expire_key") == "value"

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be None now
        assert await cache.get("expire_key") is None

        await cache.shutdown()

    @pytest.mark.asyncio
    async def test_custom_ttl(self, cache: CacheService) -> None:
        """Should respect custom TTL."""
        await cache.set("ttl_key", "value", ttl=7200)

        # Entry should be in memory with correct expiration
        entry = cache._memory_cache.get("ttl_key")
        assert entry is not None

        # Should expire roughly 2 hours from now (with some tolerance)
        time_until_expiry = (entry.expires_at - datetime.now()).total_seconds()
        assert 7100 < time_until_expiry < 7200

    @pytest.mark.asyncio
    async def test_cleanup_expired(
        self, cache: CacheService, temp_cache_dir: Path
    ) -> None:
        """Should remove expired entries on cleanup."""
        # Create entry with past expiration
        expired_entry = CacheEntry(
            key="old_key",
            value="old_value",
            expires_at=datetime.now() - timedelta(hours=1),
        )

        file_path = temp_cache_dir / "old_key.json"
        with open(file_path, "w") as f:
            json.dump(expired_entry.model_dump(mode="json"), f, default=str)

        assert file_path.exists()

        # Run cleanup
        removed = await cache.cleanup_expired()

        assert removed >= 1
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_cleanup_records_timestamp(self, cache: CacheService) -> None:
        """Should record cleanup timestamp."""
        assert cache._last_cleanup is None

        await cache.cleanup_expired()

        assert cache._last_cleanup is not None
        assert isinstance(cache._last_cleanup, datetime)


# =============================================================================
# PUBLIC API TESTS
# =============================================================================


class TestPublicAPI:
    """Tests for public API methods."""

    @pytest.mark.asyncio
    async def test_get_miss(self, cache: CacheService) -> None:
        """Should return None for missing key."""
        result = await cache.get("nonexistent")

        assert result is None
        assert cache._stats.misses == 1

    @pytest.mark.asyncio
    async def test_delete(self, cache: CacheService) -> None:
        """Should delete from both tiers."""
        await cache.set("delete_key", "value")

        # Verify exists
        assert await cache.get("delete_key") == "value"

        # Delete
        deleted = await cache.delete("delete_key")

        assert deleted is True
        assert await cache.get("delete_key") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, cache: CacheService) -> None:
        """Should return False for missing key."""
        deleted = await cache.delete("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_clear(
        self, cache: CacheService, temp_cache_dir: Path
    ) -> None:
        """Should clear all entries."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        count = await cache.clear()

        assert count >= 2
        assert len(cache._memory_cache) == 0
        assert len(list(temp_cache_dir.glob("*.json"))) == 0

    @pytest.mark.asyncio
    async def test_exists(self, cache: CacheService) -> None:
        """Should check existence without retrieving."""
        await cache.set("exist_key", "value")

        assert await cache.exists("exist_key") is True
        assert await cache.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_exists_checks_expiration(self, temp_cache_dir: Path) -> None:
        """Should return False for expired entries in exists check."""
        cache = CacheService(cache_dir=temp_cache_dir, default_ttl=1)
        await cache.initialize()

        await cache.set("expire_key", "value", ttl=1)

        assert await cache.exists("expire_key") is True

        await asyncio.sleep(1.1)

        assert await cache.exists("expire_key") is False

        await cache.shutdown()


# =============================================================================
# STATS & HEALTH TESTS
# =============================================================================


class TestStatsAndHealth:
    """Tests for statistics and health checks."""

    @pytest.mark.asyncio
    async def test_get_stats(self, cache: CacheService) -> None:
        """Should return accurate statistics."""
        await cache.set("key1", "value1")
        await cache.get("key1")  # Hit
        await cache.get("key2")  # Miss

        stats = cache.get_stats()

        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.hit_rate == 50.0

    @pytest.mark.asyncio
    async def test_get_stats_returns_copy(self, cache: CacheService) -> None:
        """Should return a copy of stats, not reference."""
        stats1 = cache.get_stats()
        await cache.get("missing")  # Add a miss
        stats2 = cache.get_stats()

        assert stats1.misses == 0
        assert stats2.misses == 1

    @pytest.mark.asyncio
    async def test_health_check(self, cache: CacheService) -> None:
        """Should return health status."""
        health = await cache.health_check()

        assert health.status == "healthy"
        assert health.file_cache_accessible is True

    @pytest.mark.asyncio
    async def test_health_check_includes_stats(self, cache: CacheService) -> None:
        """Should include stats in health check."""
        await cache.set("key", "value")
        await cache.get("key")

        health = await cache.health_check()

        assert health.stats.hits == 1
        assert health.memory_entries == 1


# =============================================================================
# DEPENDENCY INJECTION TESTS
# =============================================================================


class TestDependencyInjection:
    """Tests for singleton pattern."""

    @pytest.mark.asyncio
    async def test_get_cache_service_singleton(self, tmp_path: Path) -> None:
        """Should return same instance."""
        reset_cache_service()

        # Monkey-patch the default cache dir for testing
        from src.services.cache_service import service as cache_module

        original_default = cache_module.DEFAULT_CACHE_DIR
        cache_module.DEFAULT_CACHE_DIR = tmp_path / "singleton_cache"

        try:
            cache1 = await get_cache_service()
            cache2 = await get_cache_service()

            assert cache1 is cache2

            await shutdown_cache_service()
        finally:
            cache_module.DEFAULT_CACHE_DIR = original_default

    @pytest.mark.asyncio
    async def test_shutdown_cache_service(self, tmp_path: Path) -> None:
        """Should shutdown and clear instance."""
        reset_cache_service()

        from src.services.cache_service import service as cache_module

        original_default = cache_module.DEFAULT_CACHE_DIR
        cache_module.DEFAULT_CACHE_DIR = tmp_path / "shutdown_cache"

        try:
            cache = await get_cache_service()
            assert cache._initialized is True

            await shutdown_cache_service()

            # Getting service again should create new instance
            cache2 = await get_cache_service()
            assert cache2 is not cache

            await shutdown_cache_service()
        finally:
            cache_module.DEFAULT_CACHE_DIR = original_default

    @pytest.mark.asyncio
    async def test_reset_cache_service(self, tmp_path: Path) -> None:
        """Should reset global instance."""
        reset_cache_service()

        from src.services.cache_service import service as cache_module

        # Verify instance is None
        assert cache_module._cache_instance is None


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_set_various_value_types(self, cache: CacheService) -> None:
        """Should handle various JSON-serializable types."""
        test_values = [
            ("string_key", "simple string"),
            ("int_key", 42),
            ("float_key", 3.14),
            ("bool_key", True),
            ("none_key", None),
            ("list_key", [1, 2, 3]),
            ("dict_key", {"nested": {"deep": "value"}}),
        ]

        for key, value in test_values:
            await cache.set(key, value)
            result = await cache.get(key)
            assert result == value, f"Failed for {key}"

    @pytest.mark.asyncio
    async def test_empty_cache_clear(self, cache: CacheService) -> None:
        """Should handle clearing empty cache."""
        count = await cache.clear()
        assert count == 0

    @pytest.mark.asyncio
    async def test_empty_cache_cleanup(self, cache: CacheService) -> None:
        """Should handle cleanup on empty cache."""
        removed = await cache.cleanup_expired()
        assert removed == 0

    @pytest.mark.asyncio
    async def test_stats_after_clear(self, cache: CacheService) -> None:
        """Should reset stats after clear."""
        await cache.set("key", "value")
        await cache.get("key")

        await cache.clear()

        stats = cache.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0
