# Scout PoC - Implementation Checklist

**Purpose:** Step-by-step implementation guide for Claude Code  
**Methodology:** Each step follows the RAVE cycle (Review → Analyze → Verify → Execute)

---

## How to Use This Checklist

For each step:
1. **Review**: Read the step description, check dependencies are complete
2. **Analyze**: Understand exactly what needs to be implemented
3. **Implement**: Write the code for this step only
4. **Verify**: Run checks before marking complete

Mark steps as:
- `[ ]` Not started
- `[~]` In progress
- `[x]` Complete and verified

---

## Phase 1: Foundation Services

### S2: Cost Tracker Service

**Specification:** `docs/S2_Cost_Tracker_Service_-_Claude_Code_Instructions.md`  
**Target Files:** `app/models/cost.py`, `app/services/cost_tracker.py`, `tests/unit/services/test_cost_tracker.py`

#### Step 2.1: Data Models
```
Files: app/models/cost.py

Create:
- [ ] CostEntry model (timestamp, tokens, cost, module, provider)
- [ ] CostSummary model (daily_spent, daily_limit, monthly_spent, monthly_limit, can_proceed)
- [ ] CostTrackerHealth model (status, daily_percentage, monthly_percentage)

Verify:
  python -c "from app.models.cost import CostEntry, CostSummary; print('OK')"
```

#### Step 2.2: Configuration
```
Files: app/config/settings.py

Add:
- [ ] max_daily_spend: float = 10.00
- [ ] max_monthly_spend: float = 50.00
- [ ] cost_tracker_file: Path = Path("data/cost_tracker.json")

Verify:
  python -c "from app.config.settings import settings; print(settings.max_daily_spend)"
```

#### Step 2.3: Exceptions
```
Files: app/utils/exceptions.py

Add:
- [ ] CostTrackerError(ScoutError)
- [ ] BudgetExceededError(CostTrackerError)

Verify:
  python -c "from app.utils.exceptions import BudgetExceededError; raise BudgetExceededError('test')" 2>&1 | grep -q "test"
```

#### Step 2.4: Service - Initialization
```
Files: app/services/cost_tracker.py

Implement:
- [ ] CostTrackerService class with __init__
- [ ] _load_from_file() method - load persisted state
- [ ] _save_to_file() method - persist state
- [ ] initialize() method - load state, check dates, reset if needed

Verify:
  python -c "from app.services.cost_tracker import CostTrackerService; s = CostTrackerService(); print('OK')"
```

#### Step 2.5: Service - Core Operations
```
Files: app/services/cost_tracker.py

Implement:
- [ ] can_proceed() -> bool - check if budget allows operation
- [ ] record_cost(tokens, cost, module) - record a cost entry
- [ ] get_summary() -> CostSummary - get current status

Verify:
  pytest tests/unit/services/test_cost_tracker.py::TestCoreOperations -v
```

#### Step 2.6: Service - Budget Management
```
Files: app/services/cost_tracker.py

Implement:
- [ ] _check_daily_reset() - reset if new day
- [ ] _check_monthly_reset() - reset if new month
- [ ] estimate_cost(input_tokens, output_tokens, model) -> float

Verify:
  pytest tests/unit/services/test_cost_tracker.py::TestBudgetManagement -v
```

#### Step 2.7: Service - Health Check
```
Files: app/services/cost_tracker.py

Implement:
- [ ] health_check() -> CostTrackerHealth

Verify:
  pytest tests/unit/services/test_cost_tracker.py::TestHealthCheck -v
```

#### Step 2.8: Dependency Injection
```
Files: app/services/cost_tracker.py

Implement:
- [ ] get_cost_tracker() -> CostTrackerService (FastAPI dependency)
- [ ] Global singleton pattern

Verify:
  python -c "from app.services.cost_tracker import get_cost_tracker; import asyncio; asyncio.run(get_cost_tracker())"
```

#### Step 2.9: Unit Tests
```
Files: tests/unit/services/test_cost_tracker.py

Create:
- [ ] Fixtures (service, initialized_service)
- [ ] TestInitialization (load, save, date reset)
- [ ] TestCoreOperations (can_proceed, record_cost, get_summary)
- [ ] TestBudgetManagement (daily reset, monthly reset, budget exceeded)
- [ ] TestEdgeCases (file corruption, concurrent access)

Verify:
  pytest tests/unit/services/test_cost_tracker.py -v --cov=app/services/cost_tracker
```

