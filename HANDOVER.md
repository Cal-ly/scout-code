# Scout Project - Session Handover Document

**Last Updated:** December 16, 2025
**Current Phase:** Review & Optimization
**Status:** PoC Implementation Complete - Database Persistence Added

---

## Quick Resume Prompt (COPY THIS)

```
I'm resuming work on Scout Project after conversation compaction.

Current Status:
- Phase 1 (Foundation Services): COMPLETE - ~194 tests
- Phase 2 (Core Modules): COMPLETE - 268 tests
- Phase 3 (Integration): COMPLETE - ~145 tests
- Profile Service: COMPLETE - 45 tests
- Database Service: COMPLETE - SQLite persistence for profiles/applications
- Total: ~700+ tests passing

Recent Additions:
- SQLite database persistence (src/services/database/)
- Multi-profile support with 3 demo profiles
- Profile-scoped applications
- Legacy URL redirects for backward compatibility
- Persistent PDF output directory (data/outputs)

Architecture: Local Ollama LLM (Qwen 2.5 3B / Gemma 2 2B)

Please read HANDOVER.md and LL-LI.md for full context.
```

---

## Project Summary

Scout is an intelligent job application system that transforms job postings and user profiles into tailored CV and cover letter PDFs. Built as a PoC for a bachelor's thesis exploring generative AI with edge computing on Raspberry Pi 5.

**Architecture Flow:**
```
Job Posting → M1 Collector → M2 Rinser → M3 Analyzer → M4 Creator → M5 Formatter → PDF Output
                  ↓              ↓            ↓             ↓
            Vector Store    LLM Service   LLM Service   LLM Service
                                (Ollama)      (Ollama)      (Ollama)
```

**Pipeline Orchestrator:**
```
PipelineInput(raw_job_text) → PipelineOrchestrator.execute() → PipelineResult
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              Rinser.process_job  Analyzer.analyze  Creator.create_content
                    │                 │                 │
                    ▼                 ▼                 ▼
              ProcessedJob      AnalysisResult    CreatedContent
                                                        │
                                                        ▼
                                              Formatter.format_application
                                                        │
                                                        ▼
                                              FormattedApplication (PDFs)
```

---

## Completed Work Summary

### Phase 1: Foundation Services (~194 tests)

| Service | Location | Tests | Key Exports |
|---------|----------|-------|-------------|
| S2 Metrics Service | `src/services/metrics_service/` | ~41 | `MetricsService`, `get_metrics_service` |
| S3 Cache Service | `src/services/cache_service/` | 46 | `CacheService`, `get_cache_service` |
| S4 Vector Store | `src/services/vector_store/` | 55 | `VectorStoreService`, `get_vector_store_service` |
| S1 LLM Service | `src/services/llm_service/` | 52 | `LLMService`, `get_llm_service` |

### Phase 2: Core Modules (268 tests)

| Module | Location | Tests | Key Exports |
|--------|----------|-------|-------------|
| M1 Collector | `src/modules/collector/` | 49 | `Collector`, `get_collector`, `UserProfile` |
| M2 Rinser | `src/modules/rinser/` | 71 | `Rinser`, `get_rinser`, `ProcessedJob` |
| M3 Analyzer | `src/modules/analyzer/` | 62 | `Analyzer`, `get_analyzer`, `AnalysisResult` |
| M4 Creator | `src/modules/creator/` | 48 | `Creator`, `get_creator`, `CreatedContent` |
| M5 Formatter | `src/modules/formatter/` | 38 | `Formatter`, `get_formatter`, `FormattedApplication` |

### Phase 3: Integration (~145 tests)

| Component | Location | Tests | Status |
|-----------|----------|-------|--------|
| S6 Pipeline Orchestrator | `src/services/pipeline/` | 52 | COMPLETE |
| API Routes | `src/web/routes/` | 43 | COMPLETE |
| S8 Notification Service | `src/services/notification/` | 40 | COMPLETE |
| Web Interface | `src/web/templates/` | ~10 | COMPLETE |

### Additional Services

| Service | Location | Tests | Key Exports |
|---------|----------|-------|-------------|
| Profile Service | `src/services/profile/` | 45 | `ProfileService`, `get_profile_service` |
| Database Service | `src/services/database/` | ~50 | `DatabaseService`, `get_database_service` |

**Estimated Total: ~700+ tests**

---

## Database Service (NEW - December 2025)

### Overview
The Database Service provides SQLite persistence for profiles and applications, enabling multi-profile support with persistent storage across server restarts.

### Structure
```
src/services/database/
  __init__.py          # Package exports
  models.py            # Profile, Application, ApplicationStatus, etc.
  exceptions.py        # ProfileNotFoundError, ApplicationNotFoundError, etc.
  service.py           # DatabaseService implementation
  migrations/          # Database schema migrations
```

### Key Features
- SQLite database storage (`data/scout.db`)
- Multi-profile support (3 demo profiles included)
- Profile-scoped applications
- Active profile switching with ChromaDB re-indexing
- Auto-migration on startup
- Slug-based profile URLs

