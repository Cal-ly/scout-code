---
updated: 2025-10-04, 18:27
---

## Module 2: Rinser - Claude Code Instructions

## Context & Objective

You're building the **Rinser module** for Scout, an intelligent job application system. This module sanitizes raw job posting content and extracts structured information using LLM-powered parsing, creating clean, standardized job data for analysis.

## Module Specifications

**Purpose**: Clean, parse, and structure raw job posting text into standardized, searchable format ready for semantic matching.

**Key Responsibilities**:
1. Sanitize raw text (remove HTML, scripts, malicious content)
2. Extract structured job information using Claude API
3. Standardize data into consistent schema
4. Validate extracted requirements and qualifications
5. Cache processed results to minimize API costs

## Technical Requirements

**Dependencies**:
- FastAPI framework
- Pydantic for data validation
- Anthropic Claude 3.5 Haiku for extraction
- Bleach for HTML sanitization
- BeautifulSoup4 for HTML parsing
- Langdetect for language detection
- Redis/diskcache for caching

**File Structure**:
```
scout/
├── app/
│   ├── core/
│   │   └── rinser.py
│   ├── models/
│   │   └── job.py
│   ├── services/
│   │   ├── llm.py
│   │   └── cache.py
│   └── config/
│       └── settings.py
├── prompts/
│   └── extraction/
│       ├── job_structure.txt
│       └── requirements_parser.txt
├── data/
│   └── cache/
└── tests/
    └── test_rinser.py
```

## Data Models to Implement

Create these models in `app/models/job.py`:

```python
from pydantic import BaseModel, Field, validator, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import hashlib
import json

class EmploymentType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"
    UNKNOWN = "unknown"

class ExperienceLevel(str, Enum):
    ENTRY = "entry"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"
    UNKNOWN = "unknown"

class WorkLocation(str, Enum):
    ONSITE = "onsite"
    REMOTE = "remote"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"

class Requirement(BaseModel):
    """Individual requirement or qualification"""
    text: str
    category: str  # 'technical', 'soft_skill', 'education', 'experience', 'other'
    priority: str = "nice_to_have"  # 'must_have', 'nice_to_have'
    years_needed: Optional[float] = None
    keywords: List[str] = []
    
    def __hash__(self):
        return hash(self.text)

class SalaryRange(BaseModel):
    """Salary information if available"""
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    currency: str = "USD"
    period: str = "yearly"  # 'hourly', 'daily', 'monthly', 'yearly'
    is_negotiable: bool = False

class CompanyInfo(BaseModel):
    """Extracted company information"""
    name: str
    industry: Optional[str] = None
    size: Optional[str] = None  # 'startup', 'small', 'medium', 'large', 'enterprise'
    location: Optional[str] = None
    website: Optional[HttpUrl] = None
    description: Optional[str] = None

class RawJobPosting(BaseModel):
    """Raw input job posting"""
    content: str
    source_url: Optional[HttpUrl] = None
    source_platform: Optional[str] = None  # 'linkedin', 'jobindex', 'manual'
    fetched_at: datetime = Field(default_factory=datetime.now)
    
    @validator('content')
    def content_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Job content cannot be empty")
        return v
    
    def generate_hash(self) -> str:
        """Generate hash for caching"""
        return hashlib.md5(self.content.encode()).hexdigest()

class ProcessedJob(BaseModel):
    """Cleaned and structured job data"""
    # Identifiers
    id: str = Field(default_factory=lambda: str(uuid4()))
    content_hash: str
    
    # Basic Information
    title: str
    company: CompanyInfo
    location: str
    work_location_type: WorkLocation = WorkLocation.UNKNOWN
    employment_type: EmploymentType = EmploymentType.UNKNOWN
    experience_level: ExperienceLevel = ExperienceLevel.UNKNOWN
    
    # Content
    summary: str  # Brief 2-3 sentence summary
    description: str  # Full cleaned description
    responsibilities: List[str] = []
    
    # Requirements
    requirements: List[Requirement] = []
    must_have_requirements: List[Requirement] = []
    nice_to_have_requirements: List[Requirement] = []
    
    # Skills & Technologies
    technical_skills: List[str] = []
    soft_skills: List[str] = []
    tools_technologies: List[str] = []
    
    # Additional Information
    benefits: List[str] = []
    salary: Optional[SalaryRange] = None
    application_deadline: Optional[datetime] = None
    
    # Metadata
    language: str = "en"
    processed_at: datetime = Field(default_factory=datetime.now)
    processing_confidence: float = Field(ge=0, le=1)  # 0-1 confidence score
    extraction_warnings: List[str] = []  # Any issues during extraction
    
    @validator('must_have_requirements', 'nice_to_have_requirements', always=True)
    def categorize_requirements(cls, v, values):
        """Auto-categorize requirements by priority"""
        if 'requirements' in values:
            all_reqs = values['requirements']
            must_have = [r for r in all_reqs if r.priority == 'must_have']
            nice_to_have = [r for r in all_reqs if r.priority == 'nice_to_have']
            
            if v == values.get('must_have_requirements'):
                return must_have
            else:
                return nice_to_have
        return v

class ExtractionResult(BaseModel):
    """Result from LLM extraction"""
    job: ProcessedJob
    raw_response: Dict[str, Any]
    tokens_used: int
    cost_estimate: float
    extraction_time: float  # seconds
```

