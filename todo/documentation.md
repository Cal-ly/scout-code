# Documentation TODOs

## Overview
Scout has comprehensive documentation across root files, guides, specifications, and deployment docs. This document tracks documentation maintenance tasks.

**Status**: Well-maintained, minor cleanup needed

---

## Documentation Structure Summary

### Critical (Read First)
- `CLAUDE.md` - Primary context for Claude Code
- `LL-LI.md` - 58+ validated patterns from implementation
- `docs/guides/Scout_PoC_Scope_Document.md` - Authoritative scope
- `docs/guides/Local_LLM_Transition_Guide.md` - Ollama architecture

### Implementation
- `docs/guides/Scout_Implementation_Checklist.md`
- `docs/services/S*_*.md` (8 service specs)
- `docs/modules/Module*_*.md` (6 module specs)

### Deployment
- `docs/deployment/Raspberry_Pi_5_Deployment_Guide.md`
- `docs/deployment/Deployment_PreFlight_Verification.md`
- `docs/deployment/User_Guide.md`

### Reference
- `HANDOVER.md`, `REVIEW.md`
- `docs/architecture/*.md`

---

## Outstanding Tasks

### High Priority

- [ ] **Update SPECIFICATIONS.md**: Add references to new profile specs and todo folder
  - **Location**: `docs/SPECIFICATIONS.md`
  - **Issue**: Missing profile_poc_spec.md reference

- [ ] **Mark Historical Docs**: Add "HISTORICAL - Reference Only" header to:
  - `FOUNDATION_COMPLETE.md`
  - `docs/architecture/Raspberry Pi Instructions.md`

### Medium Priority

- [ ] **Consolidate CLAUDE.md**: Two versions exist:
  - Root `/CLAUDE.md` (18K, Dec 13) - PRIMARY
  - `docs/guides/CLAUDE.md` (13K, Dec 9) - SECONDARY
  - **Suggestion**: Add note to guides version pointing to root

- [ ] **File Naming Consistency**: Document naming patterns
  - Modules: Mixed ("Module 1 Collector" vs "Module_2_Rinser")
  - Services: Mixed ("S2 Cost Tracker" vs "S3_Cache_Service")
  - **Impact**: Glob patterns need to account for both
  - **Suggestion**: Add naming note to SPECIFICATIONS.md

- [ ] **Path References**: Some guides reference old paths
  - "app/" should be "src/" in some examples
  - `/mnt/project/` references are for knowledge base
  - **Impact**: Minor, not critical

### Low Priority

- [ ] **README.md Refresh**: Update with post-PoC status
  - **Current**: Basic project overview
  - **Suggestion**: Add screenshot, deployment status

- [ ] **API Documentation**: Consider auto-generating from FastAPI
  - **Note**: `/docs` endpoint exists via FastAPI OpenAPI
  - **Enhancement**: Export as static markdown

---

## Documentation Health Metrics

| Category | Files | Status |
|----------|-------|--------|
| Root Documentation | 8 | Excellent |
| Service Specs | 8 | Complete (S7 deferred) |
| Module Specs | 6 | Complete |
| Deployment Docs | 10 | Very Recent (Dec 14) |
| Guides | 8 | Current |
| Architecture | 2 | Current |

**Overall Score**: 95/100

---

## Key Documents by Purpose

### For New Developers
1. `README.md` - Project overview
2. `CLAUDE.md` - Development context
3. `docs/guides/Scout_Claude_Code_Development_Guide.md`

### For Understanding Architecture
1. `docs/guides/Scout_PoC_Scope_Document.md`
2. `docs/guides/Local_LLM_Transition_Guide.md`
3. `docs/architecture/Scout PoC - Complete Project Structure.md`

### For Deployment
1. `docs/deployment/Raspberry_Pi_5_Deployment_Guide.md`
2. `docs/deployment/Deployment_PreFlight_Verification.md`
3. `docs/deployment/User_Guide.md`

### For Session Continuity
1. `LL-LI.md` - Lessons learned
2. `HANDOVER.md` - Session context
3. `todo/*.md` - Tracked tasks

---

## Deferred Documentation Tasks

- [-] **Video Walkthrough**: Screen recording of workflow
- [-] **Architecture Diagrams**: Visual system design (plantuml)
- [-] **User Manual PDF**: Printable documentation

---

*Last updated: December 14, 2025*
