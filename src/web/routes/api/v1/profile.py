"""
Profile API Routes

User profile management endpoints.

Endpoints:
    GET /api/v1/profile/status - Check profile status
    GET /api/v1/profile/retrieve - Get profile data
    POST /api/v1/profile/create - Create/update profile (text-based)
    POST /api/v1/profile/index - Re-index profile
    GET /api/v1/profile/assessment - Get completeness assessment
    GET /api/v1/profile/summary - Get quick summary with score
    GET /api/v1/profile/editor-data - Get data for form editor
    POST /api/v1/profile/editor-save - Save from form editor
    POST /api/v1/profile/assess - Assess without saving
    POST /api/v1/profile/export-yaml - Export as YAML download
"""

import logging
from datetime import datetime
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import ValidationError

from src.modules.collector import (
    Collector,
    ProfileAssessment,
    assess_profile,
    get_collector,
)
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
from src.web.routes.api.schemas import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["profile"])

DEFAULT_PROFILE_PATH = Path("data/profile.yaml")


# Dependencies
async def get_profile_svc() -> ProfileService:
    """Get profile service."""
    return await get_profile_service()


async def get_collector_dep() -> Collector:
    """Get collector module."""
    return await get_collector()


# =============================================================================
# TEXT-BASED PROFILE (ProfileService)
# =============================================================================


@router.get("/status", response_model=ProfileStatus)
async def get_status(service: ProfileService = Depends(get_profile_svc)) -> ProfileStatus:
    """Check if profile exists and is indexed."""
    return await service.get_status()


@router.get("/retrieve", response_model=ProfileData)
async def get_profile(service: ProfileService = Depends(get_profile_svc)) -> ProfileData:
    """Get current profile data (text-based)."""
    try:
        return await service.get_profile()
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail="No profile found")


@router.post("/create", response_model=ProfileCreateResponse)
async def create_profile(
    request: ProfileCreateRequest,
    service: ProfileService = Depends(get_profile_svc),
) -> ProfileCreateResponse:
    """Create or update profile from text."""
    try:
        return await service.create_profile(request.profile_text)
    except ProfileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/index", response_model=ProfileIndexResponse)
async def index_profile(
    request: ProfileIndexRequest,
    service: ProfileService = Depends(get_profile_svc),
) -> ProfileIndexResponse:
    """Re-index profile for semantic search."""
    try:
        return await service.index_profile(request.profile_id)
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail="Profile not found")


# =============================================================================
# YAML-BASED PROFILE (Collector)
# =============================================================================


@router.get("/assessment", response_model=ProfileAssessment)
async def get_assessment(collector: Collector = Depends(get_collector_dep)) -> ProfileAssessment:
    """Get profile completeness assessment with scores and suggestions."""
    try:
        try:
            collector.get_profile()
        except Exception:
            await collector.load_profile()
        return collector.assess_profile_completeness()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_summary(collector: Collector = Depends(get_collector_dep)) -> dict:
    """Get quick profile summary with score."""
    try:
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
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# FORM EDITOR ENDPOINTS
# =============================================================================


@router.get("/editor-data")
async def get_editor_data(collector: Collector = Depends(get_collector_dep)) -> dict:
    """Get profile data for form editor."""
    try:
        try:
            profile = collector.get_profile()
        except Exception:
            await collector.load_profile()
            profile = collector.get_profile()
        return profile.model_dump(mode="json")
    except Exception:
        raise HTTPException(status_code=404, detail="No profile found")


@router.post("/editor-save")
async def save_editor_data(
    profile_data: dict,
    collector: Collector = Depends(get_collector_dep),
) -> dict:
    """Save profile from form editor."""
    try:
        profile = _parse_profile_data(profile_data)
        DEFAULT_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(DEFAULT_PROFILE_PATH, "w") as f:
            yaml.dump(
                profile.model_dump(mode="json"),
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        await collector.load_profile(DEFAULT_PROFILE_PATH)
        await collector.clear_index()
        chunk_count = await collector.index_profile()

        return {"status": "saved", "message": "Profile saved successfully", "chunk_count": chunk_count}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assess", response_model=ProfileAssessment)
async def assess_profile_data(profile_data: dict) -> ProfileAssessment:
    """Assess profile without saving."""
    try:
        profile = _parse_profile_data(profile_data)
        return assess_profile(profile)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/export-yaml")
async def export_yaml(profile_data: dict) -> Response:
    """Export profile as YAML file."""
    try:
        profile = _parse_profile_data(profile_data)
        yaml_content = yaml.dump(
            profile.model_dump(mode="json"),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        return Response(
            content=yaml_content,
            media_type="application/x-yaml",
            headers={"Content-Disposition": "attachment; filename=profile.yaml"},
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _parse_profile_data(data: dict) -> UserProfile:
    """Parse profile data from editor form."""
    skills = []
    for s in data.get("skills", []):
        if s.get("name"):
            try:
                level = SkillLevel(s.get("level", "intermediate"))
            except ValueError:
                level = SkillLevel.INTERMEDIATE
            skills.append(Skill(
                name=s["name"], level=level, years=s.get("years"), keywords=s.get("keywords", [])
            ))

    experiences = []
    for e in data.get("experiences", []):
        if e.get("company") and e.get("role"):
            experiences.append(Experience(
                company=e["company"],
                role=e["role"],
                start_date=_parse_date(e.get("start_date")),
                end_date=_parse_date(e.get("end_date")),
                current=e.get("current", False),
                description=e.get("description", ""),
                achievements=e.get("achievements", []),
                technologies=e.get("technologies", []),
            ))

    education = []
    for ed in data.get("education", []):
        if ed.get("institution"):
            education.append(Education(
                institution=ed["institution"],
                degree=ed.get("degree", ""),
                field=ed.get("field", ""),
                start_date=_parse_date(ed.get("start_date")),
                end_date=_parse_date(ed.get("end_date")),
                gpa=ed.get("gpa"),
                relevant_courses=ed.get("relevant_courses", []),
            ))

    certifications = []
    for c in data.get("certifications", []):
        if c.get("name"):
            certifications.append(Certification(
                name=c["name"],
                issuer=c.get("issuer", ""),
                date_obtained=_parse_date(c.get("date_obtained")),
                expiry_date=_parse_date(c.get("expiry_date")),
                credential_id=c.get("credential_id"),
            ))

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
    """Parse date string."""
    if not date_str:
        return None
    try:
        if "T" in date_str:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m")
        except ValueError:
            return None