## Rinser Implementation

Create the main module in `app/core/rinser.py`:

```python
import re
import json
import time
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime
import bleach
from bs4 import BeautifulSoup
from langdetect import detect
import asyncio
from pathlib import Path

from app.models.job import (
    RawJobPosting, ProcessedJob, ExtractionResult,
    CompanyInfo, Requirement, SalaryRange,
    EmploymentType, ExperienceLevel, WorkLocation
)
from app.services.llm import LLMService
from app.services.cache import CacheService
from app.config.settings import settings

class Rinser:
    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        cache_service: Optional[CacheService] = None,
        prompts_dir: str = "prompts/extraction"
    ):
        self.llm = llm_service or LLMService()
        self.cache = cache_service or CacheService()
        self.prompts_dir = Path(prompts_dir)
        
        # Load extraction prompts
        self.extraction_prompt = self._load_prompt("job_structure.txt")
        self.requirements_prompt = self._load_prompt("requirements_parser.txt")
        
        # Sanitization settings
        self.allowed_tags = ['p', 'br', 'strong', 'em', 'ul', 'li', 'ol']
        self.allowed_attributes = {}
        
        # Patterns for common job posting elements
        self.patterns = {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'url': re.compile(r'https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/[^\s]*)?'),
            'phone': re.compile(r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}'),
            'salary': re.compile(r'\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?(?:k|K)?(?:\s*-\s*\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?(?:k|K)?)?'),
            'years': re.compile(r'(\d+)\+?\s*(?:years?|yrs?)'),
        }
    
    def _load_prompt(self, filename: str) -> str:
        """Load prompt template from file"""
        prompt_path = self.prompts_dir / filename
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
        with open(prompt_path, 'r') as f:
            return f.read()
    
    async def process(self, raw_job: RawJobPosting) -> ExtractionResult:
        """Main processing pipeline"""
        start_time = time.time()
        
        # Check cache first
        cache_key = f"rinser_{raw_job.generate_hash()}"
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return ExtractionResult(**cached_result)
        
        # Step 1: Sanitize content
        cleaned_content = self.sanitize(raw_job.content)
        
        # Step 2: Detect language
        language = self.detect_language(cleaned_content)
        
        # Step 3: Extract structured data using LLM
        extraction_result = await self.extract_structure(cleaned_content)
        
        # Step 4: Validate and enhance extraction
        processed_job = self.validate_and_enhance(extraction_result, language)
        
        # Step 5: Calculate confidence and warnings
        processed_job.processing_confidence = self.calculate_confidence(processed_job)
        processed_job.extraction_warnings = self.identify_warnings(processed_job)
        
        # Create result
        result = ExtractionResult(
            job=processed_job,
            raw_response=extraction_result,
            tokens_used=extraction_result.get('usage', {}).get('total_tokens', 0),
            cost_estimate=self.calculate_cost(extraction_result),
            extraction_time=time.time() - start_time
        )
        
        # Cache result
        await self.cache.set(cache_key, result.dict(), ttl=settings.cache_ttl)
        
        return result
    
    def sanitize(self, content: str) -> str:
        """Clean and sanitize raw job posting content"""
        # Remove script and style tags completely
        if '<' in content and '>' in content:
            soup = BeautifulSoup(content, 'html.parser')
            for script in soup(['script', 'style']):
                script.decompose()
            content = soup.get_text()
        
        # Use bleach for additional sanitization
        content = bleach.clean(
            content,
            tags=self.allowed_tags,
            attributes=self.allowed_attributes,
            strip=True
        )
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Remove potential malicious patterns
        # Remove base64 encoded content
        content = re.sub(r'data:[^;]+;base64,[A-Za-z0-9+/]+=*', '', content)
        
        # Remove javascript: URLs
        content = re.sub(r'javascript:[^"\']*', '', content, flags=re.IGNORECASE)
        
        # Normalize unicode
        content = content.encode('ascii', 'ignore').decode('ascii', 'ignore')
        
        return content.strip()
    
    def detect_language(self, content: str) -> str:
        """Detect the language of the job posting"""
        try:
            # Take first 500 chars for detection
            sample = content[:500] if len(content) > 500 else content
            return detect(sample)
        except:
            return "en"  # Default to English
    
    async def extract_structure(self, content: str) -> Dict[str, Any]:
        """Use LLM to extract structured data from cleaned content"""
        # Prepare the prompt
        prompt = self.extraction_prompt.format(
            job_content=content[:4000]  # Limit content length for API
        )
        
        # Call LLM with structured output format
        response = await self.llm.extract_json(
            prompt=prompt,
            system_message="You are a job posting parser. Extract structured information and return valid JSON.",
            max_tokens=2000,
            temperature=0.1  # Low temperature for consistency
        )
        
        return response
    
    def validate_and_enhance(
        self, 
        extraction_data: Dict[str, Any],
        language: str
    ) -> ProcessedJob:
        """Validate extracted data and enhance with pattern matching"""
        # Create base job from extraction
        job_data = {
            'content_hash': hashlib.md5(json.dumps(extraction_data, sort_keys=True).encode()).hexdigest(),
            'title': extraction_data.get('title', 'Unknown Position'),
            'language': language,
            'summary': extraction_data.get('summary', ''),
            'description': extraction_data.get('description', ''),
            'responsibilities': extraction_data.get('responsibilities', []),
            'technical_skills': extraction_data.get('technical_skills', []),
            'soft_skills': extraction_data.get('soft_skills', []),
            'tools_technologies': extraction_data.get('tools_technologies', []),
            'benefits': extraction_data.get('benefits', [])
        }
        
        # Process company information
        company_data = extraction_data.get('company', {})
        job_data['company'] = CompanyInfo(
            name=company_data.get('name', 'Unknown Company'),
            industry=company_data.get('industry'),
            size=company_data.get('size'),
            location=company_data.get('location'),
            website=company_data.get('website'),
            description=company_data.get('description')
        )
        
        # Process location
        job_data['location'] = extraction_data.get('location', 'Not specified')
        
        # Process employment type
        emp_type = extraction_data.get('employment_type', '').lower()
        job_data['employment_type'] = self._map_employment_type(emp_type)
        
        # Process experience level
        exp_level = extraction_data.get('experience_level', '').lower()
        job_data['experience_level'] = self._map_experience_level(exp_level)
        
        # Process work location type
        work_loc = extraction_data.get('work_location_type', '').lower()
        job_data['work_location_type'] = self._map_work_location(work_loc)
        
        # Process requirements
        requirements = []
        for req_data in extraction_data.get('requirements', []):
            req = Requirement(
                text=req_data.get('text', ''),
                category=req_data.get('category', 'other'),
                priority=req_data.get('priority', 'nice_to_have'),
                years_needed=req_data.get('years_needed'),
                keywords=req_data.get('keywords', [])
            )
            requirements.append(req)
        job_data['requirements'] = requirements
        
        # Process salary if available
        salary_data = extraction_data.get('salary')
        if salary_data:
            job_data['salary'] = SalaryRange(
                min_amount=salary_data.get('min_amount'),
                max_amount=salary_data.get('max_amount'),
                currency=salary_data.get('currency', 'USD'),
                period=salary_data.get('period', 'yearly'),
                is_negotiable=salary_data.get('is_negotiable', False)
            )
        
        return ProcessedJob(**job_data)
    
    def _map_employment_type(self, emp_type: str) -> EmploymentType:
        """Map extracted employment type to enum"""
        mappings = {
            'full': EmploymentType.FULL_TIME,
            'part': EmploymentType.PART_TIME,
            'contract': EmploymentType.CONTRACT,
            'freelance': EmploymentType.FREELANCE,
            'intern': EmploymentType.INTERNSHIP,
            'temp': EmploymentType.TEMPORARY
        }
        
        for key, value in mappings.items():
            if key in emp_type:
                return value
        return EmploymentType.UNKNOWN
    
    def _map_experience_level(self, exp_level: str) -> ExperienceLevel:
        """Map extracted experience level to enum"""
        mappings = {
            'entry': ExperienceLevel.ENTRY,
            'junior': ExperienceLevel.JUNIOR,
            'mid': ExperienceLevel.MID,
            'senior': ExperienceLevel.SENIOR,
            'lead': ExperienceLevel.LEAD,
            'executive': ExperienceLevel.EXECUTIVE,
            'principal': ExperienceLevel.SENIOR,
            'staff': ExperienceLevel.SENIOR
        }
        
        for key, value in mappings.items():
            if key in exp_level:
                return value
        return ExperienceLevel.UNKNOWN
    
    def _map_work_location(self, work_loc: str) -> WorkLocation:
        """Map extracted work location type to enum"""
        if 'remote' in work_loc:
            return WorkLocation.REMOTE
        elif 'hybrid' in work_loc:
            return WorkLocation.HYBRID
        elif 'onsite' in work_loc or 'office' in work_loc:
            return WorkLocation.ONSITE
        return WorkLocation.UNKNOWN
    
    def calculate_confidence(self, job: ProcessedJob) -> float:
        """Calculate confidence score for extraction quality"""
        score = 0.0
        max_score = 10.0
        
        # Check completeness of required fields
        if job.title != 'Unknown Position':
            score += 2.0
        if job.company.name != 'Unknown Company':
            score += 1.5
        if job.location != 'Not specified':
            score += 1.0
        if job.summary:
            score += 1.0
        if len(job.responsibilities) > 0:
            score += 1.0
        if len(job.requirements) > 0:
            score += 1.5
        if len(job.technical_skills) > 0:
            score += 1.0
        if job.employment_type != EmploymentType.UNKNOWN:
            score += 0.5
        if job.experience_level != ExperienceLevel.UNKNOWN:
            score += 0.5
        
        return min(score / max_score, 1.0)
    
    def identify_warnings(self, job: ProcessedJob) -> List[str]:
        """Identify potential issues with extracted data"""
        warnings = []
        
        if job.processing_confidence < 0.5:
            warnings.append("Low extraction confidence - manual review recommended")
        
        if not job.requirements:
            warnings.append("No requirements extracted")
        
        if not job.technical_skills and not job.tools_technologies:
            warnings.append("No technical skills or tools identified")
        
        if job.title == 'Unknown Position':
            warnings.append("Could not extract job title")
        
        if job.company.name == 'Unknown Company':
            warnings.append("Could not extract company name")
        
        if len(job.description) < 100:
            warnings.append("Description seems too short")
        
        return warnings
    
    def calculate_cost(self, extraction_result: Dict) -> float:
        """Calculate estimated cost for the extraction"""
        # Claude 3.5 Haiku pricing (as of late 2024)
        input_cost_per_1k = 0.001  # $0.001 per 1K input tokens
        output_cost_per_1k = 0.005  # $0.005 per 1K output tokens
        
        usage = extraction_result.get('usage', {})
        input_tokens = usage.get('input_tokens', 0)
        output_tokens = usage.get('output_tokens', 0)
        
        cost = (input_tokens / 1000 * input_cost_per_1k) + \
               (output_tokens / 1000 * output_cost_per_1k)
        
        return round(cost, 6)
```

