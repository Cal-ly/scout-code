# Module 2: Rinser - Claude Code Instructions

**Version:** 2.0 (PoC Aligned)  
**Updated:** November 26, 2025  
**Status:** Ready for Implementation  
**Priority:** Phase 2 - Core Module (Build Second in Phase 2)

---

## PoC Scope Summary

| Feature | Status | Notes |
|---------|--------|-------|
| Accept pasted job text | ✅ In Scope | Plain text input only |
| Sanitize HTML/scripts | ✅ In Scope | Basic security cleaning |
| Extract via LLM | ✅ In Scope | Structured extraction with Claude |
| Parse requirements | ✅ In Scope | Into Requirement objects |
| Parse responsibilities | ✅ In Scope | Into Responsibility objects |
| Index in Vector Store | ✅ In Scope | JOB_REQUIREMENTS collection |
| URL fetching | ❌ Deferred | Paste-only for PoC |
| PDF parsing | ❌ Deferred | Text input only |
| Multiple job formats | ❌ Deferred | Generic extraction |
| Job deduplication | ❌ Deferred | Single job at a time |

---

## Context & Objective

Build the **Rinser Module** for Scout - takes raw job posting text, sanitizes it, extracts structured information using LLM, and indexes it for matching.

### Why This Module Exists

Job postings come in various formats with inconsistent structure. The Rinser:
- Cleans input (removes HTML, scripts, normalizes whitespace)
- Uses LLM to extract structured data (requirements, responsibilities)
- Creates searchable vector embeddings
- Produces a clean ProcessedJob for the Analyzer

This is the "job data" side of the matching equation.

### Dependencies

This module **requires**:
- **S1 LLM Service**: For intelligent extraction
- **S4 Vector Store Service**: For indexing requirements

---

## Technical Requirements

### Dependencies

```toml
[tool.poetry.dependencies]
bleach = "^6.1"  # HTML sanitization
```

### File Structure

```
scout/
├── app/
│   ├── models/
│   │   └── job.py               # Job data models
│   ├── core/
│   │   └── rinser.py            # Rinser module
│   └── prompts/
│       └── extraction.py        # Extraction prompts
└── tests/
    └── unit/
        └── core/
            └── test_rinser.py
```

---

## Data Models

Create `app/models/job.py`:

```python
"""
Job Posting Data Models

Models for representing processed job postings.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from enum import Enum
import uuid


class RequirementPriority(str, Enum):
    """Priority level for job requirements."""
    MUST_HAVE = "must_have"
    NICE_TO_HAVE = "nice_to_have"
    PREFERRED = "preferred"


class RequirementCategory(str, Enum):
    """Category of requirement."""
    TECHNICAL = "technical"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    CERTIFICATION = "certification"
    SOFT_SKILL = "soft_skill"
    OTHER = "other"


class Requirement(BaseModel):
    """
    A single job requirement.
    
    Example:
        text: "5+ years of Python experience"
        priority: "must_have"
        category: "technical"
        years_required: 5
    """
    text: str
    priority: RequirementPriority = RequirementPriority.NICE_TO_HAVE
    category: RequirementCategory = RequirementCategory.OTHER
    years_required: Optional[int] = None
    
    def to_searchable_text(self) -> str:
        """Convert to text for embedding."""
        return self.text


class Responsibility(BaseModel):
    """
    A single job responsibility.
    
    Example:
        text: "Design and implement REST APIs"
        category: "technical"
    """
    text: str
    category: RequirementCategory = RequirementCategory.OTHER
    
    def to_searchable_text(self) -> str:
        """Convert to text for embedding."""
        return self.text


class CompanyInfo(BaseModel):
    """
    Information about the hiring company.
    
    Extracted from job posting when available.
    """
    name: str
    industry: Optional[str] = None
    size: Optional[str] = None  # e.g., "50-200 employees"
    culture_notes: Optional[str] = None


class ProcessedJob(BaseModel):
    """
    A fully processed job posting.
    
    This is the output of the Rinser module.
    """
    # Identification
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # Basic info
    title: str
    company: CompanyInfo
    location: Optional[str] = None
    employment_type: Optional[str] = None  # "Full-time", "Contract", etc.
    salary_range: Optional[str] = None
    
    # Structured content
    requirements: List[Requirement] = Field(default_factory=list)
    responsibilities: List[Responsibility] = Field(default_factory=list)
    benefits: List[str] = Field(default_factory=list)
    
    # Original content
    raw_text: str
    summary: Optional[str] = None  # LLM-generated summary
    
    # Metadata
    processed_at: datetime = Field(default_factory=datetime.now)
    
    @field_validator('requirements')
    @classmethod
    def validate_requirements(cls, v):
        if not v:
            raise ValueError("Job must have at least one requirement")
        return v
    
    def get_must_have_requirements(self) -> List[Requirement]:
        """Get only must-have requirements."""
        return [r for r in self.requirements if r.priority == RequirementPriority.MUST_HAVE]
    
    def get_technical_requirements(self) -> List[Requirement]:
        """Get only technical requirements."""
        return [r for r in self.requirements if r.category == RequirementCategory.TECHNICAL]
    
    def get_experience_requirements(self) -> List[Requirement]:
        """Get experience-related requirements."""
        return [r for r in self.requirements if r.category == RequirementCategory.EXPERIENCE]


class JobInput(BaseModel):
    """
    Input for job processing.
    
    Simple text input for PoC (URL fetching deferred).
    """
    raw_text: str = Field(..., min_length=100, description="Raw job posting text")
    source: Optional[str] = None  # e.g., "linkedin", "indeed"
    url: Optional[str] = None  # For reference only, not fetched
```

