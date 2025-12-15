"""
Profile API Routes

REST API endpoints for user profile management.

Endpoints:
    GET /api/profile/status - Check if profile exists and is indexed
    POST /api/profile/create - Create or update profile
    POST /api/profile/index - Chunk and embed profile
    GET /api/profile/retrieve - Get current profile data
    GET /api/profile/assessment - Get profile completeness assessment
    GET /api/profile/completeness-summary - Get quick profile summary with score
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from src.modules.collector import ProfileAssessment, get_collector
from src.modules.collector.collector import Collector
from src.services.profile import (
    ProfileCreateRequest,
    ProfileCreateResponse,
    ProfileData,
    ProfileIndexRequest,
    ProfileIndexResponse,
    ProfileNotFoundError,
    ProfileService,
    ProfileStatus,
    ProfileValidationError,
    get_profile_service,
)
from src.web.schemas import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])


# =============================================================================
# DEPENDENCIES
# =============================================================================


async def get_profile_svc() -> ProfileService:
    """Get profile service dependency."""
    return await get_profile_service()


async def get_collector_dep() -> Collector:
    """Get collector module dependency."""
    return await get_collector()


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get(
    "/status",
    response_model=ProfileStatus,
    summary="Get profile status",
    description="Check if a profile exists and is indexed.",
)
async def get_status(
    service: ProfileService = Depends(get_profile_svc),
) -> ProfileStatus:
    """
    Check profile status.

    Returns whether a profile exists, if it's indexed,
    and basic statistics.
    """
    try:
        return await service.get_status()
    except Exception as e:
        logger.error(f"Error getting profile status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get profile status: {e}",
        )


@router.post(
    "/create",
    response_model=ProfileCreateResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Create or update profile",
    description="Create a new profile or update existing one. Profile is automatically indexed.",
)
async def create_profile(
    request: ProfileCreateRequest,
    service: ProfileService = Depends(get_profile_svc),
) -> ProfileCreateResponse:
    """
    Create or update a user profile.

    Profile text must be 100-10,000 characters.
    The profile is automatically indexed for semantic search.

    Args:
        request: Profile creation request with profile_text.
        service: Profile service.

    Returns:
        ProfileCreateResponse with profile ID and indexing status.

    Raises:
        HTTPException: 400 for validation errors, 500 for server errors.
    """
    try:
        result = await service.create_profile(request.profile_text)
        logger.info(
            f"Profile {result.status}: id={result.profile_id}, "
            f"chunks={result.chunk_count}"
        )
        return result

    except ProfileValidationError as e:
        logger.warning(f"Profile validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Error creating profile: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create profile: {e}",
        )


@router.post(
    "/index",
    response_model=ProfileIndexResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Profile not found"},
        500: {"model": ErrorResponse, "description": "Indexing error"},
    },
    summary="Index profile",
    description="Chunk and embed profile text for semantic search.",
)
async def index_profile(
    request: ProfileIndexRequest,
    service: ProfileService = Depends(get_profile_svc),
) -> ProfileIndexResponse:
    """
    Index a profile for semantic search.

    Chunks the profile text and stores embeddings in vector store.
    If already indexed, old embeddings are cleared first.

    Args:
        request: Index request with profile_id.
        service: Profile service.

    Returns:
        ProfileIndexResponse with success status and chunk count.

    Raises:
        HTTPException: 404 if profile not found, 500 for indexing errors.
    """
    try:
        result = await service.index_profile(request.profile_id)
        logger.info(
            f"Profile indexed: id={result.profile_id}, "
            f"chunks={result.chunks_created}"
        )
        return result

    except ProfileNotFoundError as e:
        logger.warning(f"Profile not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.error(f"Error indexing profile: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to index profile: {e}",
        )


@router.get(
    "/retrieve",
    response_model=ProfileData,
    responses={
        404: {"model": ErrorResponse, "description": "Profile not found"},
    },
    summary="Get profile data",
    description="Retrieve current profile text and metadata.",
)
async def get_profile(
    service: ProfileService = Depends(get_profile_svc),
) -> ProfileData:
    """
    Get current profile data.

    Returns the full profile text and metadata.

    Args:
        service: Profile service.

    Returns:
        ProfileData with full profile information.

    Raises:
        HTTPException: 404 if no profile exists.
    """
    try:
        return await service.get_profile()

    except ProfileNotFoundError as e:
        logger.info(f"Profile not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.error(f"Error retrieving profile: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve profile: {e}",
        )


# =============================================================================
# PROFILE ASSESSMENT ENDPOINTS (using Collector module)
# =============================================================================


@router.get(
    "/assessment",
    response_model=ProfileAssessment,
    responses={
        500: {"model": ErrorResponse, "description": "Assessment failed"},
    },
    summary="Get profile assessment",
    description="Get assessment of current profile completeness with scores and suggestions.",
)
async def get_profile_assessment(
    collector: Collector = Depends(get_collector_dep),
) -> ProfileAssessment:
    """
    Get assessment of current profile completeness.

    Returns:
        ProfileAssessment with overall score, section scores, and suggestions.
    """
    try:
        # Ensure profile is loaded
        try:
            collector.get_profile()
        except Exception:
            # Try to load default profile
            await collector.load_profile()

        assessment = collector.assess_profile_completeness()
        return assessment

    except Exception as e:
        logger.error(f"Assessment failed: {e}")
        raise HTTPException(status_code=500, detail=f"Assessment failed: {e}")


@router.get(
    "/completeness-summary",
    responses={
        500: {"model": ErrorResponse, "description": "Summary failed"},
    },
    summary="Get profile completeness summary",
    description="Get quick profile summary with assessment score.",
)
async def get_profile_completeness_summary(
    collector: Collector = Depends(get_collector_dep),
) -> dict:
    """
    Get quick profile summary with assessment score.

    Returns a simplified view with name, title, score, and top suggestion.
    """
    try:
        # Ensure profile is loaded
        try:
            profile = collector.get_profile()
        except Exception:
            await collector.load_profile()
            profile = collector.get_profile()

        assessment = collector.assess_profile_completeness()

        return {
            "name": profile.full_name,
            "title": profile.title,
            "completeness_score": assessment.overall_score,
            "grade": assessment.grade.value,
            "is_job_ready": assessment.is_job_ready,
            "top_suggestion": assessment.top_suggestions[0] if assessment.top_suggestions else None,
        }

    except Exception as e:
        logger.error(f"Summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
