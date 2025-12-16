# Task: Codebase Refactoring & Documentation Cleanup

## Overview

**Task ID:** SCOUT-REFACTOR-CLEANUP  
**Priority:** High  
**Total Estimated Effort:** 3-4 hours  
**Dependencies:** API Hardening (complete), Tasks A/C/E (complete)

Comprehensive cleanup and documentation consolidation to prepare the Scout codebase for thesis submission. This task is divided into three incremental phases that should be executed sequentially with verification between each.

---

## Objectives

1. **Remove legacy/obsolete files** that create confusion
2. **Consolidate documentation** into a thesis-ready structure
3. **Add architectural documentation** for self-documenting codebase
4. **Ensure consistency** in naming, structure, and patterns

---

## Pre-Flight Checklist

Before starting, verify the environment:

```bash
cd /home/cally/projects/scout-code
source venv/bin/activate

# Verify all tests pass (baseline)
pytest tests/ -q --tb=no
# Expected: 680+ passed

# Check current file count
find src/ -name "*.py" | wc -l
# Note this number for comparison

# Verify git status is clean
git status
```

**IMPORTANT:** Commit current state before starting:
```bash
git add -A
git commit -m "chore: pre-refactoring checkpoint"
```

---

# Phase R1: Legacy Cleanup

**Estimated Time:** 30-45 minutes  
**Goal:** Remove outdated files, clean up repository

## R1.1: Delete Legacy Web Files

### Check for old route files that should have been removed after API hardening:

```bash
# List files in routes directory
ls -la src/web/routes/

# Expected structure (after API hardening):
# src/web/routes/
# ├── __init__.py
# ├── pages.py
# └── api/
#     ├── __init__.py
#     ├── schemas/
#     │   └── *.py
#     └── v1/
#         └── *.py
```

### Delete old schemas file if it exists:

```bash
# Check if old schemas.py exists at web level
if [ -f "src/web/schemas.py" ]; then
    echo "Found legacy schemas.py - checking if safe to delete"
    
    # Check if it's imported anywhere
    grep -r "from src.web.schemas import" src/
    grep -r "from src.web import.*schemas" src/
    
    # If no imports found, delete it
    rm src/web/schemas.py
    echo "Deleted legacy src/web/schemas.py"
fi
```

### Delete any old route files that were moved:

```bash
# These files should have been moved to api/v1/ during API hardening
# Check and delete if they exist at the old location

OLD_ROUTES=(
    "src/web/routes/api.py"
    "src/web/routes/notifications.py"
    "src/web/routes/profile.py"
)

for file in "${OLD_ROUTES[@]}"; do
    if [ -f "$file" ]; then
        echo "Found old route file: $file"
        # Verify it's not imported
        basename=$(basename "$file" .py)
        imports=$(grep -r "from src.web.routes.$basename import" src/ 2>/dev/null || true)
        if [ -z "$imports" ]; then
            rm "$file"
            echo "Deleted: $file"
        else
            echo "WARNING: $file still has imports - manual review needed"
        fi
    fi
done
```

## R1.2: Clean Up Test Output Files

```bash
# Delete temporary test output files from project root
rm -f test_err.txt test_out.txt test_output.txt

# Verify deletion
ls -la *.txt 2>/dev/null || echo "No .txt files in root (good)"
```

## R1.3: Update .gitignore

Add patterns to prevent future commits of temporary files:

**File:** `.gitignore`

Add these lines if not present:

```gitignore
# Test outputs (add to existing .gitignore)
test_*.txt
!tests/test_*.py
!tests/test_*.txt

# Coverage artifacts
.coverage
htmlcov/
coverage.xml

# Pytest cache
.pytest_cache/

# MyPy cache
.mypy_cache/

# Ruff cache
.ruff_cache/

# IDE
.vscode/
.idea/

# OS files
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.temp
*.bak
```

## R1.4: Clean Python Cache Files

```bash
# Remove all __pycache__ directories
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Remove .pyc files
find . -name "*.pyc" -delete 2>/dev/null || true

# Remove .pyo files
find . -name "*.pyo" -delete 2>/dev/null || true

echo "Python cache cleaned"
```

## R1.5: Verify Routes Package Exports

**File:** `src/web/routes/__init__.py`

Verify it only exports the new API router structure:

```python
"""
Routes Package

Exports routers for the FastAPI application.
"""

from src.web.routes.api import router as api_router
from src.web.routes.pages import router as pages_router

__all__ = ["api_router", "pages_router"]
```

If it still exports old routers (like `notifications_router`, `profile_router`), update it.

