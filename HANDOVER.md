# Scout Project - Session Handover

**Last Updated:** January 2026
**Status:** PoC Complete - Review & Optimization Phase

---

## Quick Resume Prompt

Copy this when resuming after conversation compaction:

```
I'm resuming work on Scout Project.

Status: PoC Complete (~700+ tests passing)
- All services implemented (S1-S4, S6, S8)
- All modules implemented (M1-M5)
- Database persistence with multi-profile support
- Web interface functional

Architecture: Local Ollama LLM (Qwen 2.5 3B / Gemma 2 2B)

Please read CLAUDE.md for full context.
```

---

## Current Work Items

### Recently Completed
- Documentation cleanup and consolidation (January 2026)
- Database Service with multi-profile support
- Profile-scoped applications

### Open Items
See `todo/*.md` for tracked work:
- `todo/services.md` - Service improvements
- `todo/modules.md` - Module enhancements
- `todo/deployment.md` - Deployment tasks
- `todo/web-interface.md` - UI improvements

---

## Key Reference Files

| Document | Purpose |
|----------|---------|
| `CLAUDE.md` | **Primary context** - patterns, structure, commands |
| `LL-LI.md` | Lessons learned (58+ validated patterns) |
| `docs/current_state/` | Current implementation details |
| `docs/guides/Scout_PoC_Scope_Document.md` | PoC constraints |

---

## Quick Commands

```bash
# Activate environment
source venv/bin/activate

# Run tests
pytest tests/ -v

# Start server
make run  # or: uvicorn src.web.main:app --reload --port 8000

# Verify code
mypy src/ --ignore-missing-imports
ruff check src/
```

---

## Test Counts by Component

| Component | Tests |
|-----------|-------|
| Services (S1-S4, S6, S8) | ~270 |
| Modules (M1-M5) | ~268 |
| Database & Profile | ~95 |
| Web & API | ~70 |
| **Total** | **~700+** |

---

*For detailed architecture, patterns, and file locations, see `CLAUDE.md`.*
