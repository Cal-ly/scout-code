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

1. **`docs/Scout_PoC_Scope_Document.md`** - Authoritative scope reference
2. **`docs/Claude_Code_Development_Guide.md`** - Development workflow
3. **Relevant specification file** for the component being implemented

---

## Development Workflow: RAVE Cycle

Every implementation follows the **RAVE** cycle:

### R - Review Context
```bash
# Check what exists
ls -la src/services/
cat src/services/existing_service/service.py

# Review the specification
cat docs/services/S[N]_[Service]_-_Claude_Code_Instructions.md

# Check scope constraints
grep -A5 "Service Name" docs/architecture/Scout_PoC_-_Complete_Project_Structure___Configuration.md
```

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
pytest tests/unit/path/ -v              # Tests
```

### E - Execute Incrementally
- Implement ONE step at a time
- Complete the full RAVE cycle before next step
- Never skip verification

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
│   ├── services/               # Services (LLM, Cache, CostTracker, VectorStore)
│   │   ├── llm_service/        # S1: Claude API integration
│   │   ├── cost_tracker/       # S2: Budget & cost tracking
│   │   ├── cache_service/      # S3: Multi-tier caching
│   │   └── vector_store/       # S4: ChromaDB vector database
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
| **LLM** | Anthropic Claude 3.5 Haiku only | OpenAI fallback, model selection |
| **Cache** | Memory + file cache | Redis, semantic caching |
| **Pipeline** | Sequential execution | Parallel, checkpointing, DAG |
| **Vector Store** | 2 collections (profiles, jobs) | FAISS, batch optimization, 5 collections |
| **Notifications** | In-app toast only | Email, SMS, push, webhooks |
| **Input** | Paste job text | URL fetching, file upload |
| **Output** | PDF only | DOCX |
| **Web** | Polling updates | WebSocket |
| **Services** | Core 4 services | Content Optimizer (S7) |

If you're unsure whether something is in scope, check `docs/Scout_PoC_Scope_Document.md`.

---

## Implementation Order

Services and modules should be implemented in this order due to dependencies:

### Phase 1: Foundation Services
```
1. S2 Cost Tracker Service     # No dependencies
2. S3 Cache Service            # No dependencies  
3. S4 Vector Store Service     # No dependencies
4. S1 LLM Service              # Depends on: Cost Tracker, Cache
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

# Testing
make test                   # Run all tests
make test-cov               # Run tests with coverage
pytest tests/unit/services/test_cache.py -v  # Run specific tests

# Code Quality
make format                 # Apply black formatter
make lint                   # Run ruff linter
make typecheck              # Run mypy type checker
make clean                  # Remove cache files

# Verification (run after each change)
python -m py_compile src/path/file.py
mypy src/path/file.py --ignore-missing-imports
pytest tests/unit/path/test_file.py -v
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

---

## Quick Reference

### File Locations

| What | Where |
|------|-------|
| Module Specifications | `docs/modules/Module_[N]_*_Instructions.md` |
| Service Specifications | `docs/services/S[N]_*_Instructions.md` |
| PoC Scope & Architecture | `docs/architecture/` |
| Development Guides | `docs/guides/` |
| Specification Index | `docs/SPECIFICATIONS.md` |
| Services | `src/services/[service_name]/` |
| Core Modules | `src/modules/[module_name]/` |
| Web Interface | `src/web/` |
| Tests | `tests/` (to be organized into unit/integration) |
| Project Config | `pyproject.toml`, `.env.example` |
| Dependencies | `requirements.txt`, `requirements-dev.txt` |

### Service Dependencies

```
LLM Service ──────────────────────┐
    │                             │
    ├──▶ Cost Tracker Service     │
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

1. **Re-read the specification** - answers are usually there
2. **Check the scope document** - feature might be deferred
3. **Review adjacent implementations** - patterns are consistent
4. **Run existing tests** - understand expected behavior
5. **Check imports work** - many issues are import-related

---

---

## Current Project Status

**Phase:** Phase 1 - Foundation Services (In Progress)

- ✅ Project structure created (`src/modules/`, `src/services/`, `src/web/`)
- ✅ Virtual environment set up (Python 3.13.7)
- ✅ Dependencies configured (pyproject.toml, requirements.txt)
- ✅ Comprehensive documentation (21 specification files)
- ✅ Development tools configured (Makefile, black, ruff, mypy, pytest)
- ✅ **S2 Cost Tracker Service** - Complete with simplified PoC implementation
- 🔄 **Next:** S3 Cache Service

**Implementation status:**
- **S2 Cost Tracker**: ✅ Complete (27/27 tests passing)
- **S3 Cache Service**: Not started
- **S4 Vector Store**: Not started
- **S1 LLM Service**: Not started

---

*Last updated: December 9, 2025*