## R1.6: Verify Main App Uses New Routers

**File:** `src/web/main.py`

Verify the router includes are correct:

```python
# Should have:
from src.web.routes import api_router, pages_router

# ...

app.include_router(api_router)   # /api/v1/*
app.include_router(pages_router) # HTML pages

# Should NOT have individual old routers like:
# app.include_router(router)
# app.include_router(notifications_router)
# app.include_router(profile_router)
```

## R1 Verification

```bash
# Run tests to ensure nothing broke
pytest tests/ -q --tb=short

# Verify the web app starts
timeout 10 uvicorn src.web.main:app --host 0.0.0.0 --port 8000 &
sleep 5
curl -s http://localhost:8000/api/v1/health | python -m json.tool
pkill -f uvicorn

# Check for any import errors
python -c "from src.web.main import app; print('App imports OK')"
python -c "from src.web.routes import api_router, pages_router; print('Routes import OK')"
```

## R1 Commit

```bash
git add -A
git commit -m "chore(cleanup): remove legacy files and update gitignore

- Remove old schemas.py (moved to routes/api/schemas/)
- Remove old route files superseded by api/v1/
- Delete temporary test output files
- Update .gitignore for test outputs and caches
- Clean Python cache files"
```

---

# Phase R2: Documentation Consolidation

**Estimated Time:** 1-2 hours  
**Goal:** Thesis-ready, navigable documentation structure

## R2.1: Execute Documentation Cleanup Recommendations

Reference: `docs/DOCUMENTATION_CLEANUP.md`

### Archive Obsolete Documents

```bash
# Create archive directory if needed
mkdir -p docs/archive

# Move deferred service spec to archive
if [ -f "docs/services/S7_Content_Optimizer_Service_-_Claude_Code_Instructions.md" ]; then
    mv "docs/services/S7_Content_Optimizer_Service_-_Claude_Code_Instructions.md" docs/archive/
    echo "Archived S7 Content Optimizer spec (deferred feature)"
fi

# Check for and archive any other obsolete docs mentioned in DOCUMENTATION_CLEANUP.md
# Note: docs/architecture/ folder was already deleted based on tree output
```

### Delete the cleanup tracking file (it will be complete)

```bash
# After executing recommendations, this file is no longer needed
rm -f docs/DOCUMENTATION_CLEANUP.md
```

## R2.2: Standardize Documentation Filenames

Rename files with spaces to use underscores for consistency:

```bash
cd docs/modules

# Rename files with spaces
for file in *.md; do
    newname=$(echo "$file" | tr ' ' '_')
    if [ "$file" != "$newname" ]; then
        mv "$file" "$newname"
        echo "Renamed: $file -> $newname"
    fi
done

cd ../services

# Same for services
for file in *.md; do
    newname=$(echo "$file" | tr ' ' '_')
    if [ "$file" != "$newname" ]; then
        mv "$file" "$newname"
        echo "Renamed: $file -> $newname"
    fi
done

cd ../..
```

## R2.3: Create Consolidated Documentation Index

**File:** `docs/README.md`

Replace the entire file with:

```markdown
# Scout Documentation

**Scout** is an AI-powered job application automation system designed for edge deployment on Raspberry Pi 5. This documentation covers the complete implementation as of December 2025.

---

## Quick Navigation

| Document | Description |
|----------|-------------|
| [QUICKSTART.md](QUICKSTART.md) | Get Scout running in 5 minutes |
| [current_state/](current_state/) | **Current implementation documentation** |
| [deployment/](deployment/) | Raspberry Pi deployment guides |
| [guides/](guides/) | Development and transition guides |

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web Interface                            │
│                    FastAPI + Jinja2 Templates                   │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────┐
│                      REST API (/api/v1/)                        │
│   jobs • profile • skills • metrics • diagnostics • logs        │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────┐
│                    Pipeline Orchestrator                        │
│            Rinser → Analyzer → Creator → Formatter              │
└───────┬─────────────┬─────────────┬─────────────┬───────────────┘
        │             │             │             │
   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
   │ Rinser  │   │Analyzer │   │ Creator │   │Formatter│
   │  (M2)   │   │  (M3)   │   │  (M4)   │   │  (M5)   │
   └────┬────┘   └────┬────┘   └────┬────┘   └─────────┘
        │             │             │
        │        ┌────▼────┐        │
        │        │Collector│        │
        │        │  (M1)   │        │
        │        └────┬────┘        │
        │             │             │
┌───────▼─────────────▼─────────────▼─────────────────────────────┐
│                    Foundation Services                          │
│  LLM Service (Ollama) • Vector Store • Cache • Cost Tracker    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Documentation Structure

```
docs/
├── README.md                 # This file
├── QUICKSTART.md             # Quick setup guide
├── SPECIFICATIONS.md         # Original specifications index
│
├── current_state/            # ⭐ CURRENT IMPLEMENTATION
│   ├── README.md             # Implementation overview
│   ├── api_routes.md         # REST API documentation
│   ├── modules.md            # M1-M5 module details
│   ├── services.md           # S1-S8 service details
│   └── web_interface.md      # Web layer documentation
│
├── deployment/               # Deployment documentation
│   ├── Raspberry_Pi_5_Deployment_Guide.md
│   ├── Performance_Benchmarks.md
│   └── User_Guide.md
│
├── guides/                   # Development guides
│   ├── Local_LLM_Transition_Guide.md
│   ├── API_Diagnostics_Guide.md
│   ├── Scout_PoC_Scope_Document.md
│   └── Scout_Claude_Code_Development_Guide.md
│
├── modules/                  # Original module specifications
│   └── Module_*_Claude_Code_Instructions.md
│
├── services/                 # Original service specifications
│   └── S*_*_Claude_Code_Instructions.md
│
├── specifications/           # Feature specifications
│   └── profile_poc_spec*.md
│
├── tasks/                    # Claude Code task specifications
│   └── TASK-*.md
│
├── test_data/                # Test fixtures and sample data
│   └── *.yaml, *.txt
│
└── archive/                  # Deferred/obsolete documents
    └── S7_Content_Optimizer_Service_DEFERRED.md
```

---

## Key Documents by Topic

### Understanding the Current System
1. Start with [current_state/README.md](current_state/README.md)
2. Review [current_state/api_routes.md](current_state/api_routes.md) for API reference
3. See [current_state/modules.md](current_state/modules.md) for processing pipeline

### Deploying Scout
1. [deployment/Raspberry_Pi_5_Deployment_Guide.md](deployment/Raspberry_Pi_5_Deployment_Guide.md)
2. [deployment/User_Guide.md](deployment/User_Guide.md)
3. [deployment/Performance_Benchmarks.md](deployment/Performance_Benchmarks.md)

### Development Reference
1. [guides/Scout_Claude_Code_Development_Guide.md](guides/Scout_Claude_Code_Development_Guide.md)
2. [guides/Local_LLM_Transition_Guide.md](guides/Local_LLM_Transition_Guide.md)
3. Original specs in `modules/` and `services/` folders

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12+, FastAPI, Pydantic v2 |
| LLM | Ollama (local), Qwen 2.5 3B / Gemma 2 2B |
| Vector DB | ChromaDB, sentence-transformers |
| PDF Generation | xhtml2pdf, Jinja2 |
| Frontend | Vanilla JS, HTML/CSS (no framework) |
| Deployment | Raspberry Pi 5, Ubuntu 24.04, systemd |

---

## Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| Services (S1-S8) | ~270 | ✅ Passing |
| Modules (M1-M5) | ~270 | ✅ Passing |
| API Routes | ~50 | ✅ Passing |
| Web Interface | ~30 | ✅ Passing |
| Skill Aliases | ~35 | ✅ Passing |
| Profile Assessment | ~30 | ✅ Passing |
| **Total** | **~685** | ✅ |

Run tests: `pytest tests/ -v`

---

*Last updated: December 2025*
```

## R2.4: Update QUICKSTART.md

**File:** `docs/QUICKSTART.md`

Replace with accurate, current setup instructions:

```markdown
# Scout Quick Start Guide

Get Scout running locally in 5 minutes.

---

## Prerequisites

- Python 3.11 or 3.12
- [Ollama](https://ollama.ai/) installed and running
- 8GB+ RAM recommended (16GB for comfortable operation)

---

## Setup Steps

### 1. Clone and Setup Virtual Environment

```bash
git clone https://github.com/yourusername/scout-code.git
cd scout-code

# Create virtual environment
python -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Ollama Models

```bash
# Ensure Ollama is running
ollama serve &  # or start Ollama app

# Pull required models
ollama pull qwen2.5:3b    # Primary model (~2GB)
ollama pull gemma2:2b     # Fallback model (~1.5GB)

# Verify models
ollama list
```

### 4. Create Your Profile

```bash
# Copy example profile
cp docs/test_data/my_test_profile.yaml data/profile.yaml

# Edit with your information
nano data/profile.yaml  # or your preferred editor
```

### 5. Start Scout

