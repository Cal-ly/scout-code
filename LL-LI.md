# Scout Project - Lessons Learned & Lessons Identified

**Purpose:** Living document capturing insights from each implementation phase to improve future development.

---

## Terminology

- **Lessons Learned (LL):** Validated insights from completed work that should be applied going forward
- **Lessons Identified (LI):** Potential improvements or observations that need validation in future work

---

## Phase 1: Foundation Services

### S1 LLM Service (Complete - Refactored for Ollama)

#### Lessons Learned

> **Note:** LL-016, LL-017, and LL-018 from the original Anthropic implementation
> are no longer applicable. The service now uses Ollama with a provider abstraction.
> See LL-055 to LL-058 for the new Ollama-specific lessons.

**LL-019: LLM Service Integration Pattern** (Still Applicable)
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

**LL-055: Provider Abstraction Pattern for LLM Services**
- Use abstract base class (`LLMProvider`) for provider implementations
- Keep service interface unchanged when switching providers
- Provider handles all API-specific logic (authentication, response parsing)
```python
class LLMProvider(ABC):
    @abstractmethod
    async def initialize(self) -> None: pass
    @abstractmethod
    async def generate(self, request: LLMRequest, request_id: str) -> LLMResponse: pass
    @abstractmethod
    async def health_check(self) -> dict[str, Any]: pass
```
- **Apply to:** Any service that may need multiple provider implementations

**LL-056: Ollama AsyncClient Usage**
- Use `ollama.AsyncClient` for async operations
- Client doesn't require explicit close - set to None on shutdown
- Check model availability during initialization with `client.list()`
```python
self._client = ollama.AsyncClient(host=self._host)
models_response = await self._client.list()
model_names = [m.get("name", "") for m in models_response.get("models", [])]
```
- **Apply to:** Any Ollama integration

**LL-057: Ollama JSON Mode**
- Use `format="json"` parameter for structured JSON output
- Lower temperature (0.1) recommended for structured output
- Still need to add JSON instruction to system prompt for best results
```python
response = await self._client.chat(
    model=self._model,
    messages=messages,
    format="json" if request.purpose == "json_extraction" else None,
    options={"temperature": 0.1, "num_predict": request.max_tokens},
)
```
- **Apply to:** Any Ollama call expecting JSON output

**LL-058: Local Inference Cost Tracking**
- Local inference has no API cost but still track for metrics
- Use `total_tokens` instead of `total_cost` in health status
- Keep cost tracking infrastructure for potential future API fallback
```python
# In LLMConfig for local:
input_cost_per_1k: float = 0.0
output_cost_per_1k: float = 0.0

# In LLMHealth:
total_tokens: int = 0  # Track tokens instead of cost
```
- **Apply to:** Any local LLM integration

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

### M2 Rinser Module (Complete)

#### Lessons Learned

**LL-025: Install Type Stubs for bleach**
- mypy requires `types-bleach` for bleach type hints
- Install with: `pip install types-bleach`
- **Apply to:** Any module using bleach library for HTML sanitization

**LL-026: Order of Sanitization Matters**
- Run regex to remove script/style content BEFORE bleach.clean()
- bleach.clean() strips tags but leaves content inside them
- If you run bleach first, regex can't find `<script>...</script>` pattern
```python
# Correct order:
text = re.sub(r"<script[^>]*>.*?</script>", "", raw_text, flags=re.DOTALL | re.IGNORECASE)
text = bleach.clean(text, tags=[], strip=True)

# Wrong order - script content remains:
text = bleach.clean(raw_text, tags=[], strip=True)  # Tags stripped, content remains
text = re.sub(r"<script[^>]*>.*?</script>", "", text)  # Won't match - no tags left!
```
- **Apply to:** Any HTML sanitization with multiple steps

**LL-027: Rinser Uses job_requirements Collection**
- PoC scope limits VectorStoreService to 2 collections
- M1 Collector uses `user_profiles` collection
- M2 Rinser uses `job_requirements` collection
- Use metadata-based filtering for type-specific searches:
```python
await vector_store.add(
    collection_name="job_requirements",
    document_id=f"job_{job.id}_req_{i}",
    content=req.to_searchable_text(),
    metadata={"type": "requirement", "priority": "must_have"}
)
```
- **Apply to:** M3 Analyzer will search both collections

