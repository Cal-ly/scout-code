# Scout Project - Lessons Learned & Lessons Identified

**Purpose:** Living document capturing insights from each implementation phase to improve future development.

---

## Terminology

- **Lessons Learned (LL):** Validated insights from completed work that should be applied going forward
- **Lessons Identified (LI):** Potential improvements or observations that need validation in future work

---

## Phase 1: Foundation Services

### S1 LLM Service (Complete)

#### Lessons Learned

**LL-016: Anthropic SDK Content Block Types**
- Response content can be `TextBlock`, `ThinkingBlock`, `ToolUseBlock`, etc.
- Use `hasattr()` to check for `text` attribute before accessing:
```python
content = ""
if response.content:
    first_block = response.content[0]
    if hasattr(first_block, "text"):
        content = str(first_block.text)
```
- **Apply to:** Any Anthropic SDK response handling

**LL-017: Anthropic SDK Message Format Typing**
- Anthropic SDK expects specific `MessageParam` type for messages
- Use `Any` type annotation to avoid mypy errors:
```python
messages: Any = [m.to_api_format() for m in request.messages]
```
- **Apply to:** Any Anthropic API calls with messages

**LL-018: AsyncMock for Async Client Methods in Tests**
- When mocking `AsyncAnthropic` client, use `AsyncMock` for async methods
- `MagicMock` will fail on `await` expressions:
```python
# Wrong - will fail on await client.close()
mock_client = MagicMock()

# Correct
mock_client = AsyncMock()
```
- **Apply to:** Any tests mocking async clients

**LL-019: LLM Service Integration Pattern**
- Cache check before API call
- Budget check after cache miss
- Record cost after successful API call
- Return cached response without counting as API call
```python
cached = await self._check_cache(cache_key)
if cached:
    return cached  # No budget check needed

await self._check_budget()  # Raise if exceeded
response = await self._call_with_retry(request, request_id)
await self._cost_tracker.record_cost(...)  # Record after success
await self._store_in_cache(cache_key, response, ttl)
```
- **Apply to:** Any service integrating cache and cost tracking

---

### S4 Vector Store Service (Complete)

#### Lessons Learned

**LL-011: ChromaDB `upsert` vs `add` for Duplicates**
- `collection.add()` silently ignores duplicate IDs
- Use `collection.upsert()` for "add or update" behavior
- **Apply to:** Any ChromaDB insert operations

**LL-012: ChromaDB Merges Metadata on Update**
- Both `update()` and `upsert()` merge metadata, not replace
- Old keys persist even when not provided in new metadata
- Document this behavior in tests rather than fighting it
- **Apply to:** Any ChromaDB metadata operations

**LL-013: TYPE_CHECKING for Complex Type Hints**
```python
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from chromadb.api import ClientAPI

# In class:
self._client: "ClientAPI | None" = None
self._collections: dict[str, Any] = {}  # chromadb.Collection
```
- Avoids runtime import issues with complex library types
- Use string quotes for forward references in annotations
- **Apply to:** Services with complex third-party type dependencies

**LL-014: Casting External Library Returns**
- ChromaDB and similar libraries often return `Any` types
- Use explicit casts or type annotations to satisfy mypy:
```python
count: int = collection.count()  # Annotate variable type
return cast(list[float], embedding.tolist())  # Cast return
metadata=dict(result_metadata)  # Convert Mapping to dict
```
- **Apply to:** Any external library integration

**LL-015: Embedding Model Loading Time**
- First run downloads ~90MB model (all-MiniLM-L6-v2)
- Tests take ~90 seconds due to model loading per test file
- Consider caching model in pytest fixtures
- **Apply to:** Any tests using sentence-transformers

---

### S2 Cost Tracker Service (Complete)

#### Lessons Learned

**LL-001: PoC Simplification Pays Off**
- JSON file persistence instead of Redis reduced complexity significantly
- 27 tests achieved with minimal infrastructure
- **Apply to:** S3 Cache, S4 Vector Store - prefer simple file-based solutions

**LL-002: Three-File Service Structure Works Well**
```
service_name/
  __init__.py      # Package exports
  models.py        # Pydantic data models
  exceptions.py    # Service-specific exceptions
  service.py       # Main implementation
```
- Clear separation of concerns
- Easy to test each component
- **Apply to:** All future services

