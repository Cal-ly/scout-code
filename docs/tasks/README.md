# Scout Enhancement Tasks

This directory contains detailed task specifications for Claude Code to implement Scout enhancements.

## Task Overview

| Task | ID | Effort | Description |
|------|-----|--------|-------------|
| [Skill Aliases](./TASK-A-SKILL-ALIASES.md) | SCOUT-SKILL-ALIASES | 30-45 min | Add skill synonym/alias handling for better job-profile matching |
| [Profile Completeness](./TASK-C-PROFILE-COMPLETENESS.md) | SCOUT-PROFILE-COMPLETENESS | 45-60 min | Profile health check with scores and improvement suggestions |
| [Profile Editor UI](./TASK-E-PROFILE-EDITOR-UI.md) | SCOUT-PROFILE-EDITOR | 2-3 hours | Web-based profile editor with form UI |

## Recommended Order

1. **Task A: Skill Aliases** - No dependencies, quick win
2. **Task C: Profile Completeness** - No hard dependencies, but Task A helps
3. **Task E: Profile Editor UI** - Benefits from Task C for live scoring

## Environment Setup

All tasks assume:

```bash
# SSH to Raspberry Pi
ssh cally@192.168.1.21

# Navigate to project
cd /home/cally/projects/scout-code

# Activate virtual environment
source venv/bin/activate

# Verify environment
python -c "import src; print('Scout imports OK')"
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_skill_aliases.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

## Starting Web Server

```bash
uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000
```

Access at: `http://192.168.1.21:8000`

## Key Files Reference

```
src/
├── modules/
│   └── collector/
│       ├── __init__.py          # Module exports
│       ├── collector.py         # Main Collector class
│       ├── models.py            # Pydantic models (UserProfile, etc.)
│       ├── skill_aliases.py     # [Task A] NEW
│       └── assessment.py        # [Task C] NEW
├── services/
│   └── vector_store/            # ChromaDB integration
└── web/
    ├── main.py                  # FastAPI app
    ├── routes/
    │   ├── pages.py             # Page routes
    │   └── profile.py           # [Task C/E] Profile API
    ├── templates/
    │   ├── base.html            # Base template
    │   └── profile_editor.html  # [Task E] NEW
    └── static/
        ├── css/
        │   └── profile-editor.css  # [Task E] NEW
        └── js/
            └── profile-editor.js   # [Task E] NEW
```

## After Implementation

After each task:

1. Run tests to verify no regressions
2. Test functionality manually
3. Update `HANDOVER.md` if needed
4. Commit with descriptive message

```bash
git add -A
git commit -m "feat(collector): add skill alias support for improved matching"
git push
```