```bash
uvicorn src.web.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Access the Interface

Open your browser to: **http://localhost:8000**

---

## Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/api/v1/health

# Expected response:
# {"status": "healthy", "version": "0.1.0", "services": {...}}

# Run quick diagnostics
curl http://localhost:8000/api/v1/diagnostics
```

---

## Quick Test

1. Navigate to http://localhost:8000
2. Paste a job posting into the text area
3. Click "Analyze" for quick compatibility score
4. Click "Generate Application" for full CV + cover letter

---

## Troubleshooting

### Ollama Not Connected
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if needed
ollama serve
```

### Model Not Found
```bash
# List available models
ollama list

# Pull missing model
ollama pull qwen2.5:3b
```

### Import Errors
```bash
# Ensure you're in the virtual environment
which python  # Should show venv path

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## Next Steps

- **Customize Profile**: Edit `data/profile.yaml` with your details
- **API Reference**: See `docs/current_state/api_routes.md`
- **Deployment**: See `docs/deployment/Raspberry_Pi_5_Deployment_Guide.md`

---

*For detailed documentation, see [docs/README.md](README.md)*
```

## R2.5: Update SPECIFICATIONS.md

**File:** `docs/SPECIFICATIONS.md`

Update to reflect completed status and point to current state:

```markdown
# Scout Specifications Index

This document indexes the original specification documents used during Scout development. For current implementation details, see [current_state/](current_state/).

---

## Implementation Status: ✅ COMPLETE

All planned PoC features have been implemented and tested as of December 2025.

---

## Specification Documents

### Foundation Services

| Service | Spec Document | Status |
|---------|---------------|--------|
| S1 LLM Service | [S1_LLM_Service_-_Claude_Code_Instructions.md](services/S1_LLM_Service_-_Claude_Code_Instructions.md) | ✅ Complete (Ollama) |
| S2 Cost Tracker | [S2_Cost_Tracker_Service_-_Claude_Code_Instructions.md](services/S2_Cost_Tracker_Service_-_Claude_Code_Instructions.md) | ✅ Complete |
| S3 Cache Service | [S3_Cache_Service_-_Claude_Code_Instructions.md](services/S3_Cache_Service_-_Claude_Code_Instructions.md) | ✅ Complete |
| S4 Vector Store | [S4_Vector_Store_Service_-_Claude_Code_Instructions.md](services/S4_Vector_Store_Service_-_Claude_Code_Instructions.md) | ✅ Complete |
| S6 Pipeline | [S6_Pipeline_Orchestrator_-_Claude_Code_Instructions.md](services/S6_Pipeline_Orchestrator_-_Claude_Code_Instructions.md) | ✅ Complete |
| S7 Content Optimizer | [DEFERRED](archive/S7_Content_Optimizer_Service_DEFERRED.md) | ⏸️ Deferred |
| S8 Notifications | [S8_Notification_Service_-_Claude_Code_Instructions.md](services/S8_Notification_Service_-_Claude_Code_Instructions.md) | ✅ Complete |

### Core Modules

| Module | Spec Document | Status |
|--------|---------------|--------|
| M1 Collector | [Module_1_Collector_-_Claude_Code_Instructions.md](modules/Module_1_Collector_-_Claude_Code_Instructions.md) | ✅ Complete |
| M2 Rinser | [Module_2_Rinser_-_Claude_Code_Instructions.md](modules/Module_2_Rinser_-_Claude_Code_Instructions.md) | ✅ Complete |
| M3 Analyzer | [Module_3_Analyzer_-_Claude_Code_Instructions.md](modules/Module_3_Analyzer_-_Claude_Code_Instructions.md) | ✅ Complete |
| M4 Creator | [Module_4_Creator_-_Claude_Code_Instructions.md](modules/Module_4_Creator_-_Claude_Code_Instructions.md) | ✅ Complete |
| M5 Formatter | [Module_5_Formatter_-_Claude_Code_Instructions.md](modules/Module_5_Formatter_-_Claude_Code_Instructions.md) | ✅ Complete |

### Integration

| Component | Spec Document | Status |
|-----------|---------------|--------|
| API Routes | [S5_API_Routes_-_Claude_Code_Instructions.md](services/S5_API_Routes_-_Claude_Code_Instructions.md) | ✅ Complete |
| Web Interface | [Web_Interface_-_Claude_Code_Instructions.md](modules/Web_Interface_-_Claude_Code_Instructions.md) | ✅ Complete |

---

## PoC Scope Reference

See [guides/Scout_PoC_Scope_Document.md](guides/Scout_PoC_Scope_Document.md) for:
- Feature decisions (included vs deferred)
- Simplification choices
- Architecture constraints

