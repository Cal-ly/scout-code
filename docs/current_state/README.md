# Scout - Current State Documentation

This folder contains documentation describing the **current implementation state** of the Scout project as of December 2025. Use these documents as a reference for understanding the existing codebase before making changes.

## Document Index

| Document | Description |
|----------|-------------|
| [services.md](services.md) | Foundation services (S1-S4, S6, S8) |
| [modules.md](modules.md) | Core processing modules (M1-M5) |
| [database.md](database.md) | SQLite database service and schema |
| [web_interface.md](web_interface.md) | FastAPI web server, templates, static files |
| [api_routes.md](api_routes.md) | REST API endpoints and schemas |

## Architecture Overview

```
                                    ┌─────────────────────────────────────┐
                                    │          Web Interface              │
                                    │  FastAPI + Jinja2 + Static Files   │
                                    └──────────────────┬──────────────────┘
                                                       │
                                    ┌──────────────────▼──────────────────┐
                                    │            API Routes               │
                                    │  /api/apply, /api/status, etc.     │
                                    └──────────────────┬──────────────────┘
                                                       │
┌──────────────────────────────────────────────────────▼───────────────────────────────────────────┐
│                                    Pipeline Orchestrator (S6)                                    │
│                          Sequential: Rinser → Analyzer → Creator → Formatter                     │
└─────────────────┬───────────────────┬───────────────────┬───────────────────┬────────────────────┘
                  │                   │                   │                   │
        ┌─────────▼───────┐  ┌────────▼────────┐  ┌──────▼───────┐  ┌────────▼────────┐
        │   M2: Rinser    │  │   M3: Analyzer  │  │  M4: Creator │  │  M5: Formatter  │
        │  (Job Extract)  │  │    (Matching)   │  │  (Content)   │  │     (PDF)       │
        └────────┬────────┘  └────────┬────────┘  └──────┬───────┘  └─────────────────┘
                 │                    │                  │
                 │           ┌────────▼────────┐        │
                 │           │   M1: Collector │        │
                 │           │    (Profile)    │        │
                 │           └────────┬────────┘        │
                 │                    │                 │
┌────────────────▼────────────────────▼─────────────────▼────────────────────────────┐
│                               Foundation Services                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │ S1: LLM      │  │ S2: Cost     │  │ S3: Cache    │  │ S4: Vector   │            │
│  │   Service    │  │   Tracker    │  │   Service    │  │    Store     │            │
│  │  (Ollama)    │  │              │  │ (L1+L2)      │  │  (ChromaDB)  │            │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘            │
└────────────────────────────────────────────────────────────────────────────────────┘
```

## Implementation Status

| Component | Status | Test Count | Notes |
|-----------|--------|------------|-------|
| **S1 LLM Service** | Complete | 52 | Ollama integration (Qwen 2.5 3B) |
| **S2 Metrics Service** | Complete | ~41 | Performance & reliability tracking |
| **S3 Cache Service** | Complete | 46 | Memory (L1) + File (L2) |
| **S4 Vector Store** | Complete | 55 | ChromaDB + sentence-transformers |
| **S6 Pipeline** | Complete | 52 | Sequential orchestration |
| **S8 Notifications** | Complete | 40 | In-app toast only |
| **Database Service** | Complete | ~45 | SQLite persistence |
| **M1 Collector** | Complete | 49 | Profile management |
| **M2 Rinser** | Complete | 71 | Job extraction via LLM |
| **M3 Analyzer** | Complete | 62 | Semantic matching |
| **M4 Creator** | Complete | 48 | Content generation via LLM |
| **M5 Formatter** | Complete | 38 | PDF generation (xhtml2pdf) |
| **API Routes** | Complete | 43 | Full REST API |
| **Web Interface** | Complete | 26 | All templates done |
| **Profile Service** | Complete | 45 | Profile management (legacy) |

**Total: ~650+ passing tests**

## Deployment

Scout includes a portable deployment system for cross-platform benchmarking:

| Platform | Setup Script | Model | Expected Performance |
|----------|-------------|-------|---------------------|
| Raspberry Pi 5 | `deploy/scripts/setup-rpi.sh` | qwen2.5:3b | ~2 tok/s |
| Windows + NVIDIA | `deploy/scripts/setup-windows.ps1` | qwen2.5:7b | ~40 tok/s |
| Linux + NVIDIA | `deploy/scripts/setup-linux-gpu.sh` | qwen2.5:7b+ | ~50 tok/s |
| CPU-only | `docker-compose.cpu.yml` | qwen2.5:3b | Varies |

See `/deploy/README.md` for detailed setup and benchmarking instructions.

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.12+, FastAPI, Pydantic v2 |
| **LLM** | Ollama (local), Qwen 2.5 3B / Gemma 2 2B |
| **Vector DB** | ChromaDB, sentence-transformers (all-MiniLM-L6-v2) |
| **Caching** | Memory LRU + File (JSON) |
| **PDF** | xhtml2pdf, Jinja2 templates |
| **Frontend** | HTML/CSS/JS, no framework (vanilla JS) |
| **Deployment** | Raspberry Pi 5, systemd service |

## Key Design Decisions

1. **Local LLM Only**: No cloud API fallback (edge deployment focus)
2. **Sequential Pipeline**: No parallelization (PoC simplicity)
3. **Single Profile**: Multi-profile deferred to future version
4. **Polling Updates**: No WebSocket (PoC simplicity)
5. **PDF Only**: DOCX generation deferred
6. **In-App Notifications**: No email/SMS/webhooks

## File Structure

```
src/
├── modules/
│   ├── collector/     # M1: Profile management
│   ├── rinser/        # M2: Job processing
│   ├── analyzer/      # M3: Matching & scoring
│   ├── creator/       # M4: Content generation
│   └── formatter/     # M5: PDF output
├── services/
│   ├── llm_service/   # S1: Ollama wrapper
│   ├── metrics_service/ # S2: Performance tracking
│   ├── cache_service/ # S3: Two-tier cache
│   ├── vector_store/  # S4: ChromaDB wrapper
│   ├── database/      # SQLite persistence
│   ├── pipeline/      # S6: Orchestrator
│   ├── notification/  # S8: Toast notifications
│   └── profile/       # Profile service (legacy)
└── web/
    ├── routes/        # API + page routes
    ├── templates/     # Jinja2 HTML templates
    ├── static/        # CSS, JS assets
    └── main.py        # FastAPI application

deploy/
├── docker-compose.yml     # Main deployment config
├── docker-compose.cpu.yml # CPU-only variant
├── scripts/               # Platform setup scripts
└── benchmark/             # Cross-platform benchmarking
```

---

*Last updated: December 17, 2025*
*Updated: Added Database Service, deployment section, renamed Cost Tracker to Metrics Service*