---

### S3: Cache Service

**Specification:** `docs/S3_Cache_Service_-_Claude_Code_Instructions.md`  
**Target Files:** `app/models/cache.py`, `app/services/cache.py`, `tests/unit/services/test_cache.py`

#### Step 3.1: Data Models
```
Files: app/models/cache.py

Create:
- [ ] CacheEntry model (key, value, created_at, expires_at, hit_count)
- [ ] CacheStats model (hits, misses, size, hit_rate)
- [ ] CacheHealth model (status, memory_entries, file_entries, stats)

Verify:
  python -c "from app.models.cache import CacheEntry, CacheStats; print('OK')"
```

#### Step 3.2: Configuration
```
Files: app/config/settings.py

Add:
- [ ] cache_dir: Path = Path("data/cache")
- [ ] cache_memory_max_entries: int = 100
- [ ] cache_default_ttl: int = 3600

Verify:
  python -c "from app.config.settings import settings; print(settings.cache_dir)"
```

#### Step 3.3: Service - Initialization
```
Files: app/services/cache.py

Implement:
- [ ] CacheService class with __init__
- [ ] initialize() - create cache dir, load stats
- [ ] shutdown() - persist pending writes
- [ ] _memory_cache: Dict[str, CacheEntry] with LRU behavior

Verify:
  python -c "from app.services.cache import CacheService; s = CacheService(); print('OK')"
```

#### Step 3.4: Service - Memory Cache Operations
```
Files: app/services/cache.py

Implement:
- [ ] _get_from_memory(key) -> Optional[Any]
- [ ] _set_in_memory(key, value, ttl)
- [ ] _evict_oldest() - LRU eviction when full

Verify:
  pytest tests/unit/services/test_cache.py::TestMemoryCache -v
```

#### Step 3.5: Service - File Cache Operations
```
Files: app/services/cache.py

Implement:
- [ ] _get_from_file(key) -> Optional[Any]
- [ ] _set_in_file(key, value, ttl)
- [ ] _generate_cache_key(data) -> str (MD5 hash)
- [ ] _is_expired(entry) -> bool

Verify:
  pytest tests/unit/services/test_cache.py::TestFileCache -v
```

#### Step 3.6: Service - Public API
```
Files: app/services/cache.py

Implement:
- [ ] get(key) -> Optional[Any] - check memory then file
- [ ] set(key, value, ttl=None) - write to both tiers
- [ ] delete(key) - remove from both tiers
- [ ] clear() - clear all caches

Verify:
  pytest tests/unit/services/test_cache.py::TestPublicAPI -v
```

#### Step 3.7: Service - Stats & Health
```
Files: app/services/cache.py

Implement:
- [ ] get_stats() -> CacheStats
- [ ] health_check() -> CacheHealth

Verify:
  pytest tests/unit/services/test_cache.py::TestHealth -v
```

#### Step 3.8: Dependency Injection
```
Files: app/services/cache.py

Implement:
- [ ] get_cache_service() -> CacheService
- [ ] Global singleton pattern

Verify:
  python -c "from app.services.cache import get_cache_service; import asyncio; asyncio.run(get_cache_service())"
```

#### Step 3.9: Unit Tests
```
Files: tests/unit/services/test_cache.py

Create:
- [ ] Fixtures with tmp_path for file cache
- [ ] TestMemoryCache (get, set, eviction, expiry)
- [ ] TestFileCache (get, set, persistence)
- [ ] TestPublicAPI (tiered lookup, delete, clear)
- [ ] TestEdgeCases (corrupted files, unicode keys)

Verify:
  pytest tests/unit/services/test_cache.py -v --cov=app/services/cache
```

---

### S4: Vector Store Service

**Specification:** `docs/S4_Vector_Store_Service_-_Claude_Code_Instructions.md`  
**Target Files:** `app/models/vectors.py`, `app/services/vector_store.py`, `tests/unit/services/test_vector_store.py`

#### Step 4.1: Data Models
```
Files: app/models/vectors.py

Create:
- [ ] CollectionName enum (USER_PROFILES, JOB_REQUIREMENTS)
- [ ] EmbeddingMetadata model (source_type, source_id, text_preview, ...)
- [ ] VectorEntry model (id, text, embedding, metadata, collection)
- [ ] SearchQuery model (text, collection, top_k, threshold, filters)
- [ ] SearchResult model (id, text, score, distance, metadata)
- [ ] SearchResults model (query_text, results, total_found, search_time_ms)

Verify:
  python -c "from app.models.vectors import CollectionName, VectorEntry; print('OK')"
```

