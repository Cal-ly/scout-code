# API Routes - Current State

This document describes the current implementation of Scout's REST API with versioned endpoints.

## Overview

Scout uses FastAPI with API versioning and domain-driven route organization. All API routes are prefixed with `/api/v1/` and organized by domain.

### Directory Structure

```
src/web/routes/
├── __init__.py              # Exports api_router and pages_router
├── pages.py                 # HTML page routes (with legacy redirects)
└── api/
    ├── __init__.py          # Main /api router
    ├── schemas/
    │   ├── __init__.py      # Schema exports
    │   ├── common.py        # ErrorResponse, SuccessResponse
    │   ├── jobs.py          # Job pipeline schemas
    │   ├── profile.py       # Profile schemas (legacy)
    │   ├── profiles.py      # Multi-profile schemas
    │   ├── user.py          # User identity schemas
    │   └── metrics.py       # Metrics schemas
    └── v1/
        ├── __init__.py      # Aggregates all v1 routes
        ├── system.py        # /health, /info
        ├── jobs.py          # Job pipeline endpoints
        ├── skills.py        # Skill normalization endpoints
        ├── user.py          # User identity endpoint
        ├── profile.py       # Profile management (legacy)
        ├── profiles.py      # Multi-profile management
        ├── notifications.py # Notifications
        ├── logs.py          # Log retrieval
        ├── metrics.py       # Performance metrics
        └── diagnostics.py   # Component diagnostics
```

### Router Structure

| Router | Prefix | Tags | Location |
|--------|--------|------|----------|
| API v1 | `/api/v1` | various | `routes/api/v1/` |
| Pages | `/` | pages | `routes/pages.py` |

### Legacy Redirects

For backward compatibility:
- `GET /health` → redirects to `/api/v1/health`
- `GET /info` → redirects to `/api/v1/info`

---

## System Routes (`/api/v1`)

**Location:** `src/web/routes/api/v1/system.py`

### GET `/api/v1/health`
Health check endpoint with service status.

**Response:**
```json
{
    "status": "healthy",
    "version": "0.1.0",
    "services": {
        "pipeline": "ok",
        "job_store": "ok",
        "notifications": "ok"
    }
}
```

**Status Values:**
- `healthy`: All services operational
- `degraded`: Some services have issues

---

### GET `/api/v1/info`
Application information.

**Response:**
```json
{
    "name": "Scout",
    "version": "0.1.0",
    "status": "ready",
    "docs": "/docs",
    "api_version": "v1"
}
```

---

## Job Pipeline Routes (`/api/v1/jobs`)

**Location:** `src/web/routes/api/v1/jobs.py`

### POST `/api/v1/jobs/apply`
Start a new job application pipeline.

**Request:**
```json
{
    "job_text": "string (100+ chars, required)",
    "source": "string (optional, default: 'web')"
}
```

**Response:**
```json
{
    "job_id": "abc12345",
    "status": "running"
}
```

**Behavior:**
- Generates 8-character job ID
- Starts pipeline execution in background task
- Returns immediately for async polling
- Pipeline timeout: 900 seconds (15 minutes)

---

### GET `/api/v1/jobs/{job_id}`
Get pipeline execution status.

**Response:**
```json
{
    "job_id": "abc12345",
    "pipeline_id": "abc12345",
    "status": "completed",
    "current_step": null,
    "job_title": "Software Engineer",
    "company_name": "Example Corp",
    "compatibility_score": 78.5,
    "cv_path": "/outputs/cv_abc12345.pdf",
    "cover_letter_path": "/outputs/cover_letter_abc12345.pdf",
    "steps": [
        {
            "step": "rinser",
            "status": "completed",
            "duration_ms": 15000,
            "error": null
        }
    ],
    "error": null,
    "started_at": "2025-12-14T10:00:00Z",
    "completed_at": "2025-12-14T10:05:00Z",
    "total_duration_ms": 300000
}
```

**Errors:**
- `404`: Job not found

---

### GET `/api/v1/jobs`
List all job applications with pagination.

