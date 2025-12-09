---
updated: 2025-10-04, 19:27
---

## Cache Service - Claude Code Instructions

## Context & Objective

You're building the **Cache Service** for Scout, a high-performance caching layer that reduces costs and improves response times by storing and retrieving expensive operation results. This service supports multiple cache backends (Redis, disk, memory) and implements intelligent caching strategies.

## Module Specifications

**Purpose**: Provide a unified caching interface with intelligent invalidation, TTL management, and cache warming strategies to minimize redundant API calls and expensive computations while maintaining data freshness.

**Key Responsibilities**:
1. Multi-tier caching (memory → Redis → disk)
2. Intelligent cache key generation
3. TTL management with automatic refresh
4. Cache invalidation strategies
5. Semantic similarity caching for LLM responses
6. Cache warming and preloading
7. Cache analytics and hit rate optimization

## Technical Requirements

**Dependencies**:
- FastAPI framework
- Pydantic for data validation
- Redis for distributed cache
- Diskcache for persistent storage
- FAISS for semantic similarity
- Hashlib for key generation
- LZ4 for compression
- Pandas for analytics

**File Structure**:
```
scout/
├── app/
│   ├── services/
│   │   ├── cache.py                # Main cache service
│   │   ├── cache_backends/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Abstract cache backend
│   │   │   ├── redis_backend.py   # Redis implementation
│   │   │   ├── disk_backend.py    # Disk cache implementation
│   │   │   └── memory_backend.py  # In-memory cache
│   │   ├── cache_strategies/
│   │   │   ├── __init__.py
│   │   │   ├── lru.py            # LRU eviction
│   │   │   ├── semantic.py       # Semantic similarity cache
│   │   │   └── predictive.py     # Predictive caching
│   │   └── cache_analytics.py     # Cache performance analytics
│   ├── models/
│   │   └── cache.py               # Cache-related models
│   └── utils/
│       └── cache_utils.py         # Cache utilities
├── data/
│   ├── cache/
│   │   ├── disk/                  # Disk cache storage
│   │   └── embeddings/            # Semantic embeddings
│   └── cache_analytics/           # Analytics data
└── tests/
    └── test_cache_service.py
```

## Data Models to Implement

Create these models in `app/models/cache.py`:

```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any, Union, Generic, TypeVar
from datetime import datetime, timedelta
from enum import Enum
import hashlib
from abc import ABC, abstractmethod

T = TypeVar('T')

class CacheBackend(str, Enum):
    MEMORY = "memory"
    REDIS = "redis"
    DISK = "disk"
    HYBRID = "hybrid"  # Multi-tier

class CacheStrategy(str, Enum):
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live only
    SEMANTIC = "semantic"  # Similarity-based
    PREDICTIVE = "predictive"  # ML-based prediction

class SerializationType(str, Enum):
    JSON = "json"
    PICKLE = "pickle"
    MSGPACK = "msgpack"
    CUSTOM = "custom"

class CompressionType(str, Enum):
    NONE = "none"
    GZIP = "gzip"
    LZ4 = "lz4"
    ZSTD = "zstd"

class CacheEntry(BaseModel, Generic[T]):
    """Single cache entry"""
    key: str
    value: Any  # Will be T when retrieved
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    accessed_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    # Usage statistics
    access_count: int = 0
    size_bytes: int = 0
    
    # Categorization
    namespace: Optional[str] = None
    tags: List[str] = []
    
    # Storage details
    backend: CacheBackend
    compressed: bool = False
    compression_type: Optional[CompressionType] = None
    serialization: SerializationType = SerializationType.JSON
    
    # Invalidation
    invalidation_keys: List[str] = []  # Keys that invalidate this entry
    depends_on: List[str] = []  # Other cache keys this depends on
    
    @validator('expires_at')
    def validate_expiry(cls, v, values):
        if v and v <= values.get('created_at', datetime.now()):
            raise ValueError("Expiry time must be after creation time")
        return v
    
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
    
    def is_stale(self, max_age: timedelta) -> bool:
        """Check if entry is stale based on age"""
        age = datetime.now() - self.created_at
        return age > max_age

class CacheKey(BaseModel):
    """Cache key generation configuration"""
    prefix: str  # e.g., "llm", "job", "profile"
    identifier: str  # Main identifier
    parameters: Dict[str, Any] = {}  # Additional parameters
    
    # Key options
    include_version: bool = True
    version: str = "v1"
    hash_parameters: bool = True
    
    def generate(self) -> str:
        """Generate cache key"""
        parts = [self.prefix, self.identifier]
        
        if self.include_version:
            parts.append(self.version)
        
        if self.parameters:
            if self.hash_parameters:
                # Hash parameters for consistent key
                param_str = json.dumps(self.parameters, sort_keys=True)
                param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
                parts.append(param_hash)
            else:
                # Include parameters directly
                for k, v in sorted(self.parameters.items()):
                    parts.append(f"{k}_{v}")
        
        return ":".join(parts)

class CacheConfig(BaseModel):
    """Cache configuration"""
    # Backend configuration
    backend: CacheBackend = CacheBackend.HYBRID
    backends_config: Dict[str, Dict] = {
        "memory": {"max_size_mb": 100},
        "redis": {"host": "localhost", "port": 6379, "db": 0},
        "disk": {"directory": "data/cache/disk", "size_limit": 1024 * 1024 * 1024}  # 1GB
    }
    
    # Strategy configuration
    default_strategy: CacheStrategy = CacheStrategy.LRU
    strategy_config: Dict[CacheStrategy, Dict] = {}
    
    # TTL configuration
    default_ttl: int = 3600  # seconds
    ttl_by_prefix: Dict[str, int] = {
        "llm": 7200,  # 2 hours for LLM responses
        "job": 86400,  # 24 hours for job data
        "profile": 3600,  # 1 hour for profile data
        "analysis": 1800  # 30 minutes for analysis
    }
    
    # Performance settings
    compression_enabled: bool = True
    compression_type: CompressionType = CompressionType.LZ4
    compression_threshold: int = 1024  # Compress if > 1KB
    
    # Semantic cache settings
    semantic_threshold: float = 0.95  # Similarity threshold
    semantic_enabled: bool = True
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # Cache warming
    warm_on_startup: bool = True
    warm_patterns: List[str] = []  # Key patterns to warm
    
    # Monitoring
    track_statistics: bool = True
    statistics_sample_rate: float = 1.0  # Sample all requests

class CacheStatistics(BaseModel):
    """Cache performance statistics"""
    period_start: datetime
    period_end: datetime
    
    # Basic metrics
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    hit_rate: float = Field(ge=0, le=1)
    
    # Performance metrics
    average_hit_latency: float  # milliseconds
    average_miss_latency: float
    p95_hit_latency: float
    p95_miss_latency: float
    
    # Size metrics
    total_entries: int
    total_size_bytes: int
    average_entry_size: int
    
    # Breakdown by namespace
    stats_by_namespace: Dict[str, Dict[str, Any]] = {}
    
    # Top keys
    most_accessed_keys: List[Dict[str, Any]] = []  # key, count, last_access
    largest_entries: List[Dict[str, Any]] = []  # key, size, created
    
    # Eviction stats
    eviction_count: int = 0
    evictions_by_reason: Dict[str, int] = {}  # reason -> count
    
    # Cost savings (estimated)
    estimated_cost_saved: float = 0.0  # USD
    api_calls_saved: int = 0
    
    @validator('hit_rate', always=True)
    def calculate_hit_rate(cls, v, values):
        total = values.get('total_requests', 0)
        hits = values.get('cache_hits', 0)
        return hits / total if total > 0 else 0

class SemanticCacheEntry(BaseModel):
    """Entry in semantic similarity cache"""
    key: str
    query: str  # Original query
    response: str  # Cached response
    embedding: List[float]  # Query embedding
    
    # Metadata
    created_at: datetime
    use_count: int = 0
    last_used: datetime
    
    # Similarity matches
    similar_queries: List[str] = []  # Queries that matched this
    similarity_scores: List[float] = []

class CacheWarmingTask(BaseModel):
    """Cache warming task configuration"""
    task_id: str
    pattern: str  # Key pattern to warm
    source: str  # Where to get data from
    
    # Schedule
    run_at_startup: bool = True
    schedule: Optional[str] = None  # Cron expression
    
    # Progress
    status: str = "pending"  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    keys_warmed: int = 0
    errors: List[str] = []

class InvalidationRule(BaseModel):
    """Cache invalidation rule"""
    rule_id: str
    name: str
    
    # Trigger
    trigger_type: str  # "time", "event", "dependency"
    trigger_config: Dict[str, Any]
    
    # Target
    target_pattern: str  # Key pattern to invalidate
    cascade: bool = False  # Invalidate dependencies
    
    # Actions
    action: str = "delete"  # "delete", "refresh", "mark_stale"
    
    # Schedule for time-based
    schedule: Optional[str] = None
    last_run: Optional[datetime] = None
    
    # Event-based
    event_types: List[str] = []  # Events that trigger invalidation
    
    # Statistics
    total_invalidations: int = 0

class CacheOperation(BaseModel):
    """Cache operation for audit/debugging"""
    operation_id: str
    timestamp: datetime
    
    operation: str  # "get", "set", "delete", "invalidate"
    key: str
    
    # Result
    success: bool
    hit: Optional[bool] = None  # For get operations
    latency: float  # milliseconds
    
    # Context
    namespace: Optional[str] = None
    backend_used: Optional[CacheBackend] = None
    
    # Error info
    error: Optional[str] = None
    error_type: Optional[str] = None

class CacheTier(BaseModel):
    """Configuration for a cache tier in multi-tier setup"""
    tier_level: int  # 1 = fastest (memory), higher = slower
    backend: CacheBackend
    
    # Capacity
    max_size_bytes: int
    max_entries: int
    
    # Performance characteristics
    read_latency: float  # Average milliseconds
    write_latency: float
    
    # Promotion/demotion rules
    promote_on_hits: int = 2  # Promote after N hits
    demote_after_seconds: int = 3600  # Demote if not accessed
    
    # Current state
    current_size_bytes: int = 0
    current_entries: int = 0
    
    def has_capacity(self, size_bytes: int) -> bool:
        """Check if tier has capacity for entry"""
        return (
            self.current_size_bytes + size_bytes <= self.max_size_bytes and
            self.current_entries + 1 <= self.max_entries
        )

class CachePolicy(BaseModel):
    """Cache policy configuration"""
    policy_id: str
    name: str
    description: str
    
    # Applicability
    applies_to: List[str] = []  # Namespaces or key patterns
    priority: int = 0  # Higher priority policies override lower
    
    # TTL policy
    ttl_seconds: Optional[int] = None
    refresh_on_access: bool = False
    
    # Size policy
    max_entry_size: Optional[int] = None  # bytes
    compression_required: bool = False
    
    # Storage policy
    allowed_backends: List[CacheBackend] = []
    preferred_backend: Optional[CacheBackend] = None
    
    # Invalidation policy
    invalidation_rules: List[InvalidationRule] = []
    
    # Security
    encrypt_at_rest: bool = False
    require_authentication: bool = False
```