### Demo Profiles
Three demo profiles are auto-created on first startup:
1. **Emma Chen** (`emma-chen`) - AI/ML engineer
2. **Marcus Andersen** (`marcus-andersen`) - Backend/DevOps engineer
3. **Sofia Martinez** (`sofia-martinez`) - Full-stack developer

### Usage
```python
from src.services.database import get_database_service, DatabaseService

# Get singleton
db = await get_database_service()

# Get active profile
profile = await db.get_active_profile()

# Switch active profile (triggers ChromaDB re-indexing)
await db.set_active_profile("marcus-andersen")

# List all profiles
profiles = await db.list_profiles()

# Get profile by slug
profile = await db.get_profile_by_slug("emma-chen")

# List applications (profile-scoped)
applications, total = await db.list_applications(profile_id=1, limit=20)
```

---

## Profile Service (LEGACY)

### Overview
The Profile Service manages user profiles with database storage, file backup, and vector indexing. It's an alternative to YAML-based profile management via M1 Collector.

> **Note:** For multi-profile support, use the Database Service instead.

### Structure
```
src/services/profile/
  __init__.py          # Package exports
  models.py            # ProfileStatus, ProfileData, ProfileChunk, etc.
  exceptions.py        # ProfileError, ProfileNotFoundError, etc.
  service.py           # ProfileService implementation
tests/test_profile.py  # 45 tests
```

### Key Features
- SQLite database storage (`data/profiles.db`)
- File backup to `data/profiles/`
- Auto-indexing to VectorStore on create/update
- Text chunking (paragraph-based with sentence fallback)
- Validation (100-10,000 characters)

### Usage
```python
from src.services.profile import get_profile_service, ProfileService

# Get singleton
profile_service = await get_profile_service()

# Create/update profile (auto-indexes)
result = await profile_service.create_profile("My professional experience...")
# Returns: ProfileCreateResponse(profile_id=1, status="created", is_indexed=True, chunk_count=5)

# Get status
status = await profile_service.get_status()
# Returns: ProfileStatus(exists=True, is_indexed=True, profile_id=1, chunk_count=5, ...)

# Get full profile
profile = await profile_service.get_profile()
# Returns: ProfileData with full text and metadata
```

---

## API Routes Summary

### Profile Management (NEW)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/profiles` | GET | List all profiles with stats |
| `/api/v1/profiles` | POST | Create new profile |
| `/api/v1/profiles/{slug}` | GET | Get profile by slug |
| `/api/v1/profiles/{slug}` | PUT | Update profile |
| `/api/v1/profiles/{slug}` | DELETE | Delete profile |
| `/api/v1/profiles/{slug}/activate` | POST | Set as active profile |

### Job Applications
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/jobs/apply` | POST | Start new job application (background task) |
| `/api/v1/jobs/{job_id}` | GET | Get pipeline status and results |
| `/api/v1/jobs/{job_id}/download/{file_type}` | GET | Download PDF (cv or cover_letter) |
| `/api/v1/jobs` | GET | List all submitted job applications (paginated) |
| `/api/v1/jobs/quick-score` | POST | Get quick compatibility score |

### Notifications
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/notifications` | GET | Get notifications |
| `/api/v1/notifications/{id}/read` | POST | Mark notification as read |
| `/api/v1/notifications/read-all` | POST | Mark all as read |
| `/api/v1/notifications` | DELETE | Clear all notifications |

### System
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check endpoint |
| `/info` | GET | Application info JSON endpoint |

### Web Pages
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard (HTML page) |
| `/profiles` | GET | Profile list page |
| `/profiles/new` | GET | Create new profile page |
| `/profiles/{slug}/edit` | GET | Edit profile page |
| `/applications` | GET | Applications list page |
| `/metrics` | GET | Performance metrics dashboard |
| `/logs` | GET | Application logs page |
| `/diagnostics` | GET | System diagnostics page |

### Legacy Redirects (301)
| Old URL | Redirects To |
|---------|--------------|
| `/profile/create` | `/profiles/new` |
| `/profile/edit` | `/profiles` |
| `/profiles/create` | `/profiles/new` |
| `/profiles/edit` | `/profiles` |

---

## Key Technical Decisions

### LLM Architecture (Updated December 2025)
- **Primary Model:** Qwen 2.5 3B via Ollama (local inference)
- **Fallback Model:** Gemma 2 2B via Ollama
- **Provider Pattern:** Abstract `LLMProvider` base class
- **Target Hardware:** Raspberry Pi 5 (edge computing)

### PDF Generation
- Uses **xhtml2pdf** (not WeasyPrint) - pure Python, no GTK dependencies
- Templates in `src/templates/`

### Vector Collections (PoC Limit: 2)
- `user_profiles` - Skills, experiences, education
- `job_requirements` - Job requirements from M2 Rinser

### Data Storage
- **Database:** SQLite (`data/scout.db`) - profiles and applications
- **Profiles (legacy):** SQLite (`data/profiles.db`) + file backup
- **Cache:** Two-tier LRU (memory + file)
- **Metrics:** JSON files with 30-day retention
- **PDF Output:** Persistent directory (`data/outputs/`)