#### Step 4.2: More Data Models
```
Files: app/models/vectors.py

Create:
- [ ] CollectionStats model (name, count, source_types, categories)
- [ ] VectorStoreHealth model (status, chromadb_connected, embedding_model_loaded)
- [ ] AddResult model (success, collection, entries_added, ids, errors)
- [ ] DeleteResult model (success, collection, entries_deleted, ids_deleted)

Verify:
  python -c "from app.models.vectors import CollectionStats, AddResult; print('OK')"
```

#### Step 4.3: Configuration
```
Files: app/config/settings.py

Add:
- [ ] vector_db_path: Path = Path("data/vectors")
- [ ] embedding_model: str = "all-MiniLM-L6-v2"
- [ ] embedding_cache_size: int = 500

Verify:
  python -c "from app.config.settings import settings; print(settings.embedding_model)"
```

#### Step 4.4: Exceptions
```
Files: app/utils/exceptions.py

Add:
- [ ] VectorStoreError(ScoutError)
- [ ] EmbeddingError(VectorStoreError)
- [ ] CollectionNotFoundError(VectorStoreError)
- [ ] SearchError(VectorStoreError)

Verify:
  python -c "from app.utils.exceptions import EmbeddingError; print('OK')"
```

#### Step 4.5: Service - Initialization
```
Files: app/services/vector_store.py

Implement:
- [ ] VectorStoreService class with __init__
- [ ] initialize() - create dirs, init ChromaDB, load embedding model
- [ ] shutdown() - persist and cleanup
- [ ] _ensure_initialized() helper

Verify:
  python -c "from app.services.vector_store import VectorStoreService; s = VectorStoreService(); print('OK')"
```

#### Step 4.6: Service - Embedding Operations
```
Files: app/services/vector_store.py

Implement:
- [ ] _generate_embedding(text) with @lru_cache
- [ ] generate_embedding(text) -> List[float] (public async wrapper)
- [ ] get_embedding_cache_stats() -> Dict

Verify:
  pytest tests/unit/services/test_vector_store.py::TestEmbedding -v
```

#### Step 4.7: Service - Collection Add Operations
```
Files: app/services/vector_store.py

Implement:
- [ ] _get_collection(name) -> chromadb.Collection
- [ ] add_entry(entry) -> AddResult
- [ ] add_entries(entries) -> AddResult

Verify:
  pytest tests/unit/services/test_vector_store.py::TestAddOperations -v
```

#### Step 4.8: Service - Collection Get/Delete Operations
```
Files: app/services/vector_store.py

Implement:
- [ ] get_entry(collection, id) -> Optional[VectorEntry]
- [ ] delete_entries(collection, ids) -> DeleteResult
- [ ] clear_collection(collection) -> DeleteResult
- [ ] get_collection_stats(collection) -> CollectionStats

Verify:
  pytest tests/unit/services/test_vector_store.py::TestCollectionOperations -v
```

#### Step 4.9: Service - Search Operations
```
Files: app/services/vector_store.py

Implement:
- [ ] search(query: SearchQuery) -> SearchResults
- [ ] search_similar(text, collection, top_k, threshold) -> SearchResults
- [ ] find_matching_skills(requirement_text) -> SearchResults
- [ ] find_matching_experiences(requirement_text) -> SearchResults

Verify:
  pytest tests/unit/services/test_vector_store.py::TestSearch -v
```

#### Step 4.10: Service - Health Check
```
Files: app/services/vector_store.py

Implement:
- [ ] health_check() -> VectorStoreHealth

Verify:
  pytest tests/unit/services/test_vector_store.py::TestHealth -v
```

#### Step 4.11: Dependency Injection
```
Files: app/services/vector_store.py

Implement:
- [ ] get_vector_store() -> VectorStoreService
- [ ] shutdown_vector_store()
- [ ] Global singleton pattern

Verify:
  python -c "from app.services.vector_store import get_vector_store; import asyncio; asyncio.run(get_vector_store())"
```

