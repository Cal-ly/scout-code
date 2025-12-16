"""Database models using Pydantic.

This module defines all Pydantic models for the database layer, including:
- User models for identity management
- Profile models with normalized related data (skills, experiences, etc.)
- Application models for job application tracking
- Completeness models for profile quality scoring
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# ENUMS
# =============================================================================


class SkillLevel(str, Enum):
    """Proficiency level for skills."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class LanguageProficiency(str, Enum):
    """Proficiency level for languages."""

    BASIC = "basic"
    CONVERSATIONAL = "conversational"
    PROFESSIONAL = "professional"
    FLUENT = "fluent"
    NATIVE = "native"


class ApplicationStatus(str, Enum):
    """Application processing status."""

    PENDING = "pending"
    RUNNING = "running"  # Keep for backward compatibility
    PROCESSING = "processing"  # Alias for RUNNING
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# USER MODELS
# =============================================================================


class UserBase(BaseModel):
    """Base user fields."""

    username: str
    email: str | None = None
    display_name: str | None = None


class UserCreate(UserBase):
    """User creation request."""

    pass


class User(UserBase):
    """User database record."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# SKILL MODELS
# =============================================================================


class SkillBase(BaseModel):
    """Base skill fields."""

    name: str
    level: SkillLevel | None = None
    years: int | None = None
    category: str | None = None
    sort_order: int = 0


class SkillCreate(SkillBase):
    """Skill creation request."""

    pass


class Skill(SkillBase):
    """Skill database record."""

    id: int
    profile_id: int

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# EXPERIENCE MODELS
# =============================================================================


class ExperienceBase(BaseModel):
    """Base experience fields."""

    title: str
    company: str
    start_date: str | None = None
    end_date: str | None = None  # None = current position
    description: str | None = None
    achievements: list[str] = Field(default_factory=list)
    sort_order: int = 0


class ExperienceCreate(ExperienceBase):
    """Experience creation request."""

    pass


class Experience(ExperienceBase):
    """Experience database record."""

    id: int
    profile_id: int

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# EDUCATION MODELS
# =============================================================================


class EducationBase(BaseModel):
    """Base education fields."""

    institution: str
    degree: str | None = None
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: str | None = None
    achievements: list[str] = Field(default_factory=list)
    sort_order: int = 0


class EducationCreate(EducationBase):
    """Education creation request."""

    pass


class Education(EducationBase):
    """Education database record."""

    id: int
    profile_id: int

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# CERTIFICATION MODELS
# =============================================================================


class CertificationBase(BaseModel):
    """Base certification fields."""

    name: str
    issuer: str | None = None
    date_obtained: str | None = None
    expiry_date: str | None = None
    credential_url: str | None = None
    sort_order: int = 0


class CertificationCreate(CertificationBase):
    """Certification creation request."""

    pass


class Certification(CertificationBase):
    """Certification database record."""

    id: int
    profile_id: int

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# LANGUAGE MODELS
# =============================================================================


class LanguageBase(BaseModel):
    """Base language fields."""

    language: str
    proficiency: LanguageProficiency | None = None
    sort_order: int = 0


class LanguageCreate(LanguageBase):
    """Language creation request."""

    pass


class Language(LanguageBase):
    """Language database record."""

    id: int
    profile_id: int

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# PROFILE MODELS
# =============================================================================


class ProfileBase(BaseModel):
    """Base profile fields."""

    name: str
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None


class ProfileCreate(ProfileBase):
    """Profile creation request with all related data.

    Related data (skills, experiences, etc.) will be created along with
    the profile. If slug is not provided, it will be auto-generated from name.
    """

    slug: str | None = None  # Auto-generated from name if not provided
    skills: list[SkillCreate] = Field(default_factory=list)
    experiences: list[ExperienceCreate] = Field(default_factory=list)
    education: list[EducationCreate] = Field(default_factory=list)
    certifications: list[CertificationCreate] = Field(default_factory=list)
    languages: list[LanguageCreate] = Field(default_factory=list)


class ProfileUpdate(BaseModel):
    """Profile update request.

    All fields are optional. If a list field is provided, it REPLACES
    existing data. If a list field is None, existing data is preserved.
    """

    name: str | None = None
    slug: str | None = None
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    skills: list[SkillCreate] | None = None
    experiences: list[ExperienceCreate] | None = None
    education: list[EducationCreate] | None = None
    certifications: list[CertificationCreate] | None = None
    languages: list[LanguageCreate] | None = None


class Profile(ProfileBase):
    """Full profile with all related data."""

    id: int
    user_id: int
    slug: str
    is_active: bool = False
    is_demo: bool = False
    created_at: datetime
    updated_at: datetime

    # Related data (loaded separately)
    skills: list[Skill] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ProfileSummary(BaseModel):
    """Lightweight profile for list views.

    Includes counts and stats without loading full related data.
    """

    id: int
    user_id: int
    slug: str
    name: str
    title: str | None = None
    is_active: bool = False
    is_demo: bool = False
    created_at: datetime
    updated_at: datetime

    # Counts
    skill_count: int = 0
    experience_count: int = 0
    education_count: int = 0
    certification_count: int = 0
    language_count: int = 0

    # Application stats
    application_count: int = 0
    completed_application_count: int = 0
    avg_compatibility_score: float | None = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# COMPLETENESS MODELS
# =============================================================================


class CompletenessSection(BaseModel):
    """Completeness score for a profile section."""

    name: str
    score: int  # Points earned
    max_score: int  # Maximum possible points
    items_present: int
    items_recommended: int
    suggestions: list[str] = Field(default_factory=list)


class ProfileCompleteness(BaseModel):
    """Overall profile completeness assessment."""

    overall_score: int  # 0-100 percentage
    level: str  # "excellent", "good", "fair", "needs_work"
    sections: list[CompletenessSection] = Field(default_factory=list)
    top_suggestions: list[str] = Field(default_factory=list)  # Top 3


# =============================================================================
# APPLICATION MODELS
# =============================================================================


class ApplicationBase(BaseModel):
    """Base application fields."""

    job_title: str | None = None
    company_name: str | None = None


class ApplicationCreate(ApplicationBase):
    """Application creation request."""

    job_id: str
    user_id: int
    profile_id: int
    job_text: str


class ApplicationUpdate(BaseModel):
    """Application update request."""

    job_title: str | None = None
    company_name: str | None = None
    status: ApplicationStatus | None = None
    compatibility_score: float | None = None
    cv_path: str | None = None
    cover_letter_path: str | None = None
    analysis_data: dict[str, Any] | None = None
    pipeline_data: dict[str, Any] | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class Application(ApplicationBase):
    """Application database record."""

    id: int
    job_id: str
    user_id: int
    profile_id: int
    job_text: str
    status: ApplicationStatus = ApplicationStatus.PENDING
    compatibility_score: float | None = None
    cv_path: str | None = None
    cover_letter_path: str | None = None
    analysis_data: dict[str, Any] | None = None
    pipeline_data: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Joined fields from profile
    profile_name: str | None = None
    profile_slug: str | None = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# SETTINGS MODEL
# =============================================================================


class Settings(BaseModel):
    """Application settings."""

    active_profile_id: int | None = None
    schema_version: int = 2
    demo_data_loaded: bool = False
