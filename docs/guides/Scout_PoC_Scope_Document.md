# Scout PoC - Scope Document

**Version:** 1.0  
**Created:** November 26, 2025  
**Status:** Approved - Authoritative Reference for Implementation

---

## Executive Summary

This document defines the **approved scope** for Scout's Proof of Concept implementation. It distinguishes between features that are essential for the PoC demonstration versus those deferred to post-PoC development. All implementation work should reference this document to avoid scope creep.

### PoC Objective

Demonstrate Scout's core value proposition: **intelligent job application generation through semantic matching and LLM-powered content creation**, deployed on edge hardware (Raspberry Pi 5).

### Key Scope Decisions

| Decision | Choice |
|----------|--------|
| ~~LLM Provider~~ | ~~Anthropic only (no OpenAI fallback)~~ |
| **LLM Provider** | **Ollama (Local) - Edge deployment focus** |
| **LLM Model** | **Qwen 2.5 3B primary, Gemma 2 2B fallback** |
| Caching | Memory + File (no Redis) |
| Pipeline Execution | Sequential only (no parallelism) |
| Notifications | In-app only (no email/SMS/push) |
| Job Input | Paste only (no URL fetching) |
| Document Output | PDF only (DOCX deferred) |
| Real-time Updates | Polling (no WebSocket) |

> **Architecture Update (December 2025):** Changed from Anthropic Claude API to
> local Ollama inference to support the thesis objective of edge computing on
> Raspberry Pi 5. See `docs/guides/Local_LLM_Transition_Guide.md` for details.

---

## Part 1: Architecture Overview (PoC)

### Simplified Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web Interface                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │Dashboard │ │  Jobs    │ │Generation│ │ Profile  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   API Routes (REST)                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                               │                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Pipeline Orchestrator (Sequential)          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                               │                                  │
│  ┌───────────┬───────────┬───────────┬───────────┬─────────┐   │
│  │ Collector │  Rinser   │ Analyzer  │  Creator  │Formatter│   │
│  └───────────┴───────────┴───────────┴───────────┴─────────┘   │
│                               │                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                      Services Layer                      │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │   LLM   │ │  Cost   │ │  Cache  │ │ Vector  │       │   │
│  │  │ Service │ │ Tracker │ │ Service │ │  Store  │       │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Data Layer                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  SQLite  │ │ ChromaDB │ │File Cache│ │  Files   │           │
│  │    DB    │ │ (Vectors)│ │  (JSON)  │ │ (Exports)│           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Removed from PoC Architecture

- ❌ Redis (distributed caching)
- ❌ Celery (distributed task queue)
- ❌ WebSocket server (real-time updates)
- ❌ SMTP server (email notifications)
- ❌ External notification services (Twilio, push providers)
- ❌ ~~OpenAI API integration~~ Cloud LLM APIs (Anthropic/OpenAI)

### Added to PoC Architecture (December 2025)

- ✅ **Ollama** - Local LLM inference server
- ✅ **Qwen 2.5 3B** - Primary local model (Q4 quantized, ~2GB)
- ✅ **Gemma 2 2B** - Fallback local model (~1.6GB)

---

## Part 2: Service Specifications (PoC Scope)

### S1: LLM Service

> **Updated December 2025:** Changed from Anthropic Claude API to local Ollama inference.

#### In Scope (PoC)

| Feature | Implementation |
|---------|----------------|
| **Ollama local provider** | Full implementation with provider abstraction |
| **Qwen 2.5 3B model** | Primary model (Q4 quantized) |
| **Gemma 2 2B model** | Fallback model for reliability |
| Mock provider | For testing only |
| Token counting | Track usage for metrics (no billing) |
| Response caching | Integration with Cache Service |
| Basic retry logic | 3 attempts, 1s/2s/4s delays (simple exponential) |
| JSON response parsing | Ollama JSON mode + schema constraints |
| Usage reporting | Report metrics to Cost Tracker Service |

#### Out of Scope (Deferred)

| Feature | Reason |
|---------|--------|
| ~~Anthropic provider~~ | Replaced with local Ollama |
| Cloud API fallback | Local-only for thesis edge computing focus |
| Model selection UI | Config-based selection sufficient |
| Complex retry strategies | Basic retry sufficient for PoC |
| Streaming responses | Not needed for PoC |
| Hardware acceleration (NPU) | Future enhancement |

#### PoC Implementation Notes