#### Step 4.12: Unit Tests
```
Files: tests/unit/services/test_vector_store.py

Create:
- [ ] Fixtures (vector_store, initialized_vector_store with tmp_path)
- [ ] TestInitialization
- [ ] TestEmbedding (generation, caching, normalization)
- [ ] TestCollectionOperations (add, get, delete, clear, stats)
- [ ] TestSearch (basic, threshold, filters, ordering)
- [ ] TestEdgeCases (empty text, unicode, duplicates)

Verify:
  pytest tests/unit/services/test_vector_store.py -v --cov=app/services/vector_store
```

---

### S1: LLM Service

**Specification:** `docs/S1_LLM_Service_-_Claude_Code_Instructions.md`  
**Dependencies:** S2 Cost Tracker, S3 Cache Service  
**Target Files:** `app/models/llm.py`, `app/services/llm.py`, `tests/unit/services/test_llm.py`

#### Step 1.1: Data Models
```
Files: app/models/llm.py

Create:
- [ ] LLMProvider enum (ANTHROPIC, MOCK)
- [ ] PromptMessage model (role, content)
- [ ] LLMRequest model (messages, temperature, max_tokens, module, purpose)
- [ ] TokenUsage model (prompt_tokens, completion_tokens, total_tokens, cost)
- [ ] LLMResponse model (content, usage, cached, latency, request_id)

Verify:
  python -c "from app.models.llm import LLMRequest, LLMResponse; print('OK')"
```

#### Step 1.2: Configuration
```
Files: app/config/settings.py

Add:
- [ ] anthropic_api_key: str (from env)
- [ ] llm_model: str = "claude-3-5-haiku-20241022"
- [ ] llm_temperature: float = 0.3
- [ ] llm_max_tokens: int = 2000
- [ ] llm_timeout: int = 30
- [ ] llm_max_retries: int = 3

Verify:
  python -c "from app.config.settings import settings; print(settings.llm_model)"
```

#### Step 1.3: Exceptions
```
Files: app/utils/exceptions.py

Add:
- [ ] LLMError(ScoutError)
- [ ] LLMProviderError(LLMError)
- [ ] LLMTimeoutError(LLMError)
- [ ] LLMRateLimitError(LLMError)

Verify:
  python -c "from app.utils.exceptions import LLMError, LLMProviderError; print('OK')"
```

#### Step 1.4: Service - Initialization
```
Files: app/services/llm.py

Implement:
- [ ] LLMService class with __init__
- [ ] initialize() - init Anthropic client, verify connection
- [ ] shutdown()
- [ ] Inject CostTracker and Cache dependencies

Verify:
  python -c "from app.services.llm import LLMService; s = LLMService(); print('OK')"
```

#### Step 1.5: Service - Cost Calculation
```
Files: app/services/llm.py

Implement:
- [ ] PRICING dict (input/output cost per 1K tokens for Haiku)
- [ ] _calculate_cost(input_tokens, output_tokens) -> float
- [ ] _count_tokens(text) -> int (using tiktoken or estimate)

Verify:
  pytest tests/unit/services/test_llm.py::TestCostCalculation -v
```

#### Step 1.6: Service - Cache Integration
```
Files: app/services/llm.py

Implement:
- [ ] _generate_cache_key(request) -> str
- [ ] _check_cache(request) -> Optional[LLMResponse]
- [ ] _store_in_cache(request, response)

Verify:
  pytest tests/unit/services/test_llm.py::TestCaching -v
```

#### Step 1.7: Service - Anthropic Provider
```
Files: app/services/llm.py

Implement:
- [ ] _call_anthropic(request) -> LLMResponse
- [ ] Handle API response parsing
- [ ] Extract token usage from response

Verify:
  pytest tests/unit/services/test_llm.py::TestAnthropicProvider -v
```

#### Step 1.8: Service - Retry Logic
```
Files: app/services/llm.py

Implement:
- [ ] _execute_with_retry(request) -> LLMResponse
- [ ] Exponential backoff (1s, 2s, 4s)
- [ ] Handle rate limits, timeouts

Verify:
  pytest tests/unit/services/test_llm.py::TestRetryLogic -v
```

#### Step 1.9: Service - Main Generate Method
```
Files: app/services/llm.py

Implement:
- [ ] generate(request: LLMRequest) -> LLMResponse
- [ ] Check budget before proceeding
- [ ] Check cache first
- [ ] Record cost after success

Verify:
  pytest tests/unit/services/test_llm.py::TestGenerate -v
```

#### Step 1.10: Service - Convenience Methods
```
Files: app/services/llm.py

Implement:
- [ ] generate_text(prompt, system=None) -> str
- [ ] generate_json(prompt, system=None) -> Dict
- [ ] health_check() -> Dict

Verify:
  pytest tests/unit/services/test_llm.py::TestConvenienceMethods -v
```