## Prompt Templates

Create `prompts/extraction/job_structure.txt`:

```text
Extract structured information from the following job posting. Return a JSON object with these fields:

{job_content}

Required JSON structure:
{
  "title": "exact job title",
  "company": {
    "name": "company name",
    "industry": "industry sector",
    "size": "startup|small|medium|large|enterprise",
    "location": "company location",
    "website": "company website URL if mentioned",
    "description": "brief company description"
  },
  "location": "job location",
  "work_location_type": "onsite|remote|hybrid",
  "employment_type": "full_time|part_time|contract|freelance|internship|temporary",
  "experience_level": "entry|junior|mid|senior|lead|executive",
  "summary": "2-3 sentence job summary",
  "description": "full job description",
  "responsibilities": ["list", "of", "key", "responsibilities"],
  "requirements": [
    {
      "text": "requirement description",
      "category": "technical|soft_skill|education|experience|other",
      "priority": "must_have|nice_to_have",
      "years_needed": null or number,
      "keywords": ["relevant", "keywords"]
    }
  ],
  "technical_skills": ["programming", "languages", "frameworks"],
  "soft_skills": ["communication", "leadership"],
  "tools_technologies": ["specific", "tools", "platforms"],
  "benefits": ["health insurance", "401k", "etc"],
  "salary": {
    "min_amount": null or number,
    "max_amount": null or number,
    "currency": "USD",
    "period": "hourly|daily|monthly|yearly",
    "is_negotiable": true or false
  }
}

Focus on accuracy. If information is not present, use null or empty arrays. Do not invent information.
```

