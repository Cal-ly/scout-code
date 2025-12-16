# Scout Web Layer

FastAPI-based web application providing REST API and HTML interface.

## Directory Structure

```
src/web/
├── main.py              # FastAPI application entry point
├── dependencies.py      # Dependency injection (JobStore, etc.)
├── log_handler.py       # In-memory log storage for web UI
├── routes/
│   ├── __init__.py      # Router exports
│   ├── pages.py         # HTML page routes
│   └── api/
│       ├── __init__.py  # API router aggregation
│       ├── schemas/     # Pydantic request/response models
│       │   ├── common.py
│       │   ├── jobs.py
│       │   ├── profile.py
│       │   └── metrics.py
│       └── v1/          # API v1 endpoints
│           ├── system.py       # /health, /info
│           ├── jobs.py         # /jobs/*
│           ├── skills.py       # /skills/*
│           ├── profile.py      # /profile/*
│           ├── notifications.py
│           ├── logs.py
│           ├── metrics.py
│           └── diagnostics.py
├── templates/           # Jinja2 HTML templates
│   ├── index.html
│   ├── profile_editor.html
│   ├── applications.html
│   ├── logs.html
│   ├── metrics.html
│   └── partials/
│       └── navbar.html
└── static/
    ├── css/
    │   ├── common.css
    │   └── profile-editor.css
    └── js/
        ├── common.js
        └── profile-editor.js
```

## API Structure

```
/api/v1/
├── /health              # Health check
├── /info                # App info
├── /jobs/
│   ├── POST /apply      # Start pipeline
│   ├── POST /quick-score # Quick compatibility
│   ├── GET /            # List jobs
│   ├── GET /{id}        # Job status
│   └── GET /{id}/download/{type}  # Download PDF
├── /skills/
│   ├── GET /aliases     # All aliases
│   ├── POST /normalize  # Normalize names
│   ├── POST /expand     # Expand to aliases
│   └── GET /search      # Semantic search
├── /profile/
│   ├── GET /status      # Profile status
│   ├── GET /assessment  # Completeness score
│   ├── GET /editor-data # Form editor data
│   ├── POST /editor-save # Save from form
│   └── POST /export-yaml # Download YAML
├── /notifications/      # Toast notifications
├── /logs/               # Application logs
├── /metrics/            # Performance metrics
└── /diagnostics/        # Component health
```

## Page Routes

| Route | Template | Description |
|-------|----------|-------------|
| `/` | `index.html` | Dashboard |
| `/profile/edit` | `profile_editor.html` | Form-based editor |
| `/applications` | `applications.html` | Job applications list |
| `/logs` | `logs.html` | Log viewer |
| `/metrics` | `metrics.html` | Performance dashboard |

## Running the Server

```bash
# Development (with auto-reload)
uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn src.web.main:app --host 0.0.0.0 --port 8000 --workers 1
```

## API Documentation

FastAPI auto-generates documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

## Key Patterns

### Background Tasks for Long Operations
```python
@router.post("/apply")
async def apply(
    request: ApplyRequest,
    background_tasks: BackgroundTasks,
):
    job_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(execute_pipeline, job_id, request)
    return {"job_id": job_id, "status": "running"}
```

### Dependency Injection
```python
from src.web.dependencies import get_orchestrator

@router.get("/diagnostics")
async def diagnostics(
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator)
):
    # Use orchestrator...
```

### Error Handling
```python
from src.web.routes.api.schemas import ErrorResponse

@router.get("/{job_id}", responses={404: {"model": ErrorResponse}})
async def get_job(job_id: str):
    if not found:
        raise HTTPException(status_code=404, detail="Job not found")
```

---

*For full API documentation, see `docs/current_state/api_routes.md`.*