#### Step 1.11: Mock Provider
```
Files: app/services/llm.py

Implement:
- [ ] MockLLMProvider class for testing
- [ ] Configurable responses
- [ ] Simulated latency and token counts

Verify:
  pytest tests/unit/services/test_llm.py::TestMockProvider -v
```

#### Step 1.12: Dependency Injection
```
Files: app/services/llm.py

Implement:
- [ ] get_llm_service() -> LLMService
- [ ] Global singleton pattern with dependency injection

Verify:
  python -c "from app.services.llm import get_llm_service; import asyncio; asyncio.run(get_llm_service())"
```

#### Step 1.13: Unit Tests
```
Files: tests/unit/services/test_llm.py

Create:
- [ ] Fixtures (mock anthropic, mock cache, mock cost_tracker)
- [ ] TestInitialization
- [ ] TestCostCalculation
- [ ] TestCaching
- [ ] TestAnthropicProvider (mocked)
- [ ] TestRetryLogic
- [ ] TestGenerate (full flow)
- [ ] TestBudgetEnforcement
- [ ] TestEdgeCases

Verify:
  pytest tests/unit/services/test_llm.py -v --cov=app/services/llm
```

---

## Phase 2: Core Modules

### M1: Collector Module

**Specification:** `docs/Module_1_Collector_-_Claude_Code_Instructions.md`  
**Dependencies:** S4 Vector Store  
**Target Files:** `app/models/profile.py`, `app/core/collector.py`, `tests/unit/core/test_collector.py`

#### Step M1.1: Profile Data Models
```
Files: app/models/profile.py

Create:
- [ ] Skill model (name, level, years, category, description)
- [ ] Experience model (company, title, start_date, end_date, description, achievements, technologies)
- [ ] Education model (institution, degree, field, graduation_date)
- [ ] Certification model (name, issuer, date, expiry)
- [ ] UserProfile model (containing all above + personal info)

Verify:
  python -c "from app.models.profile import UserProfile, Skill, Experience; print('OK')"
```

#### Step M1.2: Profile Loading
```
Files: app/core/collector.py

Implement:
- [ ] Collector class with __init__(vector_store)
- [ ] load_profile(path) -> UserProfile
- [ ] _parse_yaml(content) -> Dict
- [ ] _validate_profile(data) -> UserProfile

Verify:
  pytest tests/unit/core/test_collector.py::TestProfileLoading -v
```

#### Step M1.3: Profile Indexing
```
Files: app/core/collector.py

Implement:
- [ ] index_profile(profile) -> None
- [ ] _create_skill_entries(skills) -> List[VectorEntry]
- [ ] _create_experience_entries(experiences) -> List[VectorEntry]
- [ ] _create_education_entries(education) -> List[VectorEntry]

Verify:
  pytest tests/unit/core/test_collector.py::TestProfileIndexing -v
```

#### Step M1.4: Profile Queries
```
Files: app/core/collector.py

Implement:
- [ ] get_profile() -> UserProfile
- [ ] get_skills_by_category(category) -> List[Skill]
- [ ] get_relevant_experiences(query) -> List[Experience]

Verify:
  pytest tests/unit/core/test_collector.py::TestProfileQueries -v
```

#### Step M1.5: Unit Tests
```
Files: tests/unit/core/test_collector.py

Create:
- [ ] Sample profile YAML fixture
- [ ] TestProfileLoading (valid, invalid, missing fields)
- [ ] TestProfileIndexing (skills, experiences, education)
- [ ] TestProfileQueries
- [ ] TestEdgeCases

Verify:
  pytest tests/unit/core/test_collector.py -v --cov=app/core/collector
```

---

### M2: Rinser Module

**Specification:** `docs/Module_2_Rinser_-_Claude_Code_Instructions.md`  
**Dependencies:** S1 LLM Service  
**Target Files:** `app/models/job.py`, `app/core/rinser.py`, `tests/unit/core/test_rinser.py`

#### Step M2.1: Job Data Models
```
Files: app/models/job.py

Create:
- [ ] Requirement model (text, priority, category, years_required)
- [ ] Responsibility model (text, category)
- [ ] CompanyInfo model (name, size, industry, culture_notes)
- [ ] ProcessedJob model (title, company, requirements, responsibilities, benefits, raw_text)

Verify:
  python -c "from app.models.job import ProcessedJob, Requirement; print('OK')"
```

