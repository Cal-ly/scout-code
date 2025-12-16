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
    CertificationCreate,
    DatabaseService,
    EducationCreate,
    ExperienceCreate,
    LanguageCreate,
    LanguageProficiency,
    ProfileCreate,
    ProfileUpdate,
    SkillCreate,
    SkillLevel,
    calculate_completeness,
    get_database_service,
)
from src.services.database.exceptions import ProfileNotFoundError, ProfileSlugExistsError
from src.web.routes.api.schemas.profiles import (
    CertificationSchema,
    CompletenessSection,
    EducationSchema,
    ExperienceSchema,
    LanguageSchema,
    ProfileActivateResponse,
    ProfileCompletenessSchema,
    ProfileCreateRequest,
    ProfileDetailResponse,
    ProfileListResponse,
    ProfileStatsSchema,
    ProfileSummaryResponse,
    ProfileUpdateRequest,
    SkillSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profiles", tags=["profiles"])


# =============================================================================
# HELPERS
# =============================================================================


def _profile_to_summary_response(profile) -> ProfileSummaryResponse:
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
            skill_count=getattr(profile, "skill_count", len(getattr(profile, "skills", []))),
            experience_count=getattr(
                profile, "experience_count", len(getattr(profile, "experiences", []))
            ),
            education_count=getattr(
                profile, "education_count", len(getattr(profile, "education", []))
            ),
            certification_count=getattr(
                profile, "certification_count", len(getattr(profile, "certifications", []))
            ),
            language_count=getattr(
                profile, "language_count", len(getattr(profile, "languages", []))
            ),
            application_count=getattr(profile, "application_count", 0),
            completed_application_count=getattr(profile, "completed_application_count", 0),
            avg_compatibility_score=getattr(profile, "avg_compatibility_score", None),
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


def _request_to_profile_create(request: ProfileCreateRequest) -> ProfileCreate:
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
        profiles=[_profile_to_summary_response(p) for p in profiles],
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
        profile_create = _request_to_profile_create(request)
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
                detail="Cannot delete active profile. Activate another profile first.",
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
            profile=_profile_to_summary_response(profile),
            indexed=indexed,
            index_count=count if indexed else None,
            message=f"Profile '{profile.name}' is now active"
            + (f" ({count} items indexed)" if indexed else ""),
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