**Query Parameters:**
- `skip`: Offset (default 0)
- `limit`: Max results (default 20)

**Response:**
```json
{
    "jobs": [
        {
            "job_id": "abc12345",
            "job_title": "Software Engineer",
            "company_name": "Example Corp",
            "status": "completed",
            "compatibility_score": 78.5,
            "submitted_at": "2025-12-14T10:00:00Z",
            "completed_at": "2025-12-14T10:05:00Z"
        }
    ],
    "total": 15,
    "skip": 0,
    "limit": 20
}
```

---

### GET `/api/v1/jobs/{job_id}/download/{file_type}`
Download generated PDF files.

**Parameters:**
- `job_id`: Job identifier
- `file_type`: `cv` or `cover_letter`

**Response:** PDF file download

**Errors:**
- `404`: Job not found or file not available

---

## Skills Routes (`/api/v1/skills`)

**Location:** `src/web/routes/api/v1/skills.py`

These endpoints provide skill alias normalization and expansion for consistent job matching.

### GET `/api/v1/skills/aliases`
Get all skill alias mappings.

**Response:**
```json
{
    "aliases": {
        "python": ["python3", "py", "python 3.x"],
        "javascript": ["js", "es6", "ecmascript"],
        "typescript": ["ts"],
        "golang": ["go"],
        "csharp": ["c#", ".net", "dotnet"]
    },
    "count": 50
}
```

---

### POST `/api/v1/skills/normalize`
Normalize skill names to canonical forms.

**Request:**
```json
{
    "skills": ["JS", "Python3", "c#", "AWS"]
}
```

**Response:**
```json
{
    "normalized": {
        "JS": "javascript",
        "Python3": "python",
        "c#": "csharp",
        "AWS": "aws"
    }
}
```

---

### POST `/api/v1/skills/expand`
Expand skills to include all known aliases.

**Request:**
```json
{
    "skills": ["python", "javascript"]
}
```

**Response:**
```json
{
    "expanded": {
        "python": ["python", "python3", "py", "python 3.x"],
        "javascript": ["javascript", "js", "es6", "ecmascript"]
    }
}
```

---

### GET `/api/v1/skills/search`
Search for skills matching a query.

**Query Parameters:**
- `q`: Search query (required)
- `limit`: Max results (default 10)

**Response:**
```json
{
    "query": "python",
    "matches": [
        {
            "skill": "python",
            "aliases": ["python3", "py"],
            "match_type": "exact"
        }
    ]
}
```

---

## User Routes (`/api/v1/user`)

**Location:** `src/web/routes/api/v1/user.py`

### GET `/api/v1/user`
Get current user identity information.

**Response:**
```json
{
    "id": 1,
    "username": "test_user",
    "email": "test@scout.local",
    "display_name": "Test User",
    "created_at": "2025-12-16T10:00:00Z"
}
```

---

## Multi-Profile Routes (`/api/v1/profiles`)

**Location:** `src/web/routes/api/v1/profiles.py`

These endpoints manage multiple user profiles with SQLite persistence and completeness scoring.

### GET `/api/v1/profiles`
List all profiles with statistics.

**Response:**
```json
{
    "profiles": [
        {
            "id": 1,
            "slug": "emma-chen",
            "name": "Emma Chen",
            "full_name": "Emma Chen",
            "email": "emma.chen@example.com",
            "title": "AI/ML Engineer",
            "is_active": true,
            "is_demo": true,
            "created_at": "2025-12-16T10:00:00Z",
            "updated_at": "2025-12-16T10:00:00Z",
            "stats": {
                "total_applications": 5,
                "completed_applications": 4,
                "avg_compatibility_score": 75.5
            }
        }
    ],
    "active_profile_slug": "emma-chen",
    "total": 3
}
```

---

### POST `/api/v1/profiles`
Create a new profile.

**Request:**
```json
{
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1-555-0123",
    "location": "San Francisco, CA",
    "title": "Senior Software Engineer",
    "summary": "Experienced engineer with 8+ years...",
    "profile_data": {
        "skills": [...],
        "experiences": [...],
        "education": [...]
    }
}
```

