# Modules - Current State

This document describes the current implementation of Scout's core processing modules.

## Overview

| Module | ID | Location | Test Count | Dependencies |
|--------|------|----------|------------|--------------|
| Collector | M1 | `src/modules/collector/` | 49 | S4 (Vector Store) |
| Rinser | M2 | `src/modules/rinser/` | 71 | S1 (LLM), S4 (Vector Store) |
| Analyzer | M3 | `src/modules/analyzer/` | 62 | M1, S1 (LLM) |
| Creator | M4 | `src/modules/creator/` | 48 | M1, S1 (LLM) |
| Formatter | M5 | `src/modules/formatter/` | 38 | None |

## Pipeline Flow

```
Input: Raw Job Posting Text
            │
            ▼
    ┌───────────────┐
    │ M2: Rinser    │  Sanitize → Extract via LLM → Index
    │               │  Output: ProcessedJob
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │ M3: Analyzer  │  Match skills → Match experience → Score → Strategy
    │               │  Output: AnalysisResult
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │ M4: Creator   │  Generate CV sections → Generate cover letter
    │               │  Output: CreatedContent
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │ M5: Formatter │  Render templates → Convert to PDF
    │               │  Output: FormattedApplication
    └───────┴───────┘
            │
            ▼
Output: PDF files (CV + Cover Letter)
```

---

## M1: Collector Module

**Location:** `src/modules/collector/`

### Purpose
Manages user profile data, indexes it in Vector Store for semantic search.

### Key Files
```
collector/
├── __init__.py          # Public exports
├── collector.py         # Main Collector class
├── models.py            # UserProfile, ProfileSummary, SearchMatch
└── exceptions.py        # CollectorError, ProfileNotFoundError
```

### Main Class: `Collector`

```python
class Collector:
    """Profile management and semantic search."""

    def __init__(
        self,
        vector_store: VectorStoreService,
        profile_path: Path | None = None,  # data/profile.yaml
    ): ...

    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...

    # Profile operations (YAML-based)
    async def load_profile(self) -> UserProfile: ...
    async def save_profile(self, profile: UserProfile) -> None: ...
    async def index_profile(self, force: bool = False) -> int:
        """Index profile in vector store. Returns chunk count."""

    # Profile operations (Database-based) - NEW
    async def load_profile_from_db(self) -> UserProfile | None:
        """Load the active profile from database.

        Called on startup to initialize with active profile.
        Returns the active UserProfile, or None if no active profile exists.
        """

    # Search
    async def search_experiences(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[SearchMatch]: ...

    async def search_skills(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[SkillMatch]: ...

    # Status
    @property
    def has_profile(self) -> bool: ...
    @property
    def is_indexed(self) -> bool: ...
    @property
    def profile(self) -> UserProfile | None: ...
```

### Database Integration (NEW)

The Collector can now load profiles from the Database Service:

```python
async def load_profile_from_db(self) -> UserProfile | None:
    """Load the active profile from database."""
    from src.services.database import get_database_service

    db = await get_database_service()
    active = await db.get_active_profile()

    if active is None:
        logger.warning("No active profile in database")
        return None

    # Parse profile data to UserProfile
    self._profile = UserProfile(**active.profile_data)
    self._profile_hash = str(active.id)

    logger.info(f"Loaded profile from database: {active.name}")
    return self._profile
```

**Usage:**
- YAML loading (`load_profile()`) for backward compatibility
- Database loading (`load_profile_from_db()`) for multi-profile support
- Both methods populate the same `_profile` attribute

### User Profile Model
```python
class UserProfile(BaseModel):
    name: str
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    skills: list[Skill] = []
    experiences: list[Experience] = []
    education: list[Education] = []
    certifications: list[str] = []
    languages: list[str] = []

class Skill(BaseModel):
    name: str
    level: SkillLevel | None = None  # beginner, intermediate, advanced, expert
    years: int | None = None

class Experience(BaseModel):
    title: str
    company: str
    start_date: str | None = None
    end_date: str | None = None
    description: str
    achievements: list[str] = []
```

### Indexing Strategy
Profile is chunked into searchable segments:
- Summary → single chunk
- Each experience → separate chunk
- Skills grouped → single chunk
- Education → separate chunks

Chunks are stored in `user_profiles` collection in Vector Store.

---

## M2: Rinser Module

**Location:** `src/modules/rinser/`

### Purpose
Processes raw job postings: sanitizes HTML, extracts structured data via LLM.

### Key Files
```
rinser/
├── __init__.py          # Public exports
├── rinser.py            # Main Rinser class
├── models.py            # ProcessedJob, Requirement, etc.
├── prompts.py           # LLM prompts for extraction
└── exceptions.py        # RinserError, ExtractionError
```

### Main Class: `Rinser`

