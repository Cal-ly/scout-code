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
│  LLM Service (Ollama) • Vector Store • Cache • Metrics Tracker  │
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
| **Total** | **~620** | ✅ |

Run tests: `pytest tests/ -v`

---

*Last updated: December 2025*