## Test Implementation Requirements

Create `tests/test_rinser.py`:

1. **Sanitization Tests**:
   - Test HTML removal
   - Test script/style tag removal
   - Test malicious content filtering
   - Test whitespace normalization

2. **Extraction Tests**:
   - Test with well-formatted job posting
   - Test with minimal job posting
   - Test with non-English content
   - Test missing required fields handling

3. **Validation Tests**:
   - Test enum mapping for employment types
   - Test experience level detection
   - Test requirement categorization

4. **Caching Tests**:
   - Test cache hit for identical content
   - Test cache miss for new content
   - Test cache expiration

5. **Cost Tracking Tests**:
   - Test cost calculation accuracy
   - Test token counting

## Configuration Settings

Update `app/config/settings.py`:

```python
# Add to existing Settings class
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Rinser settings
    max_job_content_length: int = 10000  # Characters
    extraction_timeout: int = 30  # Seconds
    cache_processed_jobs: bool = True
    cache_ttl_hours: int = 24
    
    # Content filters
    block_javascript: bool = True
    block_base64: bool = True
    normalize_unicode: bool = True
    
    # LLM extraction settings
    extraction_model: str = "claude-3-5-haiku-20241022"
    extraction_max_tokens: int = 2000
    extraction_temperature: float = 0.1
    
    # Confidence thresholds
    min_extraction_confidence: float = 0.5
    require_manual_review_below: float = 0.7
```

