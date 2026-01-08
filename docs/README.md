# Scout Documentation

**Scout** is an AI-powered job application automation system designed for edge deployment on Raspberry Pi 5. This documentation covers the complete PoC implementation.

---

## Quick Navigation

| Document | Description |
|----------|-------------|
| [QUICKSTART.md](QUICKSTART.md) | Get Scout running in 5 minutes |
| [current_state/](current_state/) | **Current implementation documentation** |
| [deployment/](deployment/) | Raspberry Pi deployment guides |
| [guides/](guides/) | Development and transition guides |

---

## Architecture

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
│  LLM Service (Ollama) • Vector Store • Cache • Metrics Service  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Documentation Structure

```
docs/
├── README.md                 # This file (navigation index)
├── QUICKSTART.md             # Quick setup guide
│
├── current_state/            # CURRENT IMPLEMENTATION (start here)
│   ├── README.md             # Implementation overview
│   ├── api_routes.md         # REST API documentation
│   ├── database.md           # SQLite schema & models
│   ├── modules.md            # M1-M5 module details
│   ├── services.md           # S1-S8 service details
│   └── web_interface.md      # Web layer documentation
│
├── deployment/               # DEPLOYMENT GUIDES
│   ├── Raspberry_Pi_5_Deployment_Guide.md  # Primary deployment guide
│   ├── User_Guide.md                        # End-user instructions
│   └── Performance_Benchmarks.md            # Performance data
│
├── guides/                   # DEVELOPMENT GUIDES
│   ├── Scout_Claude_Code_Development_Guide.md  # RAVE cycle workflow
│   ├── Scout_PoC_Scope_Document.md             # Scope constraints
│   ├── Local_LLM_Transition_Guide.md           # Ollama architecture
│   └── API_Diagnostics_Guide.md                # Troubleshooting
│
├── modules/                  # ORIGINAL SPECS (reference only)
│   └── Module_*_Claude_Code_Instructions.md
│
├── services/                 # ORIGINAL SPECS (reference only)
│   └── S*_*_Claude_Code_Instructions.md
│
├── specifications/           # FEATURE SPECS
│   └── profile_service_spec.md
│
├── test_data/                # Test fixtures
│   └── *.yaml, *.txt
│
└── archive/                  # ARCHIVED DOCUMENTS
    ├── deployment/           # Historical deployment checklists
    ├── tasks/                # Completed work packages
    ├── specifications/       # Superseded specs
    ├── root_tasks/           # Archived root-level task docs
    ├── CLEANUP_PLAN.md       # Completed cleanup plan
    ├── REVIEW.md             # Code review (Dec 2025)
    ├── REVIEW-GUIDE.md       # Review methodology
    └── S7_Content_Optimizer_Service_DEFERRED.md
```

---

## Key Documents by Topic

### Understanding the System
1. [current_state/README.md](current_state/README.md) - Implementation overview
2. [current_state/api_routes.md](current_state/api_routes.md) - REST API reference
3. [current_state/modules.md](current_state/modules.md) - Processing pipeline
4. [current_state/services.md](current_state/services.md) - Foundation services

### Deploying Scout
1. [deployment/Raspberry_Pi_5_Deployment_Guide.md](deployment/Raspberry_Pi_5_Deployment_Guide.md)
2. [deployment/User_Guide.md](deployment/User_Guide.md)
3. [deployment/Performance_Benchmarks.md](deployment/Performance_Benchmarks.md)

### Development
1. [guides/Scout_Claude_Code_Development_Guide.md](guides/Scout_Claude_Code_Development_Guide.md) - RAVE workflow
2. [guides/Scout_PoC_Scope_Document.md](guides/Scout_PoC_Scope_Document.md) - Scope constraints
3. [guides/Local_LLM_Transition_Guide.md](guides/Local_LLM_Transition_Guide.md) - Ollama integration

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12+, FastAPI, Pydantic v2 |
| LLM | Ollama (local), Qwen 2.5 3B / Gemma 2 2B |
| Vector DB | ChromaDB, sentence-transformers |
| Database | SQLite (aiosqlite) |
| PDF Generation | xhtml2pdf, Jinja2 |
| Frontend | Vanilla JS, HTML/CSS |
| Deployment | Raspberry Pi 5, systemd |

---

## Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| Services | ~270 | Passing |
| Modules | ~270 | Passing |
| API Routes | ~50 | Passing |
| Web Interface | ~30 | Passing |
| **Total** | **~650** | **Passing** |

```bash
pytest tests/ -v
```

---

*Last updated: January 2026*