```python
class Rinser:
    """Job posting processor."""

    def __init__(
        self,
        llm_service: LLMService,
        vector_store: VectorStoreService,
    ): ...

    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...

    async def process_job(
        self,
        raw_text: str,
        job_id: str | None = None,
    ) -> ProcessingResult: ...
```

### Processing Steps
1. **Sanitize**: Remove HTML tags, scripts, normalize whitespace (uses `bleach`)
2. **Validate**: Check minimum length (100 chars)
3. **Extract**: Call LLM with extraction prompt (JSON mode)
4. **Index**: Store in `job_requirements` collection

### Processed Job Model
```python
class ProcessedJob(BaseModel):
    job_id: str
    title: str
    company: CompanyInfo | None
    location: str | None
    employment_type: str | None  # full-time, contract, etc.
    experience_level: str | None  # junior, mid, senior
    salary_range: str | None
    requirements: list[Requirement]
    responsibilities: list[Responsibility]
    benefits: list[str] = []
    raw_text: str
    processed_at: datetime

class Requirement(BaseModel):
    text: str
    category: RequirementCategory  # technical, soft_skill, experience, education
    priority: RequirementPriority  # required, preferred, nice_to_have
    years_experience: int | None = None

class CompanyInfo(BaseModel):
    name: str = "Unknown Company"  # Default for postings without company
    industry: str | None = None
    size: str | None = None
    description: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def name_not_null(cls, v: str | None) -> str:
        """Convert null/empty name to default."""
        if v is None or v == "" or v.lower() == "null":
            return "Unknown Company"
        return v
```

**Note:** The `name` field has a validator to handle null/empty company names gracefully, preventing pipeline failures when job postings don't include explicit company information.

### LLM Extraction Prompt
Located in `prompts.py`:
- System prompt defines JSON output schema
- User prompt contains the sanitized job text
- Uses Ollama's JSON mode for reliable parsing

---

## M3: Analyzer Module

**Location:** `src/modules/analyzer/`

### Purpose
Compares user profile to job requirements, calculates compatibility score, generates strategy.

### Key Files
```
analyzer/
├── __init__.py          # Public exports
├── analyzer.py          # Main Analyzer class
├── models.py            # AnalysisResult, CompatibilityScore, etc.
├── prompts.py           # Strategy generation prompts
└── exceptions.py        # AnalyzerError, MatchingError
```

### Main Class: `Analyzer`

```python
class Analyzer:
    """Profile-to-job matching and strategy generation."""

    def __init__(
        self,
        collector: Collector,
        llm_service: LLMService,
        config: AnalyzerConfig | None = None,
    ): ...

    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...

    async def analyze(
        self,
        processed_job: ProcessedJob,
    ) -> AnalysisResult: ...
```

### Analysis Steps
1. **Skill Matching**: Semantic search of profile skills against requirements
2. **Experience Matching**: Match profile experiences to responsibilities
3. **Gap Identification**: Find missing required qualifications
4. **Score Calculation**: Weighted formula for compatibility
5. **Strategy Generation**: LLM generates positioning advice

### Analysis Result Model
```python
class AnalysisResult(BaseModel):
    job_id: str
    profile_hash: str
    compatibility: CompatibilityScore
    skill_matches: list[SkillMatchResult]
    experience_matches: list[ExperienceMatchResult]
    qualification_gaps: list[QualificationGap]
    strategy: ApplicationStrategy
    analyzed_at: datetime

class CompatibilityScore(BaseModel):
    overall: float  # 0-100
    skills_score: float
    experience_score: float
    education_score: float
    level: MatchLevel  # excellent, strong, moderate, weak

class ApplicationStrategy(BaseModel):
    positioning: str  # Main pitch angle
    key_strengths: list[str]
    gap_mitigation: list[str]  # How to address weaknesses
    keywords_to_emphasize: list[str]
    tone: str  # Formal, confident, etc.
```

### Scoring Formula
```python
overall = (
    skills_score * 0.40 +
    experience_score * 0.35 +
    education_score * 0.15 +
    nice_to_have_score * 0.10
)
```

### Match Levels
| Score Range | Level | Description |
|-------------|-------|-------------|
| 80-100 | excellent | Strong candidate |
| 60-79 | strong | Good fit |
| 40-59 | moderate | Potential with gaps |
| 0-39 | weak | Significant gaps |

---

## M4: Creator Module

**Location:** `src/modules/creator/`

### Purpose
Generates tailored CV and cover letter content using LLM based on analysis strategy.

### Key Files
```
creator/
├── __init__.py          # Public exports
├── creator.py           # Main Creator class
├── models.py            # GeneratedCV, GeneratedCoverLetter, etc.
├── prompts.py           # CV and cover letter prompts
└── exceptions.py        # CreatorError, CVGenerationError
```

### Main Class: `Creator`

