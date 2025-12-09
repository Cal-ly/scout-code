# Module 4: Creator - Claude Code Instructions

**Version:** 2.0 (PoC Aligned)  
**Updated:** November 26, 2025  
**Status:** Ready for Implementation  
**Priority:** Phase 2 - Core Module (Build Fourth in Phase 2)

---

## PoC Scope Summary

| Feature | Status | Notes |
|---------|--------|-------|
| Generate tailored CV content | ✅ In Scope | Via LLM based on analysis |
| Generate cover letter | ✅ In Scope | Via LLM based on analysis |
| Use analysis strategy | ✅ In Scope | Incorporates Analyzer output |
| Return structured content | ✅ In Scope | For Formatter to render |
| Multiple CV templates | ❌ Deferred | Single format for PoC |
| A/B testing variants | ❌ Deferred | Single version |
| Content versioning | ❌ Deferred | Not needed for PoC |
| Tone customization | ❌ Deferred | Professional default |

---

## Context & Objective

Build the **Creator Module** for Scout - generates tailored CV and cover letter content using LLM based on the Analyzer's strategy and the user's profile.

### Why This Module Exists

The Creator transforms analysis into content:
- Takes strategy from Analyzer (what to emphasize, how to position)
- Uses profile data from Collector (actual experiences, skills)
- Generates tailored CV sections and cover letter via LLM
- Produces structured content for Formatter to render

This is where the actual application materials are created.

### Dependencies

This module **requires**:
- **M3 Analyzer**: AnalysisResult with strategy
- **M1 Collector**: UserProfile for content
- **S1 LLM Service**: For content generation

---

## Technical Requirements

### File Structure

```
scout/
├── app/
│   ├── models/
│   │   └── content.py           # Generated content models
│   ├── core/
│   │   └── creator.py           # Creator module
│   └── prompts/
│       └── generation.py        # Generation prompts
└── tests/
    └── unit/
        └── core/
            └── test_creator.py
```

---

## Data Models

Create `app/models/content.py`:

```python
"""
Generated Content Data Models

Models for CV and cover letter content.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class CVSection(BaseModel):
    """
    A section of the generated CV.
    
    Content is pre-formatted for the specific job.
    """
    section_type: str  # "summary", "experience", "skills", "education"
    title: str
    content: str  # Formatted content for this section
    bullet_points: List[str] = Field(default_factory=list)


class GeneratedCV(BaseModel):
    """
    Complete generated CV content.
    
    Tailored to specific job based on analysis.
    """
    # Header info (from profile)
    full_name: str
    email: str
    phone: Optional[str] = None
    location: str
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    
    # Generated sections
    professional_summary: str
    sections: List[CVSection] = Field(default_factory=list)
    
    # Skills (organized)
    technical_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    
    # Metadata
    target_job_title: str
    target_company: str
    generated_at: datetime = Field(default_factory=datetime.now)
    
    def get_section(self, section_type: str) -> Optional[CVSection]:
        """Get a specific section by type."""
        for section in self.sections:
            if section.section_type == section_type:
                return section
        return None


class GeneratedCoverLetter(BaseModel):
    """
    Complete generated cover letter.
    
    Tailored to specific job and company.
    """
    # Header
    recipient_name: Optional[str] = None  # "Hiring Manager" if unknown
    company_name: str
    job_title: str
    
    # Content paragraphs
    opening: str  # Hook + why interested
    body_paragraphs: List[str]  # 2-3 paragraphs
    closing: str  # Call to action + sign-off
    
    # Metadata
    tone: str = "professional"
    word_count: int = 0
    generated_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def full_text(self) -> str:
        """Get complete letter as single text."""
        parts = [self.opening]
        parts.extend(self.body_paragraphs)
        parts.append(self.closing)
        return "\n\n".join(parts)


class ApplicationPackage(BaseModel):
    """
    Complete application package.
    
    Contains all generated content for one application.
    """
    # Identification
    job_id: str
    job_title: str
    company_name: str
    
    # Generated content
    cv: GeneratedCV
    cover_letter: GeneratedCoverLetter
    
    # Analysis reference
    compatibility_score: float
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
```