**Response:**
```json
{
    "id": 4,
    "slug": "john-doe",
    "name": "John Doe",
    "message": "Profile created successfully"
}
```

---

### GET `/api/v1/profiles/{slug}`
Get a specific profile by slug.

**Response:** Full profile object with `profile_data` field containing UserProfile model.

**Errors:**
- `404`: Profile not found

---

### PUT `/api/v1/profiles/{slug}`
Update an existing profile.

**Request:** Same as POST create

**Response:**
```json
{
    "slug": "john-doe",
    "message": "Profile updated successfully"
}
```

---

### DELETE `/api/v1/profiles/{slug}`
Delete a profile.

**Response:**
```json
{
    "slug": "john-doe",
    "message": "Profile deleted successfully"
}
```

**Errors:**
- `404`: Profile not found
- `400`: Cannot delete active profile

---

### GET `/api/v1/profiles/active`
Get the currently active profile.

**Response:**
```json
{
    "id": 1,
    "slug": "emma-chen",
    "name": "Emma Chen",
    "email": "emma.chen@example.com",
    "title": "AI/ML Engineer",
    "is_active": true,
    "created_at": "2025-12-16T10:00:00Z"
}
```

**Errors:**
- `404`: No active profile set

---

### POST `/api/v1/profiles/{slug}/activate`
Set a profile as active. Triggers ChromaDB re-indexing.

**Response:**
```json
{
    "slug": "emma-chen",
    "name": "Emma Chen",
    "message": "Profile activated successfully"
}
```

**Behavior:**
- Clears previous active profile flag
- Sets new profile as active
- Re-indexes profile skills to ChromaDB `user_profiles` collection

---

### GET `/api/v1/profiles/{slug}/completeness`
Get profile completeness score and breakdown.

**Response:**
```json
{
    "slug": "emma-chen",
    "overall_score": 85,
    "level": "excellent",
    "sections": {
        "contact": {"score": 100, "max": 100, "filled": 5, "total": 5},
        "summary": {"score": 80, "max": 100, "has_content": true},
        "skills": {"score": 90, "max": 100, "count": 12},
        "experience": {"score": 85, "max": 100, "count": 3},
        "education": {"score": 75, "max": 100, "count": 1},
        "certifications": {"score": 80, "max": 100, "count": 2}
    },
    "suggestions": [
        "Add more education entries",
        "Consider adding more certifications"
    ]
}
```

**Completeness Levels:**
| Level | Score Range |
|-------|-------------|
| excellent | 80-100% |
| good | 60-79% |
| fair | 40-59% |
| needs_work | 0-39% |

---

## Profile Routes (`/api/v1/profile`) - LEGACY

**Location:** `src/web/routes/api/v1/profile.py`

> **Note:** These endpoints use the legacy ProfileService. For multi-profile support, use `/api/v1/profiles` instead.

### GET `/api/v1/profile/status`
Check profile existence and indexing status.

**Response:**
```json
{
    "exists": true,
    "is_indexed": true,
    "profile_id": 1,
    "chunk_count": 15,
    "character_count": 2500,
    "last_updated": "2025-12-14T10:00:00Z"
}
```

---

### GET `/api/v1/profile/retrieve`
Get current profile data.

**Response:**
```json
{
    "profile_id": 1,
    "profile_text": "full_name: John Doe\n...",
    "created_at": "2025-12-14T10:00:00Z",
    "updated_at": "2025-12-14T10:00:00Z"
}
```

**Errors:**
- `404`: No profile exists

---

### POST `/api/v1/profile/create`
Create or update user profile from text.

**Request:**
```json
{
    "profile_text": "full_name: John Doe\ntitle: Senior Engineer\n..."
}
```

**Constraints:**
- Profile text: 100-10,000 characters
- Automatically indexes after creation

**Response:**
```json
{
    "profile_id": 1,
    "status": "created",
    "is_indexed": true,
    "chunk_count": 15
}
```

---

### POST `/api/v1/profile/index`
Re-index profile for semantic search.