#### Step M2.2: Text Sanitization
```
Files: app/core/rinser.py

Implement:
- [ ] Rinser class with __init__(llm_service)
- [ ] sanitize_text(raw_text) -> str (using bleach)
- [ ] _remove_scripts_and_styles(text) -> str
- [ ] _normalize_whitespace(text) -> str

Verify:
  pytest tests/unit/core/test_rinser.py::TestSanitization -v
```

#### Step M2.3: Structure Extraction
```
Files: app/core/rinser.py

Implement:
- [ ] process_job(raw_text) -> ProcessedJob
- [ ] _extract_structure_with_llm(text) -> Dict
- [ ] _parse_requirements(data) -> List[Requirement]
- [ ] _parse_responsibilities(data) -> List[Responsibility]

Verify:
  pytest tests/unit/core/test_rinser.py::TestStructureExtraction -v
```

#### Step M2.4: Index Job in Vector Store
```
Files: app/core/rinser.py

Implement:
- [ ] index_job(job: ProcessedJob) -> None
- [ ] _create_requirement_entries(requirements) -> List[VectorEntry]

Verify:
  pytest tests/unit/core/test_rinser.py::TestJobIndexing -v
```

#### Step M2.5: Unit Tests
```
Files: tests/unit/core/test_rinser.py

Create:
- [ ] Sample job posting fixtures (various formats)
- [ ] TestSanitization (HTML, scripts, XSS)
- [ ] TestStructureExtraction (with mocked LLM)
- [ ] TestJobIndexing
- [ ] TestEdgeCases (minimal job, malformed input)

Verify:
  pytest tests/unit/core/test_rinser.py -v --cov=app/core/rinser
```

---

### M3: Analyzer Module

**Specification:** `docs/Module_3_Analyzer_-_Claude_Code_Instructions.md`  
**Dependencies:** M1 Collector, S4 Vector Store, S1 LLM Service  
**Target Files:** `app/models/analysis.py`, `app/core/analyzer.py`, `tests/unit/core/test_analyzer.py`

#### Step M3.1: Analysis Data Models
```
Files: app/models/analysis.py

Create:
- [ ] MatchLevel enum (EXCELLENT, STRONG, MODERATE, WEAK, POOR)
- [ ] SkillMatch model (requirement, matched_skills, score, is_met)
- [ ] ExperienceMatch model (experience_id, relevance_score, matching_keywords)
- [ ] QualificationGap model (requirement, importance, gap_type, suggested_action)
- [ ] ApplicationStrategy model (positioning, key_strengths, keywords, tone)
- [ ] CompatibilityScore model (overall, technical, experience, requirements_met)
- [ ] AnalysisResult model (job_id, compatibility, skill_matches, gaps, strategy)

Verify:
  python -c "from app.models.analysis import AnalysisResult, CompatibilityScore; print('OK')"
```

#### Step M3.2: Skill Matching
```
Files: app/core/analyzer.py

Implement:
- [ ] Analyzer class with __init__(collector, vector_store, llm_service)
- [ ] _match_skills(job: ProcessedJob) -> List[SkillMatch]
- [ ] _calculate_skill_score(requirement, matches) -> float

Verify:
  pytest tests/unit/core/test_analyzer.py::TestSkillMatching -v
```

#### Step M3.3: Experience Matching
```
Files: app/core/analyzer.py

Implement:
- [ ] _match_experiences(job: ProcessedJob) -> List[ExperienceMatch]
- [ ] _calculate_experience_relevance(exp, job) -> float
- [ ] _extract_matching_keywords(exp, job) -> List[str]

Verify:
  pytest tests/unit/core/test_analyzer.py::TestExperienceMatching -v
```

#### Step M3.4: Gap Analysis
```
Files: app/core/analyzer.py

Implement:
- [ ] _identify_gaps(job, skill_matches) -> List[QualificationGap]
- [ ] _classify_gap_importance(requirement) -> str
- [ ] _suggest_gap_action(gap) -> str

Verify:
  pytest tests/unit/core/test_analyzer.py::TestGapAnalysis -v
```

#### Step M3.5: Compatibility Scoring
```
Files: app/core/analyzer.py

Implement:
- [ ] _calculate_compatibility(skill_matches, exp_matches, gaps) -> CompatibilityScore
- [ ] _determine_match_level(score) -> MatchLevel
- [ ] Weighted scoring algorithm

Verify:
  pytest tests/unit/core/test_analyzer.py::TestCompatibilityScoring -v
```

