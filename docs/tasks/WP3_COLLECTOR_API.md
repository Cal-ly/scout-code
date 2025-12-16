# Work Package 3: Collector Integration & API Routes

## Overview

This work package bridges the new normalized database schema with the Collector module and updates the API routes to use the new structure. The web interface updates will be handled in WP4.

**Prerequisites:** 
- WP1 complete (schemas, models, completeness)
- WP2 complete (DatabaseService, demo data)

**Reference:** See `docs/tasks/REFACTOR_GUIDE.md` for architectural context.

**Time Estimate:** 3-4 hours

---

## Architecture Decision: Bridge Pattern

The Collector module has its own domain model (`UserProfile`) with methods like `to_searchable_text()` for vector indexing. Rather than modifying the database models to include these methods (which would mix concerns), we'll create a **bridge/adapter** that converts between:

```
Database Layer                    Collector Layer
─────────────────                 ───────────────
Profile (normalized)    ──────►   UserProfile (for indexing)
├── skills[]                      ├── skills[] with to_searchable_text()
├── experiences[]                 ├── experiences[] with to_searchable_text()
├── education[]                   └── etc.
└── etc.

Conversion happens in Collector.load_profile_from_db()
```

This maintains separation of concerns:
- Database models: persistence and CRUD
- Collector models: semantic search and indexing

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `src/modules/collector/models.py` | UPDATE | Add `from_db_profile()` class method |
| `src/modules/collector/collector.py` | UPDATE | Rewrite `load_profile_from_db()` |
| `src/web/routes/api/v1/profiles.py` | REWRITE | Use normalized data, add completeness |
| `src/web/routes/api/schemas/profiles.py` | CREATE | Dedicated schemas for profile API |
| `tests/test_collector.py` | UPDATE | Add tests for DB loading |
| `tests/test_profiles_api.py` | CREATE | API route tests |

---

## Part 1: Collector Model Updates

**Update file:** `src/modules/collector/models.py`

### Add Conversion Method to UserProfile

Add a class method to `UserProfile` that constructs from the database `Profile`:

```python
# Add this import at the top
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.database.models import Profile as DBProfile

# Add this class method to UserProfile class
class UserProfile(BaseModel):
    # ... existing fields ...

    @classmethod
    def from_db_profile(cls, db_profile: "DBProfile") -> "UserProfile":
        """
        Construct UserProfile from database Profile.
        
        Converts normalized database data to the flat structure
        expected by the Collector for indexing.
        
        Args:
            db_profile: Profile from database with loaded relations.
            
        Returns:
            UserProfile ready for vector indexing.
        """
        # Convert skills
        skills = [
            Skill(
                name=s.name,
                level=SkillLevel(s.level) if s.level else SkillLevel.INTERMEDIATE,
                years=float(s.years) if s.years else None,
                keywords=[],  # Could be populated from category
            )
            for s in db_profile.skills
        ]
        
        # Convert experiences
        experiences = [
            Experience(
                id=str(exp.id),
                company=exp.company,
                role=exp.title,  # DB uses 'title', collector uses 'role'
                start_date=_parse_date_string(exp.start_date),
                end_date=_parse_date_string(exp.end_date),
                current=exp.end_date is None,
                description=exp.description or "",
                achievements=exp.achievements or [],
                technologies=[],  # Could be extracted from description
            )
            for exp in db_profile.experiences
        ]
        
        # Convert education
        education = [
            Education(
                institution=edu.institution,
                degree=edu.degree or "",
                field=edu.field or "",
                start_date=_parse_date_string(edu.start_date),
                end_date=_parse_date_string(edu.end_date),
                gpa=_parse_gpa(edu.gpa),
                relevant_courses=[],
            )
            for edu in db_profile.education
        ]
        
        # Convert certifications
        certifications = [
            Certification(
                name=cert.name,
                issuer=cert.issuer or "",
                date_obtained=_parse_date_string(cert.date_obtained),
                expiry_date=_parse_date_string(cert.expiry_date),
                credential_id=None,
            )
            for cert in db_profile.certifications
        ]
        
        # Calculate years of experience from experiences
        years_exp = _calculate_years_experience(experiences)
        
        return cls(
            full_name=db_profile.name,
            email=db_profile.email or "",
            phone=db_profile.phone,
            location=db_profile.location or "",
            linkedin_url=None,
            github_url=None,
            title=db_profile.title or "",
            years_experience=years_exp,
            summary=db_profile.summary or "",
            skills=skills,
            experiences=experiences,
            education=education,
            certifications=certifications,
        )


def _parse_date_string(date_str: str | None) -> datetime | None:
    """Parse date string from database to datetime."""
    if not date_str:
        return None
    try:
        # Handle YYYY-MM format
        if len(date_str) == 7:
            return datetime.strptime(date_str, "%Y-%m")
        # Handle YYYY-MM-DD format
        if len(date_str) == 10:
            return datetime.strptime(date_str, "%Y-%m-%d")
        # Try ISO format
        return datetime.fromisoformat(date_str)
    except ValueError:
        return None


def _parse_gpa(gpa_str: str | None) -> float | None:
    """Parse GPA string to float."""
    if not gpa_str:
        return None
    try:
        return float(gpa_str)
    except ValueError:
        return None


def _calculate_years_experience(experiences: list[Experience]) -> float:
    """Calculate total years of professional experience."""
    if not experiences:
        return 0.0
    
    total_months = 0
    now = datetime.now()
    
    for exp in experiences:
        start = exp.start_date
        end = exp.end_date or now
        
        if start:
            months = (end.year - start.year) * 12 + (end.month - start.month)
            total_months += max(0, months)
    
    return round(total_months / 12, 1)
```

