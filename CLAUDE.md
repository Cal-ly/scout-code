# CLAUDE.md - Scout Project Context

This file provides context for Claude Code when working on the Scout project.

## Project Overview

**Scout** is an intelligent job application system that automates job discovery, semantic matching, and tailored application generation. This is a Proof of Concept (PoC) for a bachelor's thesis exploring the intersection of generative AI with edge computing on Raspberry Pi 5.

### Core Value Proposition

Transform a job posting and user profile into tailored CV and cover letter through:
1. **Semantic Analysis**: Match user skills/experience to job requirements
2. **Gap Identification**: Identify missing qualifications
3. **Content Generation**: Create tailored application materials
4. **Professional Output**: Generate PDF documents

---

## Critical Files to Read First

Before implementing anything, read these files in order:

1. **`docs/guides/Scout_PoC_Scope_Document.md`** - Authoritative scope reference
2. **`LL-LI.md`** - Lessons Learned & Lessons Identified from previous implementations
3. **`docs/guides/Scout_Claude_Code_Development_Guide.md`** - Development workflow
4. **Relevant specification file** for the component being implemented

> **Important:** Always check `LL-LI.md` before starting new work. It contains validated patterns and pitfalls from S2/S3 implementations.

---

## Development Workflow: RAVE Cycle

Every implementation follows the **RAVE** cycle:

### R - Review Context
```bash
# Check lessons learned first
cat LL-LI.md

# Check what exists
ls -la src/services/
cat src/services/existing_service/service.py

# Review the specification
cat docs/services/S[N]_[Service]_-_Claude_Code_Instructions.md

# Check scope constraints
grep -A5 "Service Name" docs/architecture/Scout_PoC_-_Complete_Project_Structure___Configuration.md
```

**Key patterns from LL-LI.md to apply:**
- LL-002: Three-file service structure (models.py, exceptions.py, service.py)
- LL-003: Async initialization pattern
- LL-004: Singleton with dependency injection
- LL-006: Avoid variable type shadowing (use different names)

### A - Analyze Step
- Break the work into small increments (50-150 lines each)
- Identify dependencies that must exist first
- Note edge cases to handle
- Document what to defer to future steps

### V - Verify Continuously
```bash
# After each change:
python -m py_compile src/path/file.py  # Syntax
mypy src/path/file.py                   # Types
ruff check src/path/file.py            # Linting (see LL-007 for common issues)
pytest tests/test_<service>.py -v       # Tests (flat structure)
```

**Common issues from LL-LI.md:**
- LL-007: Remove unnecessary `"r"` mode from `open()` calls
- See "Common Mypy Issues & Fixes" and "Common Ruff Issues & Fixes" tables in LL-LI.md

### E - Execute Incrementally
- Implement ONE step at a time
- Complete the full RAVE cycle before next step
- Never skip verification
- **After completion:** Update LL-LI.md with new lessons learned

---

## Project Structure

```
scout-code/
├── src/
│   ├── modules/                # Core modules (Collector, Rinser, Analyzer, Creator, Formatter)
│   │   ├── collector/          # M1: Job discovery & profile management
│   │   ├── rinser/             # M2: Data normalization & extraction
│   │   ├── analyzer/           # M3: Semantic matching & scoring
│   │   ├── creator/            # M4: Tailored content generation
│   │   └── formatter/          # M5: Document output (PDF/DOCX)
│   ├── services/               # Services (LLM, Cache, Metrics, VectorStore, Profile)
│   │   ├── llm_service/        # S1: Ollama local LLM integration
│   │   ├── metrics_service/    # S2: Performance & reliability tracking
│   │   ├── cache_service/      # S3: Multi-tier caching
│   │   ├── vector_store/       # S4: ChromaDB vector database
│   │   ├── pipeline/           # S6: Pipeline orchestration
│   │   ├── notification/       # S8: In-app notifications
│   │   └── profile/            # Profile management (SQLite + vector indexing)
│   └── web/                    # Web interface (FastAPI entry point, routes, templates)
├── tests/                      # Test suite (ready for implementation)
├── docs/                       # Specifications and guides
│   ├── modules/                # Module specifications (M1-M5)
│   ├── services/               # Service specifications (S1-S8)
│   ├── architecture/           # Architecture & design docs
│   └── guides/                 # Development guides
├── venv/                       # Virtual environment
├── pyproject.toml              # Project metadata and dependencies
├── requirements.txt            # Core dependencies
├── requirements-dev.txt        # Development dependencies
├── Makefile                    # Task automation
└── .env.example                # Environment variable template

Note: templates/, static/, prompts/, data/ directories will be created during implementation
```

---