```python
# Local LLM Service configuration
class LLMServiceConfig:
    provider: str = "ollama"  # Local Ollama inference
    model: str = "qwen2.5:3b"  # Primary model
    fallback_model: str = "gemma2:2b"  # Fallback
    ollama_host: str = "http://localhost:11434"
    max_retries: int = 3
    retry_delays: list = [1, 2, 4]  # seconds
    timeout: int = 120  # Longer for local inference
    temperature: float = 0.3
    max_tokens: int = 2000
```

#### Performance Expectations (Raspberry Pi 5, 8GB)

| Model | Speed | RAM Usage |
|-------|-------|-----------|
| Qwen 2.5 3B (Q4) | 2-4 tok/s | ~3GB |
| Gemma 2 2B | 4-6 tok/s | ~2GB |

**Estimated pipeline time:** 15-30 minutes (vs <2 min with cloud API)

---

### S2: Cost Tracker Service

#### In Scope (PoC)

| Feature | Implementation |
|---------|----------------|
| Daily budget limit | Hard stop when exceeded |
| Monthly budget limit | Hard stop when exceeded |
| Total cost tracking | Aggregate across all requests |
| Budget status check | Before each LLM request |
| Basic persistence | JSON file for session recovery |
| Simple cost display | "Spent $X of $Y today" format |

#### Out of Scope (Deferred)

| Feature | Reason |
|---------|--------|
| Per-module cost breakdown | Enhancement; totals sufficient |
| Cost history analytics | Enhancement; basic display sufficient |
| Cost projection/forecasting | Not MVP-critical |
| Real-time cost alerts | Polling check sufficient |
| Detailed audit logging | Per-request logging unnecessary |

#### PoC Implementation Notes

```python
# Simplified Cost Tracker
class CostTrackerConfig:
    daily_limit: float = 10.00
    monthly_limit: float = 50.00
    persistence_file: str = "data/cost_tracker.json"
    
class CostStatus:
    daily_spent: float
    daily_limit: float
    monthly_spent: float
    monthly_limit: float
    can_proceed: bool  # Simple boolean check
```

---

### S3: Cache Service

#### In Scope (PoC)

| Feature | Implementation |
|---------|----------------|
| Memory cache (L1) | Python LRU cache, 100 entries |
| File cache (L2) | JSON files in `data/cache/` |
| Exact-match lookup | Hash-based cache keys |
| Global TTL | Single TTL value (1 hour default) |
| Cache hit/miss counting | Basic statistics |
| Manual cache clear | Admin function |

#### Out of Scope (Deferred)

| Feature | Reason |
|---------|--------|
| Redis integration | Infrastructure complexity |
| Semantic similarity caching | Complex; exact-match provides 80% value |
| Per-entry TTL | Global TTL sufficient |
| Cache warming | Not needed at PoC scale |
| Detailed cache analytics | Basic stats sufficient |
| Cache eviction strategies | LRU sufficient |

#### PoC Implementation Notes

```python
# Simplified Cache Service
class CacheConfig:
    memory_max_entries: int = 100
    file_cache_dir: str = "data/cache"
    default_ttl: int = 3600  # 1 hour
    
# Cache key generation: MD5 hash of request parameters
# Storage format: {cache_key}.json with metadata + response
```

---

### S4: Vector Store Service

#### In Scope (PoC)

| Feature | Implementation |
|---------|----------------|
| ChromaDB integration | Persistent storage |
| Embedding model | all-MiniLM-L6-v2 (384 dimensions) |
| Collections | 2 only: `user_profiles`, `job_requirements` |
| Similarity search | Cosine similarity, top-k results |
| Sequential processing | One embedding at a time |
| Basic metadata filtering | Simple key-value filters |

#### Out of Scope (Deferred)

| Feature | Reason |
|---------|--------|
| FAISS secondary index | ChromaDB sufficient for PoC scale |
| Batch embedding optimization | Sequential processing acceptable |
| Multiple embedding models | Single model sufficient |
| Cross-collection search | Not needed for PoC workflow |
| Index optimization (IVF/HNSW) | <10K vectors doesn't need it |
| Embedding versioning | Single version for PoC |
| 5 collections | 2 collections sufficient |

#### PoC Implementation Notes

```python
# Simplified Vector Store
class VectorStoreConfig:
    persist_directory: str = "data/vectors"
    embedding_model: str = "all-MiniLM-L6-v2"
    collections: list = ["user_profiles", "job_requirements"]
    similarity_metric: str = "cosine"
    default_top_k: int = 10
```