---

## Part 2: Collector Load from Database

**Update file:** `src/modules/collector/collector.py`

### Rewrite `load_profile_from_db()`

Replace the existing method with one that uses the normalized schema:

```python
async def load_profile_from_db(self) -> UserProfile | None:
    """
    Load the active profile from database.

    Converts the normalized database profile to UserProfile
    for vector indexing and matching.

    Returns:
        The active UserProfile, or None if no active profile exists.
    """
    from src.services.database import get_database_service

    db = await get_database_service()
    
    # Get active profile with all relations loaded
    db_profile = await db.get_active_profile()

    if db_profile is None:
        logger.warning("No active profile in database")
        return None

    # Convert to UserProfile using the bridge method
    self._profile = UserProfile.from_db_profile(db_profile)
    self._profile_hash = f"db_{db_profile.id}_{db_profile.updated_at.timestamp()}"

    logger.info(f"Loaded profile from database: {db_profile.name} (id={db_profile.id})")
    return self._profile
```

### Add Method to Load Specific Profile

Add a new method to load any profile by slug (not just active):

```python
async def load_profile_by_slug(self, slug: str) -> UserProfile:
    """
    Load a specific profile from database by slug.

    Args:
        slug: Profile slug to load.

    Returns:
        The loaded UserProfile.

    Raises:
        ProfileNotFoundError: If profile doesn't exist.
    """
    from src.services.database import get_database_service, ProfileNotFoundError as DBProfileNotFoundError

    db = await get_database_service()
    
    try:
        db_profile = await db.get_profile_by_slug(slug)
    except DBProfileNotFoundError:
        raise ProfileNotFoundError(f"Profile '{slug}' not found in database")

    # Convert to UserProfile
    self._profile = UserProfile.from_db_profile(db_profile)
    self._profile_hash = f"db_{db_profile.id}_{db_profile.updated_at.timestamp()}"

    logger.info(f"Loaded profile: {db_profile.name} (slug={slug})")
    return self._profile
```

### Update Initialization to Use Database

Update `get_collector()` to automatically load the active profile from DB:

```python
async def get_collector() -> Collector:
    """
    Get the Collector module instance.

    Creates and initializes singleton on first call.
    Automatically loads active profile from database.

    Returns:
        Initialized Collector instance with active profile loaded.
    """
    from src.services.vector_store import get_vector_store_service

    global _collector_instance

    if _collector_instance is None:
        vector_store = await get_vector_store_service()
        _collector_instance = Collector(vector_store)
        await _collector_instance.initialize()
        
        # Try to load active profile from database
        try:
            profile = await _collector_instance.load_profile_from_db()
            if profile:
                # Auto-index if not already indexed
                # Check if we need to index
                try:
                    stats = await vector_store.get_collection_stats(COLLECTION_NAME)
                    if stats.document_count == 0:
                        await _collector_instance.index_profile()
                except Exception:
                    # Collection might not exist yet
                    await _collector_instance.index_profile()
        except Exception as e:
            logger.warning(f"Could not load profile from database: {e}")

    return _collector_instance
```

---

## Part 3: API Schemas

**Create file:** `src/web/routes/api/schemas/profiles.py`

```python
"""
Profile API Schemas

Pydantic models for profile API requests and responses.
Uses the normalized data structure from WP2.
"""

from datetime import datetime
from typing import Any

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
    name: str = Field(..., min_length=1, max_length=200, description="Profile name (e.g., 'Backend Focus')")
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
```

---

## Part 4: API Routes Rewrite

**Rewrite file:** `src/web/routes/api/v1/profiles.py`

