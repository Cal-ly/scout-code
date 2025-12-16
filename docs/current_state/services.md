# Services - Current State

This document describes the current implementation of Scout's foundation services.

## Overview

| Service | ID | Location | Test Count | Dependencies |
|---------|------|----------|------------|--------------|
| LLM Service | S1 | `src/services/llm_service/` | 52 | S2, S3 |
| Metrics Service | S2 | `src/services/metrics_service/` | ~41 | None |
| Cache Service | S3 | `src/services/cache_service/` | 46 | None |
| Vector Store | S4 | `src/services/vector_store/` | 55 | None |
| Pipeline Orchestrator | S6 | `src/services/pipeline/` | 52 | M1-M5, Database |
| Notification Service | S8 | `src/services/notification/` | 40 | None |
| **Database Service** | - | `src/services/database/` | ~50 | None |
| Profile Service (legacy) | - | `src/services/profile/` | 45 | S4 |

---

## S1: LLM Service

**Location:** `src/services/llm_service/`

### Purpose
Wrapper around Ollama for local LLM inference with caching and retry logic.

### Key Files
```
llm_service/
├── __init__.py          # Public exports
├── service.py           # Main LLMService class
├── models.py            # LLMConfig, LLMRequest, LLMResponse, etc.
├── exceptions.py        # LLMError, LLMTimeoutError, etc.
└── providers.py         # OllamaProvider (provider abstraction)
```

### Main Class: `LLMService`

```python
class LLMService:
    """Wrapper around Ollama with caching and retry logic."""

    def __init__(
        self,
        cost_tracker: CostTrackerService,
        cache: CacheService,
        config: LLMConfig | None = None,
    ): ...

    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...

    # Main methods
    async def generate(
        self,
        messages: list[PromptMessage],
        module: str,
        **kwargs
    ) -> LLMResponse: ...

    async def generate_json(
        self,
        prompt: str,
        module: str,
        **kwargs
    ) -> dict[str, Any]: ...

    async def health_check(self) -> LLMHealth: ...
```

### Configuration
```python
@dataclass
class LLMConfig:
    model: str = "qwen2.5:3b"        # Primary model
    fallback_model: str = "gemma2:2b"  # Fallback model
    timeout: float = 300.0            # 5 min timeout
    max_retries: int = 3
    temperature: float = 0.3
    max_tokens: int = 2048
    base_url: str = "http://localhost:11434"
```

### Key Features
- **Provider Abstraction**: `OllamaProvider` implements `LLMProvider` protocol
- **Automatic Retry**: Exponential backoff (1s, 2s, 4s)
- **Response Caching**: Via Cache Service (prompt hash as key)
- **JSON Mode**: Uses Ollama's JSON output format
- **Usage Tracking**: Records token counts to Cost Tracker

### Models
```python
class PromptMessage:
    role: MessageRole  # system, user, assistant
    content: str

class LLMResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    generation_time_ms: float
    cached: bool
```

---

## S2: Metrics Service

**Location:** `src/services/metrics_service/`

### Purpose
Tracks LLM inference performance metrics including tokens per second, success rates, and system resource usage. Refactored from Cost Tracker for local LLM deployment.

### Key Files
```
metrics_service/
├── __init__.py          # Public exports
├── service.py           # Main MetricsService class
├── models.py            # InferenceMetric, MetricsSummary, SystemMetrics
└── exceptions.py        # MetricsError
```

### Main Class: `MetricsService`

```python
class MetricsService:
    """Tracks inference performance and system metrics."""

    def __init__(
        self,
        data_dir: Path | None = None,  # data/metrics/
        retention_days: int = 30,
    ): ...

    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...

    # Recording
    async def record_inference(
        self,
        module: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: float,
        success: bool = True,
        error: str | None = None,
        used_fallback: bool = False,
    ) -> InferenceMetric: ...

    # Reporting
    async def get_summary(self, days: int = 7) -> MetricsSummary: ...
    async def get_daily_metrics(self, days: int = 7) -> list[DailyMetrics]: ...
    async def get_system_metrics(self) -> SystemMetrics: ...
```