---

## Extraction Prompts

Create `app/prompts/extraction.py`:

```python
"""
LLM Prompts for Job Extraction

Prompts used by the Rinser module for structured extraction.
"""

SYSTEM_PROMPT = """You are a job posting parser. Extract structured information from job postings.
Always respond with valid JSON matching the requested format exactly.
If information is not present, use null or empty arrays.
Be precise with requirement priorities: only mark as "must_have" if the posting explicitly requires it."""

JOB_EXTRACTION_PROMPT = """Extract structured information from this job posting.

Job Posting:
---
{raw_text}
---

Return JSON with this exact structure:
{{
    "title": "Job title",
    "company": {{
        "name": "Company name",
        "industry": "Industry or null",
        "size": "Company size or null",
        "culture_notes": "Any culture/values mentioned or null"
    }},
    "location": "Location or null",
    "employment_type": "Full-time/Part-time/Contract or null",
    "salary_range": "Salary range if mentioned or null",
    "requirements": [
        {{
            "text": "Requirement text",
            "priority": "must_have|nice_to_have|preferred",
            "category": "technical|experience|education|certification|soft_skill|other",
            "years_required": number or null
        }}
    ],
    "responsibilities": [
        {{
            "text": "Responsibility text",
            "category": "technical|experience|soft_skill|other"
        }}
    ],
    "benefits": ["benefit1", "benefit2"],
    "summary": "1-2 sentence summary of the role"
}}

Guidelines:
- Mark as "must_have" only if words like "required", "must have", "essential" are used
- Default to "nice_to_have" for general requirements
- Extract years from phrases like "5+ years" → years_required: 5
- Categorize technical skills (Python, AWS) as "technical"
- Categorize "X years experience" as "experience"
- Include all distinct requirements, don't merge similar ones"""
```

---

## Module Implementation

Create `app/core/rinser.py`:

```python
"""
Rinser Module

Processes raw job postings into structured, searchable data.

Usage:
    rinser = Rinser(llm_service, vector_store)
    
    job = await rinser.process_job(raw_text)
    print(job.title)
    print(job.requirements)
"""

import re
import logging
from typing import Optional, List
import bleach

from app.models.job import (
    JobInput, ProcessedJob, Requirement, Responsibility,
    CompanyInfo, RequirementPriority, RequirementCategory
)
from app.models.vectors import VectorEntry, CollectionName, EmbeddingMetadata
from app.services.llm import LLMService
from app.services.vector_store import VectorStoreService
from app.prompts.extraction import SYSTEM_PROMPT, JOB_EXTRACTION_PROMPT
from app.utils.exceptions import ScoutError

logger = logging.getLogger(__name__)


class RinserError(ScoutError):
    """Error in Rinser operations."""
    pass


class ExtractionError(RinserError):
    """Failed to extract structured data from job posting."""
    pass


class Rinser:
    """
    Rinser Module - processes raw job postings.
    
    Responsibilities:
    - Sanitize raw text (remove HTML, scripts)
    - Extract structured data via LLM
    - Index in Vector Store for matching
    
    Attributes:
        llm: LLM Service for extraction
        vector_store: Vector Store for indexing
        
    Example:
        >>> rinser = Rinser(llm_service, vector_store)
        >>> job = await rinser.process_job('''
        ...     Senior Python Developer
        ...     Requirements:
        ...     - 5+ years Python experience
        ...     - AWS knowledge preferred
        ... ''')
        >>> print(job.title)
        "Senior Python Developer"
        >>> print(job.get_must_have_requirements())
        [Requirement(text="5+ years Python experience", ...)]
    """
    
    # Tags allowed after sanitization (basically none for text extraction)
    ALLOWED_TAGS: List[str] = []
    ALLOWED_ATTRIBUTES: dict = {}
    
    def __init__(
        self,
        llm_service: LLMService,
        vector_store: VectorStoreService
    ):
        """
        Initialize Rinser.
        
        Args:
            llm_service: LLM Service for extraction
            vector_store: Vector Store for indexing
        """
        self._llm = llm_service
        self._vector_store = vector_store
    
    # =========================================================================
    # TEXT SANITIZATION
    # =========================================================================
    
    def sanitize_text(self, raw_text: str) -> str:
        """
        Sanitize raw job posting text.
        
        Removes HTML tags, scripts, and normalizes whitespace.
        
        Args:
            raw_text: Raw input text (may contain HTML)
            
        Returns:
            Cleaned plain text
        """
        # Remove HTML tags
        text = bleach.clean(
            raw_text,
            tags=self.ALLOWED_TAGS,
            attributes=self.ALLOWED_ATTRIBUTES,
            strip=True
        )
        
        # Remove script/style content that might have slipped through
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Clean up common artifacts
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        
        return text.strip()
    
    # =========================================================================
    # LLM EXTRACTION
    # =========================================================================
    
    async def _extract_structure(self, clean_text: str) -> dict:
        """
        Extract structured data from job text using LLM.
        
        Args:
            clean_text: Sanitized job posting text
            
        Returns:
            Dictionary with extracted job data
            
        Raises:
            ExtractionError: If extraction fails
        """
        prompt = JOB_EXTRACTION_PROMPT.format(raw_text=clean_text)
        
        try:
            result = await self._llm.generate_json(
                prompt=prompt,
                system=SYSTEM_PROMPT,
                module="rinser",
                purpose="extract_job_structure",
                temperature=0.1  # Low temperature for consistency
            )
            
            logger.debug(f"Extracted structure: {list(result.keys())}")
            return result
            
        except Exception as e:
            raise ExtractionError(f"Failed to extract job structure: {e}")
    
    def _parse_requirements(self, data: list) -> List[Requirement]:
        """Parse requirement dictionaries into Requirement objects."""
        requirements = []
        for item in data or []:
            try:
                # Handle priority
                priority = item.get("priority", "nice_to_have")
                try:
                    priority = RequirementPriority(priority)
                except ValueError:
                    priority = RequirementPriority.NICE_TO_HAVE
                
                # Handle category
                category = item.get("category", "other")
                try:
                    category = RequirementCategory(category)
                except ValueError:
                    category = RequirementCategory.OTHER
                
                req = Requirement(
                    text=item.get("text", ""),
                    priority=priority,
                    category=category,
                    years_required=item.get("years_required")
                )
                requirements.append(req)
            except Exception as e:
                logger.warning(f"Failed to parse requirement: {e}")
                continue
        
        return requirements
    
    def _parse_responsibilities(self, data: list) -> List[Responsibility]:
        """Parse responsibility dictionaries into Responsibility objects."""
        responsibilities = []
        for item in data or []:
            try:
                category = item.get("category", "other")
                try:
                    category = RequirementCategory(category)
                except ValueError:
                    category = RequirementCategory.OTHER
                
                resp = Responsibility(
                    text=item.get("text", ""),
                    category=category
                )
                responsibilities.append(resp)
            except Exception as e:
                logger.warning(f"Failed to parse responsibility: {e}")
                continue
        
        return responsibilities
    
    def _parse_company(self, data: dict) -> CompanyInfo:
        """Parse company info from extracted data."""
        return CompanyInfo(
            name=data.get("name", "Unknown Company"),
            industry=data.get("industry"),
            size=data.get("size"),
            culture_notes=data.get("culture_notes")
        )
    
    # =========================================================================
    # VECTOR INDEXING
    # =========================================================================
    
    async def _index_job(self, job: ProcessedJob) -> int:
        """
        Index job requirements in Vector Store.
        
        Args:
            job: Processed job to index
            
        Returns:
            Number of entries indexed
        """
        entries: List[VectorEntry] = []
        
        # Index requirements
        for i, req in enumerate(job.requirements):
            entry = VectorEntry(
                id=f"job_{job.id}_req_{i}",
                text=req.to_searchable_text(),
                collection=CollectionName.JOB_REQUIREMENTS,
                metadata=EmbeddingMetadata(
                    source_type="requirement",
                    source_id=str(i),
                    text_preview=req.text[:100],
                    category=req.category.value,
                    extra_fields={
                        "job_id": job.id,
                        "priority": req.priority.value,
                        "years_required": req.years_required
                    }
                )
            )
            entries.append(entry)
        
        # Index responsibilities
        for i, resp in enumerate(job.responsibilities):
            entry = VectorEntry(
                id=f"job_{job.id}_resp_{i}",
                text=resp.to_searchable_text(),
                collection=CollectionName.JOB_REQUIREMENTS,
                metadata=EmbeddingMetadata(
                    source_type="responsibility",
                    source_id=str(i),
                    text_preview=resp.text[:100],
                    category=resp.category.value,
                    extra_fields={
                        "job_id": job.id
                    }
                )
            )
            entries.append(entry)
        
        if entries:
            result = await self._vector_store.add_entries(entries)
            logger.info(f"Indexed {result.entries_added} job entries for job {job.id}")
        
        return len(entries)
    
    # =========================================================================
    # MAIN PROCESSING
    # =========================================================================
    
    async def process_job(
        self,
        raw_text: str,
        source: Optional[str] = None,
        index: bool = True
    ) -> ProcessedJob:
        """
        Process a raw job posting.
        
        Main entry point for the Rinser module.
        
        Args:
            raw_text: Raw job posting text
            source: Optional source identifier
            index: Whether to index in Vector Store
            
        Returns:
            ProcessedJob with extracted structure
            
        Raises:
            RinserError: If processing fails
            
        Example:
            >>> job = await rinser.process_job('''
            ...     Software Engineer at TechCorp
            ...     
            ...     Requirements:
            ...     - 3+ years Python
            ...     - AWS experience preferred
            ...     
            ...     Responsibilities:
            ...     - Build APIs
            ...     - Code review
            ... ''')
        """
        if len(raw_text) < 100:
            raise RinserError("Job posting too short (minimum 100 characters)")
        
        logger.info(f"Processing job posting ({len(raw_text)} chars)")
        
        # Step 1: Sanitize
        clean_text = self.sanitize_text(raw_text)
        logger.debug(f"Sanitized text: {len(clean_text)} chars")
        
        # Step 2: Extract structure via LLM
        extracted = await self._extract_structure(clean_text)
        
        # Step 3: Parse into models
        requirements = self._parse_requirements(extracted.get("requirements", []))
        responsibilities = self._parse_responsibilities(extracted.get("responsibilities", []))
        company = self._parse_company(extracted.get("company", {}))
        
        if not requirements:
            raise ExtractionError("No requirements could be extracted from job posting")
        
        # Step 4: Build ProcessedJob
        job = ProcessedJob(
            title=extracted.get("title", "Unknown Position"),
            company=company,
            location=extracted.get("location"),
            employment_type=extracted.get("employment_type"),
            salary_range=extracted.get("salary_range"),
            requirements=requirements,
            responsibilities=responsibilities,
            benefits=extracted.get("benefits", []),
            raw_text=raw_text,
            summary=extracted.get("summary")
        )
        
        logger.info(
            f"Processed job: {job.title} at {job.company.name} - "
            f"{len(requirements)} requirements, {len(responsibilities)} responsibilities"
        )
        
        # Step 5: Index in Vector Store
        if index:
            await self._index_job(job)
        
        return job
    
    async def process_job_input(
        self,
        job_input: JobInput,
        index: bool = True
    ) -> ProcessedJob:
        """
        Process a JobInput model.
        
        Args:
            job_input: JobInput with raw text
            index: Whether to index in Vector Store
            
        Returns:
            ProcessedJob
        """
        return await self.process_job(
            raw_text=job_input.raw_text,
            source=job_input.source,
            index=index
        )
```

