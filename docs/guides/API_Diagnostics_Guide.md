# Scout API Diagnostics Guide

A guide for coding assistants (Claude Code, etc.) to validate Scout pipeline integrity using the diagnostic API endpoints.

## Quick Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/diagnostics` | GET | Full pipeline health check |
| `/api/diagnostics/profile` | GET | Profile details |
| `/api/diagnostics/quick-test` | POST | Component validation test |
| `/api/logs` | GET | Recent application logs |
| `/api/logs` | DELETE | Clear log buffer |
| `/health` | GET | Basic service health |

## Base URL

- **Local Development**: `http://localhost:8000`
- **Raspberry Pi Deployment**: `http://<pi-ip>:8000`

---

## 1. Full Pipeline Diagnostics

### Endpoint
```
GET /api/diagnostics
```

### Purpose
Checks all pipeline components and returns their initialization status.

### Usage
```bash
curl http://localhost:8000/api/diagnostics | jq
```

### Response Schema
```json
{
    "overall": "ok" | "degraded",
    "profile_loaded": true | false,
    "profile_name": "string | null",
    "components": [
        {
            "name": "collector" | "rinser" | "analyzer" | "creator" | "formatter" | "llm_service",
            "status": "ok" | "error" | "not_initialized" | "degraded",
            "message": "string | null",
            "details": { } | null
        }
    ]
}
```

### Interpreting Results

| Overall Status | Meaning |
|----------------|---------|
| `ok` | All components healthy, pipeline ready |
| `degraded` | One or more components have issues |

| Component Status | Meaning |
|------------------|---------|
| `ok` | Component initialized and ready |
| `not_initialized` | Component exists but `initialize()` not called |
| `error` | Component failed to initialize |
| `degraded` | Component partially functional |

### Example: Healthy Pipeline
```json
{
    "overall": "ok",
    "profile_loaded": true,
    "profile_name": "Alex Jensen",
    "components": [
        {"name": "collector", "status": "ok", "message": "Profile loaded: Alex Jensen"},
        {"name": "rinser", "status": "ok", "message": "Initialized"},
        {"name": "analyzer", "status": "ok", "message": "Initialized"},
        {"name": "creator", "status": "ok", "message": "Initialized"},
        {"name": "formatter", "status": "ok", "message": "Initialized"},
        {"name": "llm_service", "status": "ok", "message": "Ollama: qwen2.5:3b"}
    ]
}
```

### Common Issues

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `profile_loaded: false` | No profile.yaml | Create `data/profile.yaml` |
| `collector: error` | Profile YAML invalid | Check YAML syntax |
| `llm_service: degraded` | Ollama not running | `ollama serve` |
| `llm_service: error` | Model not pulled | `ollama pull qwen2.5:3b` |

---

## 2. Profile Diagnostics

### Endpoint
```
GET /api/diagnostics/profile
```

### Purpose
Returns detailed information about the loaded user profile.

### Usage
```bash
curl http://localhost:8000/api/diagnostics/profile | jq
```

### Response Schema
```json
{
    "loaded": true | false,
    "name": "string | null",
    "email": "string | null",
    "title": "string | null",
    "years_experience": 5.0 | null,
    "skill_count": 10,
    "experience_count": 3,
    "education_count": 1,
    "certification_count": 2
}
```

### Validation Checklist

For pipeline to work correctly, verify:
- [ ] `loaded: true`
- [ ] `skill_count > 0` (needed for matching)
- [ ] `experience_count > 0` (needed for CV generation)
- [ ] `name` and `email` present (required fields)

### Example: Profile Not Loaded
```json
{
    "loaded": false,
    "name": null,
    "email": null,
    "title": null,
    "years_experience": null,
    "skill_count": 0,
    "experience_count": 0,
    "education_count": 0,
    "certification_count": 0
}
```

**Action**: Create or fix `data/profile.yaml`.

---

## 3. Quick Component Test

### Endpoint
```
POST /api/diagnostics/quick-test
```

### Purpose
Runs a non-destructive test of key pipeline components without full LLM processing.

### Usage
```bash
curl -X POST http://localhost:8000/api/diagnostics/quick-test | jq
```

### Response Schema
```json
{
    "success": true | false,
    "total_duration_ms": 150,
    "results": [
        {
            "component": "profile_access" | "vector_search" | "llm_connection" | "templates",
            "status": "ok" | "warning" | "error",
            "duration_ms": 5,
            "message": "string | null",
            "error": "string | null"
        }
    ]
}
```

### What Each Test Validates

| Component | What It Tests |
|-----------|---------------|
| `profile_access` | Can load and read user profile from Collector |
| `vector_search` | ChromaDB operational, can query for skills |
| `llm_connection` | Ollama server reachable, model loaded |
| `templates` | HTML templates exist for PDF generation |

### Example: All Tests Pass
```json
{
    "success": true,
    "total_duration_ms": 127,
    "results": [
        {"component": "profile_access", "status": "ok", "duration_ms": 3, "message": "Profile: Alex Jensen"},
        {"component": "vector_search", "status": "ok", "duration_ms": 45, "message": "Found 3 skill matches"},
        {"component": "llm_connection", "status": "ok", "duration_ms": 52, "message": "Ollama ready: qwen2.5:3b"},
        {"component": "templates", "status": "ok", "duration_ms": 2, "message": "Found 2 templates"}
    ]
}
```

