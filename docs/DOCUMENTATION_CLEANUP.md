# Documentation Cleanup Recommendations

**Created:** December 14, 2025
**Purpose:** Identify outdated, obsolete, or inconsistent documentation for cleanup

This document flags documentation issues by comparing existing docs against the `docs/current_state/` documentation, which reflects the actual implementation.

---

## Summary

| Category | Count | Action |
|----------|-------|--------|
| **Critical - Wrong Structure** | 4 | Major rewrite or delete |
| **Obsolete - Deferred Feature** | 1 | Delete or archive |
| **Outdated - Needs Refresh** | 3 | Update to match current state |
| **Current - No Action** | ~15 | Keep as-is |

---

## Critical Issues - Wrong Directory Structure

These documents use `app/` directory structure instead of the actual `src/` structure.

### 1. `docs/architecture/Scout PoC - Complete Project Structure & Configuration.md`

**Status:** CRITICAL - OUTDATED
**Last Updated:** October 4, 2025

**Issues:**
- Uses `app/` directory structure (should be `src/`)
- References `app/api/routes/` (actual: `src/web/routes/`)
- References `app/core/` (actual: `src/modules/`)
- References `app/services/` (actual: `src/services/`)
- Shows Poetry configuration (actual: uses venv + pip)
- Shows Docker deployment (actual: systemd service)
- References Anthropic API (actual: Ollama local)
- Shows Redis (not used in PoC)

**Recommendation:** DELETE or archive. Replace with reference to `docs/current_state/` documents.

---

### 2. `docs/guides/Scout_Implementation_Checklist.md`

**Status:** CRITICAL - SEVERELY OUTDATED
**Last Updated:** November 26, 2025

**Issues:**
- Uses `app/` directory structure throughout
- All file paths wrong (e.g., `app/models/cost.py` vs actual `src/services/cost_tracker/models.py`)
- Progress tracking table shows most items as "Not started" (all are COMPLETE)
- References `tests/unit/services/` (actual: `tests/`)
- All verification commands use wrong paths

**Recommendation:** DELETE. This was a planning document for implementation; with all phases complete, it's now obsolete and misleading.

---

### 3. `docs/guides/Scout_PoC_Scope_Document.md`

**Status:** OUTDATED - PARTIALLY UPDATED
**Last Updated:** December 13, 2025 (version 1.1)

**Issues:**
- Appendix A (File Structure) still shows `app/` structure
- Part 6 shows Poetry dependencies (actual: requirements.txt)
- Part 9 (Implementation Order) shows future phases (all complete)
- Pre-Implementation Checklist references Poetry

**Recommendation:** UPDATE Appendix A with correct `src/` structure. The scope decisions and feature tables are still accurate and valuable as historical reference.

---

### 4. `docs/architecture/Raspberry Pi Instructions.md`

**Status:** CRITICAL - OUTDATED
**Last Updated:** October 5, 2025

**Issues:**
- References Anthropic API key requirements
- Shows Docker-based deployment (actual: systemd + venv)
- Wrong project structure (`app/` vs `src/`)
- Different username/hostname (`scout` vs actual `cally`)
- Different OS (Raspberry Pi OS vs actual Ubuntu 24.04)
- No mention of Ollama

**Recommendation:** DELETE. Replaced by `docs/deployment/Raspberry_Pi_5_Deployment_Guide.md` which is current.

---

## Obsolete Documents

### 5. `docs/services/S7 Content Optimizer Service - Claude Code Instructions.md`

**Status:** OBSOLETE - DEFERRED FEATURE
**Last Updated:** October 4, 2025

**Issues:**
- This entire service is explicitly deferred per PoC scope
- The file is 1300+ lines of implementation instructions for a feature that won't be built
- References dependencies not in requirements (spaCy, language-tool-python, etc.)
- Could confuse future developers

**Recommendation:** DELETE or move to an `archive/` or `deferred/` folder.

---

## Outdated Documents - Need Refresh

### 6. `docs/README.md`

**Status:** OUTDATED
**Last Updated:** Unknown

**Issues:**
- Links to non-existent files (e.g., `M1_Collector.md` - actual: `Module 1 Collector - Claude Code Instructions.md`)
- Lists S7 Content Optimizer as active service (deferred)
- Implementation phases shown as future work (all complete)
- No mention of local LLM / Ollama