---

## Generation Prompts

Create `app/prompts/generation.py`:

```python
"""
LLM Prompts for Content Generation

Prompts used by the Creator module.
"""

CV_SYSTEM_PROMPT = """You are an expert CV writer. Create compelling, ATS-friendly CV content.
Focus on quantifiable achievements and relevant experience.
Use action verbs and be concise. Tailor everything to the target job."""

CV_SUMMARY_PROMPT = """Write a professional summary for this CV.

Target Job: {job_title} at {company_name}
Candidate: {full_name}
Current Title: {current_title}
Years Experience: {years_experience}

Key Strengths to Highlight:
{key_strengths}

Strategy:
{positioning}

Write 3-4 sentences that:
1. State their professional identity
2. Highlight most relevant experience
3. Mention key technical skills
4. Show alignment with target role

Return ONLY the summary text, no JSON or formatting."""

CV_EXPERIENCE_PROMPT = """Tailor this experience entry for the target job.

Target Job: {job_title}
Keywords to Include: {keywords}

Original Experience:
Company: {company}
Title: {title}
Duration: {duration}
Description: {description}
Achievements: {achievements}
Technologies: {technologies}

Rewrite to emphasize relevance to target job.
Return JSON:
{{
    "title": "possibly adjusted title",
    "company": "{company}",
    "duration": "{duration}",
    "bullet_points": [
        "Achievement-focused bullet 1",
        "Achievement-focused bullet 2",
        "Achievement-focused bullet 3"
    ]
}}

Guidelines:
- Start bullets with action verbs
- Include metrics where possible
- Incorporate target keywords naturally
- Keep 3-5 bullets per role"""

COVER_LETTER_SYSTEM_PROMPT = """You are an expert cover letter writer.
Write compelling, personalized cover letters that stand out.
Be authentic, enthusiastic, and specific. Avoid generic phrases."""

COVER_LETTER_PROMPT = """Write a cover letter for this application.

Job: {job_title} at {company_name}
Applicant: {full_name}, {current_title}

Application Strategy:
{positioning}

Key Strengths:
{key_strengths}

How to Address Gaps:
{address_gaps}

Opening Hook Suggestion:
{opening_hook}

Relevant Experiences:
{relevant_experiences}

Return JSON:
{{
    "opening": "Opening paragraph (2-3 sentences with hook)",
    "body_paragraphs": [
        "Paragraph about relevant experience and skills",
        "Paragraph about specific achievements and value"
    ],
    "closing": "Closing paragraph with call to action"
}}

Guidelines:
- Opening should hook immediately (use the hook suggestion)
- Be specific about why THIS company
- Show don't tell - use examples
- Keep under 400 words total
- End with clear call to action"""
```

---

## Module Implementation

Create `app/core/creator.py`:

```python
"""
Creator Module

Generates tailored CV and cover letter content using LLM.

Usage:
    creator = Creator(collector, llm_service)
    
    package = await creator.create_application(analysis_result)
    print(package.cv.professional_summary)
    print(package.cover_letter.full_text)
"""

import logging
from typing import Optional, List
from datetime import date

from app.models.content import (
    GeneratedCV, GeneratedCoverLetter, ApplicationPackage,
    CVSection
)
from app.models.analysis import AnalysisResult, ApplicationStrategy
from app.models.profile import UserProfile, Experience, Skill, SkillCategory
from app.core.collector import Collector
from app.services.llm import LLMService
from app.prompts.generation import (
    CV_SYSTEM_PROMPT, CV_SUMMARY_PROMPT, CV_EXPERIENCE_PROMPT,
    COVER_LETTER_SYSTEM_PROMPT, COVER_LETTER_PROMPT
)
from app.utils.exceptions import ScoutError

logger = logging.getLogger(__name__)


class CreatorError(ScoutError):
    """Error in Creator operations."""
    pass


class Creator:
    """
    Creator Module - generates application content.
    
    Responsibilities:
    - Generate tailored CV content
    - Generate personalized cover letter
    - Use analysis strategy for positioning
    
    Attributes:
        collector: Collector for profile access
        llm: LLM Service for generation
        
    Example:
        >>> creator = Creator(collector, llm)
        >>> package = await creator.create_application(analysis)
        >>> print(package.cv.professional_summary)
        "Senior Python developer with 6+ years..."
    """
    
    def __init__(
        self,
        collector: Collector,
        llm_service: LLMService
    ):
        """
        Initialize Creator.
        
        Args:
            collector: Collector with loaded profile
            llm_service: LLM Service for generation
        """
        self._collector = collector
        self._llm = llm_service
    
    @property
    def profile(self) -> UserProfile:
        """Get user profile from collector."""
        return self._collector.profile
    
    # =========================================================================
    # CV GENERATION
    # =========================================================================
    
    async def _generate_summary(
        self,
        analysis: AnalysisResult
    ) -> str:
        """
        Generate professional summary.
        
        Args:
            analysis: Analysis result with strategy
            
        Returns:
            Professional summary text
        """
        strategy = analysis.strategy or ApplicationStrategy(
            positioning="Highlight relevant experience",
            key_strengths=["Technical skills", "Experience"],
            address_gaps=[],
            tone="professional",
            keywords_to_use=[]
        )
        
        current_exp = self.profile.get_current_experience()
        current_title = current_exp.title if current_exp else self.profile.title
        
        prompt = CV_SUMMARY_PROMPT.format(
            job_title=analysis.job_title,
            company_name=analysis.company_name,
            full_name=self.profile.personal.full_name,
            current_title=current_title,
            years_experience=self.profile.years_experience,
            key_strengths="\n".join(f"- {s}" for s in strategy.key_strengths),
            positioning=strategy.positioning
        )
        
        summary = await self._llm.generate_text(
            prompt=prompt,
            system=CV_SYSTEM_PROMPT,
            module="creator",
            purpose="generate_cv_summary"
        )
        
        return summary.strip()
    
    async def _generate_experience_section(
        self,
        experience: Experience,
        keywords: List[str]
    ) -> CVSection:
        """
        Generate tailored experience section.
        
        Args:
            experience: Experience to tailor
            keywords: Keywords to incorporate
            
        Returns:
            CVSection with tailored content
        """
        # Calculate duration
        end = experience.end_date or date.today()
        months = (end.year - experience.start_date.year) * 12 + (end.month - experience.start_date.month)
        years = months / 12
        
        if years >= 1:
            duration = f"{years:.1f} years"
        else:
            duration = f"{months} months"
        
        prompt = CV_EXPERIENCE_PROMPT.format(
            job_title="Target Position",  # From analysis
            keywords=", ".join(keywords[:10]),
            company=experience.company,
            title=experience.title,
            duration=duration,
            description=experience.description,
            achievements="\n".join(f"- {a}" for a in experience.achievements),
            technologies=", ".join(experience.technologies)
        )
        
        try:
            result = await self._llm.generate_json(
                prompt=prompt,
                system=CV_SYSTEM_PROMPT,
                module="creator",
                purpose="generate_experience"
            )
            
            return CVSection(
                section_type="experience",
                title=f"{result.get('title', experience.title)} | {experience.company}",
                content=result.get('duration', duration),
                bullet_points=result.get('bullet_points', experience.achievements[:4])
            )
            
        except Exception as e:
            logger.warning(f"Experience generation failed: {e}, using original")
            return CVSection(
                section_type="experience",
                title=f"{experience.title} | {experience.company}",
                content=duration,
                bullet_points=experience.achievements[:4]
            )
    
    def _build_skills_section(
        self,
        strategy: Optional[ApplicationStrategy]
    ) -> tuple[List[str], List[str]]:
        """
        Build skills lists prioritized by strategy.
        
        Args:
            strategy: Application strategy with keywords
            
        Returns:
            Tuple of (technical_skills, soft_skills)
        """
        keywords = set(strategy.keywords_to_use if strategy else [])
        
        technical = []
        soft = []
        
        for skill in self.profile.skills:
            skill_name = skill.name
            
            # Prioritize skills in keywords
            if skill.category == SkillCategory.SOFT_SKILL:
                soft.append(skill_name)
            else:
                if skill_name.lower() in [k.lower() for k in keywords]:
                    technical.insert(0, skill_name)  # Front of list
                else:
                    technical.append(skill_name)
        
        return technical[:15], soft[:5]  # Limit counts
    
    async def generate_cv(
        self,
        analysis: AnalysisResult
    ) -> GeneratedCV:
        """
        Generate complete CV.
        
        Args:
            analysis: Analysis result for tailoring
            
        Returns:
            GeneratedCV with all content
        """
        logger.info(f"Generating CV for {analysis.job_title}")
        
        # Generate summary
        summary = await self._generate_summary(analysis)
        
        # Generate experience sections
        sections = []
        keywords = analysis.strategy.keywords_to_use if analysis.strategy else []
        
        for exp in self.profile.experiences[:3]:  # Top 3 experiences
            section = await self._generate_experience_section(exp, keywords)
            sections.append(section)
        
        # Add education
        for edu in self.profile.education:
            sections.append(CVSection(
                section_type="education",
                title=f"{edu.degree} in {edu.field}",
                content=edu.institution,
                bullet_points=edu.relevant_courses[:3] if edu.relevant_courses else []
            ))
        
        # Build skills
        technical_skills, soft_skills = self._build_skills_section(analysis.strategy)
        
        return GeneratedCV(
            full_name=self.profile.personal.full_name,
            email=self.profile.personal.email,
            phone=self.profile.personal.phone,
            location=self.profile.personal.location,
            linkedin_url=self.profile.personal.linkedin_url,
            github_url=self.profile.personal.github_url,
            professional_summary=summary,
            sections=sections,
            technical_skills=technical_skills,
            soft_skills=soft_skills,
            target_job_title=analysis.job_title,
            target_company=analysis.company_name
        )
    
    # =========================================================================
    # COVER LETTER GENERATION
    # =========================================================================
    
    async def generate_cover_letter(
        self,
        analysis: AnalysisResult
    ) -> GeneratedCoverLetter:
        """
        Generate cover letter.
        
        Args:
            analysis: Analysis result for tailoring
            
        Returns:
            GeneratedCoverLetter
        """
        logger.info(f"Generating cover letter for {analysis.job_title}")
        
        strategy = analysis.strategy or ApplicationStrategy(
            positioning="Highlight relevant experience",
            key_strengths=["Technical expertise"],
            address_gaps=["Express enthusiasm to learn"],
            tone="professional",
            keywords_to_use=[],
            opening_hook=None
        )
        
        current_exp = self.profile.get_current_experience()
        current_title = current_exp.title if current_exp else self.profile.title
        
        # Build relevant experiences text
        relevant_exp_text = []
        for exp in self.profile.experiences[:2]:
            relevant_exp_text.append(
                f"- {exp.title} at {exp.company}: {exp.achievements[0] if exp.achievements else exp.description[:100]}"
            )
        
        prompt = COVER_LETTER_PROMPT.format(
            job_title=analysis.job_title,
            company_name=analysis.company_name,
            full_name=self.profile.personal.full_name,
            current_title=current_title,
            positioning=strategy.positioning,
            key_strengths="\n".join(f"- {s}" for s in strategy.key_strengths),
            address_gaps="\n".join(f"- {g}" for g in strategy.address_gaps) or "None identified",
            opening_hook=strategy.opening_hook or "Express genuine interest in the role",
            relevant_experiences="\n".join(relevant_exp_text)
        )
        
        try:
            result = await self._llm.generate_json(
                prompt=prompt,
                system=COVER_LETTER_SYSTEM_PROMPT,
                module="creator",
                purpose="generate_cover_letter"
            )
            
            letter = GeneratedCoverLetter(
                company_name=analysis.company_name,
                job_title=analysis.job_title,
                opening=result.get("opening", ""),
                body_paragraphs=result.get("body_paragraphs", []),
                closing=result.get("closing", ""),
                tone=strategy.tone
            )
            
        except Exception as e:
            logger.warning(f"Cover letter generation failed: {e}, using fallback")
            letter = GeneratedCoverLetter(
                company_name=analysis.company_name,
                job_title=analysis.job_title,
                opening=f"I am writing to express my interest in the {analysis.job_title} position at {analysis.company_name}.",
                body_paragraphs=[
                    f"With {self.profile.years_experience} years of experience, I am confident I can contribute to your team.",
                    "My background aligns well with the requirements of this role."
                ],
                closing="I look forward to the opportunity to discuss how I can contribute to your team. Thank you for your consideration."
            )
        
        # Calculate word count
        letter.word_count = len(letter.full_text.split())
        
        return letter
    
    # =========================================================================
    # MAIN GENERATION
    # =========================================================================
    
    async def create_application(
        self,
        analysis: AnalysisResult
    ) -> ApplicationPackage:
        """
        Create complete application package.
        
        Main entry point for the Creator module.
        
        Args:
            analysis: Analysis result from Analyzer
            
        Returns:
            ApplicationPackage with CV and cover letter
            
        Example:
            >>> package = await creator.create_application(analysis)
            >>> print(package.cv.professional_summary)
            >>> print(package.cover_letter.full_text)
        """
        logger.info(
            f"Creating application package for {analysis.job_title} "
            f"at {analysis.company_name}"
        )
        
        # Generate CV
        cv = await self.generate_cv(analysis)
        
        # Generate cover letter
        cover_letter = await self.generate_cover_letter(analysis)
        
        package = ApplicationPackage(
            job_id=analysis.job_id,
            job_title=analysis.job_title,
            company_name=analysis.company_name,
            cv=cv,
            cover_letter=cover_letter,
            compatibility_score=analysis.compatibility.overall
        )
        
        logger.info(
            f"Application package created: "
            f"CV ({len(cv.sections)} sections), "
            f"Cover letter ({cover_letter.word_count} words)"
        )
        
        return package
```

