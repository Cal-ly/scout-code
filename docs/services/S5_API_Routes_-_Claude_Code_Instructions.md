---
updated: 2025-10-04, 19:47
---
The user wants to continue with API Routes implementation instructions. Based on the handover document, this is the next priority after Vector Store Service. I need to provide comprehensive Claude Code instructions for implementing the RESTful API endpoints for Scout.

Key points to cover:
1. FastAPI implementation with proper structure
2. All the endpoint groups mentioned (profile, jobs, generate, system)
3. Authentication and rate limiting
4. Request/response models
5. Error handling
6. Integration with existing modules
7. Testing requirements

I should continue the numbered questions from 61 onwards.

## API Routes - Claude Code Instructions

### Context & Objective

You're building the **API Routes** for Scout, providing RESTful endpoints that expose all Scout functionality through a well-structured, secure, and performant HTTP interface. This layer coordinates between the web interface and core modules.

### Module Specifications

**Purpose**: Deliver a comprehensive REST API that enables all Scout operations, from profile management to document generation, with proper authentication, validation, and error handling.

**Key Responsibilities**:
1. Expose all module functionality through HTTP endpoints
2. Validate and sanitize input data
3. Manage authentication and authorization
4. Implement rate limiting and throttling
5. Coordinate module interactions
6. Handle errors gracefully with proper status codes
7. Provide comprehensive API documentation

### Technical Requirements

**Dependencies**:
- FastAPI for framework
- Pydantic for validation
- Python-Jose for JWT tokens (future)
- Slowapi for rate limiting
- Python-multipart for file uploads
- HTTPx for async HTTP client
- Passlib for API key hashing

**File Structure**:
```
scout/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── endpoints/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── profile.py
│   │   │   │   ├── jobs.py
│   │   │   │   ├── generation.py
│   │   │   │   ├── analysis.py
│   │   │   │   ├── system.py
│   │   │   │   └── documents.py
│   │   │   └── api.py          # Main router aggregator
│   │   ├── dependencies/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py         # Authentication deps
│   │   │   ├── database.py     # DB session deps
│   │   │   ├── services.py     # Service injection
│   │   │   └── rate_limit.py   # Rate limiting
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── cors.py
│   │   │   ├── logging.py
│   │   │   └── errors.py
│   │   └── schemas/            # Request/Response models
│   │       ├── __init__.py
│   │       ├── profile.py
│   │       ├── jobs.py
│   │       ├── generation.py
│   │       └── common.py
│   └── main.py                 # FastAPI app initialization
├── tests/
│   └── api/
│       ├── test_profile.py
│       ├── test_jobs.py
│       └── test_generation.py
└── docs/
    └── api/
        └── openapi.json
```

### Request/Response Schemas

Create comprehensive schemas in `app/api/schemas/`:

**Common Schemas** (`common.py`):
- HealthResponse with status, version, services health
- ErrorResponse with code, message, details, timestamp
- PaginationParams with offset, limit, sort_by, order
- SuccessResponse with message, data, metadata
- AsyncTaskResponse with task_id, status, progress
- CostSummaryResponse with daily, monthly, by_module breakdowns

**Profile Schemas** (`profile.py`):
- ProfileResponse with complete user profile
- ProfileUpdateRequest with partial update fields
- ExperienceCreateRequest with validation
- SkillAddRequest with proficiency levels
- ProfileSearchParams for filtering
- ProfileStatsResponse with analytics

**Jobs Schemas** (`jobs.py`):
- JobProcessRequest with raw content or URL
- JobProcessResponse with job_id, status, processed_data
- JobListResponse with pagination, filtering
- JobDetailResponse with full processed job
- JobSearchParams with keyword, date range
- JobBatchRequest for multiple jobs

**Generation Schemas** (`generation.py`):
- AnalysisRequest with job_id, profile_id, options
- AnalysisResponse with scores, gaps, recommendations
- GenerationRequest with document types, style preferences
- GenerationResponse with document URLs, previews
- RegenerationRequest for variations
- DownloadResponse with file URLs, expiry

### Endpoint Implementations

#### Profile Management Endpoints (`endpoints/profile.py`)