**LL-028: Four-File Module Structure for Modules with Prompts**
```
module_name/
  __init__.py      # Package exports
  models.py        # Pydantic data models
  exceptions.py    # Module-specific exceptions
  prompts.py       # LLM prompt templates (if using LLM)
  <module>.py      # Main implementation
```
- Add prompts.py for modules that use LLM (M2, M3, M4)
- **Apply to:** M3 Analyzer, M4 Creator

---

### M3 Analyzer Module (Complete)

#### Lessons Learned

**LL-029: Avoid @computed_field Decorator with mypy**
- mypy doesn't fully support Pydantic v2's `@computed_field` decorator
- Error: "Decorators on top of @property are not supported"
- Use plain `@property` instead - it won't serialize but works for convenience methods:
```python
# Causes mypy error
@computed_field
@property
def is_good_match(self) -> bool:
    return self.compatibility.overall >= 70

# Works without mypy error
@property
def is_good_match(self) -> bool:
    return self.compatibility.overall >= 70
```
- **Apply to:** Any Pydantic model with computed properties

**LL-030: Safe Metadata Type Coercion**
- Collector's SearchMatch.metadata values are `str | float | int | bool | None`
- `float()` doesn't accept `bool` or `None` directly with strict type checking
- Use `or 0` pattern for safe conversion:
```python
# May cause mypy error with strict typing
years = float(metadata.get("years", 0))

# Safe pattern - falsy values become 0
years = float(metadata.get("years") or 0)
```
- **Apply to:** Any code reading numeric values from mixed-type metadata

**LL-031: Analyzer Uses Both Collections**
- M3 Analyzer is the integration point for PoC's 2 collections
- Uses Collector's `search_skills()` which queries `user_profiles` collection
- Uses Collector's `search_experiences()` which also queries `user_profiles` collection
- Job data comes from ProcessedJob (from M2 Rinser, indexed in `job_requirements`)
- **Apply to:** Understanding data flow in Scout pipeline

---

### M4 Creator Module (Complete)

#### Lessons Learned

**LL-032: Cast dict.get() Results for Typed Returns**
- When returning `str` from a function, `dict.get("key", "")` returns `Any`
- mypy will flag "Returning Any from function declared to return str"
- Cast explicitly with `str()`:
```python
# Causes mypy error
def get_summary(result: dict) -> str:
    return result.get("summary", "").strip()

# Correct - cast to str
def get_summary(result: dict) -> str:
    summary_value = result.get("summary", "")
    return str(summary_value).strip()
```
- **Apply to:** Any function returning typed values from dict.get()

**LL-033: Soft Skill Categorization Without Model Field**
- PoC scope simplified Skill model without `category` field
- Use keyword-based categorization instead:
```python
SOFT_SKILL_KEYWORDS = {
    "leadership", "communication", "teamwork", "problem-solving",
    "collaboration", "mentoring", "management", "presentation",
}

def _is_soft_skill(self, skill_name: str) -> bool:
    return skill_name.lower() in SOFT_SKILL_KEYWORDS
```
- **Apply to:** Any categorization without explicit model fields

**LL-034: Helper Methods for Profile Navigation**
- UserProfile may not have convenience methods from spec
- Implement helpers in module rather than modifying models:
```python
def _get_current_experience(self, profile: UserProfile) -> Experience | None:
    # Find current=True, or most recent by start_date
    for exp in profile.experiences:
        if exp.current:
            return exp
    if profile.experiences:
        return max(profile.experiences, key=lambda e: e.start_date)
    return None
```
- **Apply to:** Any module needing profile navigation helpers

**LL-035: Experience Model Uses 'role' Not 'title'**
- Collector's Experience model uses `role` field, not `title`
- Spec examples may reference `title` - always check actual model
- **Apply to:** Any code accessing Experience attributes

---

### M5 Formatter Module (Complete)

#### Lessons Learned

**LL-036: WeasyPrint Requires GTK on Windows**
- WeasyPrint requires GTK3/Pango native libraries
- On Windows, these are not bundled and require MSYS2 or GTK bundle
- Use `xhtml2pdf` instead - pure Python, no native dependencies:
```python
# WeasyPrint (requires GTK)
from weasyprint import HTML
html = HTML(string=html_content)
html.write_pdf(output_path)

# xhtml2pdf (pure Python)
from xhtml2pdf import pisa
with open(output_path, "w+b") as pdf_file:
    pisa.CreatePDF(html_content, dest=pdf_file, encoding="utf-8")
```
- **Apply to:** Any PDF generation on Windows or cross-platform projects