```python
"""
Profile API Routes (v2 - Normalized Schema)

CRUD operations for user profiles with normalized data structure.

Endpoints:
    GET    /api/v1/profiles              - List all profiles
    POST   /api/v1/profiles              - Create new profile
    GET    /api/v1/profiles/active       - Get active profile
    GET    /api/v1/profiles/{slug}       - Get profile details
    PUT    /api/v1/profiles/{slug}       - Update profile
    DELETE /api/v1/profiles/{slug}       - Delete profile
    POST   /api/v1/profiles/{slug}/activate - Set as active
    GET    /api/v1/profiles/{slug}/completeness - Get completeness score
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from src.services.database import (
    DatabaseService,
    ProfileCreate,
    ProfileUpdate,
    SkillCreate,
    ExperienceCreate,
    EducationCreate,
    CertificationCreate,
    LanguageCreate,
    SkillLevel,
    LanguageProficiency,
    get_database_service,
    calculate_completeness,
)
from src.services.database.exceptions import ProfileNotFoundError, ProfileSlugExistsError
from src.web.routes.api.schemas.profiles import (
    ProfileCreateRequest,
    ProfileUpdateRequest,
    ProfileSummaryResponse,
    ProfileDetailResponse,
    ProfileListResponse,
    ProfileActivateResponse,
    ProfileStatsSchema,
    ProfileCompletenessSchema,
    CompletenessSection,
    SkillSchema,
    ExperienceSchema,
    EducationSchema,
    CertificationSchema,
    LanguageSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profiles", tags=["profiles"])


# =============================================================================
# HELPERS
# =============================================================================


def _profile_to_summary_response(profile, stats) -> ProfileSummaryResponse:
    """Convert database profile to summary response."""
    return ProfileSummaryResponse(
        id=profile.id,
        slug=profile.slug,
        name=profile.name,
        title=profile.title,
        is_active=profile.is_active,
        is_demo=profile.is_demo,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat(),
        stats=ProfileStatsSchema(
            skill_count=stats.skill_count if hasattr(stats, 'skill_count') else len(profile.skills),
            experience_count=stats.experience_count if hasattr(stats, 'experience_count') else len(profile.experiences),
            education_count=stats.education_count if hasattr(stats, 'education_count') else len(profile.education),
            certification_count=stats.certification_count if hasattr(stats, 'certification_count') else len(profile.certifications),
            language_count=stats.language_count if hasattr(stats, 'language_count') else len(profile.languages),
            application_count=getattr(stats, 'application_count', 0),
            completed_application_count=getattr(stats, 'completed_application_count', 0),
            avg_compatibility_score=getattr(stats, 'avg_compatibility_score', None),
        ),
    )


def _profile_to_detail_response(profile, completeness=None) -> ProfileDetailResponse:
    """Convert database profile to detail response."""
    return ProfileDetailResponse(
        id=profile.id,
        slug=profile.slug,
        name=profile.name,
        title=profile.title,
        email=profile.email,
        phone=profile.phone,
        location=profile.location,
        summary=profile.summary,
        is_active=profile.is_active,
        is_demo=profile.is_demo,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat(),
        skills=[
            SkillSchema(
                name=s.name,
                level=s.level.value if s.level else None,
                years=s.years,
                category=s.category,
            )
            for s in profile.skills
        ],
        experiences=[
            ExperienceSchema(
                title=e.title,
                company=e.company,
                start_date=e.start_date,
                end_date=e.end_date,
                description=e.description,
                achievements=e.achievements or [],
            )
            for e in profile.experiences
        ],
        education=[
            EducationSchema(
                institution=ed.institution,
                degree=ed.degree,
                field=ed.field,
                start_date=ed.start_date,
                end_date=ed.end_date,
                gpa=ed.gpa,
                achievements=ed.achievements or [],
            )
            for ed in profile.education
        ],
        certifications=[
            CertificationSchema(
                name=c.name,
                issuer=c.issuer,
                date_obtained=c.date_obtained,
                expiry_date=c.expiry_date,
                credential_url=c.credential_url,
            )
            for c in profile.certifications
        ],
        languages=[
            LanguageSchema(
                language=lang.language,
                proficiency=lang.proficiency.value if lang.proficiency else None,
            )
            for lang in profile.languages
        ],
        stats=ProfileStatsSchema(
            skill_count=len(profile.skills),
            experience_count=len(profile.experiences),
            education_count=len(profile.education),
            certification_count=len(profile.certifications),
            language_count=len(profile.languages),
        ),
        completeness=_completeness_to_schema(completeness) if completeness else None,
    )


def _completeness_to_schema(comp) -> ProfileCompletenessSchema:
    """Convert completeness result to schema."""
    return ProfileCompletenessSchema(
        overall_score=comp.overall_score,
        level=comp.level,
        sections=[
            CompletenessSection(
                name=s.name,
                score=s.score,
                max_score=s.max_score,
                items_present=s.items_present,
                items_recommended=s.items_recommended,
                suggestions=s.suggestions,
            )
            for s in comp.sections
        ],
        top_suggestions=comp.top_suggestions,
    )


def _request_to_profile_create(request: ProfileCreateRequest, user_id: int) -> ProfileCreate:
    """Convert API request to database ProfileCreate."""
    return ProfileCreate(
        name=request.name,
        title=request.title,
        email=request.email,
        phone=request.phone,
        location=request.location,
        summary=request.summary,
        skills=[
            SkillCreate(
                name=s.name,
                level=SkillLevel(s.level) if s.level else None,
                years=s.years,
                category=s.category,
            )
            for s in request.skills
        ],
        experiences=[
            ExperienceCreate(
                title=e.title,
                company=e.company,
                start_date=e.start_date,
                end_date=e.end_date,
                description=e.description,
                achievements=e.achievements,
            )
            for e in request.experiences
        ],
        education=[
            EducationCreate(
                institution=ed.institution,
                degree=ed.degree,
                field=ed.field,
                start_date=ed.start_date,
                end_date=ed.end_date,
                gpa=ed.gpa,
                achievements=ed.achievements,
            )
            for ed in request.education
        ],
        certifications=[
            CertificationCreate(
                name=c.name,
                issuer=c.issuer,
                date_obtained=c.date_obtained,
                expiry_date=c.expiry_date,
                credential_url=c.credential_url,
            )
            for c in request.certifications
        ],
        languages=[
            LanguageCreate(
                language=lang.language,
                proficiency=LanguageProficiency(lang.proficiency) if lang.proficiency else None,
            )
            for lang in request.languages
        ],
    )


def _request_to_profile_update(request: ProfileUpdateRequest) -> ProfileUpdate:
    """Convert API request to database ProfileUpdate."""
    update = ProfileUpdate(
        name=request.name,
        title=request.title,
        email=request.email,
        phone=request.phone,
        location=request.location,
        summary=request.summary,
    )
    
    # Only include lists if provided (None means preserve existing)
    if request.skills is not None:
        update.skills = [
            SkillCreate(
                name=s.name,
                level=SkillLevel(s.level) if s.level else None,
                years=s.years,
                category=s.category,
            )
            for s in request.skills
        ]
    
    if request.experiences is not None:
        update.experiences = [
            ExperienceCreate(
                title=e.title,
                company=e.company,
                start_date=e.start_date,
                end_date=e.end_date,
                description=e.description,
                achievements=e.achievements,
            )
            for e in request.experiences
        ]
    
    if request.education is not None:
        update.education = [
            EducationCreate(
                institution=ed.institution,
                degree=ed.degree,
                field=ed.field,
                start_date=ed.start_date,
                end_date=ed.end_date,
                gpa=ed.gpa,
                achievements=ed.achievements,
            )
            for ed in request.education
        ]
    
    if request.certifications is not None:
        update.certifications = [
            CertificationCreate(
                name=c.name,
                issuer=c.issuer,
                date_obtained=c.date_obtained,
                expiry_date=c.expiry_date,
                credential_url=c.credential_url,
            )
            for c in request.certifications
        ]
    
    if request.languages is not None:
        update.languages = [
            LanguageCreate(
                language=lang.language,
                proficiency=LanguageProficiency(lang.proficiency) if lang.proficiency else None,
            )
            for lang in request.languages
        ]
    
    return update


async def _reindex_active_profile() -> tuple[bool, int]:
    """Re-index the active profile in vector store.
    
    Returns:
        Tuple of (success, document_count).
    """
    try:
        from src.modules.collector import get_collector
        
        collector = await get_collector()
        
        # Reload from database
        profile = await collector.load_profile_from_db()
        if profile is None:
            return False, 0
        
        # Clear and re-index
        await collector.clear_index()
        count = await collector.index_profile()
        
        return True, count
    except Exception as e:
        logger.error(f"Failed to re-index profile: {e}")
        return False, 0


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("", response_model=ProfileListResponse)
async def list_profiles(
    db: DatabaseService = Depends(get_database_service),
) -> ProfileListResponse:
    """List all profiles with summary stats."""
    profiles = await db.list_profiles()
    
    # Get active profile
    active = await db.get_active_profile()
    active_slug = active.slug if active else None
    
    return ProfileListResponse(
        profiles=[_profile_to_summary_response(p, p) for p in profiles],
        total=len(profiles),
        active_profile_slug=active_slug,
    )


@router.post("", response_model=ProfileDetailResponse, status_code=201)
async def create_profile(
    request: ProfileCreateRequest,
    db: DatabaseService = Depends(get_database_service),
) -> ProfileDetailResponse:
    """Create a new profile."""
    try:
        # Get current user
        user = await db.get_current_user()
        
        # Create profile
        profile_create = _request_to_profile_create(request, user.id)
        profile = await db.create_profile(user.id, profile_create)
        
        # Activate and index if requested
        if request.set_active:
            profile = await db.activate_profile(profile.slug)
            await _reindex_active_profile()
        
        # Get completeness
        completeness = calculate_completeness(profile)
        
        return _profile_to_detail_response(profile, completeness)
        
    except ProfileSlugExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/active", response_model=ProfileDetailResponse | None)
async def get_active_profile(
    db: DatabaseService = Depends(get_database_service),
) -> ProfileDetailResponse | None:
    """Get the currently active profile."""
    profile = await db.get_active_profile()
    if profile is None:
        return None
    
    completeness = calculate_completeness(profile)
    return _profile_to_detail_response(profile, completeness)


@router.get("/{slug}", response_model=ProfileDetailResponse)
async def get_profile(
    slug: str,
    db: DatabaseService = Depends(get_database_service),
) -> ProfileDetailResponse:
    """Get profile by slug with full details."""
    try:
        profile = await db.get_profile_by_slug(slug)
        completeness = calculate_completeness(profile)
        return _profile_to_detail_response(profile, completeness)
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found")


@router.put("/{slug}", response_model=ProfileDetailResponse)
async def update_profile(
    slug: str,
    request: ProfileUpdateRequest,
    db: DatabaseService = Depends(get_database_service),
) -> ProfileDetailResponse:
    """Update a profile."""
    try:
        # Update profile
        profile_update = _request_to_profile_update(request)
        profile = await db.update_profile(slug, profile_update)
        
        # Re-index if active profile was updated
        if profile.is_active:
            await _reindex_active_profile()
        
        completeness = calculate_completeness(profile)
        return _profile_to_detail_response(profile, completeness)
        
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found")


@router.delete("/{slug}")
async def delete_profile(
    slug: str,
    db: DatabaseService = Depends(get_database_service),
) -> dict:
    """Delete a profile."""
    try:
        profile = await db.get_profile_by_slug(slug)
        
        if profile.is_active:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete active profile. Activate another profile first."
            )
        
        await db.delete_profile(slug)
        return {"status": "deleted", "slug": slug}
        
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found")


@router.post("/{slug}/activate", response_model=ProfileActivateResponse)
async def activate_profile(
    slug: str,
    db: DatabaseService = Depends(get_database_service),
) -> ProfileActivateResponse:
    """Set a profile as active and re-index for matching."""
    try:
        # Activate in database
        profile = await db.activate_profile(slug)
        
        # Re-index in vector store
        indexed, count = await _reindex_active_profile()
        
        return ProfileActivateResponse(
            profile=_profile_to_summary_response(profile, profile),
            indexed=indexed,
            index_count=count if indexed else None,
            message=f"Profile '{profile.name}' is now active" + (f" ({count} items indexed)" if indexed else ""),
        )
        
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found")


@router.get("/{slug}/completeness", response_model=ProfileCompletenessSchema)
async def get_profile_completeness(
    slug: str,
    db: DatabaseService = Depends(get_database_service),
) -> ProfileCompletenessSchema:
    """Get profile completeness score with suggestions."""
    try:
        profile = await db.get_profile_by_slug(slug)
        completeness = calculate_completeness(profile)
        return _completeness_to_schema(completeness)
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found")
```