---

### S6: Pipeline Orchestrator

#### In Scope (PoC)

| Feature | Implementation |
|---------|----------------|
| Sequential task execution | Ordered list of tasks |
| Single pipeline definition | "Job Application Pipeline" |
| Basic progress tracking | Percentage complete |
| Simple error handling | Stop on failure, report error |
| Basic retry | Retry failed task up to 3 times |
| Task timeout | 60 seconds per task default |

#### Out of Scope (Deferred)

| Feature | Reason |
|---------|--------|
| Parallel execution | Sequential sufficient; no parallelizable tasks |
| DAG-based dependencies | Ordered list sufficient |
| Celery integration | Single-machine execution sufficient |
| Checkpointing/resume | Restart acceptable for PoC |
| Multiple pipeline templates | Single pipeline sufficient |
| Resource management | OS-level management sufficient |
| Pipeline metrics/analytics | Basic timing logs sufficient |

#### PoC Implementation Notes

```python
# Simplified Pipeline - Ordered Task List
JOB_APPLICATION_PIPELINE = [
    {"id": "load_profile", "module": "collector", "function": "load_profile"},
    {"id": "process_job", "module": "rinser", "function": "process_job"},
    {"id": "analyze", "module": "analyzer", "function": "analyze"},
    {"id": "generate_cv", "module": "creator", "function": "generate_cv"},
    {"id": "generate_cover", "module": "creator", "function": "generate_cover_letter"},
    {"id": "format_documents", "module": "formatter", "function": "format_pdf"},
]

class PipelineStatus:
    current_task: int
    total_tasks: int
    progress_percent: float
    status: str  # "running", "completed", "failed"
    error: Optional[str]
```

---

### S7: Content Optimizer Service

#### PoC Status: ENTIRELY DEFERRED

The Content Optimizer Service is **not implemented** in the PoC. Its functionality (ATS optimization, readability scoring, grammar checking) is deferred to post-PoC.

**Rationale:** The Creator module's LLM-generated output is sufficient quality for demonstration. Optimization is an enhancement layer.

---

### S8: Notification Service

#### In Scope (PoC)

| Feature | Implementation |
|---------|----------------|
| In-app notifications | Toast/alert messages in UI |
| Notification types | Info, Success, Warning, Error |
| Session-only storage | No persistence |
| Simple display | Stack of recent notifications |

#### Out of Scope (Deferred)

| Feature | Reason |
|---------|--------|
| Email notifications | Infrastructure complexity |
| SMS notifications | Not needed for single-user PoC |
| Push notifications | Not needed for single-user PoC |
| Webhook notifications | Not needed for PoC |
| Notification preferences | Single channel = no preferences |
| Notification history | Session-only sufficient |
| Delivery tracking | Not applicable |

#### PoC Implementation Notes

```python
# Simplified Notification - In-App Only
class Notification:
    id: str
    type: str  # "info", "success", "warning", "error"
    title: str
    message: str
    timestamp: datetime
    dismissed: bool = False

# UI displays as toast notifications, auto-dismiss after 5 seconds
# Error notifications persist until manually dismissed
```

---

## Part 3: Module Specifications (PoC Scope)

### Module 1: Collector

#### In Scope (PoC)

| Feature | Implementation |
|---------|----------------|
| YAML profile loading | Single `profile.yaml` file |
| Profile validation | Pydantic model validation |
| Profile indexing | Store embeddings in Vector Store |
| Experience/skill access | Query methods for Analyzer |

#### Out of Scope (Deferred)

| Feature | Reason |
|---------|--------|
| Profile versioning | Single version sufficient |
| Incremental updates | Full reload acceptable |
| Multiple profile formats | YAML only |
| Profile import/export | Manual YAML editing |

---

### Module 2: Rinser

#### In Scope (PoC)

| Feature | Implementation |
|---------|----------------|
| HTML sanitization | Bleach library |
| Plain text extraction | BeautifulSoup |
| Structure extraction | LLM-powered parsing |
| Requirement identification | Must-have vs nice-to-have |
| Basic format support | Plain text, basic HTML |

#### Out of Scope (Deferred)

| Feature | Reason |
|---------|--------|
| URL content fetching | Avoids scraping complexity |
| PDF parsing | Text input only |
| Multi-language support | English only for PoC |
| Advanced HTML parsing | Basic extraction sufficient |

#### PoC Input Method