#### Step M3.6: Strategy Generation
```
Files: app/core/analyzer.py

Implement:
- [ ] _generate_strategy(job, compatibility, gaps) -> ApplicationStrategy
- [ ] Use LLM for positioning statement
- [ ] Extract keywords for ATS optimization

Verify:
  pytest tests/unit/core/test_analyzer.py::TestStrategyGeneration -v
```

#### Step M3.7: Main Analyze Method
```
Files: app/core/analyzer.py

Implement:
- [ ] analyze(job: ProcessedJob) -> AnalysisResult
- [ ] Orchestrate all matching and scoring steps
- [ ] Build complete AnalysisResult

Verify:
  pytest tests/unit/core/test_analyzer.py::TestAnalyze -v
```

#### Step M3.8: Unit Tests
```
Files: tests/unit/core/test_analyzer.py

Create:
- [ ] Fixtures (mock collector, vector_store, llm, sample job)
- [ ] TestSkillMatching
- [ ] TestExperienceMatching
- [ ] TestGapAnalysis
- [ ] TestCompatibilityScoring
- [ ] TestStrategyGeneration
- [ ] TestAnalyze (integration)
- [ ] TestEdgeCases

Verify:
  pytest tests/unit/core/test_analyzer.py -v --cov=app/core/analyzer
```

---

### M4: Creator Module

**Specification:** `docs/Module_4_Creator_-_Claude_Code_Instructions.md`  
**Dependencies:** S1 LLM Service, M3 Analyzer output  
**Target Files:** `app/models/generation.py`, `app/core/creator.py`, `tests/unit/core/test_creator.py`

#### Step M4.1: Generation Data Models
```
Files: app/models/generation.py

Create:
- [ ] CVSection model (title, content, order)
- [ ] GeneratedCV model (sections, tailored_summary, keywords_used)
- [ ] GeneratedCoverLetter model (opening, body, closing, tone)
- [ ] ApplicationPackage model (cv, cover_letter, job_id, created_at)

Verify:
  python -c "from app.models.generation import GeneratedCV, ApplicationPackage; print('OK')"
```

#### Step M4.2: CV Generation
```
Files: app/core/creator.py

Implement:
- [ ] Creator class with __init__(llm_service)
- [ ] generate_cv(profile, analysis) -> GeneratedCV
- [ ] _create_cv_prompt(profile, analysis) -> str
- [ ] _parse_cv_response(response) -> GeneratedCV

Verify:
  pytest tests/unit/core/test_creator.py::TestCVGeneration -v
```

#### Step M4.3: Cover Letter Generation
```
Files: app/core/creator.py

Implement:
- [ ] generate_cover_letter(profile, job, analysis) -> GeneratedCoverLetter
- [ ] _create_cover_letter_prompt(profile, job, analysis) -> str
- [ ] _parse_cover_letter_response(response) -> GeneratedCoverLetter

Verify:
  pytest tests/unit/core/test_creator.py::TestCoverLetterGeneration -v
```

#### Step M4.4: Application Package
```
Files: app/core/creator.py

Implement:
- [ ] create_application_package(profile, job, analysis) -> ApplicationPackage
- [ ] Orchestrate CV and cover letter generation

Verify:
  pytest tests/unit/core/test_creator.py::TestApplicationPackage -v
```

#### Step M4.5: Unit Tests
```
Files: tests/unit/core/test_creator.py

Create:
- [ ] Fixtures (mock llm, sample profile, sample analysis)
- [ ] TestCVGeneration
- [ ] TestCoverLetterGeneration
- [ ] TestApplicationPackage
- [ ] TestEdgeCases

Verify:
  pytest tests/unit/core/test_creator.py -v --cov=app/core/creator
```

---

### M5: Formatter Module

**Specification:** `docs/Module_5_Formatter_-_Claude_Code_Instructions.md`  
**Dependencies:** M4 Creator output  
**Target Files:** `app/core/formatter.py`, `tests/unit/core/test_formatter.py`

#### Step M5.1: Template Setup
```
Files: templates/documents/cv_modern.html, templates/documents/cover_letter.html

Create:
- [ ] CV HTML template with Jinja2 placeholders
- [ ] Cover letter HTML template
- [ ] Shared CSS for professional styling

Verify:
  ls templates/documents/
```