### Key Features
- **Performance Tracking**: Tokens per second, duration, success rate
- **System Metrics**: CPU, memory, temperature (for Raspberry Pi 5)
- **File Persistence**: JSON storage with 30-day retention
- **Monthly Archival**: Old metrics archived for historical analysis

### Note on Local LLM
With Ollama, costs are $0.00 but token throughput metrics are essential for performance optimization on edge devices.

---

## S3: Cache Service

**Location:** `src/services/cache_service/`

### Purpose
Two-tier caching to reduce LLM calls. Memory (L1) for speed, File (L2) for persistence.

### Key Files
```
cache_service/
├── __init__.py          # Public exports
├── service.py           # Main CacheService class
├── models.py            # CacheEntry, CacheStats, CacheHealth
└── exceptions.py        # CacheError
```

### Main Class: `CacheService`

```python
class CacheService:
    """Two-tier cache: Memory (L1) + File (L2)."""

    def __init__(
        self,
        cache_dir: Path | None = None,        # data/cache
        memory_max_entries: int = 100,        # LRU size
        default_ttl: int = 3600,              # 1 hour
    ): ...

    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...

    # Core methods
    async def get(self, key: str) -> Any | None: ...
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> bool: ...
    async def clear(self) -> None: ...

    # Key generation for LLM caching
    def generate_key(
        self,
        prompt: str,
        model: str = "",
        temperature: float = 0.0,
        **kwargs
    ) -> str: ...  # Returns MD5 hash

    # Stats
    async def get_stats(self) -> CacheStats: ...
    async def health_check(self) -> CacheHealth: ...
```

### Cache Tiers

| Tier | Storage | Speed | Size | Persistence |
|------|---------|-------|------|-------------|
| L1 (Memory) | OrderedDict (LRU) | ~1ms | 100 entries | No |
| L2 (File) | JSON files | ~10ms | Unlimited | Yes |

### Cache Flow
1. Check L1 (memory) first
2. If miss, check L2 (file)
3. If L2 hit, promote to L1
4. On set: write to both L1 and L2

### Key Generation
```python
key = cache.generate_key(
    prompt="Extract job title from...",
    model="qwen2.5:3b",
    temperature=0.3
)
# Returns: "a1b2c3d4e5f6..." (MD5 hash)
```

---

## S4: Vector Store Service

**Location:** `src/services/vector_store/`

### Purpose
ChromaDB-based vector storage for semantic search of profiles and job requirements.

### Key Files
```
vector_store/
├── __init__.py          # Public exports
├── service.py           # Main VectorStoreService class
├── models.py            # VectorEntry, SearchResult, SearchResponse
└── exceptions.py        # VectorStoreError, CollectionNotFoundError
```

### Main Class: `VectorStoreService`

```python
class VectorStoreService:
    """ChromaDB wrapper with sentence-transformers embeddings."""

    def __init__(
        self,
        persist_directory: Path | None = None,  # data/vectors
        embedding_model: str = "all-MiniLM-L6-v2",
    ): ...

    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...

    # Collection management
    async def create_collection(self, name: str) -> None: ...
    async def delete_collection(self, name: str) -> None: ...
    async def list_collections(self) -> list[str]: ...

    # Document operations
    async def add(
        self,
        collection: str,
        doc_id: str,
        text: str,
        metadata: dict | None = None,
    ) -> VectorEntry: ...

    async def get(self, collection: str, doc_id: str) -> VectorEntry | None: ...
    async def delete(self, collection: str, doc_id: str) -> bool: ...

    # Search
    async def search(
        self,
        collection: str,
        query: str,
        top_k: int = 10,
        filter_metadata: dict | None = None,
    ) -> SearchResponse: ...

    # Batch operations
    async def add_batch(
        self,
        collection: str,
        entries: list[tuple[str, str, dict | None]],
    ) -> list[VectorEntry]: ...
```

### Collections (PoC Scope)
Only 2 collections for PoC:
```python
POC_COLLECTIONS = ["user_profiles", "job_requirements"]
```

### Embedding Model
- **Model**: `all-MiniLM-L6-v2` (sentence-transformers)
- **Dimensions**: 384
- **Similarity**: Cosine (ChromaDB default)