**Request:**
```json
{
    "profile_id": 1
}
```

**Response:**
```json
{
    "success": true,
    "profile_id": 1,
    "chunks_created": 15
}
```

---

### GET `/api/v1/profile/assessment`
Get profile completeness assessment with scores and suggestions.

**Response:**
```json
{
    "overall_score": 75,
    "grade": "B",
    "section_scores": [
        {
            "section": "skills",
            "score": 80,
            "max_score": 100,
            "weight": 0.25,
            "issues": [],
            "suggestions": ["Add more technical skills"]
        }
    ],
    "top_suggestions": ["Add more work experience details"],
    "strengths": ["Strong education section"],
    "is_job_ready": true
}
```

---

### GET `/api/v1/profile/summary`
Get quick profile summary with score.

**Response:**
```json
{
    "name": "John Doe",
    "title": "Senior Software Engineer",
    "completeness_score": 75,
    "grade": "B",
    "is_job_ready": true,
    "top_suggestion": "Add more work experience details"
}
```

---

### GET `/api/v1/profile/editor-data`
Get profile data formatted for form editor.

**Response:** Full UserProfile model as JSON

---

### POST `/api/v1/profile/editor-save`
Save profile from form editor.

**Request:** UserProfile data as JSON

**Response:**
```json
{
    "status": "saved",
    "message": "Profile saved successfully",
    "chunk_count": 15
}
```

---

### POST `/api/v1/profile/assess`
Assess profile without saving.

**Request:** Profile data as JSON

**Response:** ProfileAssessment model

---

### POST `/api/v1/profile/export-yaml`
Export profile as YAML file download.

**Request:** Profile data as JSON

**Response:** YAML file download

---

## Notification Routes (`/api/v1/notifications`)

**Location:** `src/web/routes/api/v1/notifications.py`

### GET `/api/v1/notifications`
Get all or unread notifications.

**Query Parameters:**
- `unread_only`: Boolean (default false)
- `limit`: Max notifications (default 20)

**Response:**
```json
{
    "notifications": [
        {
            "id": "notif_abc123",
            "type": "success",
            "title": "Application Complete",
            "message": "Your CV has been generated",
            "read": false,
            "created_at": "2025-12-14T10:00:00Z"
        }
    ],
    "unread_count": 3,
    "total": 10
}
```

---

### POST `/api/v1/notifications/{notification_id}/read`
Mark a notification as read.

**Response:**
```json
{
    "success": true
}
```

---

### POST `/api/v1/notifications/read-all`
Mark all notifications as read.

**Response:**
```json
{
    "marked_read": 5
}
```

---

### DELETE `/api/v1/notifications`
Clear all notifications.

**Response:**
```json
{
    "cleared": 10
}
```

---

## Log Routes (`/api/v1/logs`)

**Location:** `src/web/routes/api/v1/logs.py`

### GET `/api/v1/logs`
Retrieve application logs from memory buffer.

**Query Parameters:**
- `limit`: Max entries (default 100, max 500)
- `level`: Filter by level (INFO, WARNING, ERROR, DEBUG)
- `logger_filter`: Filter by logger name (partial match)

**Response:**
```json
{
    "entries": [
        {
            "timestamp": "2025-12-14T10:00:00.123Z",
            "level": "INFO",
            "logger": "src.services.llm_service",
            "message": "Processing request..."
        }
    ],
    "total": 50
}
```

---

### DELETE `/api/v1/logs`
Clear all log entries from memory buffer.

**Response:**
```json
{
    "status": "cleared"
}
```

---

## Metrics Routes (`/api/v1/metrics`)

**Location:** `src/web/routes/api/v1/metrics.py`

### GET `/api/v1/metrics/summary`
Get performance metrics summary for the last 7 days.

**Query Parameters:**
- `days`: Number of days (default 7)