**LL-037: xhtml2pdf Error Handling**
- `pisa.CreatePDF()` returns a status object with `err` count
- Check `pisa_status.err` for errors, don't just rely on exceptions:
```python
pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
if pisa_status.err:
    raise PDFGenerationError(f"xhtml2pdf reported {pisa_status.err} errors")
```
- **Apply to:** Any xhtml2pdf PDF generation

**LL-038: Pydantic Path Type Requires Config**
- Using `pathlib.Path` in Pydantic models requires `arbitrary_types_allowed`:
```python
from pathlib import Path

class FormattedDocument(BaseModel):
    file_path: Path

    model_config = {"arbitrary_types_allowed": True}
```
- **Apply to:** Any Pydantic model with Path fields

**LL-039: Jinja2 selectattr Filter for Template Filtering**
- Filter sections by type in Jinja2 templates:
```html
{% for section in cv.sections | selectattr('section_type', 'equalto', 'experience') | list %}
    <!-- render experience sections -->
{% endfor %}
```
- `| list` needed after `selectattr` to iterate
- **Apply to:** Any Jinja2 template filtering by object attributes

**LL-040: Templates Directory Convention**
- Spec used `app/templates/` - adapted to `src/templates/`
- Keep templates separate from module code
- Use FileSystemLoader with absolute or project-relative paths:
```python
Environment(loader=FileSystemLoader(str(templates_dir)))
```
- **Apply to:** Any Jinja2 template loading

---

## Phase 3: Integration

### S6 Pipeline Orchestrator (Complete)

#### Lessons Learned

**LL-041: Import from collections.abc for Python 3.9+**
- For `Callable` and `Awaitable` types, import from `collections.abc` not `typing`
- Ruff UP035 flags the deprecated `typing` import:
```python
# Old way (deprecated)
from typing import Callable, Awaitable

# New way (Python 3.9+)
from collections.abc import Callable, Awaitable
```
- **Apply to:** Any code using callable types

**LL-042: Cast Mock Return Values for Type Safety**
- Mock `return_value` is typed as `Any` by mypy
- Use explicit `cast()` when returning from typed test helper functions:
```python
from typing import cast

async def track_rinser(*args: object, **kwargs: object) -> ProcessedJob:
    call_order.append("rinser")
    return cast(ProcessedJob, mock_rinser.process_job.return_value)
```
- **Apply to:** Any tests with typed helper functions using mocks

**LL-043: Pipeline Orchestrator Adapts Spec to Actual Module Interfaces**
- Spec may use different method names than actual implementations
- Always check actual module interfaces before implementing integration:
  - Spec: `create_application()` → Actual: `create_content()`
  - Spec: `ApplicationPackage` → Actual: `CreatedContent`
- **Apply to:** Any integration service connecting multiple modules

**LL-044: Progress Callback Pattern for Long-Running Operations**
- Use async callback for progress reporting:
```python
ProgressCallback = Callable[[PipelineProgress], Awaitable[None]]

async def execute(self, input_data, progress_callback=None):
    if progress_callback:
        await progress_callback(progress)
```
- Enables polling updates for web interface (PoC scope)
- **Apply to:** Any long-running service operations

---

### API Routes (Complete)

#### Lessons Learned

**LL-045: Generator Return Type for pytest Fixtures with yield**
- Fixtures using `yield` need `Generator` return type for mypy:
```python
from collections.abc import Generator

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    # setup
    yield TestClient(app)
    # cleanup
```
- Without this, mypy reports "The return type of a generator function should be Generator"
- **Apply to:** Any pytest fixtures using yield

**LL-046: FastAPI BackgroundTasks for Long-Running Operations**
- Use `BackgroundTasks` for pipeline execution to return immediately:
```python
@router.post("/apply")
async def apply(
    request: ApplyRequest,
    background_tasks: BackgroundTasks,
):
    job_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(execute_pipeline, ...)
    return ApplyResponse(job_id=job_id, status="running")
```
- Client polls `/api/status/{job_id}` for completion
- **Apply to:** Any endpoint that triggers long-running operations

**LL-047: In-Memory JobStore for PoC**
- Simple dict-based storage works for PoC:
```python
class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, PipelineResult] = {}

    def store(self, result: PipelineResult) -> str:
        job_id = result.job_id or result.pipeline_id
        self._jobs[job_id] = result
        return job_id
```
- Use fallback to `pipeline_id` if `job_id` is None
- Production would use a database
- **Apply to:** Simple state management in PoC APIs