```python
# Key endpoints to implement:

@router.get("/", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    collector: Collector = Depends(get_collector)
):
    """Get current user profile with all sections"""

@router.put("/", response_model=ProfileResponse)
async def update_profile(
    updates: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    collector: Collector = Depends(get_collector)
):
    """Update profile fields with validation"""

@router.post("/experience", response_model=ExperienceResponse)
async def add_experience(
    experience: ExperienceCreateRequest,
    current_user: User = Depends(get_current_user),
    collector: Collector = Depends(get_collector)
):
    """Add new experience with vector indexing"""

@router.delete("/experience/{experience_id}")
async def delete_experience(
    experience_id: str,
    current_user: User = Depends(get_current_user),
    collector: Collector = Depends(get_collector)
):
    """Remove experience and update indexes"""

@router.post("/skills/batch", response_model=List[SkillResponse])
async def add_skills_batch(
    skills: List[SkillAddRequest],
    current_user: User = Depends(get_current_user),
    collector: Collector = Depends(get_collector)
):
    """Batch add skills with deduplication"""

@router.get("/export", response_model=ProfileExportResponse)
async def export_profile(
    format: str = Query("json", enum=["json", "yaml", "pdf"]),
    current_user: User = Depends(get_current_user)
):
    """Export profile in various formats"""
```

#### Job Processing Endpoints (`endpoints/jobs.py`)

```python
# Key endpoints to implement:

@router.post("/process", response_model=JobProcessResponse)
async def process_job(
    request: JobProcessRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    rinser: Rinser = Depends(get_rinser),
    limiter = Depends(RateLimiter(times=10, per=60))
):
    """Process raw job posting asynchronously"""

@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get processed job details with caching"""

@router.get("/", response_model=JobListResponse)
async def list_jobs(
    pagination: PaginationParams = Depends(),
    filters: JobSearchParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List processed jobs with filtering and pagination"""

@router.post("/batch", response_model=BatchProcessResponse)
async def batch_process_jobs(
    jobs: JobBatchRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    limiter = Depends(RateLimiter(times=5, per=60))
):
    """Process multiple jobs in batch"""

@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete job and associated data"""

@router.get("/{job_id}/similar", response_model=List[JobSummaryResponse])
async def find_similar_jobs(
    job_id: str,
    limit: int = Query(5, le=20),
    current_user: User = Depends(get_current_user),
    vector_store: VectorStore = Depends(get_vector_store)
):
    """Find similar jobs using vector similarity"""
```

#### Generation Endpoints (`endpoints/generation.py`)

```python
# Key endpoints to implement:

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_compatibility(
    request: AnalysisRequest,
    current_user: User = Depends(get_current_user),
    analyzer: Analyzer = Depends(get_analyzer),
    cache: CacheService = Depends(get_cache)
):
    """Analyze job-profile compatibility with caching"""

@router.post("/create", response_model=GenerationResponse)
async def generate_documents(
    request: GenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    creator: Creator = Depends(get_creator),
    formatter: Formatter = Depends(get_formatter),
    limiter = Depends(RateLimiter(times=5, per=60))
):
    """Generate tailored CV and cover letter"""

@router.get("/download/{task_id}", response_model=DownloadResponse)
async def get_download_links(
    task_id: str,
    current_user: User = Depends(get_current_user),
    export_manager: ExportManager = Depends(get_export_manager)
):
    """Get download URLs for generated documents"""

@router.post("/regenerate/{task_id}", response_model=GenerationResponse)
async def regenerate_variation(
    task_id: str,
    request: RegenerationRequest,
    current_user: User = Depends(get_current_user),
    creator: Creator = Depends(get_creator)
):
    """Generate variations of existing documents"""

@router.get("/preview/{document_id}")
async def preview_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    export_manager: ExportManager = Depends(get_export_manager)
):
    """Stream document preview"""

@router.post("/feedback/{task_id}")
async def submit_feedback(
    task_id: str,
    feedback: GenerationFeedback,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit feedback on generated documents"""
```

#### System Endpoints (`endpoints/system.py`)

```python
# Key endpoints to implement:

@router.get("/health", response_model=HealthResponse)
async def health_check(
    include_details: bool = Query(False),
    services: Dict = Depends(get_all_services)
):
    """Comprehensive health check with service status"""

@router.get("/costs", response_model=CostSummaryResponse)
async def get_cost_summary(
    period: str = Query("daily", enum=["daily", "weekly", "monthly"]),
    current_user: User = Depends(get_current_user),
    cost_tracker: CostTracker = Depends(get_cost_tracker)
):
    """Get cost breakdown and usage statistics"""

@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_statistics(
    current_user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache)
):
    """Get cache performance metrics"""

@router.post("/cache/clear")
async def clear_cache(
    namespace: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache)
):
    """Clear cache by namespace or entirely"""

@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(
    current_user: User = Depends(get_current_user)
):
    """Get system performance metrics"""

@router.get("/logs")
async def stream_logs(
    level: str = Query("INFO"),
    tail: int = Query(100),
    current_user: User = Depends(get_current_user)
):
    """Stream application logs"""
```