## PoC Constraints (IMPORTANT)

These decisions are **locked** - do not implement deferred features:

| Component | In Scope | Deferred |
|-----------|----------|----------|
| **LLM** | **Ollama local: Qwen 2.5 3B + Gemma 2 2B** | ~~Anthropic API~~, cloud fallback |
| **Cache** | Memory + file cache | Redis, semantic caching |
| **Pipeline** | Sequential execution | Parallel, checkpointing, DAG |
| **Vector Store** | 2 collections (profiles, jobs) | FAISS, batch optimization, 5 collections |
| **Notifications** | In-app toast only | Email, SMS, push, webhooks |
| **Input** | Paste job text | URL fetching, file upload |
| **Output** | PDF only | DOCX |
| **Web** | Polling updates | WebSocket |
| **Services** | Core 4 services | Content Optimizer (S7) |

> **Architecture Update (December 2025):** LLM changed from Anthropic Claude API
> to local Ollama inference for edge deployment on Raspberry Pi 5.
> See `docs/guides/Local_LLM_Transition_Guide.md` for implementation details.

If you're unsure whether something is in scope, check `docs/guides/Scout_PoC_Scope_Document.md`.

---

## Implementation Order

Services and modules should be implemented in this order due to dependencies:

### Phase 1: Foundation Services
```
1. S2 Metrics Service          # No dependencies (performance tracking)
2. S3 Cache Service            # No dependencies
3. S4 Vector Store Service     # No dependencies
4. S1 LLM Service              # Depends on: Metrics, Cache
```

### Phase 2: Core Modules
```
5. M1 Collector                # Depends on: Vector Store
6. M2 Rinser                   # Depends on: LLM Service
7. M3 Analyzer                 # Depends on: Collector, Vector Store, LLM
8. M4 Creator                  # Depends on: LLM Service
9. M5 Formatter                # Depends on: Creator output
```

### Phase 3: Integration
```
10. S6 Pipeline Orchestrator   # Depends on: All modules
11. API Routes                 # Depends on: Pipeline
12. S8 Notification Service    # Depends on: API events
13. Web Interface              # Depends on: API Routes
```

---

## Code Patterns

### Imports (follow this order)

```python
# Standard library
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

# Third-party
from pydantic import BaseModel, Field
from fastapi import Depends

# Local - absolute imports (use src. prefix)
from src.services.vector_store import VectorStoreService
from src.services.llm_service import LLMService
from src.modules.analyzer import Analyzer
```

### Class Structure

```python
class ServiceName:
    """
    One-line description.
    
    Longer description of what this service does and
    how it fits into the Scout architecture.
    
    Attributes:
        attr1: Description of attribute.
        attr2: Description of attribute.
    
    Example:
        >>> service = ServiceName()
        >>> await service.initialize()
        >>> result = await service.do_something()
    """
    
    def __init__(self):
        """Initialize service (call initialize() before use)."""
        self._initialized = False
        # Private attributes with underscore prefix
        
    async def initialize(self) -> None:
        """
        Initialize the service.
        
        Must be called before using the service.
        
        Raises:
            ServiceError: If initialization fails.
        """
        if self._initialized:
            logger.warning("Service already initialized")
            return
        # Initialization logic
        self._initialized = True
        
    async def shutdown(self) -> None:
        """Gracefully shutdown the service."""
        if not self._initialized:
            return
        # Cleanup logic
        self._initialized = False
```

### Error Handling

```python
# Define custom exceptions within each service/module
# Or create a shared exceptions module if needed
class ScoutError(Exception):
    """Base exception for Scout application."""
    pass

class ServiceError(ScoutError):
    """Error in service operations."""
    pass

# Use in code
try:
    result = await risky_operation()
except SomeLibraryError as e:
    error_msg = f"Operation failed: {e}"
    logger.error(error_msg)
    raise ServiceError(error_msg) from e  # Always chain with 'from e'
```

### Async Patterns

```python
# Most service methods should be async
async def do_something(self) -> ResultType:
    ...

# FastAPI dependency
async def get_service() -> ServiceName:
    global _instance
    if _instance is None:
        _instance = ServiceName()
        await _instance.initialize()
    return _instance
```

### Testing Patterns

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch

@pytest.fixture
def service():
    """Create uninitialized service for testing."""
    return ServiceName()

@pytest.fixture
async def initialized_service(tmp_path):
    """Create initialized service with temp storage."""
    with patch("src.services.service_name.settings") as mock_settings:
        mock_settings.some_path = tmp_path / "data"
        service = ServiceName()
        await service.initialize()
        yield service
        await service.shutdown()