---

## Part 5: Update Schemas `__init__.py`

**Update file:** `src/web/routes/api/schemas/__init__.py`

Add the new profiles schemas:

```python
# Add to existing exports
from .profiles import (
    ProfileCreateRequest,
    ProfileUpdateRequest,
    ProfileSummaryResponse,
    ProfileDetailResponse,
    ProfileListResponse,
    ProfileActivateResponse,
    ProfileStatsSchema,
    ProfileCompletenessSchema,
    SkillSchema,
    ExperienceSchema,
    EducationSchema,
    CertificationSchema,
    LanguageSchema,
)
```

---

## Part 6: Update User Endpoint

**Create/Update file:** `src/web/routes/api/v1/user.py`

Add a simple user endpoint for the navbar:

```python
"""
User API Routes

Current user information for the UI.
"""

import logging

from fastapi import APIRouter, Depends

from src.services.database import DatabaseService, get_database_service
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["user"])


class UserResponse(BaseModel):
    """Current user info."""
    id: int
    username: str
    display_name: str | None
    email: str | None


@router.get("", response_model=UserResponse)
async def get_current_user(
    db: DatabaseService = Depends(get_database_service),
) -> UserResponse:
    """Get current user information."""
    user = await db.get_current_user()
    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
    )
```

**Update:** `src/web/routes/api/v1/__init__.py` to include the user router:

```python
from .user import router as user_router

# Add to router includes
api_router.include_router(user_router)
```

---

## Validation Steps

### 1. Verify Imports

```bash
python -c "
from src.modules.collector.models import UserProfile
from src.services.database import Profile, get_database_service
from src.web.routes.api.schemas.profiles import (
    ProfileCreateRequest,
    ProfileDetailResponse,
)
print('All imports successful')
"
```

### 2. Test Collector Bridge

```bash
python -c "
import asyncio
from src.services.database import get_database_service
from src.modules.collector.models import UserProfile

async def test():
    db = await get_database_service()
    
    # Get a profile from database
    profile = await db.get_active_profile()
    print(f'DB Profile: {profile.name}')
    print(f'  Skills: {len(profile.skills)}')
    print(f'  Experiences: {len(profile.experiences)}')
    
    # Convert to UserProfile
    user_profile = UserProfile.from_db_profile(profile)
    print(f'UserProfile: {user_profile.full_name}')
    print(f'  Skills: {len(user_profile.skills)}')
    print(f'  Experiences: {len(user_profile.experiences)}')
    
    # Verify searchable text works
    if user_profile.skills:
        print(f'  Skill text: {user_profile.skills[0].to_searchable_text()[:50]}...')

asyncio.run(test())
"
```