```python
class Creator:
    """Content generation for applications."""

    def __init__(
        self,
        collector: Collector,
        llm_service: LLMService,
        config: CreatorConfig | None = None,
    ): ...

    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...

    async def create_content(
        self,
        analysis: AnalysisResult,
    ) -> CreatedContent: ...
```

### Generation Steps
1. **CV Summary**: Generate tailored professional summary
2. **Experience Bullets**: Rewrite experience to emphasize relevant skills
3. **Skills Section**: Prioritize based on job requirements
4. **Cover Letter**: Generate personalized letter with strategy positioning

### Created Content Model
```python
class CreatedContent(BaseModel):
    job_id: str
    cv: GeneratedCV
    cover_letter: GeneratedCoverLetter
    created_at: datetime

class GeneratedCV(BaseModel):
    professional_summary: str
    experience_sections: list[CVExperienceSection]
    skills_section: CVSkillsSection
    education_section: str | None
    additional_sections: list[CVSection] = []

class CVExperienceSection(BaseModel):
    title: str
    company: str
    dates: str
    bullets: list[str]  # Tailored achievement bullets

class GeneratedCoverLetter(BaseModel):
    greeting: str
    opening_paragraph: str
    body_paragraphs: list[str]
    closing_paragraph: str
    signature: str
```

### LLM Prompts
Located in `prompts.py`:
- `CV_SUMMARY_PROMPT`: Professional summary generation
- `CV_EXPERIENCE_PROMPT`: Experience bullet rewriting
- `COVER_LETTER_PROMPT`: Full cover letter generation

All prompts incorporate the strategy from Analyzer for consistent positioning.

---

## M5: Formatter Module

**Location:** `src/modules/formatter/`

### Purpose
Converts generated content to PDF documents using Jinja2 templates and xhtml2pdf.

### Key Files
```
formatter/
├── __init__.py          # Public exports
├── formatter.py         # Main Formatter class
├── models.py            # FormattedDocument, FormattedApplication
└── exceptions.py        # FormatterError, PDFGenerationError
```

### Main Class: `Formatter`

```python
class Formatter:
    """PDF document generation."""

    def __init__(
        self,
        templates_dir: Path | None = None,  # src/templates
        output_dir: Path | None = None,     # data/outputs/ (persistent)
    ): ...

    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...

    async def format_application(
        self,
        content: CreatedContent,
        job_id: str | None = None,
    ) -> FormattedApplication: ...
```

### PDF Generation Flow
1. **Load Template**: Jinja2 HTML template
2. **Render**: Fill template with content data
3. **Convert**: xhtml2pdf converts HTML to PDF
4. **Save**: Output to `output/{job_id}/cv.pdf` and `cover_letter.pdf`

### Templates
Located in `src/templates/`:
```
templates/
├── cv_template.html          # CV/resume template
├── cover_letter_template.html  # Cover letter template
└── base.css                  # Shared styles
```

### Formatted Application Model
```python
class FormattedApplication(BaseModel):
    job_id: str
    cv: FormattedDocument
    cover_letter: FormattedDocument
    output_directory: Path
    created_at: datetime

class FormattedDocument(BaseModel):
    document_type: str  # "cv" or "cover_letter"
    file_path: Path
    file_size_bytes: int
    page_count: int
```

### Output Structure
```
data/outputs/
├── cv_abc123.pdf
├── cover_letter_abc123.pdf
├── cv_def456.pdf
├── cover_letter_def456.pdf
└── ...
```

**Note:** Output directory changed from `output/` to `data/outputs/` for persistent storage across deployments. File naming uses `{type}_{job_id}.pdf` format.

---

## Singleton Access Pattern

All modules use singleton pattern for FastAPI:

```python
# Example from Collector
_instance: Collector | None = None

async def get_collector() -> Collector:
    """Get singleton Collector instance."""
    global _instance
    if _instance is None:
        vector_store = await get_vector_store_service()
        _instance = Collector(vector_store)
        await _instance.initialize()
    return _instance
```

Usage in other modules:
```python
# Analyzer depends on Collector
collector = await get_collector()
analyzer = Analyzer(collector, llm_service)
```

---

## Error Handling Pattern

Each module defines its own exceptions:

```python
# Base exception for module
class CollectorError(Exception):
    """Base exception for Collector module."""
    pass

# Specific exceptions
class ProfileNotFoundError(CollectorError):
    """Profile file not found."""
    pass

class ProfileValidationError(CollectorError):
    """Profile data validation failed."""
    pass

class IndexingError(CollectorError):
    """Failed to index profile in vector store."""
    pass
```

Modules raise specific exceptions, caught by Pipeline Orchestrator which wraps them in `StepError`.

---

*Last updated: December 17, 2025*
*Updated: Added CompanyInfo null handling validator, Collector database integration, Formatter output directory*