class TestServiceOperation:
    """Tests for specific operation."""
    
    @pytest.mark.asyncio
    async def test_success_case(self, initialized_service):
        """Should handle normal case correctly."""
        result = await initialized_service.operation()
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_error_case(self, initialized_service):
        """Should raise appropriate error."""
        with pytest.raises(ServiceError, match="expected message"):
            await initialized_service.bad_operation()
```

---

## Environment

### Development Machine

| Component | Spec |
|-----------|------|
| CPU | AMD Ryzen 9 9950X (16C/32T) |
| GPU | NVIDIA RTX 5070 Ti |
| RAM | 32GB DDR5 6000 MT/s |
| OS | EndeavourOS (Arch Linux) |
| IDE | VS Code |
| Python | 3.13.7 (3.12+ required) |

### Key Commands

```bash
# Development (using venv, not poetry)
source venv/bin/activate    # Activate venv (Linux/Mac)
# or: venv\Scripts\activate  # Activate venv (Windows)
make install                # Install dependencies
make run                    # Run dev server (uvicorn on port 8000)

# Ollama (Local LLM - required)
ollama serve                # Start Ollama server (if not running)
ollama list                 # List installed models
ollama pull qwen2.5:3b      # Pull primary model
ollama pull gemma2:2b       # Pull fallback model

# Testing
make test                   # Run all tests
make test-cov               # Run tests with coverage
pytest tests/test_cache.py -v  # Run specific tests

# Code Quality
make format                 # Apply black formatter
make lint                   # Run ruff linter
make typecheck              # Run mypy type checker
make clean                  # Remove cache files

# Verification (run after each change)
python -m py_compile src/path/file.py
mypy src/path/file.py --ignore-missing-imports
pytest tests/test_<service>.py -v
```

### Deployment to Raspberry Pi

The project includes deployment scripts to automate pushing changes to the Raspberry Pi:

```powershell
# Windows PowerShell
.\scripts\deploy.ps1                           # Interactive mode
.\scripts\deploy.ps1 -Message "Fix bug"        # Commit with message and deploy
.\scripts\deploy.ps1 -SkipCommit               # Deploy without committing
.\scripts\deploy.ps1 -NoRestart                # Deploy without restarting service
```

```bash
# Bash (Linux/Mac/WSL/Git Bash)
./scripts/deploy.sh                            # Interactive mode
./scripts/deploy.sh "Fix bug"                  # Commit with message and deploy
./scripts/deploy.sh --skip-commit              # Deploy without committing
./scripts/deploy.sh --no-restart               # Deploy without restarting service
```

**Raspberry Pi Configuration:**
| Setting | Value |
|---------|-------|
| Host | 192.168.1.21 |
| User | cally |
| Project Path | /home/cally/projects/scout-code |
| Service | scout.service |
| Web URL | http://192.168.1.21:8000/ |

**Manual Deployment (if scripts unavailable):**
```bash
# 1. Push changes to GitHub
git add -A && git commit -m "message" && git push origin main

# 2. SSH to Pi and pull
ssh cally@192.168.1.21 "cd /home/cally/projects/scout-code && git stash && git pull"

# 3. Restart service
ssh cally@192.168.1.21 "sudo systemctl restart scout.service"

# 4. Verify
ssh cally@192.168.1.21 "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/"
```

---

## Common Gotchas

### 1. Async Initialization
Services need explicit `initialize()` call - constructors can't be async:
```python
# Wrong
service = ServiceName()  # Not ready to use!

# Right
service = ServiceName()
await service.initialize()  # Now ready
```

### 2. ChromaDB Version
Use the specific import pattern for ChromaDB 0.4.x:
```python
import chromadb
from chromadb.config import Settings as ChromaSettings
```

### 3. Pydantic v2
We use Pydantic v2 - note the syntax differences:
```python
# v2 style
from pydantic import field_validator

@field_validator('field_name')
@classmethod
def validate_field(cls, v):
    ...
```

### 4. Type Hints for Optional
Always use `Optional[T]` or `T | None` for nullable fields:
```python
from typing import Optional

def func(param: Optional[str] = None) -> Optional[int]:
    ...
```

### 5. GPU Detection
Check for CUDA availability when loading ML models:
```python
import torch
device = "cuda" if torch.cuda.is_available() else "cpu"
```

### 6. Ollama Must Be Running
LLM Service requires Ollama server to be running:
```bash
# Check if running
curl http://localhost:11434/api/tags

# Start if not running
ollama serve &