### 3. Test Collector Loading from DB

```bash
python -c "
import asyncio
from src.modules.collector import get_collector

async def test():
    collector = await get_collector()
    
    # Should have loaded active profile
    profile = collector.get_profile()
    print(f'Loaded: {profile.full_name}')
    print(f'Skills: {len(profile.skills)}')
    
    # Test search
    results = await collector.search_skills('Python')
    print(f'Search results: {len(results)}')

asyncio.run(test())
"
```

### 4. Test API Endpoints

```bash
# Start server in background or use existing
# Then test with curl:

# List profiles
curl -s http://localhost:8000/api/v1/profiles | python -m json.tool | head -30

# Get active profile
curl -s http://localhost:8000/api/v1/profiles/active | python -m json.tool | head -50

# Get completeness
curl -s http://localhost:8000/api/v1/profiles/backend-focus/completeness | python -m json.tool
```

### 5. Run Existing Tests (May Need Updates)

```bash
# Run collector tests
pytest tests/test_collector.py -v --tb=short 2>&1 | head -50

# Check for failures that need fixing in WP3
```

---

## Files to NOT Modify

These will be updated in WP4 (Web Interface):
- `src/web/templates/*.html`
- `src/web/static/js/common.js`
- `src/web/static/css/common.css`
- `src/web/routes/pages.py`

---

## Completion Checklist

- [ ] `src/modules/collector/models.py` updated with `from_db_profile()`
- [ ] `src/modules/collector/collector.py` updated with new DB loading
- [ ] `src/web/routes/api/schemas/profiles.py` created
- [ ] `src/web/routes/api/v1/profiles.py` rewritten
- [ ] `src/web/routes/api/v1/user.py` created
- [ ] `src/web/routes/api/v1/__init__.py` updated
- [ ] `src/web/routes/api/schemas/__init__.py` updated
- [ ] All validation steps pass
- [ ] Code committed

```bash
git add src/modules/collector/
git add src/web/routes/api/
git commit -m "WP3: Integrate Collector with normalized database schema

- Add UserProfile.from_db_profile() bridge method
- Update Collector to load from normalized database
- Rewrite profile API routes for normalized data
- Add dedicated profile API schemas
- Add user endpoint for navbar
- Add profile completeness endpoint

Part of user/profile refactor - see docs/tasks/REFACTOR_GUIDE.md"
```

---

## Notes for Work Package 4

WP4 will cover the Web Interface updates:
1. Update navbar (remove profile switcher, add user menu)
2. Update profile list page (`profiles_list.html`)
3. Rewrite profile editor with tabs (`profile_edit.html`)
4. Update `common.js` for new API structure
5. Update any other templates that reference profiles