```
User pastes job posting text directly into web interface.
No URL fetching, no file upload, no scraping.
```

---

### Module 3: Analyzer

#### In Scope (PoC)

| Feature | Implementation |
|---------|----------------|
| Semantic matching | Vector similarity via ChromaDB |
| Skill matching | Compare profile skills to requirements |
| Experience relevance | Score experience against job |
| Gap analysis | Identify missing qualifications |
| Strategy generation | LLM-powered recommendations |
| Compatibility scoring | Single algorithm, 0-100 scale |

#### Out of Scope (Deferred)

| Feature | Reason |
|---------|--------|
| Multiple scoring algorithms | Single algorithm sufficient |
| Feedback loop learning | Static scoring for PoC |
| Historical comparison | No history in PoC |
| Confidence calibration | Enhancement feature |

---

### Module 4: Creator

#### In Scope (PoC)

| Feature | Implementation |
|---------|----------------|
| CV generation | LLM-powered, single pass |
| Cover letter generation | LLM-powered, single pass |
| Keyword incorporation | Include from Analyzer |
| Professional tone | Single tone style |
| Section generation | Standard CV/CL sections |

#### Out of Scope (Deferred)

| Feature | Reason |
|---------|--------|
| Multiple tone options | Single professional tone |
| Iterative refinement | Single-pass generation |
| Multiple variants | Single output per type |
| User edit integration | Regenerate if changes needed |

---

### Module 5: Formatter

#### In Scope (PoC)

| Feature | Implementation |
|---------|----------------|
| PDF generation | WeasyPrint |
| HTML to PDF | Jinja2 templates → WeasyPrint |
| Template application | 1-2 predefined templates |
| Professional styling | Clean, ATS-friendly design |

#### Out of Scope (Deferred)

| Feature | Reason |
|---------|--------|
| DOCX generation | PDF covers primary use case |
| Multiple templates | 1-2 templates sufficient |
| Custom template upload | Predefined only |
| Template editing | Static templates |

#### PoC Templates

```
Templates included:
1. modern_cv.html - Clean, modern CV layout
2. standard_cover.html - Professional cover letter

Output format: PDF only
```

---

## Part 4: Web Interface (PoC Scope)

### Pages Included

| Page | Features |
|------|----------|
| **Dashboard** | Profile status, cost summary, quick actions |
| **Profile View** | Display loaded profile, basic edit link |
| **Job Processing** | Paste job text, trigger processing |
| **Analysis Results** | Display match score, gaps, strategy |
| **Generation** | Generate CV/Cover Letter, preview |
| **Download** | Download generated PDF |

### Pages Deferred

| Page | Reason |
|------|--------|
| Analytics Dashboard | Enhancement feature |
| Settings/Preferences | Hardcoded defaults |
| Job History | No persistence in PoC |
| Template Management | Predefined templates only |

### Technical Approach

| Aspect | PoC Implementation |
|--------|-------------------|
| Templating | Jinja2 |
| Styling | Tailwind CSS |
| Interactivity | Alpine.js (minimal) |
| Dynamic updates | HTMX with polling (no WebSocket) |
| Status updates | 3-second polling interval |

---

## Part 5: Data Persistence (PoC Scope)

### Storage Strategy

| Data Type | Storage | Persistence |
|-----------|---------|-------------|
| User Profile | `data/profile.yaml` | Persistent (user-managed) |
| Vector Embeddings | `data/vectors/` (ChromaDB) | Persistent |
| LLM Cache | `data/cache/*.json` | Persistent (with TTL) |
| Cost Tracking | `data/cost_tracker.json` | Persistent |
| Generated Documents | `data/exports/` | Persistent |
| Session State | Memory | Session only |
| Notifications | Memory | Session only |

### Database Usage

SQLite is available but minimally used in PoC:
- Job processing history: **Deferred** (no persistence)
- User preferences: **Deferred** (hardcoded)
- Analytics data: **Deferred**

Primary data storage relies on file system for simplicity.

---

## Part 6: Dependencies (PoC)

### Python Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.11"

# Web Framework
fastapi = "^0.110.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
jinja2 = "^3.1.3"
python-multipart = "^0.0.9"

# Data Validation
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"

# LLM Integration (Local Ollama)
ollama = "^0.4.0"
# anthropic - removed, using local inference

# Vector Store
chromadb = "^0.4.22"
sentence-transformers = "^2.3.0"