### Example: Vector Search Issue
```json
{
    "success": true,
    "total_duration_ms": 89,
    "results": [
        {"component": "profile_access", "status": "ok", "duration_ms": 2, "message": "Profile: Alex Jensen"},
        {"component": "vector_search", "status": "ok", "duration_ms": 38, "message": "Found 0 skill matches"},
        ...
    ]
}
```

**Note**: `0 skill matches` with `status: ok` means vector store works but profile is not indexed. Call `collector.index_profile()` to enable semantic matching.

---

## 4. Application Logs

### Get Recent Logs
```
GET /api/logs?limit=100&level=ERROR
```

### Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 100 | Max entries (max 500) |
| `level` | string | null | Filter: DEBUG, INFO, WARNING, ERROR |
| `logger_filter` | string | null | Filter by logger name (partial match) |

### Usage Examples
```bash
# Get last 50 logs
curl "http://localhost:8000/api/logs?limit=50" | jq

# Get only errors
curl "http://localhost:8000/api/logs?level=ERROR" | jq

# Get pipeline-related logs
curl "http://localhost:8000/api/logs?logger_filter=pipeline" | jq
```

### Response Schema
```json
{
    "entries": [
        {
            "timestamp": "2025-12-14T10:30:45.123456",
            "level": "INFO",
            "logger": "src.services.pipeline.pipeline",
            "message": "Pipeline execution completed"
        }
    ],
    "total": 42
}
```

### Clear Logs
```
DELETE /api/logs
```

```bash
curl -X DELETE http://localhost:8000/api/logs
```

---

## 5. Basic Health Check

### Endpoint
```
GET /health
```

### Purpose
Quick check that the service is running.

### Usage
```bash
curl http://localhost:8000/health | jq
```

### Response
```json
{
    "status": "healthy" | "degraded",
    "version": "0.1.0",
    "services": {
        "pipeline": "ready",
        "notifications": "active"
    }
}
```

---

## Validation Workflow for Coding Assistants

### Before Making Changes

Run this sequence to verify baseline health:

```bash
# 1. Check service is running
curl -s http://localhost:8000/health | jq -r '.status'
# Expected: "healthy"

# 2. Check all components
curl -s http://localhost:8000/api/diagnostics | jq -r '.overall'
# Expected: "ok"

# 3. Run quick test
curl -s -X POST http://localhost:8000/api/diagnostics/quick-test | jq -r '.success'
# Expected: "true"
```

### After Making Changes

```bash
# 1. Clear logs to see fresh output
curl -X DELETE http://localhost:8000/api/logs

# 2. Restart service (if needed)
sudo systemctl restart scout

# 3. Wait for startup
sleep 5

# 4. Check diagnostics
curl -s http://localhost:8000/api/diagnostics | jq

# 5. Run quick test
curl -s -X POST http://localhost:8000/api/diagnostics/quick-test | jq

# 6. Check for errors in logs
curl -s "http://localhost:8000/api/logs?level=ERROR" | jq
```

### Testing Pipeline End-to-End

Use minimal test data for quick validation:

```bash
# Submit minimal job posting
curl -X POST http://localhost:8000/api/apply \
  -H "Content-Type: application/json" \
  -d '{
    "job_text": "Python Developer\nTestCorp\nCopenhagen\n\nRequirements:\n- Python programming\n- REST API development\n- Git version control\n\nResponsibilities:\n- Write Python code\n- Build APIs\n- Code reviews"
  }' | jq

# Note the job_id from response, then poll status
curl http://localhost:8000/api/status/<job_id> | jq
```

---

## Troubleshooting Decision Tree

```
Pipeline not working?
│
├─► Check /health
│   └─► status != "healthy"
│       └─► Service not running properly
│           └─► Check: sudo systemctl status scout
│
├─► Check /api/diagnostics
│   ├─► profile_loaded: false
│   │   └─► Create data/profile.yaml
│   │
│   ├─► llm_service: error/degraded
│   │   ├─► Ollama not running
│   │   │   └─► Run: ollama serve
│   │   └─► Model not available
│   │       └─► Run: ollama pull qwen2.5:3b
│   │
│   └─► other component: error
│       └─► Check /api/logs?level=ERROR for details
│
├─► Check /api/diagnostics/quick-test
│   ├─► vector_search: 0 matches
│   │   └─► Profile not indexed
│   │       └─► Indexing happens on startup (restart service)
│   │
│   └─► templates: warning
│       └─► Missing template files
│           └─► Check src/modules/formatter/templates/
│
└─► Check /api/logs
    └─► Look for ERROR entries with stack traces
```

---

## File Locations Reference

| Component | Configuration Location |
|-----------|----------------------|
| User Profile | `data/profile.yaml` |
| Test Data | `docs/test_data/` |
| Templates | `src/modules/formatter/templates/` |
| Service Config | `/etc/systemd/system/scout.service` (Pi) |
| Environment | `.env` or `.env.production` |

---

## Quick Commands Summary

```bash
# Health check
curl http://localhost:8000/health | jq

# Full diagnostics
curl http://localhost:8000/api/diagnostics | jq

# Profile info
curl http://localhost:8000/api/diagnostics/profile | jq

# Quick test
curl -X POST http://localhost:8000/api/diagnostics/quick-test | jq

# Get error logs
curl "http://localhost:8000/api/logs?level=ERROR" | jq

# Clear logs
curl -X DELETE http://localhost:8000/api/logs

# List jobs
curl http://localhost:8000/api/jobs | jq
```

---

*Last updated: December 14, 2025*