## Cache Service Implementation

Create the main service in `app/services/cache.py`:

```python
import asyncio
import json
import pickle
import time
import hashlib
from typing import Optional, Any, Dict, List, Union, TypeVar, Generic
from datetime import datetime, timedelta
import logging
from functools import wraps
import lz4.frame
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

from app.models.cache import (
    CacheEntry, CacheKey, CacheConfig, CacheStatistics,
    SemanticCacheEntry, CacheBackend, CacheStrategy,
    CompressionType, SerializationType, CacheTier,
    CacheOperation, InvalidationRule
)
from app.services.cache_backends.redis_backend import RedisBackend
from app.services.cache_backends.disk_backend import DiskBackend
from app.services.cache_backends.memory_backend import MemoryBackend
from app.config.settings import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheService(Generic[T]):
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        
        # Initialize backends
        self.backends = {}
        self._initialize_backends()
        
        # Initialize tiers for hybrid caching
        self.tiers = self._initialize_tiers()
        
        # Statistics tracking
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0
        }
        self.operation_log = []
        
        # Semantic cache for LLM responses
        if self.config.semantic_enabled:
            self.semantic_cache = SemanticCache(
                model_name=self.config.embedding_model,
                threshold=self.config.semantic_threshold
            )
        else:
            self.semantic_cache = None
        
        # Invalidation rules
        self.invalidation_rules: List[InvalidationRule] = []
        
        # Lock for thread safety
        self.lock = asyncio.Lock()
        
        # Background tasks
        self.background_tasks = []
        if self.config.warm_on_startup:
            self.background_tasks.append(
                asyncio.create_task(self._warm_cache())
            )
    
    def _initialize_backends(self):
        """Initialize cache backends"""
        if self.config.backend in [CacheBackend.MEMORY, CacheBackend.HYBRID]:
            self.backends[CacheBackend.MEMORY] = MemoryBackend(
                **self.config.backends_config.get("memory", {})
            )
        
        if self.config.backend in [CacheBackend.REDIS, CacheBackend.HYBRID]:
            self.backends[CacheBackend.REDIS] = RedisBackend(
                **self.config.backends_config.get("redis", {})
            )
        
        if self.config.backend in [CacheBackend.DISK, CacheBackend.HYBRID]:
            self.backends[CacheBackend.DISK] = DiskBackend(
                **self.config.backends_config.get("disk", {})
            )
    
    def _initialize_tiers(self) -> List[CacheTier]:
        """Initialize cache tiers for hybrid mode"""
        if self.config.backend != CacheBackend.HYBRID:
            return []
        
        return [
            CacheTier(
                tier_level=1,
                backend=CacheBackend.MEMORY,
                max_size_bytes=100 * 1024 * 1024,  # 100MB
                max_entries=1000,
                read_latency=0.1,
                write_latency=0.1
            ),
            CacheTier(
                tier_level=2,
                backend=CacheBackend.REDIS,
                max_size_bytes=1024 * 1024 * 1024,  # 1GB
                max_entries=100000,
                read_latency=1.0,
                write_latency=1.0
            ),
            CacheTier(
                tier_level=3,
                backend=CacheBackend.DISK,
                max_size_bytes=10 * 1024 * 1024 * 1024,  # 10GB
                max_entries=1000000,
                read_latency=10.0,
                write_latency=10.0
            )
        ]
    
    async def get(
        self,
        key: Union[str, CacheKey],
        default: Optional[T] = None,
        namespace: Optional[str] = None
    ) -> Optional[T]:
        """Get value from cache"""
        start_time = time.time()
        
        # Generate key if needed
        if isinstance(key, CacheKey):
            cache_key = key.generate()
            namespace = namespace or key.prefix
        else:
            cache_key = key
        
        # Log operation
        operation = CacheOperation(
            operation_id=str(time.time()),
            timestamp=datetime.now(),
            operation="get",
            key=cache_key,
            namespace=namespace
        )
        
        try:
            # Try semantic cache first for LLM responses
            if namespace == "llm" and self.semantic_cache:
                result = await self.semantic_cache.get(cache_key)
                if result:
                    self.stats['hits'] += 1
                    operation.success = True
                    operation.hit = True
                    return result
            
            # Try each tier in order (hybrid mode)
            if self.config.backend == CacheBackend.HYBRID:
                for tier in self.tiers:
                    backend = self.backends[tier.backend]
                    result = await backend.get(cache_key)
                    
                    if result is not None:
                        # Cache hit
                        self.stats['hits'] += 1
                        operation.success = True
                        operation.hit = True
                        operation.backend_used = tier.backend
                        
                        # Promote to faster tier if accessed frequently
                        if tier.tier_level > 1:
                            await self._promote_entry(cache_key, result, tier)
                        
                        # Deserialize and decompress
                        value = await self._deserialize(result)
                        
                        # Update access time
                        await self._update_access_time(cache_key)
                        
                        return value
            else:
                # Single backend mode
                backend = self.backends[self.config.backend]
                result = await backend.get(cache_key)
                
                if result is not None:
                    self.stats['hits'] += 1
                    operation.success = True
                    operation.hit = True
                    
                    value = await self._deserialize(result)
                    await self._update_access_time(cache_key)
                    
                    return value
            
            # Cache miss
            self.stats['misses'] += 1
            operation.success = True
            operation.hit = False
            
            return default
            
        except Exception as e:
            self.stats['errors'] += 1
            operation.success = False
            operation.error = str(e)
            operation.error_type = type(e).__name__
            logger.error(f"Cache get error for key {cache_key}: {e}")
            return default
            
        finally:
            operation.latency = (time.time() - start_time) * 1000
            self.operation_log.append(operation)
    
    async def set(
        self,
        key: Union[str, CacheKey],
        value: T,
        ttl: Optional[int] = None,
        namespace: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Set value in cache"""
        start_time = time.time()
        
        # Generate key if needed
        if isinstance(key, CacheKey):
            cache_key = key.generate()
            namespace = namespace or key.prefix
        else:
            cache_key = key
        
        # Determine TTL
        if ttl is None:
            ttl = self.config.ttl_by_prefix.get(
                namespace,
                self.config.default_ttl
            )
        
        # Log operation
        operation = CacheOperation(
            operation_id=str(time.time()),
            timestamp=datetime.now(),
            operation="set",
            key=cache_key,
            namespace=namespace
        )
        
        try:
            # Serialize and compress
            serialized = await self._serialize(value)
            size_bytes = len(serialized)
            
            # Create cache entry
            entry = CacheEntry(
                key=cache_key,
                value=serialized,
                expires_at=datetime.now() + timedelta(seconds=ttl) if ttl else None,
                size_bytes=size_bytes,
                namespace=namespace,
                tags=tags or [],
                backend=self.config.backend,
                compressed=size_bytes > self.config.compression_threshold,
                compression_type=self.config.compression_type if size_bytes > self.config.compression_threshold else None
            )
            
            # Add to semantic cache if LLM response
            if namespace == "llm" and self.semantic_cache and isinstance(value, str):
                await self.semantic_cache.add(cache_key, value)
            
            # Store in appropriate tier (hybrid mode)
            if self.config.backend == CacheBackend.HYBRID:
                stored = False
                for tier in self.tiers:
                    if tier.has_capacity(size_bytes):
                        backend = self.backends[tier.backend]
                        success = await backend.set(cache_key, serialized, ttl)
                        
                        if success:
                            tier.current_size_bytes += size_bytes
                            tier.current_entries += 1
                            stored = True
                            operation.backend_used = tier.backend
                            break
                
                if not stored:
                    # Evict from lowest tier and retry
                    await self._evict_from_tier(self.tiers[-1], size_bytes)
                    backend = self.backends[self.tiers[-1].backend]
                    success = await backend.set(cache_key, serialized, ttl)
                    operation.backend_used = self.tiers[-1].backend
            else:
                # Single backend mode
                backend = self.backends[self.config.backend]
                success = await backend.set(cache_key, serialized, ttl)
            
            self.stats['sets'] += 1
            operation.success = success
            
            # Trigger invalidation of dependent keys
            await self._invalidate_dependencies(cache_key)
            
            return success
            
        except Exception as e:
            self.stats['errors'] += 1
            operation.success = False
            operation.error = str(e)
            operation.error_type = type(e).__name__
            logger.error(f"Cache set error for key {cache_key}: {e}")
            return False
            
        finally:
            operation.latency = (time.time() - start_time) * 1000
            self.operation_log.append(operation)
    
    async def delete(
        self,
        key: Union[str, CacheKey],
        namespace: Optional[str] = None
    ) -> bool:
        """Delete value from cache"""
        start_time = time.time()
        
        # Generate key if needed
        if isinstance(key, CacheKey):
            cache_key = key.generate()
            namespace = namespace or key.prefix
        else:
            cache_key = key
        
        # Log operation
        operation = CacheOperation(
            operation_id=str(time.time()),
            timestamp=datetime.now(),
            operation="delete",
            key=cache_key,
            namespace=namespace
        )
        
        try:
            deleted = False
            
            # Delete from all backends
            for backend_type, backend in self.backends.items():
                success = await backend.delete(cache_key)
                deleted = deleted or success
            
            # Remove from semantic cache
            if namespace == "llm" and self.semantic_cache:
                await self.semantic_cache.remove(cache_key)
            
            self.stats['deletes'] += 1
            operation.success = deleted
            
            # Trigger invalidation of dependent keys
            await self._invalidate_dependencies(cache_key)
            
            return deleted
            
        except Exception as e:
            self.stats['errors'] += 1
            operation.success = False
            operation.error = str(e)
            operation.error_type = type(e).__name__
            logger.error(f"Cache delete error for key {cache_key}: {e}")
            return False
            
        finally:
            operation.latency = (time.time() - start_time) * 1000
            self.operation_log.append(operation)
    
    async def invalidate_pattern(
        self,
        pattern: str,
        cascade: bool = False
    ) -> int:
        """Invalidate all keys matching pattern"""
        invalidated_count = 0
        
        for backend_type, backend in self.backends.items():
            keys = await backend.keys(pattern)
            
            for key in keys:
                if await self.delete(key):
                    invalidated_count += 1
                    
                    if cascade:
                        # Invalidate dependencies
                        await self._invalidate_dependencies(key)
        
        logger.info(f"Invalidated {invalidated_count} keys matching pattern {pattern}")
        return invalidated_count
    
    async def clear(self, namespace: Optional[str] = None) -> bool:
        """Clear all cache or specific namespace"""
        try:
            if namespace:
                pattern = f"{namespace}:*"
                await self.invalidate_pattern(pattern)
            else:
                for backend in self.backends.values():
                    await backend.clear()
                
                if self.semantic_cache:
                    await self.semantic_cache.clear()
            
            return True
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    async def get_statistics(
        self,
        period_minutes: int = 60
    ) -> CacheStatistics:
        """Get cache performance statistics"""
        period_start = datetime.now() - timedelta(minutes=period_minutes)
        period_end = datetime.now()
        
        # Calculate basic metrics
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
        
        # Calculate latencies from operation log
        recent_ops = [
            op for op in self.operation_log
            if op.timestamp >= period_start
        ]
        
        hit_latencies = [op.latency for op in recent_ops if op.hit is True]
        miss_latencies = [op.latency for op in recent_ops if op.hit is False]
        
        # Get size metrics
        total_entries = 0
        total_size = 0
        
        for backend in self.backends.values():
            info = await backend.info()
            total_entries += info.get('keys', 0)
            total_size += info.get('used_memory', 0)
        
        # Calculate cost savings (rough estimate)
        # Assume $0.01 per API call saved
        estimated_cost_saved = self.stats['hits'] * 0.01
        
        return CacheStatistics(
            period_start=period_start,
            period_end=period_end,
            total_requests=total_requests,
            cache_hits=self.stats['hits'],
            cache_misses=self.stats['misses'],
            hit_rate=hit_rate,
            average_hit_latency=np.mean(hit_latencies) if hit_latencies else 0,
            average_miss_latency=np.mean(miss_latencies) if miss_latencies else 0,
            p95_hit_latency=np.percentile(hit_latencies, 95) if hit_latencies else 0,
            p95_miss_latency=np.percentile(miss_latencies, 95) if miss_latencies else 0,
            total_entries=total_entries,
            total_size_bytes=total_size,
            average_entry_size=total_size // total_entries if total_entries > 0 else 0,
            estimated_cost_saved=estimated_cost_saved,
            api_calls_saved=self.stats['hits']
        )
    
    async def _serialize(self, value: Any) -> bytes:
        """Serialize and optionally compress value"""
        # Choose serialization method
        if self.config.backend == CacheBackend.REDIS:
            # Redis needs string or bytes
            if isinstance(value, str):
                serialized = value.encode('utf-8')
            else:
                serialized = pickle.dumps(value)
        else:
            serialized = pickle.dumps(value)
        
        # Compress if needed
        if len(serialized) > self.config.compression_threshold and self.config.compression_enabled:
            if self.config.compression_type == CompressionType.LZ4:
                serialized = lz4.frame.compress(serialized)
            # Add other compression types as needed
        
        return serialized
    
    async def _deserialize(self, data: bytes) -> Any:
        """Decompress and deserialize value"""
        # Decompress if needed
        if self.config.compression_enabled:
            try:
                # Try to decompress
                data = lz4.frame.decompress(data)
            except:
                # Not compressed or different format
                pass
        
        # Deserialize
        try:
            return pickle.loads(data)
        except:
            # Try as string
            return data.decode('utf-8')
    
    async def _promote_entry(
        self,
        key: str,
        value: Any,
        current_tier: CacheTier
    ):
        """Promote entry to faster tier"""
        if current_tier.tier_level <= 1:
            return  # Already in fastest tier
        
        target_tier = self.tiers[current_tier.tier_level - 2]  # Move up one tier
        
        if target_tier.has_capacity(len(value)):
            backend = self.backends[target_tier.backend]
            await backend.set(key, value)
            target_tier.current_entries += 1
            target_tier.current_size_bytes += len(value)
    
    async def _evict_from_tier(
        self,
        tier: CacheTier,
        required_space: int
    ):
        """Evict entries from tier to make space"""
        backend = self.backends[tier.backend]
        
        # Get LRU entries
        # This is simplified - real implementation would track LRU properly
        keys = await backend.keys("*")
        
        freed_space = 0
        for key in keys[:10]:  # Evict up to 10 entries
            entry_size = await backend.get_size(key)
            await backend.delete(key)
            
            freed_space += entry_size
            tier.current_size_bytes -= entry_size
            tier.current_entries -= 1
            
            if freed_space >= required_space:
                break
    
    async def _update_access_time(self, key: str):
        """Update last access time for entry"""
        # This would update metadata in the backend
        pass
    
    async def _invalidate_dependencies(self, key: str):
        """Invalidate keys that depend on this key"""
        # Find and invalidate dependent keys
        pattern = f"*:depends:{key}"
        await self.invalidate_pattern(pattern)
    
    async def _warm_cache(self):
        """Warm cache on startup"""
        logger.info("Starting cache warming")
        
        for pattern in self.config.warm_patterns:
            try:
                # Load data for pattern
                # This is application-specific
                pass
            except Exception as e:
                logger.error(f"Cache warming error for pattern {pattern}: {e}")
        
        logger.info("Cache warming completed")
    
    def cache_decorator(
        self,
        ttl: Optional[int] = None,
        namespace: Optional[str] = None,
        key_func: Optional[callable] = None
    ):
        """Decorator for caching function results"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # Default key generation
                    key_parts = [func.__name__]
                    key_parts.extend(str(arg) for arg in args)
                    key_parts.extend(f"{k}_{v}" for k, v in sorted(kwargs.items()))
                    cache_key = ":".join(key_parts)
                
                # Try to get from cache
                result = await self.get(cache_key, namespace=namespace)
                if result is not None:
                    return result
                
                # Call function
                result = await func(*args, **kwargs)
                
                # Store in cache
                await self.set(
                    cache_key,
                    result,
                    ttl=ttl,
                    namespace=namespace
                )
                
                return result
            
            return wrapper
        return decorator

class SemanticCache:
    """Semantic similarity cache for LLM responses"""
    
    def __init__(self, model_name: str, threshold: float = 0.95):
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold
        
        # FAISS index for similarity search
        self.dimension = 384  # Dimension of all-MiniLM-L6-v2
        self.index = faiss.IndexFlatL2(self.dimension)
        
        # Store entries
        self.entries: List[SemanticCacheEntry] = []
    
    async def get(self, query: str) -> Optional[str]:
        """Get cached response for semantically similar query"""
        if not self.entries:
            return None
        
        # Generate embedding
        embedding = self.model.encode([query])[0]
        
        # Search for similar
        D, I = self.index.search(
            np.array([embedding]).astype('float32'),
            k=1
        )
        
        if len(I[0]) > 0:
            distance = D[0][0]
            similarity = 1 - (distance / 2)  # Convert L2 distance to similarity
            
            if similarity >= self.threshold:
                entry = self.entries[I[0][0]]
                entry.use_count += 1
                entry.last_used = datetime.now()
                return entry.response
        
        return None
    
    async def add(self, query: str, response: str):
        """Add query-response pair to semantic cache"""
        # Generate embedding
        embedding = self.model.encode([query])[0]
        
        # Create entry
        entry = SemanticCacheEntry(
            key=hashlib.md5(query.encode()).hexdigest(),
            query=query,
            response=response,
            embedding=embedding.tolist(),
            created_at=datetime.now(),
            last_used=datetime.now()
        )
        
        # Add to index
        self.index.add(np.array([embedding]).astype('float32'))
        self.entries.append(entry)
    
    async def remove(self, key: str):
        """Remove entry from semantic cache"""
        # Find and remove entry
        for i, entry in enumerate(self.entries):
            if entry.key == key:
                self.entries.pop(i)
                # Rebuild index without this entry
                self._rebuild_index()
                break
    
    async def clear(self):
        """Clear semantic cache"""
        self.entries = []
        self.index = faiss.IndexFlatL2(self.dimension)
    
    def _rebuild_index(self):
        """Rebuild FAISS index"""
        self.index = faiss.IndexFlatL2(self.dimension)
        
        if self.entries:
            embeddings = np.array([e.embedding for e in self.entries]).astype('float32')
            self.index.add(embeddings)
```

