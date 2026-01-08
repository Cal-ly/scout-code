# Documentation Cleanup & Consolidation Plan

**Date**: January 2026
**Purpose**: Clean up and consolidate documentation for a presentable, manageable codebase

---

## Summary of Issues Found

### High Priority
1. **Root README.md is outdated** - References Anthropic Claude API, Redis, WeasyPrint (removed dependencies)
2. **S2 Service naming mismatch** - File says "Cost Tracker" but code uses "Metrics Service"
3. **Multiple overlapping deployment docs** - 3 handover files, 3+ checklist files

### Medium Priority
4. **Duplicate specification files** - `profile_poc_spec.md` vs `profile_poc_spec_expand.md`
5. **Historical task documents** - `docs/tasks/` contains completed work packages
6. **Outdated todo/ tracking** - Some items may be stale

### Low Priority
7. **Original spec docs** - `docs/modules/` and `docs/services/` are implementation specs (completed)
8. **Navigation updates needed** - docs/README.md structure listing

---

## Cleanup Actions

### 1. Update Root README.md
**File**: `/README.md`
**Changes**:
- Change "Claude 3.5 Haiku" → "Ollama (Qwen 2.5 3B / Gemma 2 2B)"
- Remove Redis reference (use file-based cache)
- Change "WeasyPrint, python-docx" → "xhtml2pdf"
- Change "Cost Tracker" → "Metrics Service"
- Update status to reflect completed PoC
- Update technology stack section

### 2. Rename S2 Service Documentation
**File**: `docs/services/S2_Cost_Tracker_Service_-_Claude_Code_Instructions.md`
**Action**: Rename to `S2_Metrics_Service_-_Claude_Code_Instructions.md`
**Additional**: Add header note that this is the original spec (implementation in current_state/)

### 3. Consolidate Deployment Documentation
**Current files** (11 files in docs/deployment/):
- `Raspberry_Pi_5_Deployment_Guide.md` - KEEP (primary guide)
- `User_Guide.md` - KEEP (end-user guide)
- `Performance_Benchmarks.md` - KEEP (reference data)
- `Deployment_PreFlight_Checklist.md` - ARCHIVE
- `Deployment_PreFlight_Verification.md` - ARCHIVE
- `Deployment_Execution_Checklist.md` - ARCHIVE
- `PreFlight_QuickWins_Status.md` - ARCHIVE
- `Verification_Results_Summary.md` - ARCHIVE
- `HANDOVER_PI5_DEPLOYMENT.md` - ARCHIVE
- `HANDOVER_SUMMARY.md` - ARCHIVE
- `CLAUDE_CODE_START_PROMPT.md` - ARCHIVE

**Result**: 3 files remain, 8 archived to `docs/archive/deployment/`

### 4. Archive Historical Task Documents
**Current files** (7 files in docs/tasks/):
- `WP1_DATABASE_SCHEMA_MODELS.md` - ARCHIVE
- `WP2_DATABASE_SERVICE.md` - ARCHIVE
- `WP3_COLLECTOR_API.md` - ARCHIVE
- `WP4_WEB_INTERFACE.md` - ARCHIVE
- `WP5_PORTABLE_DEPLOYMENT.md` - ARCHIVE
- `REFACTOR_GUIDE.md` - ARCHIVE
- `README.md` - DELETE (obsolete index)

**Action**: Move to `docs/archive/tasks/`

### 5. Clean Up Specification Files
**Files**: `docs/specifications/`
- Keep `profile_poc_spec_expand.md` (comprehensive version)
- Archive `profile_poc_spec.md` (original, less detailed)
- Rename kept file to `profile_service_spec.md` for clarity

### 6. Update docs/README.md
**Changes**:
- Remove references to archived directories
- Simplify navigation to active docs only
- Update file counts/structure

### 7. Clean Up todo/ Directory
**Action**: Review and either update or archive based on completion status
- Check if items are still relevant
- Remove completed items
- Consolidate if necessary

### 8. Update CLAUDE.md
**Changes**:
- Update "File Locations" table to reflect new structure
- Update any stale references

---

## Final Documentation Structure

```
scout-code/
├── README.md                    # Updated project overview
├── CLAUDE.md                    # Claude Code context (updated)
├── LL-LI.md                     # Lessons learned (keep as-is)
├── HANDOVER.md                  # Session handover (keep as-is)
├── REVIEW.md                    # Code review (keep as-is)
├── REVIEW-GUIDE.md              # Review methodology (keep as-is)
│
├── docs/
│   ├── README.md                # Navigation index (updated)
│   ├── QUICKSTART.md            # Quick setup
│   ├── SPECIFICATIONS.md        # Spec index
│   │
│   ├── current_state/           # CURRENT IMPLEMENTATION (primary reference)
│   │   ├── README.md
│   │   ├── api_routes.md
│   │   ├── database.md
│   │   ├── modules.md
│   │   ├── services.md
│   │   └── web_interface.md
│   │
│   ├── deployment/              # DEPLOYMENT (consolidated)
│   │   ├── Raspberry_Pi_5_Deployment_Guide.md
│   │   ├── User_Guide.md
│   │   └── Performance_Benchmarks.md
│   │
│   ├── guides/                  # DEVELOPMENT GUIDES (keep as-is)
│   │   ├── Local_LLM_Transition_Guide.md
│   │   ├── API_Diagnostics_Guide.md
│   │   ├── Scout_PoC_Scope_Document.md
│   │   └── Scout_Claude_Code_Development_Guide.md
│   │
│   ├── modules/                 # ORIGINAL MODULE SPECS (reference)
│   │   └── Module_*_Claude_Code_Instructions.md
│   │
│   ├── services/                # ORIGINAL SERVICE SPECS (reference)
│   │   └── S*_*_Claude_Code_Instructions.md (S2 renamed)
│   │
│   ├── specifications/          # FEATURE SPECS (cleaned)
│   │   └── profile_service_spec.md
│   │
│   └── archive/                 # ARCHIVED DOCUMENTS
│       ├── deployment/          # Historical deployment docs
│       ├── tasks/               # Completed work packages
│       ├── specifications/      # Superseded specs
│       └── S7_Content_Optimizer_Service_DEFERRED.md
│
├── todo/                        # TODO TRACKING (cleaned/archived)
│   └── README.md                # Or archived if obsolete
│
└── src/                         # Source code (unchanged)
    ├── README.md
    ├── modules/README.md
    ├── services/README.md
    └── web/README.md
```

---

## Implementation Order

1. Create archive directories
2. Move/archive deployment docs
3. Move/archive task docs
4. Clean up specifications
5. Rename S2 service doc
6. Update root README.md
7. Update docs/README.md
8. Update CLAUDE.md
9. Clean up todo/ directory
10. Final verification

---

*Plan created: January 2026*
