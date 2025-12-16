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
    GET /api/profile/editor-data - Get profile data for form editor
    POST /api/profile/editor-save - Save profile from form editor
    POST /api/profile/assess - Assess profile completeness without saving
    POST /api/profile/export-yaml - Export profile as YAML file download
"""

import logging
from datetime import datetime
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import ValidationError

from src.modules.collector import ProfileAssessment, get_collector
from src.modules.collector.assessment import assess_profile
from src.modules.collector.collector import Collector
from src.modules.collector.models import (
    Certification,
    Education,
    Experience,
    Skill,
    SkillLevel,
    UserProfile,
)
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


# =============================================================================
# PROFILE EDITOR ENDPOINTS
# =============================================================================

# Default profile path
DEFAULT_PROFILE_PATH = Path("data/profile.yaml")


@router.get(
    "/editor-data",
    responses={
        404: {"model": ErrorResponse, "description": "Profile not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Get profile data for editor",
    description="Get profile data in JSON format for the form-based editor.",
)
async def get_editor_data(
    collector: Collector = Depends(get_collector_dep),
) -> dict:
    """
    Get profile data for the form editor.

    Returns profile data as a JSON object that can populate the editor form.
    """
    try:
        # Try to get loaded profile
        try:
            profile = collector.get_profile()
        except Exception:
            # Try to load default profile
            await collector.load_profile()
            profile = collector.get_profile()

        # Convert to dict with JSON-safe serialization
        return profile.model_dump(mode="json")

    except Exception as e:
        logger.info(f"No profile found for editor: {e}")
        raise HTTPException(status_code=404, detail="No profile found")


@router.post(
    "/editor-save",
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Save profile from editor",
    description="Save profile data from the form-based editor.",
)
async def save_editor_data(
    profile_data: dict,
    collector: Collector = Depends(get_collector_dep),
) -> dict:
    """
    Save profile from the form editor.

    Validates the profile data, saves to YAML file, and re-indexes.
    """
    try:
        # Parse and validate profile data
        profile = _parse_profile_data(profile_data)

        # Ensure data directory exists
        DEFAULT_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Save to YAML file
        profile_dict = profile.model_dump(mode="json")
        with open(DEFAULT_PROFILE_PATH, "w") as f:
            yaml.dump(
                profile_dict,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        # Reload in collector and re-index
        await collector.load_profile(DEFAULT_PROFILE_PATH)
        await collector.clear_index()
        chunk_count = await collector.index_profile()

        logger.info(f"Profile saved and indexed: {chunk_count} chunks")

        return {
            "status": "saved",
            "message": "Profile saved successfully",
            "chunk_count": chunk_count,
        }

    except ValidationError as e:
        logger.warning(f"Profile validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error saving profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/assess",
    response_model=ProfileAssessment,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Assessment failed"},
    },
    summary="Assess profile completeness",
    description="Assess profile completeness without saving.",
)
async def assess_profile_data(profile_data: dict) -> ProfileAssessment:
    """
    Assess profile completeness without saving.

    Takes profile data as JSON and returns assessment with scores and suggestions.
    """
    try:
        # Parse and validate profile data
        profile = _parse_profile_data(profile_data)

        # Run assessment
        return assess_profile(profile)

    except ValidationError as e:
        logger.warning(f"Profile validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Assessment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/export-yaml",
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Export failed"},
    },
    summary="Export profile as YAML",
    description="Export profile data as a downloadable YAML file.",
)
async def export_profile_yaml(profile_data: dict) -> Response:
    """
    Export profile as YAML file download.

    Takes profile data as JSON and returns a YAML file.
    """
    try:
        # Parse and validate profile data
        profile = _parse_profile_data(profile_data)

        # Convert to YAML
        yaml_content = yaml.dump(
            profile.model_dump(mode="json"),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        return Response(
            content=yaml_content,
            media_type="application/x-yaml",
            headers={
                "Content-Disposition": "attachment; filename=profile.yaml"
            },
        )

    except ValidationError as e:
        logger.warning(f"Profile validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _parse_profile_data(data: dict) -> UserProfile:
    """
    Parse profile data from editor form format to UserProfile.

    Handles conversion of nested objects and date parsing.
    """
    # Parse skills
    skills = []
    for skill_data in data.get("skills", []):
        if skill_data.get("name"):
            level_str = skill_data.get("level", "intermediate")
            try:
                level = SkillLevel(level_str)
            except ValueError:
                level = SkillLevel.INTERMEDIATE

            skills.append(Skill(
                name=skill_data["name"],
                level=level,
                years=skill_data.get("years"),
                keywords=skill_data.get("keywords", []),
            ))

    # Parse experiences
    experiences = []
    for exp_data in data.get("experiences", []):
        if exp_data.get("company") and exp_data.get("role"):
            experiences.append(Experience(
                company=exp_data["company"],
                role=exp_data["role"],
                start_date=_parse_date(exp_data.get("start_date")),
                end_date=_parse_date(exp_data.get("end_date")),
                current=exp_data.get("current", False),
                description=exp_data.get("description", ""),
                achievements=exp_data.get("achievements", []),
                technologies=exp_data.get("technologies", []),
            ))

    # Parse education
    education = []
    for edu_data in data.get("education", []):
        if edu_data.get("institution"):
            education.append(Education(
                institution=edu_data["institution"],
                degree=edu_data.get("degree", ""),
                field=edu_data.get("field", ""),
                start_date=_parse_date(edu_data.get("start_date")),
                end_date=_parse_date(edu_data.get("end_date")),
                gpa=edu_data.get("gpa"),
                relevant_courses=edu_data.get("relevant_courses", []),
            ))

    # Parse certifications
    certifications = []
    for cert_data in data.get("certifications", []):
        if cert_data.get("name"):
            certifications.append(Certification(
                name=cert_data["name"],
                issuer=cert_data.get("issuer", ""),
                date_obtained=_parse_date(cert_data.get("date_obtained")),
                expiry_date=_parse_date(cert_data.get("expiry_date")),
                credential_id=cert_data.get("credential_id"),
            ))

    # Create profile
    return UserProfile(
        full_name=data.get("full_name", ""),
        email=data.get("email", ""),
        phone=data.get("phone"),
        location=data.get("location", ""),
        linkedin_url=data.get("linkedin_url"),
        github_url=data.get("github_url"),
        title=data.get("title", ""),
        years_experience=data.get("years_experience", 0.0),
        summary=data.get("summary", ""),
        skills=skills,
        experiences=experiences,
        education=education,
        certifications=certifications,
        last_updated=datetime.now(),
    )


def _parse_date(date_str: str | None) -> datetime | None:
    """Parse date string to datetime, handling various formats."""
    if not date_str:
        return None

    try:
        # Try ISO format first (YYYY-MM-DD)
        if "T" in date_str:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        # Try date-only format
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            # Try year-month format
            return datetime.strptime(date_str, "%Y-%m")
        except ValueError:
            return None