## Backend Implementations

Create `app/services/cache_backends/redis_backend.py`:

```python
import redis.asyncio as redis
from typing import Optional, Any, List
import pickle

class RedisBackend:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=False  # We handle serialization
        )
    
    async def get(self, key: str) -> Optional[bytes]:
        """Get value from Redis"""
        return await self.client.get(key)
    
    async def set(self, key: str, value: bytes, ttl: Optional[int] = None) -> bool:
        """Set value in Redis"""
        if ttl:
            return await self.client.setex(key, ttl, value)
        else:
            return await self.client.set(key, value)
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        return await self.client.delete(key) > 0
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern"""
        keys = await self.client.keys(pattern)
        return [k.decode('utf-8') if isinstance(k, bytes) else k for k in keys]
    
    async def clear(self):
        """Clear all keys"""
        await self.client.flushdb()
    
    async def info(self) -> Dict[str, Any]:
        """Get Redis info"""
        info = await self.client.info()
        return {
            'keys': await self.client.dbsize(),
            'used_memory': info.get('used_memory', 0)
        }
    
    async def get_size(self, key: str) -> int:
        """Get size of value"""
        value = await self.get(key)
        return len(value) if value else 0
```

## Test Implementation Requirements

Create `tests/test_cache_service.py`:

1. **Basic Operations Tests**:
   - Test get/set/delete operations
   - Test TTL expiration
   - Test namespace isolation
   - Test key generation