**LL-048: FastAPI Dependency Override for Testing**
- Override dependencies in tests using `app.dependency_overrides`:
```python
from src.web.dependencies import get_orchestrator

async def override_orchestrator() -> Mock:
    return mock_orchestrator

app.dependency_overrides[get_orchestrator] = override_orchestrator

# Cleanup
app.dependency_overrides.clear()
```
- Always clear overrides in fixture cleanup
- **Apply to:** Any FastAPI endpoint tests

---

### S8 Notification Service (Complete)

#### Lessons Learned

**LL-049: Use deque for Bounded Collections**
- `collections.deque` with `maxlen` automatically evicts oldest items:
```python
from collections import deque

self._notifications: deque[Notification] = deque(maxlen=50)
# Adding item 51 automatically removes item 1
```
- Simpler than manual eviction logic
- **Apply to:** Any bounded in-memory collection

**LL-050: Notification Type-Specific Defaults**
- Warning and error notifications should not auto-dismiss:
```python
def notify_warning(self, title: str, message: str, ...) -> Notification:
    return self.notify(
        NotificationType.WARNING, title, message,
        auto_dismiss=False,  # Warnings stay visible
        ...
    )
```
- Info and success can auto-dismiss (5-10 seconds)
- **Apply to:** Any notification system design

**LL-051: Service Integration with Web Routes**
- When adding new services, update multiple files:
  1. Create service package in `src/services/<name>/`
  2. Create API routes in `src/web/routes/<name>.py`
  3. Update `src/web/routes/__init__.py` to export router
  4. Update `src/web/main.py` to include router
  5. Update health check to include new service
- **Apply to:** Any new service integration

**LL-052: Jinja2 Templates with FastAPI**
- Use `Jinja2Templates` from `fastapi.templating` for server-rendered pages
- Templates need `request` parameter passed for proper rendering
- Keep templates in dedicated directory (`src/web/templates/`)
- Use `TemplateResponse(request=request, name="template.html")` pattern
- **Apply to:** Server-rendered web pages

**LL-053: Vanilla JS for PoC Web Interface**
- For PoC, vanilla JavaScript with fetch API is sufficient
- Avoids complexity of npm, build tools, Vue/React frameworks
- Polling pattern works well for status updates (1-3 second intervals)
- Use CSS-in-style tags for self-contained templates
- **Apply to:** Simple PoC web interfaces

**LL-054: Update Tests When Changing Endpoint Paths**
- When moving an endpoint (e.g., `/` to `/info`), update corresponding tests
- Search for endpoint path in test files before changing routes
- Tests may call specific paths that need to be updated
- **Apply to:** Any route path changes

---

## Architecture Change: Local LLM Transition (December 2025)

### Context

The project transitioned from Anthropic Claude Haiku 3.5 API to local Ollama inference
to support the thesis objective of edge computing on Raspberry Pi 5.

**Status:** ✅ Implementation Complete (December 13, 2025)

### Lessons Validated (Promoted to LL-055 to LL-058)

**LI-003: Ollama Provider Abstraction** → ✅ **Validated as LL-055**
- Created provider abstraction layer (`LLMProvider` base class)
- Implemented `OllamaProvider` as primary provider
- Service interface unchanged - modules don't need modification

**LI-004: Ollama Structured Output** → ✅ **Validated as LL-057**
- `format="json"` works for basic JSON output
- Lower temperature (0.1) used for structured output
- JSON instruction in system prompt still recommended

**LI-005: Local LLM Performance Expectations** → ⏳ **Pending Pi 5 Testing**
- Performance expectations documented but need validation on actual Pi 5 hardware
- Development machine testing shows good performance with Ollama

**LI-006: Ollama Service Dependency** → ✅ **Validated as LL-056**
- Initialization checks Ollama connectivity and model availability
- Helpful error messages guide users to `ollama pull` commands
- Health check endpoint verifies Ollama status

**LI-007: Cost Tracker Adaptation** → ✅ **Validated as LL-058**
- Cost rates set to 0.0 for local inference
- Token tracking still active for metrics
- Budget check infrastructure retained for future API fallback

### Reference Documents