# Verify models are available
ollama list
```

### 7. Local LLM Performance
Expect slower inference on Raspberry Pi 5:
- Qwen 2.5 3B: ~2-4 tokens/second
- Gemma 2 2B: ~4-6 tokens/second
- Full pipeline: 15-30 minutes (vs <2 min with cloud API)

---

## Code Documentation

The source code includes README files for navigation:
- `src/README.md` - Source overview and architecture
- `src/modules/README.md` - Module documentation with flow diagrams
- `src/services/README.md` - Service documentation with usage examples
- `src/web/README.md` - Web layer and API structure

For full documentation, see `docs/README.md`.

---

## Quick Reference

### File Locations

| What | Where |
|------|-------|
| **Lessons Learned** | `LL-LI.md` (read first!) |
| **Session Handover** | `HANDOVER.md` |
| **PoC Scope** | `docs/guides/Scout_PoC_Scope_Document.md` |
| **Current Implementation** | `docs/current_state/` (primary reference) |
| **Local LLM Transition** | `docs/guides/Local_LLM_Transition_Guide.md` |
| Development Guides | `docs/guides/` |
| Deployment Guides | `docs/deployment/` (3 files: Pi guide, User guide, Benchmarks) |
| Original Module Specs | `docs/modules/` (reference only) |
| Original Service Specs | `docs/services/` (reference only) |
| Archives | `docs/archive/` (deployment checklists, tasks, old specs) |
| Services | `src/services/[service_name]/` |
| Core Modules | `src/modules/[module_name]/` |
| Web Interface | `src/web/` |
| Tests | `tests/test_[service].py` (flat structure, ~650 tests) |
| TODO Tracking | `todo/*.md` (web-interface, services, modules, deployment, docs) |
| Project Config | `pyproject.toml`, `.env.example` |
| **Deployment Scripts** | `scripts/deploy.ps1` (Windows), `scripts/deploy.sh` (Bash) |

> **Note**: Original specs in `docs/modules/` and `docs/services/` are reference only.
> For current implementation details, see `docs/current_state/`.

### Service Dependencies

```
LLM Service ──────────────────────┐
    │                             │
    ├──▶ Metrics Service          │
    │                             │
    └──▶ Cache Service            │
                                  │
Vector Store Service ─────────────┤
                                  │
                                  ▼
              ┌─────────────────────────────────┐
              │         Core Modules            │
              │ Collector → Rinser → Analyzer   │
              │              → Creator → Formatter│
              └─────────────────────────────────┘
                                  │
                                  ▼
                      Pipeline Orchestrator
                                  │
                                  ▼
                      API Routes + Web Interface
```

---

## When Stuck

1. **Check LL-LI.md first** - similar issues may have been solved before
2. **Re-read the specification** - answers are usually there
3. **Check the scope document** - feature might be deferred
4. **Review adjacent implementations** - patterns are consistent
5. **Run existing tests** - understand expected behavior
6. **Check imports work** - many issues are import-related

---

---

## Current Project Status

**Phase:** Review & Optimization

### Phase 1: Foundation Services (COMPLETE - ~194 tests)
- ✅ **S2 Metrics Service** - Complete (~41 tests) - **Refactored from Cost Tracker**
- ✅ **S3 Cache Service** - Complete (46 tests)
- ✅ **S4 Vector Store Service** - Complete (55 tests)
- ✅ **S1 LLM Service** - Complete (~52 tests) - **Refactored for Ollama + Metrics**

### Phase 2: Core Modules (COMPLETE - 268 tests)
- ✅ **M1 Collector** - Complete (49 tests)
- ✅ **M2 Rinser** - Complete (71 tests)
- ✅ **M3 Analyzer** - Complete (62 tests)
- ✅ **M4 Creator** - Complete (48 tests)
- ✅ **M5 Formatter** - Complete (38 tests)

### Phase 3: Integration (COMPLETE - ~145 tests)
- ✅ **S6 Pipeline Orchestrator** - Complete (52 tests)
- ✅ **API Routes** - Complete (43 tests)
- ✅ **S8 Notification Service** - Complete (40 tests)
- ✅ **Web Interface** - Complete (~10 tests)

### Additional Services
- ✅ **Profile Service** - Complete (45 tests) - SQLite + vector indexing

**Estimated Total Tests:** ~652

**Learning Documentation:**
- See `LL-LI.md` for validated patterns (LL-001 to LL-058)
- See `HANDOVER.md` for session continuity context

**Architecture:** Local LLM via Ollama (Qwen 2.5 3B / Gemma 2 2B)

**Metrics Service (S2):**
- Tracks inference performance (duration, tokens/second)
- Records reliability (success rate, errors, retries, fallbacks)
- Collects system metrics (CPU, memory, temperature for Pi 5)
- 30-day retention with monthly archival

---

*Last updated: January 2026*