---

## Test Implementation

Create `tests/unit/core/test_creator.py`:

```python
"""
Unit tests for Creator Module.

Run with: pytest tests/unit/core/test_creator.py -v
"""

import pytest
from datetime import date
from unittest.mock import Mock, AsyncMock, PropertyMock

from app.core.creator import Creator, CreatorError
from app.models.content import (
    GeneratedCV, GeneratedCoverLetter, ApplicationPackage
)
from app.models.analysis import (
    AnalysisResult, CompatibilityScore, MatchLevel, ApplicationStrategy
)
from app.models.profile import (
    UserProfile, PersonalInfo, Skill, Experience, Education,
    SkillLevel, SkillCategory
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_profile():
    """Create sample user profile."""
    return UserProfile(
        personal=PersonalInfo(
            full_name="Jane Developer",
            email="jane@example.com",
            phone="+1-555-1234",
            location="San Francisco, CA",
            linkedin_url="https://linkedin.com/in/jane"
        ),
        title="Senior Software Engineer",
        summary="Experienced developer",
        years_experience=6.0,
        skills=[
            Skill(name="Python", level=SkillLevel.EXPERT, years=6, category=SkillCategory.PROGRAMMING),
            Skill(name="FastAPI", level=SkillLevel.ADVANCED, years=3, category=SkillCategory.FRAMEWORK),
            Skill(name="Leadership", level=SkillLevel.INTERMEDIATE, category=SkillCategory.SOFT_SKILL)
        ],
        experiences=[
            Experience(
                company="TechCorp",
                title="Senior Developer",
                start_date=date(2020, 1, 1),
                description="Led backend development",
                achievements=["Improved performance by 40%", "Led team of 5"],
                technologies=["Python", "FastAPI", "PostgreSQL"]
            )
        ],
        education=[
            Education(
                institution="UC Berkeley",
                degree="BS",
                field="Computer Science",
                graduation_date=date(2018, 5, 15)
            )
        ]
    )


@pytest.fixture
def sample_analysis():
    """Create sample analysis result."""
    return AnalysisResult(
        job_id="test-job",
        job_title="Senior Python Developer",
        company_name="TargetCorp",
        compatibility=CompatibilityScore(
            overall=75.0,
            level=MatchLevel.STRONG,
            technical_skills=80.0,
            experience_relevance=70.0,
            requirements_met=75.0,
            must_haves_met=2,
            must_haves_total=3
        ),
        skill_matches=[],
        experience_matches=[],
        gaps=[],
        strategy=ApplicationStrategy(
            positioning="Position as experienced Python developer",
            key_strengths=["Python expertise", "Backend development", "Team leadership"],
            address_gaps=["Highlight cloud learning path"],
            tone="professional",
            keywords_to_use=["Python", "FastAPI", "API", "backend"],
            opening_hook="With 6 years of Python experience..."
        )
    )


@pytest.fixture
def mock_collector(sample_profile):
    """Create mock Collector."""
    collector = Mock()
    type(collector).profile = PropertyMock(return_value=sample_profile)
    return collector


@pytest.fixture
def mock_llm_service():
    """Create mock LLM Service."""
    llm = AsyncMock()
    
    # Mock text generation (for summary)
    llm.generate_text.return_value = "Senior Python developer with 6+ years of experience building scalable backend systems."
    
    # Mock JSON generation (for experience and cover letter)
    llm.generate_json.side_effect = [
        # Experience section
        {
            "title": "Senior Developer",
            "company": "TechCorp",
            "duration": "4 years",
            "bullet_points": [
                "Improved system performance by 40%",
                "Led team of 5 developers",
                "Built REST APIs with FastAPI"
            ]
        },
        # Cover letter
        {
            "opening": "I am excited to apply for the Senior Python Developer position at TargetCorp.",
            "body_paragraphs": [
                "With 6 years of Python experience, I have built scalable backend systems.",
                "At TechCorp, I led initiatives that improved performance by 40%."
            ],
            "closing": "I look forward to discussing how I can contribute to your team."
        }
    ]
    
    return llm


@pytest.fixture
def creator(mock_collector, mock_llm_service):
    """Create Creator for testing."""
    return Creator(mock_collector, mock_llm_service)


# =============================================================================
# CV GENERATION TESTS
# =============================================================================

class TestCVGeneration:
    """Tests for CV generation."""
    
    @pytest.mark.asyncio
    async def test_generate_cv(self, creator, sample_analysis):
        """Should generate complete CV."""
        cv = await creator.generate_cv(sample_analysis)
        
        assert isinstance(cv, GeneratedCV)
        assert cv.full_name == "Jane Developer"
        assert cv.professional_summary != ""
        assert len(cv.sections) > 0
        assert cv.target_job_title == "Senior Python Developer"
    
    @pytest.mark.asyncio
    async def test_generate_summary(self, creator, sample_analysis, mock_llm_service):
        """Should generate professional summary."""
        summary = await creator._generate_summary(sample_analysis)
        
        assert summary != ""
        mock_llm_service.generate_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_skills_prioritized_by_keywords(self, creator, sample_analysis):
        """Should prioritize skills matching keywords."""
        technical, soft = creator._build_skills_section(sample_analysis.strategy)
        
        # Python should be first (it's in keywords)
        assert "Python" in technical
        assert "Leadership" in soft


# =============================================================================
# COVER LETTER TESTS
# =============================================================================

class TestCoverLetterGeneration:
    """Tests for cover letter generation."""
    
    @pytest.mark.asyncio
    async def test_generate_cover_letter(self, creator, sample_analysis):
        """Should generate complete cover letter."""
        # Need to set up mock for cover letter (it's second call)
        creator._llm.generate_json.side_effect = None
        creator._llm.generate_json.return_value = {
            "opening": "Opening paragraph",
            "body_paragraphs": ["Body 1", "Body 2"],
            "closing": "Closing paragraph"
        }
        
        letter = await creator.generate_cover_letter(sample_analysis)
        
        assert isinstance(letter, GeneratedCoverLetter)
        assert letter.company_name == "TargetCorp"
        assert letter.opening != ""
        assert len(letter.body_paragraphs) >= 1
        assert letter.word_count > 0
    
    @pytest.mark.asyncio
    async def test_cover_letter_full_text(self, creator, sample_analysis):
        """Should combine paragraphs into full text."""
        creator._llm.generate_json.return_value = {
            "opening": "Opening",
            "body_paragraphs": ["Body"],
            "closing": "Closing"
        }
        
        letter = await creator.generate_cover_letter(sample_analysis)
        
        assert "Opening" in letter.full_text
        assert "Body" in letter.full_text
        assert "Closing" in letter.full_text


# =============================================================================
# APPLICATION PACKAGE TESTS
# =============================================================================

class TestApplicationPackage:
    """Tests for complete application generation."""
    
    @pytest.mark.asyncio
    async def test_create_application(self, creator, sample_analysis):
        """Should create complete application package."""
        # Reset mock for multiple calls
        creator._llm.generate_json.side_effect = [
            # Experience
            {"title": "Dev", "company": "Co", "duration": "1y", "bullet_points": ["Did stuff"]},
            # Cover letter
            {"opening": "Hi", "body_paragraphs": ["Body"], "closing": "Bye"}
        ]
        
        package = await creator.create_application(sample_analysis)
        
        assert isinstance(package, ApplicationPackage)
        assert package.job_id == "test-job"
        assert package.cv is not None
        assert package.cover_letter is not None
        assert package.compatibility_score == 75.0
    
    @pytest.mark.asyncio
    async def test_application_without_strategy(self, creator, sample_analysis):
        """Should handle analysis without strategy."""
        sample_analysis.strategy = None
        
        creator._llm.generate_json.side_effect = [
            {"title": "Dev", "company": "Co", "duration": "1y", "bullet_points": ["Did stuff"]},
            {"opening": "Hi", "body_paragraphs": ["Body"], "closing": "Bye"}
        ]
        
        package = await creator.create_application(sample_analysis)
        
        # Should still work with defaults
        assert package.cv is not None
        assert package.cover_letter is not None


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_experience_generation_fallback(self, creator, sample_analysis):
        """Should use fallback when experience generation fails."""
        creator._llm.generate_json.side_effect = Exception("LLM error")
        
        exp = creator.profile.experiences[0]
        section = await creator._generate_experience_section(exp, ["Python"])
        
        # Should return fallback content
        assert section.title is not None
        assert len(section.bullet_points) > 0
```