---

## Test Implementation

Create `tests/unit/core/test_rinser.py`:

```python
"""
Unit tests for Rinser Module.

Run with: pytest tests/unit/core/test_rinser.py -v
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.core.rinser import Rinser, RinserError, ExtractionError
from app.models.job import (
    ProcessedJob, Requirement, RequirementPriority, RequirementCategory
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_job_text():
    """Sample job posting for testing."""
    return """
    Senior Python Developer
    TechCorp Inc - San Francisco, CA
    
    About Us:
    TechCorp is a leading technology company specializing in cloud solutions.
    
    Requirements:
    - 5+ years of Python experience (required)
    - Strong knowledge of FastAPI or Django
    - AWS experience preferred
    - Bachelor's degree in Computer Science or related field
    
    Responsibilities:
    - Design and implement REST APIs
    - Mentor junior developers
    - Participate in code reviews
    
    Benefits:
    - Competitive salary ($150,000 - $200,000)
    - Health insurance
    - Remote work options
    """


@pytest.fixture
def mock_llm_service():
    """Create mock LLM Service."""
    llm = AsyncMock()
    llm.generate_json.return_value = {
        "title": "Senior Python Developer",
        "company": {
            "name": "TechCorp Inc",
            "industry": "Technology",
            "size": None,
            "culture_notes": "Leading technology company"
        },
        "location": "San Francisco, CA",
        "employment_type": "Full-time",
        "salary_range": "$150,000 - $200,000",
        "requirements": [
            {
                "text": "5+ years of Python experience",
                "priority": "must_have",
                "category": "technical",
                "years_required": 5
            },
            {
                "text": "Strong knowledge of FastAPI or Django",
                "priority": "must_have",
                "category": "technical",
                "years_required": None
            },
            {
                "text": "AWS experience preferred",
                "priority": "nice_to_have",
                "category": "technical",
                "years_required": None
            }
        ],
        "responsibilities": [
            {
                "text": "Design and implement REST APIs",
                "category": "technical"
            },
            {
                "text": "Mentor junior developers",
                "category": "soft_skill"
            }
        ],
        "benefits": ["Health insurance", "Remote work options"],
        "summary": "Senior Python Developer role at TechCorp"
    }
    return llm


@pytest.fixture
def mock_vector_store():
    """Create mock Vector Store."""
    store = AsyncMock()
    store.add_entries.return_value = Mock(entries_added=5)
    return store


@pytest.fixture
def rinser(mock_llm_service, mock_vector_store):
    """Create Rinser for testing."""
    return Rinser(mock_llm_service, mock_vector_store)


# =============================================================================
# SANITIZATION TESTS
# =============================================================================

class TestSanitization:
    """Tests for text sanitization."""
    
    def test_sanitize_removes_html(self, rinser):
        """Should remove HTML tags."""
        text = "<div><p>Job <b>Title</b></p></div>"
        result = rinser.sanitize_text(text)
        assert "<" not in result
        assert ">" not in result
        assert "Job Title" in result
    
    def test_sanitize_removes_scripts(self, rinser):
        """Should remove script tags."""
        text = "Job Title<script>alert('xss')</script>Description"
        result = rinser.sanitize_text(text)
        assert "script" not in result.lower()
        assert "alert" not in result
    
    def test_sanitize_normalizes_whitespace(self, rinser):
        """Should normalize excessive whitespace."""
        text = "Job    Title\n\n\n\nDescription"
        result = rinser.sanitize_text(text)
        assert "    " not in result
    
    def test_sanitize_handles_entities(self, rinser):
        """Should convert HTML entities."""
        text = "Python &amp; Django"
        result = rinser.sanitize_text(text)
        assert "Python & Django" in result


# =============================================================================
# EXTRACTION TESTS
# =============================================================================

class TestExtraction:
    """Tests for LLM extraction."""
    
    @pytest.mark.asyncio
    async def test_extract_structure_calls_llm(
        self, rinser, mock_llm_service
    ):
        """Should call LLM with correct parameters."""
        await rinser._extract_structure("Test job posting")
        
        mock_llm_service.generate_json.assert_called_once()
        call_kwargs = mock_llm_service.generate_json.call_args[1]
        assert call_kwargs["module"] == "rinser"
        assert call_kwargs["purpose"] == "extract_job_structure"
    
    @pytest.mark.asyncio
    async def test_extract_structure_returns_dict(
        self, rinser, mock_llm_service
    ):
        """Should return extracted data as dict."""
        result = await rinser._extract_structure("Test job posting")
        
        assert "title" in result
        assert "requirements" in result


# =============================================================================
# PARSING TESTS
# =============================================================================

class TestParsing:
    """Tests for data parsing."""
    
    def test_parse_requirements(self, rinser):
        """Should parse requirement dicts into objects."""
        data = [
            {
                "text": "Python required",
                "priority": "must_have",
                "category": "technical",
                "years_required": 3
            }
        ]
        
        requirements = rinser._parse_requirements(data)
        
        assert len(requirements) == 1
        assert requirements[0].text == "Python required"
        assert requirements[0].priority == RequirementPriority.MUST_HAVE
        assert requirements[0].category == RequirementCategory.TECHNICAL
        assert requirements[0].years_required == 3
    
    def test_parse_requirements_handles_invalid(self, rinser):
        """Should handle invalid priority/category gracefully."""
        data = [
            {
                "text": "Test requirement",
                "priority": "invalid_priority",
                "category": "invalid_category"
            }
        ]
        
        requirements = rinser._parse_requirements(data)
        
        assert len(requirements) == 1
        assert requirements[0].priority == RequirementPriority.NICE_TO_HAVE
        assert requirements[0].category == RequirementCategory.OTHER
    
    def test_parse_responsibilities(self, rinser):
        """Should parse responsibility dicts."""
        data = [
            {"text": "Build APIs", "category": "technical"}
        ]
        
        responsibilities = rinser._parse_responsibilities(data)
        
        assert len(responsibilities) == 1
        assert responsibilities[0].text == "Build APIs"


# =============================================================================
# PROCESSING TESTS
# =============================================================================

class TestProcessJob:
    """Tests for main processing flow."""
    
    @pytest.mark.asyncio
    async def test_process_job_success(
        self, rinser, sample_job_text, mock_vector_store
    ):
        """Should process job posting successfully."""
        job = await rinser.process_job(sample_job_text)
        
        assert isinstance(job, ProcessedJob)
        assert job.title == "Senior Python Developer"
        assert job.company.name == "TechCorp Inc"
        assert len(job.requirements) == 3
        assert len(job.responsibilities) == 2
    
    @pytest.mark.asyncio
    async def test_process_job_indexes(
        self, rinser, sample_job_text, mock_vector_store
    ):
        """Should index job in Vector Store."""
        await rinser.process_job(sample_job_text, index=True)
        
        mock_vector_store.add_entries.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_job_skip_index(
        self, rinser, sample_job_text, mock_vector_store
    ):
        """Should skip indexing when disabled."""
        await rinser.process_job(sample_job_text, index=False)
        
        mock_vector_store.add_entries.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_job_too_short_raises(self, rinser):
        """Should raise for very short text."""
        with pytest.raises(RinserError, match="too short"):
            await rinser.process_job("Too short")
    
    @pytest.mark.asyncio
    async def test_process_job_no_requirements_raises(
        self, rinser, mock_llm_service
    ):
        """Should raise if no requirements extracted."""
        mock_llm_service.generate_json.return_value = {
            "title": "Test",
            "company": {"name": "Test"},
            "requirements": [],
            "responsibilities": []
        }
        
        with pytest.raises(ExtractionError, match="No requirements"):
            await rinser.process_job("A" * 200)


# =============================================================================
# PROCESSED JOB TESTS
# =============================================================================

class TestProcessedJob:
    """Tests for ProcessedJob model methods."""
    
    @pytest.mark.asyncio
    async def test_get_must_have_requirements(
        self, rinser, sample_job_text
    ):
        """Should filter must-have requirements."""
        job = await rinser.process_job(sample_job_text)
        
        must_haves = job.get_must_have_requirements()
        
        assert len(must_haves) == 2
        assert all(r.priority == RequirementPriority.MUST_HAVE for r in must_haves)
    
    @pytest.mark.asyncio
    async def test_get_technical_requirements(
        self, rinser, sample_job_text
    ):
        """Should filter technical requirements."""
        job = await rinser.process_job(sample_job_text)
        
        technical = job.get_technical_requirements()
        
        assert len(technical) == 3
        assert all(r.category == RequirementCategory.TECHNICAL for r in technical)
```