## Sample Test Job Posting

Create `tests/fixtures/job_postings/sample_job.txt`:

```text
Senior Python Developer - Remote

TechCorp is seeking an experienced Python developer to join our growing team.

About Us:
TechCorp is a leading SaaS company in the fintech space, serving over 10,000 customers globally.

Responsibilities:
- Design and implement scalable Python applications
- Lead code reviews and mentor junior developers
- Collaborate with product team on feature development
- Optimize application performance

Requirements:
- 5+ years of Python development experience (required)
- Experience with FastAPI or Django (required)
- Knowledge of SQL and NoSQL databases (required)
- AWS experience (nice to have)
- Machine learning experience (nice to have)

We Offer:
- Competitive salary: $120,000 - $150,000
- Health, dental, and vision insurance
- Remote work flexibility
- Professional development budget

Location: Remote (US timezones preferred)
Type: Full-time

Apply at careers.techcorp.com
```

## Success Criteria

1. **Sanitization**: Removes 100% of HTML tags, scripts, and malicious patterns
2. **Extraction Accuracy**: Correctly identifies >90% of job fields from well-formatted postings
3. **Performance**: Processes average job posting in <3 seconds
4. **Cost Efficiency**: Average cost per job <$0.02
5. **Caching**: 80% cache hit rate for duplicate postings
6. **Validation**: Zero invalid data structures passed to next module
7. **Language Support**: Correctly detects language for 95% of postings

## Edge Cases to Handle

1. **Malformed HTML**: Job postings with broken HTML tags
2. **Multiple languages**: Postings with mixed language content
3. **Salary variations**: Different salary formats (hourly, yearly, ranges)
4. **Missing information**: Jobs with minimal details
5. **Very long postings**: Content exceeding token limits
6. **Rate limiting**: API throttling during high volume
7. **Non-standard formats**: Creative job posting layouts
8. **Special characters**: Unicode, emojis, special symbols
9. **Duplicate requirements**: Same requirement listed multiple times
10. **Network failures**: LLM API timeouts or errors

## Integration Notes

The Rinser module integrates with:
- **Collector**: Will receive job requirements for matching
- **Analyzer**: Provides structured job data for semantic analysis
- **LLM Service**: Handles all Claude API interactions
- **Cache Service**: Manages processed job caching
- **Cost Tracker**: Reports extraction costs

Build this module with robust error handling, comprehensive logging, and make it production-ready. Ensure clean interfaces for seamless integration with other Scout modules.

---

**37. Should we implement fallback extraction using regex patterns if LLM extraction fails?**
*Recommendation: Yes - Basic regex patterns can extract critical fields (title, company, email) as a safety net when LLM extraction fails or confidence is too low.*

This completes the Rinser module specifications. The module provides robust sanitization, intelligent extraction, and comprehensive validation - ready for integration with the Scout pipeline.