---

## Current Implementation

For **what was actually built** (vs what was specified), see:

- [current_state/services.md](current_state/services.md) - Service implementations
- [current_state/modules.md](current_state/modules.md) - Module implementations  
- [current_state/api_routes.md](current_state/api_routes.md) - API reference
- [current_state/web_interface.md](current_state/web_interface.md) - Web layer

---

*Original specifications written October-November 2025*  
*Implementation completed December 2025*
```

## R2.6: Update current_state/api_routes.md

Replace with the uploaded API documentation (the user already has this file - just verify it's in place):

```bash
# Verify the api_routes.md file exists and is current
ls -la docs/current_state/api_routes.md
head -50 docs/current_state/api_routes.md
```

## R2 Verification

```bash
# Verify documentation structure
find docs/ -name "*.md" | head -30

# Check for broken internal links (basic check)
grep -r "\](.*\.md)" docs/ | grep -v node_modules | head -20

# Verify no references to deleted files
grep -r "schemas.py" docs/ || echo "No references to old schemas.py"
grep -r "S7.*Content" docs/ --include="*.md" | grep -v archive || echo "S7 references cleaned"
```

## R2 Commit

```bash
git add -A
git commit -m "docs: consolidate and update documentation for thesis

- Standardize filenames (spaces → underscores)
- Archive deferred S7 Content Optimizer spec
- Update docs/README.md with navigation structure
- Rewrite QUICKSTART.md with accurate setup steps
- Update SPECIFICATIONS.md to reflect completion status
- Remove DOCUMENTATION_CLEANUP.md (recommendations executed)"
```

---

# Phase R3: Code Documentation

**Estimated Time:** 1-2 hours  
**Goal:** Self-documenting codebase with architectural README files

## R3.1: Create Source Directory README

**File:** `src/README.md`

```markdown
# Scout Source Code

This directory contains the complete Scout implementation.

## Directory Structure

```
src/
├── modules/          # Core processing modules (M1-M5)
├── services/         # Foundation services (S1-S8)
├── templates/        # PDF generation templates
├── web/              # FastAPI web application
└── __init__.py
```

## Architecture Overview

### Data Flow

```
Job Posting (text)
       │
       ▼
┌──────────────┐     ┌──────────────┐
│   Rinser     │────▶│   Analyzer   │
│     (M2)     │     │     (M3)     │
│ Extract info │     │ Match skills │
└──────────────┘     └──────┬───────┘
                            │
                     ┌──────▼───────┐
                     │   Collector  │
                     │     (M1)     │
                     │ User Profile │
                     └──────────────┘
                            │
       ┌────────────────────┴────────────────────┐
       │                                         │
       ▼                                         ▼
┌──────────────┐                         ┌──────────────┐
│   Creator    │                         │  Formatter   │
│     (M4)     │                         │     (M5)     │
│ Gen content  │────────────────────────▶│  Create PDF  │
└──────────────┘                         └──────────────┘
                                                │
                                                ▼
                                    CV + Cover Letter (PDF)
```

### Service Dependencies

```
Modules                          Services
───────                          ────────
Rinser (M2)    ─────────────────▶ LLM Service (S1)
Analyzer (M3)  ─────────────────▶ Vector Store (S4)
Creator (M4)   ─────────────────▶ LLM Service (S1)
Collector (M1) ─────────────────▶ Vector Store (S4)
                                  Cache Service (S3)
All Modules    ─────────────────▶ Cost Tracker (S2)
```

## Key Files

| File | Purpose |
|------|---------|
| `web/main.py` | FastAPI application entry point |
| `services/pipeline/pipeline.py` | Pipeline orchestrator |
| `modules/*/models.py` | Pydantic data models |
| `modules/*/*.py` | Core business logic |

## Import Patterns

```python
# Import a service
from src.services.llm_service import get_llm_service

# Import a module
from src.modules.collector import get_collector, UserProfile

# Import models
from src.modules.analyzer.models import AnalysisResult
```

---

*See individual directory README files for detailed documentation.*
```

## R3.2: Create Modules README

**File:** `src/modules/README.md`

```markdown
# Scout Modules

Core processing modules that implement the job application pipeline.

## Module Overview

| Module | Purpose | Key Class | LLM? |
|--------|---------|-----------|------|
| **M1 Collector** | User profile management | `Collector` | No |
| **M2 Rinser** | Job posting extraction | `Rinser` | Yes |
| **M3 Analyzer** | Profile-job matching | `Analyzer` | Yes |
| **M4 Creator** | Content generation | `Creator` | Yes |
| **M5 Formatter** | PDF generation | `Formatter` | No |

