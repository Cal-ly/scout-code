"""
M1 Collector Data Models

Pydantic models for user profile management and semantic search.
"""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class SkillLevel(str, Enum):
    """Skill proficiency levels."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class Skill(BaseModel):
    """
    A professional skill with proficiency level.

    Attributes:
        name: Skill name (e.g., "Python", "Project Management").
        level: Proficiency level.
        years: Years of experience with this skill.
        keywords: Related terms for better matching.
    """

    name: str
    level: SkillLevel = SkillLevel.INTERMEDIATE
    years: float | None = None
    keywords: list[str] = Field(default_factory=list)

    def to_searchable_text(self) -> str:
        """Create text representation for vector embedding."""
        text = f"{self.name} - {self.level.value} level"
        if self.years:
            text += f", {self.years} years experience"
        if self.keywords:
            text += f". Related: {', '.join(self.keywords)}"
        return text


class Experience(BaseModel):
    """
    A work experience entry.

    Attributes:
        id: Unique identifier for this experience.
        company: Company/organization name.
        role: Job title/role.
        start_date: When the role started.
        end_date: When the role ended (None if current).
        current: Whether this is the current role.
        description: Role description and responsibilities.
        achievements: Notable accomplishments in this role.
        technologies: Technologies/tools used.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    company: str
    role: str
    start_date: datetime
    end_date: datetime | None = None
    current: bool = False
    description: str = ""
    achievements: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def set_current_from_end_date(self) -> "Experience":
        """Set current=True if end_date is None."""
        if self.end_date is None:
            object.__setattr__(self, "current", True)
        return self

    def to_searchable_text(self) -> str:
        """Create text representation for vector embedding."""
        text = f"{self.role} at {self.company}. {self.description}"
        if self.technologies:
            text += f" Technologies: {', '.join(self.technologies)}."
        if self.achievements:
            text += f" Achievements: {' '.join(self.achievements)}"
        return text


class Education(BaseModel):
    """
    An education entry.

    Attributes:
        institution: School/university name.
        degree: Degree type (e.g., "Bachelor's", "Master's").
        field: Field of study.
        start_date: When education started.
        end_date: When education ended (None if ongoing).
        gpa: Grade point average (optional).
        relevant_courses: Courses relevant for job matching.
    """

    institution: str
    degree: str
    field: str
    start_date: datetime
    end_date: datetime | None = None
    gpa: float | None = None
    relevant_courses: list[str] = Field(default_factory=list)

    @field_validator("gpa", mode="before")
    @classmethod
    def parse_gpa(cls, v: str | float | None) -> float | None:
        """Parse GPA value, handling string formats like '9.8/12'."""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            # Handle fraction format like "9.8/12"
            if "/" in v:
                try:
                    numerator, _ = v.split("/", 1)
                    return float(numerator.strip())
                except (ValueError, IndexError):
                    return None
            # Try direct float conversion
            try:
                return float(v)
            except ValueError:
                return None
        return None

    def to_searchable_text(self) -> str:
        """Create text representation for vector embedding."""
        text = f"{self.degree} in {self.field} from {self.institution}"
        if self.relevant_courses:
            text += f". Courses: {', '.join(self.relevant_courses)}"
        return text


class Certification(BaseModel):
    """
    A professional certification.

    Attributes:
        name: Certification name.
        issuer: Issuing organization.
        date_obtained: When certification was obtained (optional).
        expiry_date: When certification expires (None if permanent).
        credential_id: Credential/license number.
    """

    name: str
    issuer: str
    date_obtained: datetime | None = None
    expiry_date: datetime | None = None
    credential_id: str | None = None

    def to_searchable_text(self) -> str:
        """Create text representation for vector embedding."""
        text = f"{self.name} certification from {self.issuer}"
        if self.credential_id:
            text += f" (ID: {self.credential_id})"
        return text


class UserProfile(BaseModel):
    """
    Complete user professional profile.

    This is the primary data structure for storing and matching
    user qualifications against job requirements.

    Attributes:
        full_name: User's full name.
        email: Contact email.
        phone: Contact phone (optional).
        location: City/region.
        linkedin_url: LinkedIn profile URL (optional).
        github_url: GitHub profile URL (optional).
        title: Professional title.
        years_experience: Total years of professional experience.
        summary: Professional summary/bio.
        skills: List of professional skills.
        experiences: Work experience history.
        education: Education history.
        certifications: Professional certifications.
        profile_version: Schema version for migrations.
        last_updated: When profile was last modified.
    """

    # Basic Info
    full_name: str
    email: str
    phone: str | None = None
    location: str = ""
    linkedin_url: str | None = None
    github_url: str | None = None

    # Professional Summary
    title: str = ""
    years_experience: float = 0.0
    summary: str = ""

    # Detailed Sections
    skills: list[Skill] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)

    # Metadata
    profile_version: str = "1.0"
    last_updated: datetime = Field(default_factory=datetime.now)


class ProfileSummary(BaseModel):
    """
    Summary view of a user profile.

    Used for quick access without full profile data.
    """

    name: str
    title: str
    years_experience: float
    skill_count: int
    experience_count: int
    education_count: int
    certification_count: int
    last_updated: datetime


class SearchMatch(BaseModel):
    """
    A search result for profile content.

    Attributes:
        id: Document ID in vector store.
        content: Original text content.
        match_type: Type of content (skill, experience, education, certification).
        score: Similarity score (0-1).
        metadata: Additional context about the match.
    """

    id: str
    content: str
    match_type: str  # "skill", "experience", "education", "certification"
    score: float
    metadata: dict[str, str | float | int | bool | None] = Field(default_factory=dict)


class SkillMatch(BaseModel):
    """
    Result of matching a requirement against skills.

    Attributes:
        requirement: The original requirement searched for.
        matched_skills: Skills that matched this requirement.
    """

    requirement: str
    matched_skills: list[SearchMatch] = Field(default_factory=list)

    @property
    def best_match(self) -> SearchMatch | None:
        """Get the highest scoring match."""
        if not self.matched_skills:
            return None
        return max(self.matched_skills, key=lambda x: x.score)

    @property
    def has_match(self) -> bool:
        """Whether any skills matched this requirement."""
        return len(self.matched_skills) > 0
