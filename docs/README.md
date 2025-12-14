# Scout Documentation Index

This directory contains specifications, guides, and documentation for Scout - an intelligent job application system.

## Project Status

**All phases complete.** Scout is a working PoC with 609+ tests passing.

- **Architecture:** Local LLM via Ollama (Qwen 2.5 3B / Gemma 2 2B)
- **Deployment:** Raspberry Pi 5 (16GB) with Ubuntu 24.04

## Directory Structure

```
docs/
├── current_state/    # Current implementation documentation (START HERE)
├── deployment/       # Raspberry Pi deployment guides
├── guides/           # Development guides and scope documents
├── modules/          # Module specifications (M1-M5)
├── services/         # Service specifications (S1-S8)
└── archive/          # Deferred feature specs
```

## Current State Documentation

For **accurate, up-to-date** documentation of the implemented system:

| Document | Description |
|----------|-------------|
| [Overview](current_state/README.md) | Architecture diagram and component summary |
| [Services](current_state/services.md) | S1-S4, S6, S8 implementation details |
| [Modules](current_state/modules.md) | M1-M5 module documentation |
| [Web Interface](current_state/web_interface.md) | FastAPI, templates, static files |
| [API Routes](current_state/api_routes.md) | REST endpoint reference |

## Deployment Guides

| Document | Description |
|----------|-------------|
| [Raspberry Pi 5 Deployment](deployment/Raspberry_Pi_5_Deployment_Guide.md) | Complete deployment guide |
| [User Guide](deployment/User_Guide.md) | End-user documentation |
| [Performance Benchmarks](deployment/Performance_Benchmarks.md) | Pipeline timing data |

## Development Guides

| Document | Description |
|----------|-------------|
| [PoC Scope Document](guides/Scout_PoC_Scope_Document.md) | Authoritative scope reference |
| [Local LLM Transition](guides/Local_LLM_Transition_Guide.md) | Anthropic to Ollama migration |
| [Claude Code Guide](guides/Scout_Claude_Code_Development_Guide.md) | Development workflow |

## Specifications (Historical Reference)

Original specifications used during development. For current implementation, see `current_state/`.

### Modules
- Module 1: Collector - Profile management
- Module 2: Rinser - Job text extraction
- Module 3: Analyzer - Semantic matching
- Module 4: Creator - Content generation
- Module 5: Formatter - PDF generation

### Services
- S1: LLM Service - Ollama integration
- S2: Cost Tracker - Usage metrics
- S3: Cache Service - Memory + file caching
- S4: Vector Store - ChromaDB embeddings
- S6: Pipeline Orchestrator - Module coordination
- S8: Notification Service - In-app notifications

### Deferred (see `archive/`)
- S7: Content Optimizer - Deferred to post-PoC

## Implementation Phases (Complete)

| Phase | Components | Tests |
|-------|------------|-------|
| Phase 1: Foundation | S2, S3, S4, S1 | 180 |
| Phase 2: Modules | M1, M2, M3, M4, M5 | 268 |
| Phase 3: Integration | S6, API, S8, Web | 161 |
| **Total** | **All components** | **609+** |

## Key Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` (project root) | Claude Code context and patterns |
| `LL-LI.md` (project root) | Lessons learned during development |
| `HANDOVER.md` (project root) | Session continuity notes |

---

*Last updated: December 14, 2025*
