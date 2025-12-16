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
All Modules    ─────────────────▶ Metrics Tracker (S2)
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