#### Step M5.2: Formatter Initialization
```
Files: app/core/formatter.py

Implement:
- [ ] Formatter class with __init__()
- [ ] _load_templates() - load Jinja2 templates
- [ ] Template selection logic

Verify:
  python -c "from app.core.formatter import Formatter; f = Formatter(); print('OK')"
```

#### Step M5.3: HTML Rendering
```
Files: app/core/formatter.py

Implement:
- [ ] _render_cv_html(cv: GeneratedCV, profile: UserProfile) -> str
- [ ] _render_cover_letter_html(letter: GeneratedCoverLetter) -> str

Verify:
  pytest tests/unit/core/test_formatter.py::TestHTMLRendering -v
```

#### Step M5.4: PDF Generation
```
Files: app/core/formatter.py

Implement:
- [ ] format_to_pdf(html_content, output_path) -> Path
- [ ] Using WeasyPrint
- [ ] Handle fonts and styling

Verify:
  pytest tests/unit/core/test_formatter.py::TestPDFGeneration -v
```

#### Step M5.5: Full Formatting Pipeline
```
Files: app/core/formatter.py

Implement:
- [ ] format_application(package: ApplicationPackage) -> Dict[str, Path]
- [ ] Returns paths to CV PDF and cover letter PDF

Verify:
  pytest tests/unit/core/test_formatter.py::TestFullPipeline -v
```

#### Step M5.6: Unit Tests
```
Files: tests/unit/core/test_formatter.py

Create:
- [ ] TestHTMLRendering
- [ ] TestPDFGeneration (verify PDF created)
- [ ] TestFullPipeline
- [ ] TestEdgeCases

Verify:
  pytest tests/unit/core/test_formatter.py -v --cov=app/core/formatter
```

---

## Phase 3: Integration

### S6: Pipeline Orchestrator

**Specification:** `docs/S6_Pipeline_Orchestrator_-_Claude_Code_Instructions.md`  
**Dependencies:** All core modules  

[Steps follow same pattern - abbreviated for space]

### API Routes

**Specification:** (see Web Interface document)  
**Dependencies:** Pipeline Orchestrator  

[Steps follow same pattern]

### S8: Notification Service

**Specification:** `docs/S8_Notification_Service_-_Claude_Code_Instructions.md`  
**Dependencies:** API Routes  

[Steps follow same pattern - in-app only per PoC scope]

### Web Interface

**Specification:** `docs/Web_Interface_-_Claude_Code_Instructions.md`  
**Dependencies:** API Routes, all services  

[Steps follow same pattern]

---

## Final Integration Checklist

After all components are implemented:

- [ ] All unit tests pass: `make test-unit`
- [ ] All integration tests pass: `make test-integration`
- [ ] End-to-end workflow verified manually
- [ ] Cost tracking works correctly
- [ ] PDF generation produces valid documents
- [ ] Web interface accessible and functional
- [ ] Error handling works gracefully
- [ ] Logging provides useful debugging information
- [ ] Documentation is complete

---

## Progress Tracking

### Phase 1: Foundation Services
| Service | Models | Config | Core | Tests | Status |
|---------|--------|--------|------|-------|--------|
| S2 Cost Tracker | [x] | [x] | [x] | [x] | ✅ Complete (Simplified PoC) |
| S3 Cache | [ ] | [ ] | [ ] | [ ] | Not started |
| S4 Vector Store | [ ] | [ ] | [ ] | [ ] | Not started |
| S1 LLM | [ ] | [ ] | [ ] | [ ] | Not started |

### Phase 2: Core Modules
| Module | Models | Core | Tests | Status |
|--------|--------|------|-------|--------|
| M1 Collector | [ ] | [ ] | [ ] | Not started |
| M2 Rinser | [ ] | [ ] | [ ] | Not started |
| M3 Analyzer | [ ] | [ ] | [ ] | Not started |
| M4 Creator | [ ] | [ ] | [ ] | Not started |
| M5 Formatter | [ ] | [ ] | [ ] | Not started |

### Phase 3: Integration
| Component | Core | Tests | Status |
|-----------|------|-------|--------|
| S6 Pipeline | [ ] | [ ] | Not started |
| API Routes | [ ] | [ ] | Not started |
| S8 Notifications | [ ] | [ ] | Not started |
| Web Interface | [ ] | [ ] | Not started |

---

*Last updated: November 26, 2025*