# Document Processing
bleach = "^6.1.0"
beautifulsoup4 = "^4.12.0"
weasyprint = "^61.0"
pyyaml = "^6.0.1"

# Utilities
httpx = "^0.26.0"
numpy = "^1.26.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.23.0"
pytest-cov = "^4.1.0"
black = "^24.1.0"
isort = "^5.13.0"
mypy = "^1.8.0"
```

### Removed Dependencies

| Dependency | Reason |
|------------|--------|
| `redis` | No Redis caching |
| `celery` | No distributed execution |
| `openai` | No cloud API fallback |
| `anthropic` | Replaced with local Ollama |
| `tiktoken` | Not needed for local inference |
| `websockets` | Polling instead |
| `twilio` | No SMS notifications |
| `apscheduler` | No scheduled tasks |
| `networkx` | No DAG processing |

### Added Dependencies (December 2025)

| Dependency | Reason |
|------------|--------|
| `ollama` | Local LLM inference client |

### System Dependencies

```bash
# For WeasyPrint PDF generation
apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info

# For Ollama local LLM (required)
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull qwen2.5:3b
ollama pull gemma2:2b
```

---

## Part 7: Implementation Order

### Phase 1: Foundation Services

```
1. S2 Cost Tracker Service (simplest, no dependencies)
2. S3 Cache Service (depends on file system only)
3. S4 Vector Store Service (depends on ChromaDB)
4. S1 LLM Service (depends on Cost Tracker, Cache)
```

### Phase 2: Core Modules

```
5. M1 Collector (depends on Vector Store)
6. M2 Rinser (depends on LLM Service)
7. M3 Analyzer (depends on Collector, Vector Store, LLM)
8. M4 Creator (depends on LLM Service, Analyzer output)
9. M5 Formatter (depends on Creator output)
```

### Phase 3: Integration

```
10. S6 Pipeline Orchestrator (integrates all modules)
11. API Routes (exposes pipeline functionality)
12. S8 Notification Service (simple, in-app only)
13. Web Interface (consumes API)
```

### Phase 4: Testing & Polish

```
14. Integration testing
15. End-to-end testing
16. Documentation
17. Deployment packaging
```

---

## Part 8: Success Criteria (PoC)

### Functional Requirements

| Requirement | Acceptance Criteria |
|-------------|---------------------|
| Profile Loading | Load YAML profile, display in UI |
| Job Processing | Paste text, extract structured data |
| Analysis | Generate match score, identify gaps |
| CV Generation | Produce tailored CV content |
| Cover Letter | Produce tailored cover letter |
| PDF Output | Download professional PDF document |
| Cost Control | Stop processing when budget exceeded |

### Performance Targets

| Metric | Target |
|--------|--------|
| Job processing time | < 30 seconds |
| Full pipeline (paste to PDF) | < 2 minutes |
| UI responsiveness | < 500ms for interactions |
| Memory usage | < 2GB total |

### Quality Gates

| Gate | Requirement |
|------|-------------|
| Unit test coverage | > 70% |
| All tests passing | 100% |
| No critical security issues | Verified |
| Documentation complete | All modules documented |

---

## Part 9: Explicitly Out of Scope

### Features NOT in PoC

| Feature | Category | Rationale |
|---------|----------|-----------|
| OpenAI fallback | LLM | Complexity reduction |
| Model selection | LLM | Single model sufficient |
| Redis caching | Cache | Infrastructure reduction |
| Semantic cache | Cache | Exact-match sufficient |
| Parallel execution | Pipeline | Sequential sufficient |
| Checkpointing | Pipeline | Restart acceptable |
| Email notifications | Notification | In-app sufficient |
| SMS/Push | Notification | Not needed |
| Content Optimizer | Service | Enhancement, not core |
| URL fetching | Input | Avoids scraping issues |
| DOCX output | Output | PDF sufficient |
| WebSocket | UI | Polling sufficient |
| Analytics pages | UI | Basic display sufficient |
| Job history | Persistence | No history needed |
| Multiple templates | Formatter | 1-2 sufficient |

### Features for Post-PoC

These features should be considered for the next phase:

1. **Multi-provider LLM** - OpenAI fallback for reliability
2. **Distributed caching** - Redis for multi-user scenarios
3. **Parallel pipelines** - Performance optimization
4. **Email notifications** - User preference
5. **Content optimization** - Quality enhancement
6. **Job URL fetching** - Convenience feature
7. **DOCX output** - Format flexibility
8. **Advanced analytics** - Usage insights
9. **Template customization** - User flexibility
10. **Edge model deployment** - Thesis core objective

---

## Part 10: Reference Checklist

### Pre-Implementation Checklist

- [ ] Development environment configured (Pi 5 or dev machine)
- [ ] Python 3.11+ installed
- [ ] Poetry installed and configured
- [ ] System dependencies installed (WeasyPrint)
- [ ] Anthropic API key obtained
- [ ] Project structure created
- [ ] Git repository initialized

### Per-Module Implementation Checklist

- [ ] Read this scope document section for the module
- [ ] Read the detailed module specification
- [ ] Implement core functionality only (PoC scope)
- [ ] Write unit tests (>70% coverage)
- [ ] Document public interfaces
- [ ] Integration test with dependent modules

### Pre-Deployment Checklist

- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] End-to-end workflow verified
- [ ] Cost limits tested
- [ ] Error handling verified
- [ ] Documentation complete
- [ ] Docker build successful (if applicable)

---

## Appendix A: File Structure (PoC)

```
scout/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── profile.py
│   │   │   ├── jobs.py
│   │   │   └── generation.py
│   │   └── dependencies.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── collector.py
│   │   ├── rinser.py
│   │   ├── analyzer.py
│   │   ├── creator.py
│   │   ├── formatter.py
│   │   └── pipeline.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── profile.py
│   │   ├── job.py
│   │   ├── analysis.py
│   │   ├── generation.py
│   │   └── common.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm.py
│   │   ├── cost_tracker.py
│   │   ├── cache.py
│   │   ├── vector_store.py
│   │   └── notification.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── logging.py
│   └── utils/
│       ├── __init__.py
│       ├── validators.py
│       └── exceptions.py
├── templates/
│   ├── base/
│   │   └── layout.html
│   ├── pages/
│   │   ├── dashboard.html
│   │   ├── profile.html
│   │   ├── jobs.html
│   │   ├── analysis.html
│   │   ├── generation.html
│   │   └── download.html
│   ├── components/
│   │   ├── alerts.html
│   │   ├── navigation.html
│   │   └── progress.html
│   └── documents/
│       ├── cv_modern.html
│       └── cover_letter.html
├── static/
│   ├── css/
│   │   └── main.css
│   └── js/
│       └── app.js
├── prompts/
│   ├── extraction/
│   │   └── job_structure.txt
│   ├── analysis/
│   │   ├── gap_analysis.txt
│   │   └── strategy.txt
│   └── generation/
│       ├── cv.txt
│       └── cover_letter.txt
├── data/
│   ├── profile.yaml
│   ├── profile.example.yaml
│   ├── vectors/
│   ├── cache/
│   ├── exports/
│   └── cost_tracker.json
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_collector.py
│   │   ├── test_rinser.py
│   │   ├── test_analyzer.py
│   │   ├── test_creator.py
│   │   ├── test_formatter.py
│   │   └── services/
│   │       ├── test_llm.py
│   │       ├── test_cache.py
│   │       ├── test_cost_tracker.py
│   │       └── test_vector_store.py
│   ├── integration/
│   │   ├── test_pipeline.py
│   │   └── test_api.py
│   └── fixtures/
│       ├── sample_job.txt
│       └── sample_profile.yaml
├── .env.example
├── .gitignore
├── pyproject.toml
├── Makefile
├── README.md
└── docker/
    ├── Dockerfile
    └── docker-compose.yml
```

---

## Appendix B: Configuration Defaults (PoC)

### Environment Variables

```bash
# .env.example for PoC

# Application
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=generate-with-openssl-rand-hex-32

# Ollama Local LLM (REQUIRED - no API key needed)
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:3b
LLM_FALLBACK_MODEL=gemma2:2b
OLLAMA_HOST=http://localhost:11434

# LLM Configuration
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2000
LLM_TIMEOUT=120

# Note: No cost control needed - local inference is free
# Cost tracker now tracks usage metrics only

# Cache
CACHE_TTL=3600
CACHE_MAX_MEMORY_ENTRIES=100

# Vector Store
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Logging
LOG_LEVEL=INFO
```

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-26 | Initial approved scope document |
| 1.1 | 2025-12-13 | Changed LLM provider from Anthropic API to local Ollama (Qwen 2.5 3B / Gemma 2 2B) |

---

**This document is the authoritative reference for Scout PoC implementation. All scope questions should be resolved by consulting this document first.**
