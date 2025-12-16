"""
Profile API Schemas (Multi-Profile CRUD)

Pydantic models for profile API requests and responses.
Uses the normalized data structure from WP2.
"""

from pydantic import BaseModel, Field

# =============================================================================
# COMPONENT SCHEMAS (for nested data)
# =============================================================================


class SkillSchema(BaseModel):
    """Skill in API requests/responses."""

    name: str
    level: str | None = None  # beginner, intermediate, advanced, expert
    years: int | None = None
    category: str | None = None


class ExperienceSchema(BaseModel):
    """Experience in API requests/responses."""

    title: str
    company: str
    start_date: str | None = None  # YYYY-MM format
    end_date: str | None = None  # YYYY-MM format, null = current
    description: str | None = None
    achievements: list[str] = Field(default_factory=list)


class EducationSchema(BaseModel):
    """Education in API requests/responses."""

    institution: str
    degree: str | None = None
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: str | None = None
    achievements: list[str] = Field(default_factory=list)


class CertificationSchema(BaseModel):
    """Certification in API requests/responses."""

    name: str
    issuer: str | None = None
    date_obtained: str | None = None
    expiry_date: str | None = None
    credential_url: str | None = None


class LanguageSchema(BaseModel):
    """Language in API requests/responses."""

    language: str
    proficiency: str | None = None  # basic, conversational, professional, fluent, native


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================


class ProfileCreateRequest(BaseModel):
    """Request to create a new profile."""

    name: str = Field(
        ..., min_length=1, max_length=200, description="Profile name (e.g., 'Backend Focus')"
    )
    title: str | None = Field(None, max_length=200, description="Professional title")
    email: str | None = Field(None, description="Contact email for applications")
    phone: str | None = Field(None, description="Contact phone")
    location: str | None = Field(None, description="Location (e.g., 'San Francisco, CA')")
    summary: str | None = Field(None, description="Professional summary")

    # Related data
    skills: list[SkillSchema] = Field(default_factory=list)
    experiences: list[ExperienceSchema] = Field(default_factory=list)
    education: list[EducationSchema] = Field(default_factory=list)
    certifications: list[CertificationSchema] = Field(default_factory=list)
    languages: list[LanguageSchema] = Field(default_factory=list)

    # Options
    set_active: bool = Field(False, description="Set as active profile after creation")


class ProfileUpdateRequest(BaseModel):
    """Request to update a profile. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=200)
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None

    # Related data - if provided, REPLACES existing
    skills: list[SkillSchema] | None = None
    experiences: list[ExperienceSchema] | None = None
    education: list[EducationSchema] | None = None
    certifications: list[CertificationSchema] | None = None
    languages: list[LanguageSchema] | None = None


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================


class ProfileStatsSchema(BaseModel):
    """Profile statistics."""

    skill_count: int = 0
    experience_count: int = 0
    education_count: int = 0
    certification_count: int = 0
    language_count: int = 0
    application_count: int = 0
    completed_application_count: int = 0
    avg_compatibility_score: float | None = None


class CompletenessSection(BaseModel):
    """Completeness score for one section."""

    name: str
    score: int
    max_score: int
    items_present: int
    items_recommended: int
    suggestions: list[str] = Field(default_factory=list)


class ProfileCompletenessSchema(BaseModel):
    """Profile completeness assessment."""

    overall_score: int
    level: str  # excellent, good, fair, needs_work
    sections: list[CompletenessSection] = Field(default_factory=list)
    top_suggestions: list[str] = Field(default_factory=list)


class ProfileSummaryResponse(BaseModel):
    """Profile summary for list views."""

    id: int
    slug: str
    name: str
    title: str | None
    is_active: bool
    is_demo: bool
    created_at: str
    updated_at: str
    stats: ProfileStatsSchema


class ProfileDetailResponse(BaseModel):
    """Full profile details."""

    id: int
    slug: str
    name: str
    title: str | None
    email: str | None
    phone: str | None
    location: str | None
    summary: str | None
    is_active: bool
    is_demo: bool
    created_at: str
    updated_at: str

    # Related data
    skills: list[SkillSchema] = Field(default_factory=list)
    experiences: list[ExperienceSchema] = Field(default_factory=list)
    education: list[EducationSchema] = Field(default_factory=list)
    certifications: list[CertificationSchema] = Field(default_factory=list)
    languages: list[LanguageSchema] = Field(default_factory=list)

    # Stats and completeness
    stats: ProfileStatsSchema
    completeness: ProfileCompletenessSchema | None = None


class ProfileListResponse(BaseModel):
    """Response for profile list."""

    profiles: list[ProfileSummaryResponse]
    total: int
    active_profile_slug: str | None


class ProfileActivateResponse(BaseModel):
    """Response after activating a profile."""

    profile: ProfileSummaryResponse
    indexed: bool
    index_count: int | None = None
    message: str