## Pipeline Flow

```
                    ┌─────────────────────────────────────────┐
                    │         Pipeline Orchestrator           │
                    │   (src/services/pipeline/pipeline.py)   │
                    └─────────────────────────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
        ▼                              ▼                              ▼
┌───────────────┐              ┌───────────────┐              ┌───────────────┐
│    Rinser     │              │   Collector   │              │   Analyzer    │
│ ┌───────────┐ │              │ ┌───────────┐ │              │ ┌───────────┐ │
│ │process_job│─┼──────────────┼▶│get_profile│ │◀─────────────┼─│  analyze  │ │
│ └───────────┘ │              │ └───────────┘ │              │ └───────────┘ │
│               │              │               │              │               │
│ Input:        │              │ Input:        │              │ Input:        │
│  Raw job text │              │  YAML file    │              │  ProcessedJob │
│               │              │               │              │  UserProfile  │
│ Output:       │              │ Output:       │              │               │
│  ProcessedJob │              │  UserProfile  │              │ Output:       │
└───────────────┘              └───────────────┘              │  AnalysisResult│
        │                                                     └───────────────┘
        │                                                             │
        │                              ┌──────────────────────────────┘
        │                              │
        ▼                              ▼
┌───────────────┐              ┌───────────────┐
│    Creator    │              │   Formatter   │
│ ┌───────────┐ │              │ ┌───────────┐ │
│ │create_    │ │              │ │format_    │ │
│ │content    │─┼─────────────▶│ │documents  │ │
│ └───────────┘ │              │ └───────────┘ │
│               │              │               │
│ Input:        │              │ Input:        │
│  UserProfile  │              │  CVContent    │
│  AnalysisResult              │  CoverLetter  │
│               │              │               │
│ Output:       │              │ Output:       │
│  CreatedContent              │  PDF files    │
└───────────────┘              └───────────────┘
```

## Module Structure

Each module follows the same pattern:

```
module_name/
├── __init__.py       # Exports (get_module, Module, models)
├── models.py         # Pydantic data models
├── exceptions.py     # Module-specific exceptions
├── prompts.py        # LLM prompts (if applicable)
└── <module>.py       # Main implementation
```

## Usage Examples

### Get User Profile
```python
from src.modules.collector import get_collector

collector = await get_collector()
await collector.load_profile(Path("data/profile.yaml"))
profile = collector.get_profile()
```

### Process Job Posting
```python
from src.modules.rinser import get_rinser

rinser = await get_rinser()
processed_job = await rinser.process_job(raw_job_text)
print(f"Title: {processed_job.title}")
print(f"Company: {processed_job.company.name}")
```

### Analyze Compatibility
```python
from src.modules.analyzer import get_analyzer

analyzer = await get_analyzer()
result = await analyzer.analyze(processed_job)
print(f"Score: {result.compatibility.overall}%")
```

### Generate Content
```python
from src.modules.creator import get_creator

creator = await get_creator()
content = await creator.create_content(profile, analysis_result)
```

### Create PDFs
```python
from src.modules.formatter import get_formatter

formatter = await get_formatter()
docs = await formatter.format_documents(
    cv_content=content.cv,
    cover_letter=content.cover_letter,
    output_dir=Path("outputs/")
)
```

## Key Models

### UserProfile (M1)
```python
class UserProfile(BaseModel):
    full_name: str
    email: str
    title: str
    skills: list[Skill]
    experiences: list[Experience]
    education: list[Education]
    certifications: list[Certification]
```

### ProcessedJob (M2)
```python
class ProcessedJob(BaseModel):
    title: str
    company: Company
    requirements: list[Requirement]
    responsibilities: list[str]
    benefits: list[str]
```

### AnalysisResult (M3)
```python
class AnalysisResult(BaseModel):
    compatibility: CompatibilityScore
    skill_matches: list[SkillMatch]
    gaps: list[SkillGap]
    strategy: ApplicationStrategy
```

---

*For full model definitions, see each module's `models.py` file.*
```

## R3.3: Create Services README

**File:** `src/services/README.md`

```markdown
# Scout Services

Foundation services providing shared functionality to modules.

## Service Overview

| Service | Purpose | Singleton | Async Init |
|---------|---------|-----------|------------|
| **S1 LLM Service** | Local LLM inference (Ollama) | Yes | Yes |
| **S2 Cost Tracker** | Usage tracking & budgets | Yes | Yes |
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
│ Cost Tracker  │      │ Notification  │
│     (S2)      │      │     (S8)      │
│               │      │               │
│ Token counting│      │ Toast alerts  │
│ Budget limits │      │               │
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
```

## R3.4: Create Web Layer README

**File:** `src/web/README.md`

```markdown
# Scout Web Layer