- **Transition Guide:** `docs/guides/Local_LLM_Transition_Guide.md`
- **Updated S1 Spec:** `docs/services/S1_LLM_Service_-_Claude_Code_Instructions.md`
- **Updated Scope:** `docs/guides/Scout_PoC_Scope_Document.md`

---

## Quick Reference

### Implementation Order

#### Phase 1: Services (Complete)
1. S2 Metrics Service - Complete (formerly Cost Tracker)
2. S3 Cache Service - Complete
3. S4 Vector Store - Complete
4. S1 LLM Service - Complete (✅ Refactored for Ollama)
5. Profile Service - Complete (alternative to YAML profiles)
6. Database Service - Complete (✅ SQLite persistence, Dec 2025)

#### Phase 2: Modules (Complete)
5. M1 Collector - Complete
6. M2 Rinser - Complete
7. M3 Analyzer - Complete
8. M4 Creator - Complete
9. M5 Formatter - Complete

#### Phase 3: Integration (Complete)
10. S6 Pipeline Orchestrator - Complete
11. API Routes - Complete
12. S8 Notification Service - Complete
13. Web Interface - Complete

### Test Targets
| Component | Tests | Coverage |
|-----------|-------|----------|
| S2 Metrics Service | ~41 | >90% |
| S3 Cache Service | 46 | >90% |
| S4 Vector Store | 55 | >90% |
| S1 LLM Service | 52 | >90% |
| M1 Collector | 49 | >90% |
| M2 Rinser | 71 | >90% |
| M3 Analyzer | 62 | >90% |
| M4 Creator | 48 | >90% |
| M5 Formatter | 38 | >90% |
| S6 Pipeline | 52 | >90% |
| API Routes | 43 | >90% |
| S8 Notification | 40 | >90% |
| Web Interface | ~10 | >90% |
| Profile Service | 45 | >90% |
| Skill Aliases | 36 | >90% |
| Database Service | ~50 | >90% |
| **Total** | **~738** | **>90%** |

---

## Enhancement Features

### Skill Aliases Feature (Complete)

#### Lessons Learned

**LL-059: Skill Alias System Pattern**
- Use a central dictionary mapping canonical names to aliases
- Build reverse lookup at module load time for O(1) normalization
- Keep all aliases lowercase for consistent matching
```python
SKILL_ALIASES: dict[str, list[str]] = {
    "kubernetes": ["k8s", "kube"],
    "python": ["py", "python3", "python 3.x"],
}

# Build reverse lookup once at module load
_ALIAS_TO_CANONICAL: dict[str, str] = {}
for canonical, aliases in SKILL_ALIASES.items():
    _ALIAS_TO_CANONICAL[canonical.lower()] = canonical
    for alias in aliases:
        _ALIAS_TO_CANONICAL[alias.lower()] = canonical
```
- **Apply to:** Any terminology normalization system

**LL-060: Query Expansion for Better Semantic Search**
- Expand search queries to include all known aliases
- Combine original query with expanded terms in parentheses
- This helps vector embeddings capture terminology variance
```python
expanded_terms = expand_skill_query(query)  # ["kubernetes", "k8s", "kube"]
if len(expanded_terms) > 1:
    enhanced_query = f"{query} ({', '.join(expanded_terms)})"
# Result: "kubernetes (kubernetes, k8s, kube)"
```
- **Apply to:** Any semantic search needing terminology normalization

**LL-061: Test Updates When Behavior Changes**
- When enhancing search behavior, existing tests may need updates
- Tests that check exact query strings will fail with query expansion
- Update tests to validate behavior rather than exact implementation
```python
# Old test (too rigid):
mock.search.assert_called_with(query="machine learning")

# New test (validates behavior):
call_args = mock.search.call_args
assert "machine learning" in call_args.kwargs["query"]
assert "ml" in call_args.kwargs["query"]  # Alias is included
```
- **Apply to:** Any behavior-changing enhancements

**LL-062: Metadata Enrichment for Indexed Documents**
- Add canonical_name and aliases to document metadata during indexing
- Append alias text to searchable content for embedding coverage
- Enables both exact matching and semantic similarity
```python
metadata={
    "name": skill.name,
    "canonical_name": normalize_skill_name(skill.name),
    "aliases": ",".join(expand_skill_query(skill.name)),
}
content = f"{searchable_text} Also known as: {', '.join(aliases)}"
```
- **Apply to:** Any vector store indexing with terminology variants

---

## Database Persistence Implementation (December 2025)

