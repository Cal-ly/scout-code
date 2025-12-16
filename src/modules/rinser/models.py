"""
M2 Rinser Models

Pydantic models for job posting data.
"""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


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
    years_required: int | None = None

    def to_searchable_text(self) -> str:
        """Convert to text for embedding."""
        parts = [self.text]
        if self.years_required:
            parts.append(f"{self.years_required} years")
        return " ".join(parts)


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

    name: str = "Unknown Company"  # Default for postings without explicit company name
    industry: str | None = None
    size: str | None = None  # e.g., "50-200 employees"
    culture_notes: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def name_not_null(cls, v: str | None) -> str:
        """Convert null/empty name to default."""
        if v is None or v == "" or v.lower() == "null":
            return "Unknown Company"
        return v


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
    location: str | None = None
    employment_type: str | None = None  # "Full-time", "Contract", etc.
    salary_range: str | None = None

    # Structured content
    requirements: list[Requirement] = Field(default_factory=list)
    responsibilities: list[Responsibility] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)

    # Original content
    raw_text: str
    summary: str | None = None  # LLM-generated summary

    # Metadata
    processed_at: datetime = Field(default_factory=datetime.now)
    indexed: bool = False
    index_count: int = 0

    @field_validator("requirements")
    @classmethod
    def validate_requirements(cls, v: list[Requirement]) -> list[Requirement]:
        """Ensure at least one requirement exists."""
        if not v:
            raise ValueError("Job must have at least one requirement")
        return v

    def get_must_have_requirements(self) -> list[Requirement]:
        """Get only must-have requirements."""
        return [
            r for r in self.requirements if r.priority == RequirementPriority.MUST_HAVE
        ]

    def get_nice_to_have_requirements(self) -> list[Requirement]:
        """Get only nice-to-have requirements."""
        return [
            r
            for r in self.requirements
            if r.priority == RequirementPriority.NICE_TO_HAVE
        ]

    def get_technical_requirements(self) -> list[Requirement]:
        """Get only technical requirements."""
        return [
            r for r in self.requirements if r.category == RequirementCategory.TECHNICAL
        ]

    def get_experience_requirements(self) -> list[Requirement]:
        """Get experience-related requirements."""
        return [
            r for r in self.requirements if r.category == RequirementCategory.EXPERIENCE
        ]

    def get_requirements_by_category(
        self, category: RequirementCategory
    ) -> list[Requirement]:
        """Get requirements filtered by category."""
        return [r for r in self.requirements if r.category == category]


class JobInput(BaseModel):
    """
    Input for job processing.

    Simple text input for PoC (URL fetching deferred).
    """

    raw_text: str = Field(..., min_length=100, description="Raw job posting text")
    source: str | None = None  # e.g., "linkedin", "indeed"
    url: str | None = None  # For reference only, not fetched


class ProcessingResult(BaseModel):
    """Result of job processing operation."""

    success: bool
    job: ProcessedJob | None = None
    error: str | None = None
    processing_time_ms: int = 0
