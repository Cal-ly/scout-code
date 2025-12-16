"""
Multi-Profile API Routes

CRUD operations for user profiles.

Endpoints:
    GET /api/v1/profiles - List all profiles
    POST /api/v1/profiles - Create new profile
    GET /api/v1/profiles/{slug} - Get profile by slug
    PUT /api/v1/profiles/{slug} - Update profile
    DELETE /api/v1/profiles/{slug} - Delete profile
    POST /api/v1/profiles/{slug}/activate - Set as active profile
    GET /api/v1/profiles/active - Get currently active profile
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.services.database import (
    DatabaseService,
    Profile,
    ProfileCreate,
    ProfileUpdate,
    get_database_service,
)
from src.services.database.exceptions import ProfileNotFoundError, ProfileExistsError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profiles", tags=["profiles"])


# =============================================================================
# SCHEMAS
# =============================================================================


class ProfileCreateRequest(BaseModel):
    """Request to create a profile."""
    name: str = Field(..., min_length=1, max_length=200)
    full_name: str = Field(..., min_length=1, max_length=200)
    email: str | None = None
    title: str | None = None
    profile_data: dict[str, Any]
    set_active: bool = False


class ProfileUpdateRequest(BaseModel):
    """Request to update a profile."""
    name: str | None = None
    full_name: str | None = None
    email: str | None = None
    title: str | None = None
    profile_data: dict[str, Any] | None = None


class ProfileResponse(BaseModel):
    """Profile response with stats."""
    id: int
    name: str
    slug: str
    full_name: str
    email: str | None
    title: str | None
    is_active: bool
    is_indexed: bool
    is_demo: bool
    created_at: str
    updated_at: str
    stats: dict[str, Any] | None = None


class ProfileListResponse(BaseModel):
    """List of profiles."""
    profiles: list[ProfileResponse]
    total: int
    active_profile_slug: str | None


# =============================================================================
# DEPENDENCIES
# =============================================================================


async def get_db() -> DatabaseService:
    """Get database service."""
    return await get_database_service()


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("", response_model=ProfileListResponse)
async def list_profiles(
    include_demo: bool = True,
    db: DatabaseService = Depends(get_db),
) -> ProfileListResponse:
    """List all profiles."""
    profiles = await db.list_profiles(include_demo=include_demo)

    # Get active profile
    active = await db.get_active_profile()
    active_slug = active.slug if active else None

    # Build response with stats
    profile_responses = []
    for p in profiles:
        stats = await db.get_profile_stats(p.id)
        profile_responses.append(ProfileResponse(
            id=p.id,
            name=p.name,
            slug=p.slug,
            full_name=p.full_name,
            email=p.email,
            title=p.title,
            is_active=p.is_active,
            is_indexed=p.is_indexed,
            is_demo=p.is_demo,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
            stats=stats,
        ))

    return ProfileListResponse(
        profiles=profile_responses,
        total=len(profiles),
        active_profile_slug=active_slug,
    )


@router.post("", response_model=ProfileResponse)
async def create_profile(
    request: ProfileCreateRequest,
    db: DatabaseService = Depends(get_db),
) -> ProfileResponse:
    """Create a new profile."""
    try:
        profile = await db.create_profile(ProfileCreate(
            name=request.name,
            full_name=request.full_name,
            email=request.email,
            title=request.title,
            profile_data=request.profile_data,
            is_active=request.set_active,
            is_demo=False,
        ))

        # If set as active, re-index
        if request.set_active:
            await _reindex_profile(profile, db)

        stats = await db.get_profile_stats(profile.id)

        return ProfileResponse(
            id=profile.id,
            name=profile.name,
            slug=profile.slug,
            full_name=profile.full_name,
            email=profile.email,
            title=profile.title,
            is_active=profile.is_active,
            is_indexed=profile.is_indexed,
            is_demo=profile.is_demo,
            created_at=profile.created_at.isoformat(),
            updated_at=profile.updated_at.isoformat(),
            stats=stats,
        )

    except ProfileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/active", response_model=ProfileResponse | None)
async def get_active_profile(db: DatabaseService = Depends(get_db)):
    """Get the currently active profile."""
    profile = await db.get_active_profile()
    if profile is None:
        return None

    stats = await db.get_profile_stats(profile.id)

    return ProfileResponse(
        id=profile.id,
        name=profile.name,
        slug=profile.slug,
        full_name=profile.full_name,
        email=profile.email,
        title=profile.title,
        is_active=profile.is_active,
        is_indexed=profile.is_indexed,
        is_demo=profile.is_demo,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat(),
        stats=stats,
    )


@router.get("/{slug}", response_model=ProfileResponse)
async def get_profile(slug: str, db: DatabaseService = Depends(get_db)) -> ProfileResponse:
    """Get profile by slug."""
    try:
        profile = await db.get_profile_by_slug(slug)
        stats = await db.get_profile_stats(profile.id)

        return ProfileResponse(
            id=profile.id,
            name=profile.name,
            slug=profile.slug,
            full_name=profile.full_name,
            email=profile.email,
            title=profile.title,
            is_active=profile.is_active,
            is_indexed=profile.is_indexed,
            is_demo=profile.is_demo,
            created_at=profile.created_at.isoformat(),
            updated_at=profile.updated_at.isoformat(),
            stats=stats,
        )

    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found")


@router.get("/{slug}/data")
async def get_profile_data(slug: str, db: DatabaseService = Depends(get_db)) -> dict:
    """Get full profile data (for editing)."""
    try:
        profile = await db.get_profile_by_slug(slug)
        return profile.profile_data
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found")


@router.put("/{slug}", response_model=ProfileResponse)
async def update_profile(
    slug: str,
    request: ProfileUpdateRequest,
    db: DatabaseService = Depends(get_db),
) -> ProfileResponse:
    """Update a profile."""
    try:
        profile = await db.get_profile_by_slug(slug)

        updated = await db.update_profile(profile.id, ProfileUpdate(
            name=request.name,
            full_name=request.full_name,
            email=request.email,
            title=request.title,
            profile_data=request.profile_data,
        ))

        # If active profile was updated, re-index
        if updated.is_active and request.profile_data is not None:
            await _reindex_profile(updated, db)

        stats = await db.get_profile_stats(updated.id)

        return ProfileResponse(
            id=updated.id,
            name=updated.name,
            slug=updated.slug,
            full_name=updated.full_name,
            email=updated.email,
            title=updated.title,
            is_active=updated.is_active,
            is_indexed=updated.is_indexed,
            is_demo=updated.is_demo,
            created_at=updated.created_at.isoformat(),
            updated_at=updated.updated_at.isoformat(),
            stats=stats,
        )

    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found")


@router.delete("/{slug}")
async def delete_profile(slug: str, db: DatabaseService = Depends(get_db)) -> dict:
    """Delete a profile."""
    try:
        profile = await db.get_profile_by_slug(slug)

        if profile.is_active:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete active profile. Activate another profile first."
            )

        await db.delete_profile(profile.id)
        return {"status": "deleted", "slug": slug}

    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found")


@router.post("/{slug}/activate", response_model=ProfileResponse)
async def activate_profile(slug: str, db: DatabaseService = Depends(get_db)) -> ProfileResponse:
    """Set a profile as active and re-index for matching."""
    try:
        profile = await db.get_profile_by_slug(slug)

        # Activate in database
        activated = await db.activate_profile(profile.id)

        # Re-index in vector store
        await _reindex_profile(activated, db)

        stats = await db.get_profile_stats(activated.id)

        return ProfileResponse(
            id=activated.id,
            name=activated.name,
            slug=activated.slug,
            full_name=activated.full_name,
            email=activated.email,
            title=activated.title,
            is_active=activated.is_active,
            is_indexed=activated.is_indexed,
            is_demo=activated.is_demo,
            created_at=activated.created_at.isoformat(),
            updated_at=activated.updated_at.isoformat(),
            stats=stats,
        )

    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found")


async def _reindex_profile(profile: Profile, db: DatabaseService) -> None:
    """Re-index profile in vector store."""
    try:
        from src.modules.collector.models import UserProfile
        from src.modules.collector import get_collector

        collector = await get_collector()

        # Parse profile data to UserProfile
        user_profile = UserProfile(**profile.profile_data)

        # Set in collector (this clears and re-indexes)
        collector._profile = user_profile
        collector._profile_loaded = True

        # Clear and re-index
        await collector.clear_index()
        chunk_count = await collector.index_profile()

        # Mark as indexed in database
        await db.set_profile_indexed(profile.id, True)

        logger.info(f"Re-indexed profile {profile.slug}: {chunk_count} chunks")

    except Exception as e:
        logger.error(f"Failed to re-index profile {profile.slug}: {e}")
        await db.set_profile_indexed(profile.id, False)
        raise