---

## Implementation Steps

### Step M2.1: Data Models
```bash
# Create app/models/job.py
# Verify:
python -c "from app.models.job import ProcessedJob, Requirement; print('OK')"
```

### Step M2.2: Extraction Prompts
```bash
# Create app/prompts/extraction.py
# Verify:
python -c "from app.prompts.extraction import JOB_EXTRACTION_PROMPT; print('OK')"
```

### Step M2.3: Module Implementation
```bash
# Create app/core/rinser.py
# Verify:
python -c "from app.core.rinser import Rinser; print('OK')"
```

### Step M2.4: Unit Tests
```bash
# Create tests/unit/core/test_rinser.py
# Verify:
pytest tests/unit/core/test_rinser.py -v
```

### Step M2.5: Integration Test
```bash
# Verify with real LLM (uses API and budget):
python -c "
import asyncio
from app.services.llm import get_llm_service
from app.services.vector_store import get_vector_store
from app.core.rinser import Rinser

JOB_TEXT = '''
Software Engineer at ExampleCorp
Remote

We're looking for a Software Engineer to join our team.

Requirements:
- 3+ years Python experience
- FastAPI knowledge
- PostgreSQL experience preferred

Responsibilities:
- Build and maintain APIs
- Write tests
'''

async def test():
    llm = await get_llm_service()
    vs = await get_vector_store()
    rinser = Rinser(llm, vs)
    
    job = await rinser.process_job(JOB_TEXT)
    print(f'Title: {job.title}')
    print(f'Company: {job.company.name}')
    print(f'Requirements: {len(job.requirements)}')
    for req in job.requirements:
        print(f'  - [{req.priority.value}] {req.text}')

asyncio.run(test())
"
```

---

## Success Criteria

| Metric | Target | Verification |
|--------|--------|--------------|
| HTML sanitization | Clean text output | Test with HTML input |
| LLM extraction | Valid structured data | Test with real job posting |
| Requirement parsing | Correct types/priorities | Test type coercion |
| Vector indexing | All entries indexed | Count matches |
| Test coverage | >90% | `pytest --cov=app/core/rinser` |

---

*This specification is aligned with Scout PoC Scope Document v1.0*