2. **Backend Tests**:
   - Test Redis backend
   - Test disk backend
   - Test memory backend
   - Test hybrid tier promotion

3. **Semantic Cache Tests**:
   - Test similarity matching
   - Test threshold behavior
   - Test embedding generation

4. **Performance Tests**:
   - Test compression impact
   - Test cache hit latency
   - Test concurrent access

5. **Invalidation Tests**:
   - Test pattern invalidation
   - Test cascade invalidation
   - Test dependency tracking

## Success Criteria

1. **Hit Rate**: >60% cache hit rate for repeated operations
2. **Latency**: <1ms for memory cache, <5ms for Redis
3. **Compression**: 50% size reduction for large entries
4. **Semantic Match**: 95% accuracy for similar queries
5. **Tier Promotion**: Correct promotion of hot entries
6. **Thread Safety**: No race conditions under load
7. **Cost Savings**: >70% reduction in API calls

## Edge Cases to Handle

1. **Cache stampede**: Multiple requests for expired key
2. **Memory overflow**: Graceful eviction when full
3. **Network failures**: Redis connection issues
4. **Corrupt entries**: Handle unpickleable data
5. **Circular dependencies**: Prevent infinite invalidation
6. **Large values**: Chunking for oversized entries
7. **Unicode keys**: Proper encoding handling
8. **Concurrent updates**: Prevent dirty reads
9. **TTL precision**: Sub-second expiration
10. **Cache poisoning**: Validate cached data integrity

---

**45. Should we implement cache preloading based on usage patterns?**
*Recommendation: Yes - Analyze access patterns to predict and preload frequently accessed data during off-peak hours, improving hit rates.*

This completes the Cache Service specifications. The service provides intelligent multi-tier caching with semantic similarity support, dramatically reducing costs and improving performance.