### Authentication & Security Implementation

**API Key Authentication** (`dependencies/auth.py`):
- Header-based API key validation
- Key hashing and storage
- Rate limiting per key
- Scope-based permissions
- Key rotation support
- Request signing validation

**Rate Limiting** (`dependencies/rate_limit.py`):
- Per-endpoint rate limits
- User-based quotas
- Sliding window algorithm
- Burst allowance
- Rate limit headers
- Graceful degradation

**CORS Configuration** (`middleware/cors.py`):
- Configurable origins
- Credential support
- Method restrictions
- Header whitelisting
- Preflight caching

### Error Handling Strategy

**Global Exception Handler** (`middleware/errors.py`):
- Structured error responses
- Error code mapping
- Stack trace in development
- Error logging with context
- Client-friendly messages
- Retry-after headers

**Standard Error Codes**:
- 400: Validation errors with field details
- 401: Authentication required
- 403: Insufficient permissions
- 404: Resource not found
- 429: Rate limit exceeded
- 500: Internal server error with tracking ID
- 503: Service temporarily unavailable

### Dependency Injection Setup

**Service Dependencies** (`dependencies/services.py`):
- Singleton service instances
- Lazy initialization
- Health check integration
- Graceful degradation
- Circuit breaker pattern
- Connection pooling

### Testing Requirements

1. **Endpoint Tests**: All CRUD operations, edge cases
2. **Authentication Tests**: Valid/invalid keys, permissions
3. **Validation Tests**: Request schemas, data types
4. **Rate Limit Tests**: Quota enforcement, reset
5. **Integration Tests**: Module coordination, workflows
6. **Performance Tests**: Latency, throughput, concurrent requests

### API Documentation

**OpenAPI/Swagger Integration**:
- Auto-generated from routes
- Interactive documentation at `/docs`
- ReDoc at `/redoc`
- Example requests/responses
- Authentication documentation
- Rate limit documentation

### Success Criteria

- Response time: <200ms for simple queries
- <2s for complex operations
- Rate limiting: Accurate to ±1 request
- Validation: 100% of invalid requests caught
- Documentation: 100% endpoint coverage
- Error rate: <0.1% 5xx errors
- Uptime: 99.9% availability

### Edge Cases to Handle

- Large file uploads
- Timeout for long-running operations
- Partial update conflicts
- Concurrent modification
- Invalid JSON payloads
- Missing required headers
- Malformed authentication
- Database connection loss
- Service unavailability
- Request body size limits

---

## Strategic Questions for API Design

**61. Should we implement API versioning from the start (v1, v2) or add it later?**
*Recommendation: Yes - Start with `/api/v1/` prefix to enable backward compatibility from day one.*

**62. Should we use JWT tokens or API keys for authentication in the PoC?**
*Recommendation: API keys for PoC simplicity, but structure auth to easily swap to JWT for production.*

**63. Should long-running operations return immediately with task IDs or wait for completion?**
*Recommendation: Return task IDs immediately for operations >2 seconds, implement polling/webhook for status.*

**64. Should we implement GraphQL alongside REST or REST-only?**
*Recommendation: REST-only for PoC, but structure responses to be GraphQL-friendly for future migration.*

**65. Should API responses include HAL/JSON-API hypermedia links?**
*Recommendation: No for PoC, but include a `links` field in responses for future hypermedia support.*

**66. Should we implement request/response compression at the API level?**
*Recommendation: Yes - Enable gzip compression for responses >1KB to reduce bandwidth usage.*

**67. Should rate limiting be global, per-endpoint, or both?**
*Recommendation: Both - Global limit of 1000/hour with per-endpoint limits for expensive operations.*

**68. Should we implement request retry logic in the API or leave it to clients?**
*Recommendation: Client responsibility, but provide clear retry-after headers and idempotency keys.*

**69. Should the API support batch operations for all endpoints or just specific ones?**
*Recommendation: Specific ones only (jobs, skills) where batch processing provides clear performance benefits.*

**70. Should we implement webhook callbacks for async operations?**
*Recommendation: Not for PoC, but design async responses to include optional webhook_url field for future.*