**LL-003: Async Initialization Pattern**
```python
def __init__(self):
    self._initialized = False
    # Set attributes only

async def initialize(self):
    if self._initialized:
        return
    # Actual setup
    self._initialized = True
```
- Constructors can't be async in Python
- Explicit `initialize()` makes lifecycle clear
- **Apply to:** All services requiring async setup

**LL-004: Singleton with Dependency Injection**
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
- Works well with FastAPI's `Depends()`
- `reset_service()` essential for test isolation
- **Apply to:** All services

---

### S3 Cache Service (Complete)

#### Lessons Learned

**LL-005: Windows Development Environment Considerations**
- PowerShell commands required for venv activation on Windows
- Use `powershell.exe -Command "Set-Location '...'; ..."` pattern
- Pytest requires full path or proper working directory
- **Apply to:** All future commands on Windows

**LL-006: Type Hint Variable Shadowing**
- Mypy catches variable type changes within same scope
- Using different variable names prevents type conflicts:
```python
# Bad - mypy error
entry = self._memory_cache[key]  # CacheEntry
entry = await self._file_get(key)  # CacheEntry | None

# Good - no error
entry = self._memory_cache[key]  # CacheEntry
file_entry = await self._file_get(key)  # CacheEntry | None
```
- **Apply to:** All code with optional returns

**LL-007: Ruff Lint - Unnecessary Mode Arguments**
- `open(file, "r")` - the `"r"` is default and unnecessary
- Use `open(file)` for reading
- Only specify mode for writing: `open(file, "w")`
- **Apply to:** All file operations

**LL-008: LRU Cache with OrderedDict**
```python
from collections import OrderedDict

# Store with eviction
while len(cache) >= max_entries:
    oldest = next(iter(cache))
    del cache[oldest]
cache[key] = entry
cache.move_to_end(key)

# Access updates recency
cache.move_to_end(key)
```
- Built-in Python, no external dependencies
- `move_to_end()` is O(1)
- **Apply to:** Any LRU caching needs

**LL-009: Two-Tier Cache Promotion**
- File cache hits should be promoted to memory cache
- Reduces file I/O on repeated access
- Memory acts as hot cache for frequently accessed items
- **Apply to:** Any multi-tier caching

**LL-010: Test Coverage Strategy**
- 46 tests covering: models, initialization, core operations, edge cases, dependency injection
- Use `tmp_path` fixture for isolated file operations
- Test expiration with short TTLs (1-2 seconds) and `time.sleep()`
- **Apply to:** All service test suites

#### Lessons Identified

**LI-001: Venv Dependency Installation**
- Fresh venv may not have all dev dependencies
- Run `pip install -r requirements.txt -r requirements-dev.txt` early
- **Validate in:** S4 Vector Store implementation

**LI-002: Test Organization**
- Current: `tests/test_<service>.py` (flat)
- Spec suggests: `tests/unit/services/test_<service>.py`
- Flat structure works for PoC, may need reorganization for larger projects
- **Validate in:** When test count exceeds ~100

---

## Code Quality Standards

### Verification Checklist (Run After Each Component)

```bash
# Syntax check
python -m py_compile src/services/<service>/

# Type checking
mypy src/services/<service>/ --ignore-missing-imports

# Linting
ruff check src/services/<service>/

# Tests
pytest tests/test_<service>.py -v
```

### Common Mypy Issues & Fixes

| Issue | Fix |
|-------|-----|
| Variable type changes | Use different variable names |
| `Optional[T]` vs `T \| None` | Use `T \| None` (Python 3.10+) |
| Missing return type | Add `-> ReturnType` to all functions |
| `Any` type warnings | Be explicit with types where possible |

### Common Ruff Issues & Fixes

| Code | Issue | Fix |
|------|-------|-----|
| UP015 | Unnecessary mode argument | Remove `"r"` from `open()` |
| E501 | Line too long | Break into multiple lines |
| F401 | Unused import | Remove or use `__all__` |

---

## Implementation Patterns

### Path Translation (Spec to Actual)

