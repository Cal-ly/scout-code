# Documentation TODOs

## Overview
Scout has comprehensive documentation that has been cleaned up and consolidated. This document tracks remaining documentation tasks.

**Status**: Cleanup completed January 2026

---

## Documentation Structure (Post-Cleanup)

### Critical (Read First)
- `CLAUDE.md` - Primary context for Claude Code
- `LL-LI.md` - 58+ validated patterns from implementation
- `docs/guides/Scout_PoC_Scope_Document.md` - Authoritative scope
- `docs/guides/Local_LLM_Transition_Guide.md` - Ollama architecture

### Current Implementation
- `docs/current_state/` - **Primary implementation reference**
  - `README.md` - Overview
  - `api_routes.md` - REST API
  - `services.md` - S1-S8 services
  - `modules.md` - M1-M5 modules
  - `database.md` - SQLite schema
  - `web_interface.md` - Web layer

### Deployment
- `docs/deployment/Raspberry_Pi_5_Deployment_Guide.md` - Primary guide
- `docs/deployment/User_Guide.md` - End-user docs
- `docs/deployment/Performance_Benchmarks.md` - Performance data

### Development Guides
- `docs/guides/Scout_Claude_Code_Development_Guide.md` - RAVE workflow
- `docs/guides/Scout_PoC_Scope_Document.md` - Scope constraints
- `docs/guides/Local_LLM_Transition_Guide.md` - Ollama integration

### Archives
- `docs/archive/deployment/` - Historical deployment checklists
- `docs/archive/tasks/` - Completed work packages (WP1-WP5)
- `docs/archive/specifications/` - Superseded specs

---

## Completed Cleanup Tasks (January 2026)

- [x] **Root README.md Updated**: Now reflects Ollama/local LLM stack
- [x] **Deployment Docs Consolidated**: 8 files archived, 3 kept
- [x] **Task Docs Archived**: WP1-WP5 moved to archive
- [x] **S2 Service Doc Updated**: Added redirect to current Metrics Service
- [x] **Spec Files Cleaned**: Duplicates removed, profile spec renamed
- [x] **docs/README.md Updated**: Reflects new structure

---

## Remaining Tasks

### Low Priority

- [ ] **API Documentation**: Consider auto-generating from FastAPI
  - **Note**: `/docs` endpoint exists via FastAPI OpenAPI
  - **Enhancement**: Export as static markdown

- [ ] **Path References**: Some original specs reference old paths
  - "app/" should be "src/" in some examples
  - **Impact**: Minor - original specs are reference only

---

## Documentation Health

| Category | Files | Status |
|----------|-------|--------|
| Root Documentation | 6 | Current |
| Current State Docs | 6 | Current |
| Deployment Docs | 3 | Current |
| Development Guides | 4 | Current |
| Original Specs | 14 | Reference only |
| Archives | 16 | Historical |

---

## Key Documents by Purpose

### For New Developers
1. `README.md` - Project overview
2. `CLAUDE.md` - Development context
3. `docs/current_state/README.md` - What's implemented

### For Understanding the System
1. `docs/current_state/api_routes.md` - API reference
2. `docs/current_state/services.md` - Service implementations
3. `docs/current_state/modules.md` - Processing pipeline

### For Deployment
1. `docs/deployment/Raspberry_Pi_5_Deployment_Guide.md`
2. `docs/deployment/User_Guide.md`
3. `docs/deployment/Performance_Benchmarks.md`

---

*Last updated: January 2026*
