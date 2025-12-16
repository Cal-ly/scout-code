# Scout Services

Foundation services providing shared functionality to modules.

## Service Overview

| Service | Purpose | Singleton | Async Init |
|---------|---------|-----------|------------|
| **S1 LLM Service** | Local LLM inference (Ollama) | Yes | Yes |
| **S2 Metrics Tracker** | Usage tracking & performance | Yes | Yes |
| **S3 Cache Service** | Two-tier caching (L1+L2) | Yes | Yes |
| **S4 Vector Store** | Semantic search (ChromaDB) | Yes | Yes |
| **S6 Pipeline** | Module orchestration | Yes | Yes |
| **S8 Notification** | In-app notifications | Yes | No |
| **Profile Service** | Profile management helper | Yes | Yes |

## Service Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                    Pipeline Orchestrator (S6)               │
│                                                             │
│    Coordinates: Rinser → Analyzer → Creator → Formatter     │
└──────────────────────────────┬──────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│  LLM Service  │      │ Vector Store  │      │    Cache      │
│     (S1)      │      │     (S4)      │      │     (S3)      │
│               │      │               │      │               │
│ Ollama        │      │ ChromaDB      │      │ Memory + File │
│ qwen2.5:3b    │      │ Embeddings    │      │ LRU eviction  │
│ gemma2:2b     │      │               │      │               │
└───────┬───────┘      └───────────────┘      └───────────────┘
        │
        ▼
┌───────────────┐      ┌───────────────┐
│Metrics Tracker│      │ Notification  │
│     (S2)      │      │     (S8)      │
│               │      │               │
│ Token counting│      │ Toast alerts  │
│ Performance   │      │               │
└───────────────┘      └───────────────┘
```

## Service Structure

Each service follows the same pattern:

```
service_name/
├── __init__.py       # Exports (get_service, Service, models)
├── models.py         # Pydantic data models
├── exceptions.py     # Service-specific exceptions
└── service.py        # Main implementation
```

## Singleton Pattern

All services use async singleton pattern:

```python
_instance: ServiceClass | None = None

async def get_service() -> ServiceClass:
    global _instance
    if _instance is None:
        _instance = ServiceClass()
        await _instance.initialize()
    return _instance

def reset_service() -> None:  # For testing
    global _instance
    _instance = None
```

## Usage Examples

### LLM Service (S1)
```python
from src.services.llm_service import get_llm_service, LLMRequest

llm = await get_llm_service()
response = await llm.generate(LLMRequest(
    prompt="Extract job requirements...",
    system_prompt="You are a job posting analyzer.",
    max_tokens=2000,
    purpose="json_extraction"
))
print(response.content)
```

### Cache Service (S3)
```python
from src.services.cache_service import get_cache_service

cache = await get_cache_service()

# Store with TTL
await cache.set("key", "value", ttl_seconds=3600)

# Retrieve
value = await cache.get("key")
```

### Vector Store (S4)
```python
from src.services.vector_store import get_vector_store_service

vector_store = await get_vector_store_service()

# Add document
await vector_store.add_documents(
    collection_name="user_profiles",
    documents=["Python expert with 5 years experience"],
    metadatas=[{"type": "skill", "name": "Python"}],
    ids=["skill_1"]
)

# Search
results = await vector_store.search(
    collection_name="user_profiles",
    query="programming languages",
    n_results=5
)
```

### Pipeline (S6)
```python
from src.services.pipeline import get_pipeline_orchestrator, PipelineInput

orchestrator = await get_pipeline_orchestrator()
result = await orchestrator.execute(PipelineInput(
    raw_job_text="Software Engineer at Example Corp...",
    source="web"
))

if result.status == PipelineStatus.COMPLETED:
    print(f"CV: {result.cv_path}")
    print(f"Cover Letter: {result.cover_letter_path}")
```

## Configuration

Services are configured via environment variables:

```bash
# LLM Service
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=qwen2.5:3b
LLM_FALLBACK_MODEL=gemma2:2b

# Cache Service
CACHE_DIR=./data/cache
CACHE_MEMORY_MAX_ENTRIES=100
CACHE_FILE_MAX_SIZE_MB=100

# Vector Store
CHROMA_PERSIST_DIR=./data/chroma
```

---

*For full service documentation, see `docs/current_state/services.md`.*