### Search Response
```python
class SearchResult:
    doc_id: str
    text: str
    score: float  # 0.0 to 1.0 (cosine similarity)
    metadata: dict | None

class SearchResponse:
    results: list[SearchResult]
    query: str
    collection: str
    total_results: int
    search_time_ms: float
```

---

## S6: Pipeline Orchestrator

**Location:** `src/services/pipeline/`

### Purpose
Coordinates sequential execution of all modules for job application processing.

### Key Files
```
pipeline/
├── __init__.py          # Public exports
├── pipeline.py          # Main PipelineOrchestrator class
├── models.py            # PipelineInput, PipelineResult, PipelineStep
└── exceptions.py        # PipelineError, StepError
```

### Main Class: `PipelineOrchestrator`

```python
class PipelineOrchestrator:
    """Coordinates module execution: Rinser → Analyzer → Creator → Formatter"""

    STEPS = [
        PipelineStep.RINSER,
        PipelineStep.ANALYZER,
        PipelineStep.CREATOR,
        PipelineStep.FORMATTER,
    ]

    def __init__(
        self,
        collector: Collector,
        rinser: Rinser,
        analyzer: Analyzer,
        creator: Creator,
        formatter: Formatter,
    ): ...

    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...

    async def execute(
        self,
        input_data: PipelineInput,
        progress_callback: ProgressCallback | None = None,
    ) -> PipelineResult: ...
```

### Pipeline Flow
```
PipelineInput (raw job text)
       │
       ▼
   ┌───────┐
   │Rinser │ → ProcessedJob (structured job data)
   └───┬───┘
       │
       ▼
   ┌────────┐
   │Analyzer│ → AnalysisResult (scores, strategy)
   └───┬────┘
       │
       ▼
   ┌───────┐
   │Creator│ → CreatedContent (CV, cover letter text)
   └───┬───┘
       │
       ▼
   ┌─────────┐
   │Formatter│ → FormattedApplication (PDF files)
   └────┬────┘
       │
       ▼
PipelineResult (paths to PDFs, score, metadata)
```

### Pipeline Result
```python
class PipelineResult:
    pipeline_id: str
    job_id: str | None
    status: PipelineStatus  # pending, running, completed, failed
    current_step: PipelineStep | None
    steps: list[StepResult]

    # Output
    job_title: str | None
    company_name: str | None
    compatibility_score: float | None
    cv_path: str | None
    cover_letter_path: str | None

    # Timing
    started_at: datetime | None
    completed_at: datetime | None
    total_duration_ms: int | None

    # Error info
    error: str | None

    @property
    def is_success(self) -> bool: ...
    @property
    def is_complete(self) -> bool: ...
```

---

## S8: Notification Service

**Location:** `src/services/notification/`

### Purpose
In-app toast notifications for pipeline status updates. PoC scope: no email/SMS/webhooks.

### Key Files
```
notification/
├── __init__.py          # Public exports
├── notification.py      # Main NotificationService class
├── models.py            # Notification, NotificationType
└── exceptions.py        # NotificationError
```

### Main Class: `NotificationService`

```python
class NotificationService:
    """In-memory notification service for toast messages."""

    def __init__(self, max_notifications: int = 100): ...

    # Creating notifications
    async def notify(
        self,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        auto_dismiss: bool = True,
        dismiss_after_seconds: int = 5,
    ) -> Notification: ...

    # Pipeline-specific helpers
    async def notify_job_started(self, job_id: str) -> Notification: ...
    async def notify_job_completed(self, job_id: str, score: float) -> Notification: ...
    async def notify_job_failed(self, job_id: str, error: str) -> Notification: ...

    # Retrieval
    async def get_notifications(
        self,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Notification]: ...

    async def mark_as_read(self, notification_id: str) -> bool: ...
    async def clear_all(self) -> None: ...
```

### Notification Types
```python
class NotificationType(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
```

### Notification Model
```python
class Notification:
    id: str
    title: str
    message: str
    type: NotificationType
    is_read: bool
    auto_dismiss: bool
    dismiss_after_seconds: int
    created_at: datetime
```