**Recommendation:** UPDATE to:
- Fix broken links or simplify to reference `docs/current_state/`
- Remove S7 Content Optimizer from active list
- Update phases to show completion status
- Add note about Ollama architecture

---

### 7. `docs/QUICKSTART.md`

**Status:** OUTDATED

**Issues:**
- References `/mnt/project/` path (meaningless in current context)
- References Poetry (actual: venv + pip)
- Commands use wrong paths (`app/` vs `src/`)
- No mention of Ollama setup
- References "Foundation Complete" but setup instructions are for pre-implementation

**Recommendation:** REWRITE as a simple quick start:
1. Clone repo
2. Create venv
3. Install requirements
4. Start Ollama + pull models
5. Run `uvicorn src.web.main:app`

---

### 8. `docs/SPECIFICATIONS.md`

**Status:** PARTIALLY OUTDATED
**Last Updated:** December 13, 2025

**Issues:**
- Still lists S7 Content Optimizer (deferred)
- Some `/mnt/project/` references
- File paths for module specs inconsistent with actual filenames

**Recommendation:** UPDATE to:
- Remove S7 from active list
- Note all phases as complete
- Consider consolidating with `docs/current_state/README.md`

---

## Current Documents - No Action Needed

These documents are current and accurate:

### Deployment Folder (December 2025)
- `docs/deployment/Raspberry_Pi_5_Deployment_Guide.md` - Current
- `docs/deployment/Performance_Benchmarks.md` - Current
- `docs/deployment/User_Guide.md` - Current
- `docs/deployment/Deployment_PreFlight_Verification.md` - Current
- Other deployment docs - Recent, likely current

### Current State Folder (Just Created)
- `docs/current_state/README.md` - Current
- `docs/current_state/services.md` - Current
- `docs/current_state/modules.md` - Current
- `docs/current_state/web_interface.md` - Current
- `docs/current_state/api_routes.md` - Current

### Updated Service Specs
- `docs/services/S1_LLM_Service_-_Claude_Code_Instructions.md` - Updated December 13, 2025 (v3.0)
- Other service specs with recent updates

### Guide Documents
- `docs/guides/Local_LLM_Transition_Guide.md` - Current
- `docs/guides/API_Diagnostics_Guide.md` - Recent

---

## Recommended Actions

### Immediate (Before Thesis Submission)

1. **DELETE** these obsolete/dangerous documents:
   - `docs/architecture/Scout PoC - Complete Project Structure & Configuration.md`
   - `docs/architecture/Raspberry Pi Instructions.md`
   - `docs/guides/Scout_Implementation_Checklist.md`

2. **ARCHIVE** deferred feature docs:
   - Move `docs/services/S7 Content Optimizer Service - Claude Code Instructions.md` to `docs/archive/`

3. **UPDATE** key index documents:
   - `docs/README.md` - Fix links, mark complete
   - `docs/QUICKSTART.md` - Simplify for current architecture

### Optional Cleanup

4. Consolidate specification index:
   - `docs/SPECIFICATIONS.md` could reference `docs/current_state/` for current info
   - Keep original specs as historical reference

5. Standardize spec filenames:
   - Some use spaces, some use underscores
   - Not critical but would improve organization

---

## File Status Summary

| File | Status | Action |
|------|--------|--------|
| `docs/architecture/Scout PoC - Complete Project Structure & Configuration.md` | CRITICAL | DELETE |
| `docs/architecture/Raspberry Pi Instructions.md` | CRITICAL | DELETE |
| `docs/guides/Scout_Implementation_Checklist.md` | CRITICAL | DELETE |
| `docs/services/S7 Content Optimizer Service - Claude Code Instructions.md` | OBSOLETE | ARCHIVE |
| `docs/README.md` | OUTDATED | UPDATE |
| `docs/QUICKSTART.md` | OUTDATED | REWRITE |
| `docs/SPECIFICATIONS.md` | PARTIAL | UPDATE |
| `docs/guides/Scout_PoC_Scope_Document.md` | PARTIAL | UPDATE Appendix A |
| `docs/deployment/*` | CURRENT | KEEP |
| `docs/current_state/*` | CURRENT | KEEP |
| `docs/services/S1_LLM_Service_*` | CURRENT | KEEP |
| `docs/guides/Local_LLM_Transition_Guide.md` | CURRENT | KEEP |

---

*Document created by reviewing all docs against `docs/current_state/` implementation documentation.*