**Response:**
```json
{
    "period_start": "2025-12-09T10:00:00Z",
    "period_end": "2025-12-16T10:00:00Z",
    "total_calls": 50,
    "total_tokens": 125000,
    "successful_calls": 48,
    "avg_tokens_per_second": 2.5,
    "median_duration_seconds": 45.0,
    "p95_duration_seconds": 120.0,
    "success_rate": 96.0,
    "error_breakdown": {"timeout": 2},
    "fallback_rate": 4.0,
    "avg_cpu_percent": 45.5,
    "avg_memory_mb": 512.0,
    "avg_temperature_c": 55.0
}
```

---

### GET `/api/v1/metrics/daily`
Get daily metrics for charting.

**Query Parameters:**
- `days`: Number of days (default 7)

**Response:**
```json
{
    "daily_metrics": [
        {
            "date": "2025-12-15",
            "total_calls": 10,
            "successful_calls": 9,
            "avg_duration_seconds": 42.5,
            "avg_tokens_per_second": 2.8
        }
    ]
}
```

---

### GET `/api/v1/metrics/system`
Get current system metrics (CPU, memory, temperature).

**Response:**
```json
{
    "cpu_percent": 25.5,
    "memory_mb": 512.0,
    "memory_percent": 12.5,
    "temperature_c": 55.0,
    "timestamp": "2025-12-16T10:00:00Z"
}
```

---

## Diagnostics Routes (`/api/v1/diagnostics`)

**Location:** `src/web/routes/api/v1/diagnostics.py`

### GET `/api/v1/diagnostics`
Get diagnostic status of all pipeline components.

**Response:**
```json
{
    "overall": "ok",
    "profile_loaded": true,
    "profile_name": "John Doe",
    "components": [
        {
            "name": "collector",
            "status": "ok",
            "message": "Profile: John Doe",
            "details": {"profile_hash": "abc123"}
        },
        {
            "name": "llm_service",
            "status": "ok",
            "message": "Ollama: qwen2.5:3b",
            "details": null
        }
    ]
}
```

**Checked Components:**
- `collector` - Profile loading
- `rinser` - Initialization status
- `analyzer` - Initialization status
- `creator` - Initialization status
- `formatter` - Initialization status
- `llm_service` - Ollama connection and model status

---

### GET `/api/v1/diagnostics/profile`
Get detailed profile information.

**Response:**
```json
{
    "loaded": true,
    "name": "John Doe",
    "email": "john@example.com",
    "title": "Senior Software Engineer",
    "years_experience": 8.5,
    "skill_count": 25,
    "experience_count": 4,
    "education_count": 2,
    "certification_count": 3
}
```

---

### POST `/api/v1/diagnostics/quick-test`
Run quick component tests without full LLM processing.

**Response:**
```json
{
    "success": true,
    "total_duration_ms": 150,
    "results": [
        {
            "component": "profile_access",
            "status": "ok",
            "duration_ms": 5,
            "message": "Profile: John Doe"
        },
        {
            "component": "vector_search",
            "status": "ok",
            "duration_ms": 45,
            "message": "Found 3 skill matches"
        },
        {
            "component": "llm_connection",
            "status": "ok",
            "duration_ms": 80,
            "message": "Ollama ready: qwen2.5:3b"
        },
        {
            "component": "templates",
            "status": "ok",
            "duration_ms": 10,
            "message": "Found 4 templates"
        }
    ]
}
```

---

## Page Routes

**Location:** `src/web/routes/pages.py`

These routes serve HTML pages using Jinja2 templates.

### Active Pages

| Route | Template | Description |
|-------|----------|-------------|
| `GET /` | `index.html` | Dashboard (main page) |
| `GET /profiles` | `profiles_list.html` | Profile management list |
| `GET /profiles/new` | `profile_edit.html` | Create new profile |
| `GET /profiles/{slug}/edit` | `profile_edit.html` | Edit profile by slug |
| `GET /applications` | `applications.html` | Applications list |
| `GET /metrics` | `metrics.html` | Performance metrics dashboard |
| `GET /logs` | `logs.html` | Application logs viewer |
| `GET /diagnostics` | `diagnostics.html` | System diagnostics page |

### Legacy Redirects (301 Permanent)