FastAPI-based web application providing REST API and HTML interface.

## Directory Structure

```
src/web/
├── main.py              # FastAPI application entry point
├── dependencies.py      # Dependency injection (JobStore, etc.)
├── log_handler.py       # In-memory log storage for web UI
├── routes/
│   ├── __init__.py      # Router exports
│   ├── pages.py         # HTML page routes
│   └── api/
│       ├── __init__.py  # API router aggregation
│       ├── schemas/     # Pydantic request/response models
│       │   ├── common.py
│       │   ├── jobs.py
│       │   ├── profile.py
│       │   └── metrics.py
│       └── v1/          # API v1 endpoints
│           ├── system.py       # /health, /info
│           ├── jobs.py         # /jobs/*
│           ├── skills.py       # /skills/*
│           ├── profile.py      # /profile/*
│           ├── notifications.py
│           ├── logs.py
│           ├── metrics.py
│           └── diagnostics.py
├── templates/           # Jinja2 HTML templates
│   ├── index.html
│   ├── profile_editor.html
│   ├── applications.html
│   ├── logs.html
│   ├── metrics.html
│   └── partials/
│       └── navbar.html
└── static/
    ├── css/
    │   ├── common.css
    │   └── profile-editor.css
    └── js/
        ├── common.js
        └── profile-editor.js
```

## API Structure

```
/api/v1/
├── /health              # Health check
├── /info                # App info
├── /jobs/
│   ├── POST /apply      # Start pipeline
│   ├── POST /quick-score # Quick compatibility
│   ├── GET /            # List jobs
│   ├── GET /{id}        # Job status
│   └── GET /{id}/download/{type}  # Download PDF
├── /skills/
│   ├── GET /aliases     # All aliases
│   ├── POST /normalize  # Normalize names
│   ├── POST /expand     # Expand to aliases
│   └── GET /search      # Semantic search
├── /profile/
│   ├── GET /status      # Profile status
│   ├── GET /assessment  # Completeness score
│   ├── GET /editor-data # Form editor data
│   ├── POST /editor-save # Save from form
│   └── POST /export-yaml # Download YAML
├── /notifications/      # Toast notifications
├── /logs/               # Application logs
├── /metrics/            # Performance metrics
└── /diagnostics/        # Component health
```

## Page Routes

| Route | Template | Description |
|-------|----------|-------------|
| `/` | `index.html` | Dashboard |
| `/profile/edit` | `profile_editor.html` | Form-based editor |
| `/applications` | `applications.html` | Job applications list |
| `/logs` | `logs.html` | Log viewer |
| `/metrics` | `metrics.html` | Performance dashboard |

## Running the Server

```bash
# Development (with auto-reload)
uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn src.web.main:app --host 0.0.0.0 --port 8000 --workers 1
```

## API Documentation

FastAPI auto-generates documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

## Key Patterns

### Background Tasks for Long Operations
```python
@router.post("/apply")
async def apply(
    request: ApplyRequest,
    background_tasks: BackgroundTasks,
):
    job_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(execute_pipeline, job_id, request)
    return {"job_id": job_id, "status": "running"}
```

### Dependency Injection
```python
from src.web.dependencies import get_orchestrator

@router.get("/diagnostics")
async def diagnostics(
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator)
):
    # Use orchestrator...
```

### Error Handling
```python
from src.web.routes.api.schemas import ErrorResponse

@router.get("/{job_id}", responses={404: {"model": ErrorResponse}})
async def get_job(job_id: str):
    if not found:
        raise HTTPException(status_code=404, detail="Job not found")
```

---

*For full API documentation, see `docs/current_state/api_routes.md`.*
```

## R3.5: Enhance Module __init__.py Files

Update each module's `__init__.py` with better docstrings:

### Example: `src/modules/collector/__init__.py`

```python
"""
M1 Collector Module - User Profile Management

The Collector module handles user profile loading, validation, indexing,
and semantic search for job matching.

Key Features:
- YAML profile loading with Pydantic validation
- Skill alias normalization (Task A enhancement)
- Profile completeness assessment (Task C enhancement)
- Semantic search via ChromaDB embeddings

Usage:
    from src.modules.collector import get_collector, UserProfile

    # Get singleton instance
    collector = await get_collector()
    
    # Load and index profile
    await collector.load_profile(Path("data/profile.yaml"))
    await collector.index_profile()
    
    # Get profile data
    profile = collector.get_profile()
    
    # Search skills semantically
    matches = await collector.search_skills("Python programming")
    
    # Assess completeness
    assessment = collector.assess_profile_completeness()

Classes:
    Collector: Main profile management class
    UserProfile: User profile data model
    Skill, Experience, Education, Certification: Profile components
    ProfileAssessment: Completeness assessment result

Functions:
    get_collector(): Get singleton Collector instance
    normalize_skill_name(): Normalize skill to canonical form
    expand_skill_query(): Get all aliases for a skill
    assess_profile(): Assess profile completeness
"""