### Database Service (Complete)

#### Lessons Learned

**LL-063: SQLite for PoC Persistence**
- SQLite is sufficient for PoC-level persistence needs
- Single file database (`data/scout.db`) simplifies deployment
- No need for PostgreSQL or other database servers
- aiosqlite provides async SQLite access for FastAPI integration
```python
import aiosqlite

async with aiosqlite.connect(self._db_path) as db:
    db.row_factory = aiosqlite.Row
    await db.execute(query, params)
    await db.commit()
```
- **Apply to:** Any PoC needing simple persistence

**LL-064: Auto-Migration Pattern for Schema Changes**
- Check schema version on startup and apply migrations
- Store version in a metadata table or dedicated file
- Keep migrations idempotent (safe to run multiple times)
```python
async def _ensure_schema(self) -> None:
    """Create tables if they don't exist."""
    async with aiosqlite.connect(self._db_path) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY,
                slug TEXT UNIQUE NOT NULL,
                ...
            )
        ''')
        await db.commit()
```
- **Apply to:** Any database with evolving schema

**LL-065: Demo Data Seeding Pattern**
- Create demo data on first startup when tables are empty
- Use conditional insert (only if no profiles exist)
- Provide realistic demo data for immediate testing
```python
async def _seed_demo_profiles(self) -> None:
    """Create demo profiles if none exist."""
    count = await self._count_profiles()
    if count == 0:
        for demo in DEMO_PROFILES:
            await self.create_profile(demo)
```
- **Apply to:** Any application needing out-of-box demo experience

**LL-066: Slug-Based URLs for Human-Readable Routes**
- Generate URL slugs from profile names (lowercase, hyphenated)
- Ensure uniqueness by appending numbers if needed
- Use slugs in URLs instead of integer IDs for better UX
```python
def generate_slug(name: str) -> str:
    """Convert name to URL-safe slug."""
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return slug  # "Emma Chen" -> "emma-chen"
```
- **Apply to:** Any user-facing resource URLs

**LL-067: Active Profile Pattern with Re-indexing**
- Only one profile can be "active" at a time
- Switching profiles triggers ChromaDB re-indexing
- Web interface reflects active profile in navbar
```python
async def set_active_profile(self, slug: str) -> Profile:
    """Activate a profile and re-index to ChromaDB."""
    # Clear previous active
    await self._db.execute("UPDATE profiles SET is_active = 0")
    # Set new active
    await self._db.execute(
        "UPDATE profiles SET is_active = 1 WHERE slug = ?",
        (slug,)
    )
    # Re-index to ChromaDB
    await self._reindex_profile(profile)
    return profile
```
- **Apply to:** Any application with "current selection" pattern

**LL-068: Legacy URL Redirects for Backward Compatibility**
- Add 301 redirects for old URLs when restructuring routes
- Keeps bookmarks and external links working
- Use RedirectResponse with status_code=301
```python
@router.get("/profile/create", response_class=RedirectResponse)
async def profile_create_redirect() -> RedirectResponse:
    """Redirect legacy URL to new location."""
    return RedirectResponse(url="/profiles/new", status_code=301)
```
- **Apply to:** Any route restructuring

**LL-069: Profile-Scoped Applications**
- Associate applications with specific profiles via foreign key
- Filter applications by active profile in list views
- Allows comparing results across different profiles
```python
async def list_applications(
    self,
    profile_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Application], int]:
    query = "SELECT * FROM applications"
    if profile_id:
        query += " WHERE profile_id = ?"
```
- **Apply to:** Any multi-tenant or multi-profile application

**LL-070: Collector Database Integration**
- Add `load_profile_from_db()` method to Collector for database integration
- Keeps existing YAML loading for backward compatibility
- Module adapts to data source without changing interface
```python
async def load_profile_from_db(self) -> UserProfile | None:
    """Load the active profile from database."""
    from src.services.database import get_database_service
    db = await get_database_service()
    active = await db.get_active_profile()
    if active is None:
        return None
    self._profile = UserProfile(**active.profile_data)
    return self._profile
```
- **Apply to:** Any module needing multiple data source support

---

*Last Updated: December 16, 2025*
*Review & Optimization Phase - PoC implementation complete (~700+ total tests)*
*Architecture: Local Ollama LLM (Qwen 2.5 3B / Gemma 2 2B)*
*Database: SQLite with multi-profile support*