---

## Development Environment

### Windows Commands
```powershell
cd c:\Users\Cal-l\Documents\GitHub\Scout\scout-code
.\venv\Scripts\Activate.ps1

# Run all tests
.\venv\Scripts\python.exe -m pytest tests/ -v

# Run specific test file
.\venv\Scripts\python.exe -m pytest tests/test_profile.py -v

# Verification for any component
.\venv\Scripts\python.exe -m py_compile src/services/profile/service.py
.\venv\Scripts\python.exe -m mypy src/services/profile/ --ignore-missing-imports
.\venv\Scripts\python.exe -m ruff check src/services/profile/

# Start the server
.\venv\Scripts\python.exe -m uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000
```

### Ollama Commands
```bash
ollama serve                # Start Ollama server
ollama list                 # List installed models
ollama pull qwen2.5:3b      # Pull primary model
ollama pull gemma2:2b       # Pull fallback model
```

---

## Key Patterns (from LL-LI.md)

### Service/Module Structure (LL-002)
```
component_name/
  __init__.py      # Package exports
  models.py        # Pydantic models
  exceptions.py    # Custom exceptions
  <main>.py        # Implementation
```

### Singleton Pattern (LL-004)
```python
_instance: ServiceClass | None = None

async def get_service() -> ServiceClass:
    global _instance
    if _instance is None:
        _instance = ServiceClass()
        await _instance.initialize()
    return _instance

def reset_service() -> None:
    global _instance
    _instance = None
```

### Provider Abstraction (LL-055)
```python
class LLMProvider(ABC):
    @abstractmethod
    async def initialize(self) -> None: pass
    @abstractmethod
    async def generate(self, request: LLMRequest, request_id: str) -> LLMResponse: pass
    @abstractmethod
    async def health_check(self) -> dict[str, Any]: pass
```

---

## Reference Files

| Document | Purpose |
|----------|---------|
| `CLAUDE.md` | Project context and patterns |
| `LL-LI.md` | Lessons learned (LL-001 to LL-062+) |
| `REVIEW.md` | Code review findings (Dec 13, 2025) |
| `REVIEW-GUIDE.md` | Review methodology |
| `docs/guides/Scout_PoC_Scope_Document.md` | PoC constraints |
| `docs/guides/Local_LLM_Transition_Guide.md` | Ollama architecture details |
| `docs/tasks/TASK-PERSISTENCE-UI.md` | Database persistence task (COMPLETED) |

---

## Module Inputs/Outputs Reference

```
Database Service
  Input: Profile/Application data
  Output: Persisted records (SQLite)
  Notes: Auto-creates 3 demo profiles on startup

M1 Collector
  Input: YAML profile path OR database profile
  Output: UserProfile (indexed in vector store)
  Notes: load_profile_from_db() method loads active profile

Profile Service (Legacy)
  Input: Raw profile text (100-10,000 chars)
  Output: ProfileData (indexed in vector store)

M2 Rinser
  Input: Raw job text
  Output: ProcessedJob (requirements indexed)

M3 Analyzer
  Input: ProcessedJob + UserProfile
  Output: AnalysisResult (compatibility + strategy)

M4 Creator
  Input: AnalysisResult
  Output: CreatedContent (CV + cover letter text)

M5 Formatter
  Input: CreatedContent
  Output: FormattedApplication (PDF files in data/outputs/)

S6 Pipeline Orchestrator
  Input: PipelineInput(raw_job_text, source?, skip_formatting?)
  Output: PipelineResult (status, paths, scores, timing)
  Notes: Persists results to database
```

---

## Current Phase: Review & Optimization

### Completed: Database Persistence (December 2025)
- [x] SQLite database service implementation
- [x] Multi-profile support with demo profiles
- [x] Profile-scoped applications
- [x] API endpoints for profile management
- [x] Web UI for profile listing/editing
- [x] Legacy URL redirects for backward compatibility
- [x] Collector integration with database
- [x] Persistent PDF output directory

### Phase A: Consolidation (In Progress)
- [x] A-01: Sync pyproject.toml with requirements.txt
- [x] A-02: Document Profile Service in HANDOVER.md
- [x] A-03: Document Database Service in HANDOVER.md
- [x] A-04: Update API routes documentation
- [ ] A-05: Verify all imports resolve correctly

### Phase B: Validation Testing (Upcoming)
- [ ] B-01: End-to-end test with synthetic job postings
- [ ] B-02: Performance baseline on dev machine
- [ ] B-03: Error path validation
- [ ] B-04: Cache effectiveness measurement

### Phase C: Enhancement Opportunities (Planned)
- Pipeline resilience (checkpointing)
- Observability improvements
- Output quality improvements

---

*Last Updated: December 16, 2025*
*Architecture: Local Ollama LLM (Qwen 2.5 3B / Gemma 2 2B)*
*Database: SQLite with multi-profile support*
*Estimated Total Tests: ~700+*