# ... existing imports and exports ...
```

Apply similar enhancements to other module `__init__.py` files.

## R3.6: Update Root CLAUDE.md

**File:** `CLAUDE.md`

Add a section pointing to the new README files:

```markdown
## Code Documentation

The source code includes README files for navigation:

- `src/README.md` - Source overview and architecture
- `src/modules/README.md` - Module documentation with flow diagrams
- `src/services/README.md` - Service documentation with usage examples
- `src/web/README.md` - Web layer and API structure

For full documentation, see `docs/README.md`.
```

## R3 Verification

```bash
# Verify all README files exist
ls -la src/README.md src/modules/README.md src/services/README.md src/web/README.md

# Verify imports still work
python -c "from src.modules.collector import get_collector; print('Collector OK')"
python -c "from src.services.llm_service import get_llm_service; print('LLM OK')"
python -c "from src.web.main import app; print('Web OK')"

# Run full test suite
pytest tests/ -q --tb=no

# Verify no syntax errors in new files
python -m py_compile src/README.md 2>/dev/null || echo "README.md is not Python (expected)"
```

## R3 Commit

```bash
git add -A
git commit -m "docs(code): add architectural README files throughout codebase

- Add src/README.md with architecture overview
- Add src/modules/README.md with pipeline flow diagrams
- Add src/services/README.md with service documentation
- Add src/web/README.md with API structure
- Enhance module __init__.py docstrings
- Update CLAUDE.md with documentation pointers

Self-documenting codebase for thesis reference."
```

---

# Final Verification

After completing all three phases:

```bash
cd /home/cally/projects/scout-code
source venv/bin/activate

# 1. Run full test suite
pytest tests/ -v --tb=short
# Expected: 680+ tests passing

# 2. Verify web app starts
uvicorn src.web.main:app --host 0.0.0.0 --port 8000 &
sleep 5
curl -s http://localhost:8000/api/v1/health | python -m json.tool
curl -s http://localhost:8000/api/v1/info | python -m json.tool
pkill -f uvicorn

# 3. Check documentation structure
find docs/ -name "*.md" | wc -l
ls -la src/README.md src/*/README.md

# 4. Verify no import errors
python -c "
from src.web.main import app
from src.modules.collector import get_collector
from src.modules.rinser import get_rinser
from src.modules.analyzer import get_analyzer
from src.modules.creator import get_creator
from src.modules.formatter import get_formatter
from src.services.llm_service import get_llm_service
from src.services.pipeline import get_pipeline_orchestrator
print('All imports successful!')
"

# 5. Final git status
git log --oneline -5
git status
```

---

# Summary

| Phase | Duration | Key Outcomes |
|-------|----------|--------------|
| **R1: Legacy Cleanup** | 30-45 min | Removed obsolete files, cleaned caches |
| **R2: Doc Consolidation** | 1-2 hours | Thesis-ready documentation structure |
| **R3: Code Documentation** | 1-2 hours | Self-documenting codebase with READMEs |

## Files Created

```
src/README.md
src/modules/README.md
src/services/README.md
src/web/README.md
```

## Files Modified

```
docs/README.md
docs/QUICKSTART.md
docs/SPECIFICATIONS.md
CLAUDE.md
.gitignore
src/modules/collector/__init__.py (and other modules)
```

## Files Deleted

```
src/web/schemas.py (if existed)
src/web/routes/api.py (if existed - old location)
src/web/routes/notifications.py (if existed - old location)
src/web/routes/profile.py (if existed - old location)
test_*.txt
docs/DOCUMENTATION_CLEANUP.md
```

## Files Archived

```
docs/archive/S7_Content_Optimizer_Service_DEFERRED.md
```

---

## Environment

- SSH: `ssh cally@192.168.1.21`
- Project: `/home/cally/projects/scout-code`
- Venv: `source venv/bin/activate`
- Test: `pytest tests/ -v`
