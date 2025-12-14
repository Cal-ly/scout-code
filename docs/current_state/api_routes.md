# API Routes - Current State

This document describes the current implementation of Scout's REST API.

## Overview

Scout uses FastAPI with automatic OpenAPI documentation. All API routes are prefixed and organized into four router modules.

### Router Structure
| Router | Prefix | Tags | File |
|--------|--------|------|------|
| API | `/api` | api | `routes/api.py` |
| Profile | `/api/profile` | profile | `routes/profile.py` |
| Notifications | `/api/notifications` | notifications | `routes/notifications.py` |
| Pages | `/` | pages | `routes/pages.py` |

---

## Core API Routes (`/api`)

**Location:** `src/web/routes/api.py`

### Pipeline Endpoints

#### POST `/api/apply`
Start a new job application pipeline.

**Request:**
```json
{
    "job_text": "string (100-50000 chars, required)",
    "source": "string (optional, max 100 chars)"
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

#### GET `/api/status/{job_id}`
Get pipeline execution status.

**Response:**
```json
{
    "job_id": "abc12345",
    "pipeline_id": "abc12345",
    "status": "completed|running|failed",
    "current_step": "rinser|analyzer|creator|formatter",
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

#### GET `/api/download/{job_id}/{file_type}`
Download generated PDF files.

**Parameters:**
- `job_id`: Job identifier
- `file_type`: `cv` or `cover_letter`

**Response:** PDF file download

**Errors:**
- `404`: Job not found or file not available

---

#### GET `/api/jobs`
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

### Log Endpoints

#### GET `/api/logs`
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

#### DELETE `/api/logs`
Clear all log entries from memory buffer.

**Response:**
```json
{
    "status": "cleared"
}
```

---

### Diagnostic Endpoints

#### GET `/api/diagnostics`
Get diagnostic status of all pipeline components.

**Response:**
```json
{
    "overall": "ok|degraded",
    "profile_loaded": true,
    "profile_name": "John Doe",
    "components": [
        {
            "name": "collector",
            "status": "ok|error|not_initialized",
            "message": "Profile loaded: John Doe",
            "details": {"profile_hash": "abc123"}
        },
        {
            "name": "llm_service",
            "status": "ok",
            "message": "Ollama: qwen2.5:3b",
            "details": {
                "status": "healthy",
                "ollama_connected": true,
                "model": "qwen2.5:3b"
            }
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

#### GET `/api/diagnostics/profile`
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

#### POST `/api/diagnostics/quick-test`
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

**Tests Performed:**
1. Profile access
2. Vector store query
3. LLM connection (health check only)
4. Template file loading

---

## Profile Routes (`/api/profile`)

**Location:** `src/web/routes/profile.py`

### GET `/api/profile/status`
Check profile existence and indexing status.

**Response:**
```json
{
    "exists": true,
    "is_indexed": true,
    "profile_id": "prof_abc123",
    "chunk_count": 15,
    "last_indexed": "2025-12-14T10:00:00Z"
}
```

---

### POST `/api/profile/create`
Create or update user profile.

**Request:**
```json
{
    "profile_text": "name: John Doe\ntitle: Senior Engineer\n..."
}
```

**Constraints:**
- Profile text: 100-10,000 characters
- Automatically indexes after creation

**Response:**
```json
{
    "status": "created|updated",
    "profile_id": "prof_abc123",
    "chunk_count": 15
}
```

**Errors:**
- `400`: Validation error (invalid YAML, length constraints)
- `500`: Server error

---

### POST `/api/profile/index`
Chunk and embed profile for semantic search.

**Request:**
```json
{
    "profile_id": "prof_abc123"
}
```

**Response:**
```json
{
    "success": true,
    "profile_id": "prof_abc123",
    "chunks_created": 15
}
```

**Errors:**
- `404`: Profile not found
- `500`: Indexing error

---

### GET `/api/profile/retrieve`
Get current profile data.

**Response:**
```json
{
    "profile_id": "prof_abc123",
    "profile_text": "name: John Doe\n...",
    "created_at": "2025-12-14T10:00:00Z",
    "updated_at": "2025-12-14T10:00:00Z"
}
```

**Errors:**
- `404`: No profile exists

---

## Notification Routes (`/api/notifications`)

**Location:** `src/web/routes/notifications.py`

### GET `/api/notifications`
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
            "type": "success|error|info|warning",
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

### POST `/api/notifications/{notification_id}/read`
Mark a notification as read.

**Response:**
```json
{
    "success": true
}
```

---

### POST `/api/notifications/read-all`
Mark all notifications as read.

**Response:**
```json
{
    "marked_read": 5
}
```

---

### DELETE `/api/notifications`
Clear all notifications.

**Response:**
```json
{
    "cleared": 10
}
```

---

## Page Routes

**Location:** `src/web/routes/pages.py`

These routes serve HTML pages using Jinja2 templates.

| Route | Template | Description |
|-------|----------|-------------|
| `GET /` | `index.html` | Dashboard (main page) |
| `GET /profile/create` | `profile.html` | Legacy profile editor |
| `GET /profiles` | `profiles_list.html` | Profile management |
| `GET /profiles/create` | `profile_edit.html` | Create new profile |
| `GET /profiles/{filename}` | `profile_detail.html` | View profile |
| `GET /profiles/{filename}/edit` | `profile_edit.html` | Edit profile |
| `GET /applications` | `applications.html` | Applications list |
| `GET /logs` | `logs.html` | Log viewer |

---

## Request/Response Schemas

**Location:** `src/web/schemas.py`

### Request Models

```python
class ApplyRequest(BaseModel):
    job_text: str = Field(..., min_length=100, max_length=50000)
    source: str | None = Field(None, max_length=100)
```

### Response Models

```python
class ApplyResponse(BaseModel):
    job_id: str
    status: str

class JobSummary(BaseModel):
    job_id: str
    job_title: str | None
    company_name: str | None
    status: str
    compatibility_score: float | None
    submitted_at: datetime
    completed_at: datetime | None

class JobListResponse(BaseModel):
    jobs: list[JobSummary]
    total: int
    skip: int = 0
    limit: int = 20

class StepInfo(BaseModel):
    step: str
    status: str
    duration_ms: int = 0
    error: str | None

class StatusResponse(BaseModel):
    job_id: str
    pipeline_id: str
    status: str
    current_step: str | None
    job_title: str | None
    company_name: str | None
    compatibility_score: float | None
    cv_path: str | None
    cover_letter_path: str | None
    steps: list[StepInfo]
    error: str | None
    started_at: datetime
    completed_at: datetime | None
    total_duration_ms: int = 0

class ErrorResponse(BaseModel):
    error: str
    message: str
    detail: str | None
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

    def store(self, result: PipelineResult) -> None: ...
    def get(self, job_id: str) -> PipelineResult | None: ...
    def list_all(self) -> list[PipelineResult]: ...
```

### Dependency Functions

```python
async def get_store() -> JobStore:
    """Get singleton JobStore."""

async def get_orchestrator() -> PipelineOrchestrator:
    """Get singleton PipelineOrchestrator."""
```

---

## Pipeline Execution

### Background Task Flow
```
POST /api/apply
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
│  execute_pipeline()     │
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
        const response = await fetch(`/api/status/${jobId}`);
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
| 400 | Validation error |
| 404 | Resource not found |
| 500 | Server error |

---

## OpenAPI Documentation

FastAPI automatically generates OpenAPI documentation:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

---

*Last updated: December 14, 2025*