For backward compatibility, these URLs redirect to new locations:

| Old Route | Redirects To | Reason |
|-----------|--------------|--------|
| `GET /profile/create` | `/profiles/new` | URL structure change |
| `GET /profile/edit` | `/profiles` | Needs slug selection |
| `GET /profiles/create` | `/profiles/new` | URL naming change |
| `GET /profiles/edit` | `/profiles` | Needs slug selection |

---

## Request/Response Schemas

**Location:** `src/web/routes/api/schemas/`

### Common Schemas (`common.py`)

```python
class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    message: str
    detail: str | None = None

class SuccessResponse(BaseModel):
    """Standard success response."""
    status: str = "success"
    message: str | None = None
```

### Job Schemas (`jobs.py`)

```python
class ApplyRequest(BaseModel):
    job_text: str = Field(..., min_length=100)
    source: str | None = Field(default="web")

class ApplyResponse(BaseModel):
    job_id: str
    status: str

class StepInfo(BaseModel):
    step: str
    status: str
    duration_ms: int
    error: str | None = None

class StatusResponse(BaseModel):
    job_id: str
    pipeline_id: str
    status: str
    current_step: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    compatibility_score: float | None = None
    cv_path: str | None = None
    cover_letter_path: str | None = None
    steps: list[StepInfo] = []
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_duration_ms: int = 0

class JobSummary(BaseModel):
    job_id: str
    job_title: str | None = None
    company_name: str | None = None
    status: str
    compatibility_score: float | None = None
    submitted_at: datetime | None = None
    completed_at: datetime | None = None

class JobListResponse(BaseModel):
    jobs: list[JobSummary]
    total: int
    skip: int = 0
    limit: int = 20
```

---

## Dependencies

**Location:** `src/web/dependencies.py`

### JobStore
In-memory store for tracking pipeline jobs:

```python
class JobStore:
    def __init__(self):
        self._jobs: dict[str, PipelineResult] = {}

    def store(self, result: PipelineResult) -> str: ...
    def get(self, job_id: str) -> PipelineResult | None: ...
    def list_all(self) -> list[PipelineResult]: ...
    def count(self) -> int: ...
```

### Dependency Functions

```python
def get_job_store() -> JobStore:
    """Get singleton JobStore."""

async def get_orchestrator() -> PipelineOrchestrator:
    """Get singleton PipelineOrchestrator."""
```

---

## Pipeline Execution

### Background Task Flow
```
POST /api/v1/jobs/apply
      │
      ▼
┌─────────────────────────┐
│  Generate job_id        │
│  Create PipelineInput   │
│  Add background task    │
│  Return immediately     │
└─────────────────────────┘
      │
      ▼ (background)
┌─────────────────────────┐
│  _execute_pipeline()    │
│  - asyncio.wait_for()   │
│  - 15 min timeout       │
│  - Store result         │
└─────────────────────────┘
```

### Polling Pattern
```javascript
// Frontend polling
function startPolling() {
    pollInterval = setInterval(async () => {
        const response = await fetch(`/api/v1/jobs/${jobId}`);
        const status = await response.json();

        if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(pollInterval);
            showResults(status);
        }
    }, 1000);
}
```

---

## Error Handling

All endpoints return consistent error responses:

```json
{
    "error": "validation_error",
    "message": "Human-readable error message",
    "detail": "Additional details if available"
}
```

### HTTP Status Codes
| Code | Usage |
|------|-------|
| 200 | Success |
| 307 | Redirect (legacy endpoints) |
| 400 | Validation error |
| 404 | Resource not found |
| 422 | Request validation error |
| 500 | Server error |

---

## OpenAPI Documentation

FastAPI automatically generates OpenAPI documentation:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

---

## CORS Configuration

Allowed origins for cross-origin requests:
- `http://localhost:3000` (Vue dev server)
- `http://localhost:8000`
- `http://192.168.1.21:3000`
- `http://192.168.1.21:8000`

---

*Last updated: December 16, 2025*
*Updated: Added user endpoint, profile completeness endpoint, active profile endpoint*