---

## Implementation Steps

### Step M4.1: Data Models
```bash
# Create app/models/content.py
# Verify:
python -c "from app.models.content import GeneratedCV, ApplicationPackage; print('OK')"
```

### Step M4.2: Generation Prompts
```bash
# Create app/prompts/generation.py
# Verify:
python -c "from app.prompts.generation import CV_SUMMARY_PROMPT; print('OK')"
```

### Step M4.3: Module Implementation
```bash
# Create app/core/creator.py
# Verify:
python -c "from app.core.creator import Creator; print('OK')"
```

### Step M4.4: Unit Tests
```bash
# Create tests/unit/core/test_creator.py
# Verify:
pytest tests/unit/core/test_creator.py -v
```

### Step M4.5: Integration Test
```bash
# Verify end-to-end (after Analyzer is working):
python -c "
import asyncio
# ... full pipeline test ...
"
```

---

## Success Criteria

| Metric | Target | Verification |
|--------|--------|--------------|
| CV generation | All sections created | Check sections list |
| Cover letter | 3-4 paragraphs | Check structure |
| Strategy incorporation | Keywords used | Check content |
| Fallback handling | Graceful degradation | Test with errors |
| Test coverage | >90% | `pytest --cov=app/core/creator` |

---

*This specification is aligned with Scout PoC Scope Document v1.0*