---

## Database Service (NEW - December 2025)

**Location:** `src/services/database/`

### Purpose
SQLite persistence for profiles and applications, enabling multi-profile support with persistent storage across server restarts.

### Key Files
```
database/
├── __init__.py          # Public exports
├── service.py           # Main DatabaseService class
├── models.py            # Profile, Application, ApplicationStatus
├── exceptions.py        # ProfileNotFoundError, ApplicationNotFoundError
└── demo_profiles.py     # Demo profile data (Emma, Marcus, Sofia)
```

### Main Class: `DatabaseService`

```python
class DatabaseService:
    """SQLite persistence for profiles and applications."""

    def __init__(
        self,
        db_path: Path | None = None,  # data/scout.db
    ): ...

    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...

    # Profile operations
    async def list_profiles(self) -> list[Profile]: ...
    async def get_profile_by_slug(self, slug: str) -> Profile: ...
    async def get_active_profile(self) -> Profile | None: ...
    async def set_active_profile(self, slug: str) -> Profile: ...
    async def create_profile(self, data: ProfileCreate) -> Profile: ...
    async def update_profile(self, slug: str, data: ProfileUpdate) -> Profile: ...
    async def delete_profile(self, slug: str) -> None: ...

    # Application operations
    async def list_applications(
        self,
        profile_id: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Application], int]: ...
    async def get_application_by_job_id(self, job_id: str) -> Application | None: ...
    async def create_application(self, data: ApplicationCreate) -> Application: ...
    async def update_application(self, job_id: str, data: ApplicationUpdate) -> Application: ...
```

### Key Features
- **SQLite Storage**: Single file database (`data/scout.db`)
- **Multi-Profile Support**: 3 demo profiles auto-created on startup
- **Profile-Scoped Applications**: Applications linked to profiles via foreign key
- **Active Profile Pattern**: Only one profile active at a time
- **ChromaDB Re-indexing**: Profile switch triggers vector store update
- **Slug-Based URLs**: Human-readable profile URLs

### Demo Profiles
Auto-created on first startup:
1. **Emma Chen** (`emma-chen`) - AI/ML engineer
2. **Marcus Andersen** (`marcus-andersen`) - Backend/DevOps engineer
3. **Sofia Martinez** (`sofia-martinez`) - Full-stack developer

### Usage
```python
from src.services.database import get_database_service

db = await get_database_service()

# Get active profile
profile = await db.get_active_profile()

# Switch profile (triggers re-indexing)
await db.set_active_profile("marcus-andersen")

# List applications for active profile
apps, total = await db.list_applications(profile_id=profile.id)
```

---

## Profile Service (LEGACY)

**Location:** `src/services/profile/`

### Purpose
Higher-level service for single-profile management, combining Collector + Vector Store operations.

> **Note:** For multi-profile support, use the Database Service instead.

### Main Class: `ProfileService`

```python
class ProfileService:
    """Profile management combining file storage and vector indexing."""

    async def get_status(self) -> ProfileStatus: ...
    async def create_profile(self, request: ProfileCreateRequest) -> ProfileCreateResponse: ...
    async def index_profile(self, request: ProfileIndexRequest) -> ProfileIndexResponse: ...
    async def retrieve_profile(self) -> ProfileData: ...
```

### Used By
- `/api/v1/profile/*` routes (legacy)
- Legacy profile editor

---

## Singleton Access Pattern

All services use a singleton pattern for FastAPI dependency injection:

```python
# Example from Database Service
_instance: DatabaseService | None = None

async def get_database_service() -> DatabaseService:
    """Get singleton Database Service instance."""
    global _instance
    if _instance is None:
        _instance = DatabaseService()
        await _instance.initialize()
    return _instance
```

Usage in FastAPI:
```python
@router.post("/api/v1/profiles")
async def create_profile(
    data: ProfileCreate,
    db: DatabaseService = Depends(get_database_service),
):
    return await db.create_profile(data)
```

---

*Last updated: December 16, 2025*
*Updated: Added Database Service, renamed Cost Tracker to Metrics Service*