```
Specification Says    ->    Actually Use
app/services/         ->    src/services/
app/models/           ->    src/services/<service>/models.py
app/config/           ->    src/config/ (create if needed)
tests/unit/services/  ->    tests/
```

### Error Handling Pattern

```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise ServiceError(f"Descriptive message: {e}") from e
```

### Pydantic Model Pattern

```python
from pydantic import BaseModel, Field
from datetime import datetime

class DataModel(BaseModel):
    required_field: str
    optional_field: str | None = None
    with_default: int = 0
    auto_timestamp: datetime = Field(default_factory=datetime.now)

    model_config = {"arbitrary_types_allowed": True}  # If needed

    @property
    def computed_value(self) -> float:
        return self.some_field * 100
```

---

## Session Continuity Notes

### What Works Well
1. **HANDOVER.md** - Comprehensive context for session resumption
2. **Todo tracking** - Keeps implementation focused
3. **Incremental verification** - Catches issues early
4. **Following established patterns** - S2 patterns applied successfully to S3

### What to Improve
1. Check venv dependencies early in session
2. Use PowerShell for Windows paths consistently
3. Run full test suite after each file change

---

## Phase 2: Core Modules

### M1 Collector Module (Complete)

#### Lessons Learned

**LL-020: Install Type Stubs for PyYAML**
- mypy requires `types-PyYAML` for yaml type hints
- `--ignore-missing-imports` doesn't ignore missing stubs
- Install with: `pip install types-PyYAML`
- **Apply to:** Any module using yaml library

**LL-021: Patch Source Module for Dependency Injection Tests**
- When function imports dependencies inside the function body:
```python
async def get_collector():
    from src.services.vector_store import get_vector_store_service
    # ...
```
- Patch the source module, not the target:
```python
# Wrong - function hasn't imported yet
patch("src.modules.collector.collector.get_vector_store_service")

# Correct - patch the source module
patch("src.services.vector_store.get_vector_store_service")
```
- **Apply to:** Any dependency injection tests with dynamic imports

**LL-022: Module Adapts to Service Collection Constraints**
- PoC scope limits VectorStoreService to 2 collections
- Collector stores all profile data in single `user_profiles` collection
- Use metadata-based filtering for type-specific searches:
```python
await vector_store.search(
    collection_name="user_profiles",
    query=query,
    metadata_filter={"type": "skill"}  # Filter by document type
)
```
- **Apply to:** Any module using VectorStoreService

**LL-023: Three-File Module Structure (Consistent with Services)**
```
module_name/
  __init__.py      # Package exports
  models.py        # Pydantic data models
  exceptions.py    # Module-specific exceptions
  <module>.py      # Main implementation
```
- Same pattern as services works for modules
- **Apply to:** All future modules (M2-M5)

**LL-024: Pydantic model_validator for Computed Fields**
- Use `model_validator(mode="after")` for computed fields:
```python
@model_validator(mode="after")
def set_current_from_end_date(self) -> "Experience":
    if self.end_date is None:
        object.__setattr__(self, "current", True)
    return self
```
- Pydantic v2 syntax differs from v1 `@validator`
- **Apply to:** Any model with auto-computed fields

---

## Quick Reference

### Implementation Order

#### Phase 1: Services (Complete)
1. S2 Cost Tracker - Complete
2. S3 Cache Service - Complete
3. S4 Vector Store - Complete
4. S1 LLM Service - Complete

#### Phase 2: Modules (In Progress)
5. M1 Collector - Complete
6. M2 Rinser - Not Started
7. M3 Analyzer - Not Started
8. M4 Creator - Not Started
9. M5 Formatter - Not Started

### Test Targets
| Component | Tests | Coverage |
|-----------|-------|----------|
| S2 Cost Tracker | 27 | >90% |
| S3 Cache Service | 46 | >90% |
| S4 Vector Store | 55 | >90% |
| S1 LLM Service | 50 | >90% |
| M1 Collector | 49 | >90% |
| **Total** | **227** | **>90%** |

---

*Last Updated: December 10, 2025*
*Phase 2 Core Modules In Progress - M1 Collector Complete with 227 total tests*
