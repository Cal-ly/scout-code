# Services TODOs

## Overview
Scout has 4 core services implemented for the PoC. This document tracks service-level improvements.

**Status**: All services complete and tested (180 tests passing)

---

## Service Status

| Service | Tests | Status | Spec |
|---------|-------|--------|------|
| S1 LLM Service | 52 | Complete | `docs/services/S1_LLM_Service_*.md` |
| S2 Cost Tracker | 27 | Complete | `docs/services/S2 Cost Tracker*.md` |
| S3 Cache Service | 46 | Complete | `docs/services/S3_Cache_Service_*.md` |
| S4 Vector Store | 55 | Complete | `docs/services/S4 Vector Store*.md` |
| S6 Pipeline | 52 | Complete | `docs/services/S6_Pipeline_*.md` |
| S8 Notifications | 40 | Complete | `docs/services/S8_Notification_*.md` |

**Note**: S5 (API Routes) covered by web tests. S7 (Content Optimizer) deferred.

---

## Outstanding Items by Service

### S1 LLM Service (`src/services/llm_service/`)

- [ ] **Fallback Model Testing**: Test automatic fallback from Qwen to Gemma
  - **Context**: Fallback implemented but not tested on Pi under load
  - **Priority**: Medium

- [ ] **Token Counting Accuracy**: Current estimation may be off
  - **Location**: `token_counter.py`
  - **Impact**: Cost tracking slightly inaccurate

### S2 Cost Tracker (`src/services/cost_tracker/`)

- [ ] **Local Model Costs**: Add cost profiles for Ollama models
  - **Current**: Uses Anthropic pricing (doesn't apply to local)
  - **Priority**: Low - informational only for PoC

### S3 Cache Service (`src/services/cache_service/`)

- [x] All features complete for PoC
- [-] **Redis**: Deferred per scope document
- [-] **Semantic Caching**: Deferred per scope document

### S4 Vector Store (`src/services/vector_store/`)

- [x] All features complete for PoC
- [ ] **Collection Cleanup**: Consider cleanup routine for old job embeddings
  - **Current**: Jobs accumulate indefinitely
  - **Priority**: Low

### S6 Pipeline Orchestrator (`src/services/pipeline/`)

- [ ] **Retry Logic**: Failed steps could have configurable retry
  - **Current**: Single attempt, then fail
  - **Priority**: Low

- [-] **Checkpointing**: Deferred per scope document
- [-] **Parallel Execution**: Deferred per scope document

### S8 Notification Service (`src/services/notification/`)

- [x] All features complete for PoC
- [-] **Email/SMS/Push**: Deferred per scope document

---

## Service Architecture Notes

### Initialization Pattern (LL-003)
All services follow async initialization:
```python
service = ServiceName()
await service.initialize()
# ... use service ...
await service.shutdown()
```

### Singleton Pattern (LL-004)
Services use singleton with dependency injection:
```python
_instance: ServiceName | None = None

async def get_service() -> ServiceName:
    global _instance
    if _instance is None:
        _instance = ServiceName()
        await _instance.initialize()
    return _instance
```

### Three-File Structure (LL-002)
Each service has:
- `models.py` - Pydantic models and types
- `exceptions.py` - Custom exceptions
- `service.py` - Main service implementation

---

## Test Coverage

```
tests/
├── test_llm_service.py      # 52 tests
├── test_cost_tracker.py     # 27 tests
├── test_cache.py            # 46 tests
├── test_vector_store.py     # 55 tests
├── test_pipeline.py         # 52 tests
└── test_notification.py     # 40 tests
```

Run all service tests:
```bash
pytest tests/test_*.py -v --ignore=tests/test_integration.py
```

---

## Deferred Services

### S7 Content Optimizer
- **Status**: Explicitly deferred per scope document
- **Purpose**: Would enhance CV/cover letter quality
- **Spec**: `docs/services/S7 Content Optimizer Service*.md`

---

*Last updated: December 14, 2025*
