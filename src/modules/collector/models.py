"""
M1 Collector Data Models

Pydantic models for user profile management and semantic search.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

if TYPE_CHECKING:
    from src.services.database.models import Profile as DBProfile


def _parse_partial_date(v: str | datetime | None) -> datetime | None:
    """Parse date string, handling partial dates like '2022-02'."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return None
        # Try full ISO format first
        try:
            return datetime.fromisoformat(v)
        except ValueError:
            pass
        # Handle YYYY-MM format
        if len(v) == 7 and v[4] == "-":
            try:
                return datetime.fromisoformat(f"{v}-01")
            except ValueError:
                pass
        # Handle YYYY format
        if len(v) == 4 and v.isdigit():
            try:
                return datetime(int(v), 1, 1)
            except ValueError:
                pass
    return None


def _parse_gpa_string(gpa_str: str | None) -> float | None:
    """Parse GPA string to float."""
    if not gpa_str:
        return None
    try:
        return float(gpa_str)
    except ValueError:
        return None


def _calculate_years_experience(experiences: list) -> float:
    """Calculate total years of professional experience from experience list."""
    if not experiences:
        return 0.0

    total_months = 0
    now = datetime.now()

    for exp in experiences:
        start = exp.start_date if hasattr(exp, "start_date") else None
        end = exp.end_date if hasattr(exp, "end_date") else None

        if start is None:
            continue

        end_date = end or now

        months = (end_date.year - start.year) * 12 + (end_date.month - start.month)
        total_months += max(0, months)

    return round(total_months / 12, 1)


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

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_dates(cls, v: str | datetime | None) -> datetime | None:
        """Parse date string, handling partial dates like '2022-02'."""
        return _parse_partial_date(v)

    @model_validator(mode="after")
    def set_current_from_end_date(self) -> Experience:
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
        field: Field of study (optional).
        start_date: When education started.
        end_date: When education ended (None if ongoing).
        gpa: Grade point average (optional).
        relevant_courses: Courses relevant for job matching.
    """

    institution: str
    degree: str
    field: str = ""
    start_date: datetime
    end_date: datetime | None = None
    gpa: float | None = None
    relevant_courses: list[str] = Field(default_factory=list)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_dates(cls, v: str | datetime | None) -> datetime | None:
        """Parse date string, handling partial dates like '2022-02'."""
        return _parse_partial_date(v)

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

    @field_validator("date_obtained", "expiry_date", mode="before")
    @classmethod
    def parse_dates(cls, v: str | datetime | None) -> datetime | None:
        """Parse date string, handling partial dates like '2022-02'."""
        return _parse_partial_date(v)

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

    @model_validator(mode="before")
    @classmethod
    def transform_legacy_format(cls, data: dict) -> dict:
        """Transform legacy profile formats to the expected schema."""
        if not isinstance(data, dict):
            return data

        # Handle 'name' -> 'full_name' mapping
        if "name" in data and "full_name" not in data:
            data["full_name"] = data.pop("name")

        # Handle 'linkedin' -> 'linkedin_url' mapping
        if "linkedin" in data and "linkedin_url" not in data:
            data["linkedin_url"] = data.pop("linkedin")

        # Handle 'github' -> 'github_url' mapping
        if "github" in data and "github_url" not in data:
            data["github_url"] = data.pop("github")

        # Handle categorized skills format (dict -> list)
        if "skills" in data and isinstance(data["skills"], dict):
            flat_skills = []
            level_map = {
                "expert": SkillLevel.EXPERT,
                "proficient": SkillLevel.ADVANCED,
                "advanced": SkillLevel.ADVANCED,
                "intermediate": SkillLevel.INTERMEDIATE,
                "familiar": SkillLevel.BEGINNER,
                "beginner": SkillLevel.BEGINNER,
            }
            for category, skills_list in data["skills"].items():
                level = level_map.get(category.lower(), SkillLevel.INTERMEDIATE)
                if isinstance(skills_list, list):
                    for skill in skills_list:
                        if isinstance(skill, dict):
                            flat_skills.append({
                                "name": skill.get("name", ""),
                                "level": level.value,
                                "years": skill.get("years", 0),
                                "context": skill.get("context", ""),
                            })
                        elif isinstance(skill, str):
                            flat_skills.append({
                                "name": skill,
                                "level": level.value,
                            })
            data["skills"] = flat_skills

        return data

    @classmethod
    def from_db_profile(cls, db_profile: DBProfile) -> UserProfile:
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
                level=SkillLevel(s.level.value) if s.level else SkillLevel.INTERMEDIATE,
                years=float(s.years) if s.years else None,
                keywords=[s.category] if s.category else [],
            )
            for s in db_profile.skills
        ]

        # Convert experiences
        experiences = [
            Experience(
                id=str(exp.id),
                company=exp.company,
                role=exp.title,  # DB uses 'title', collector uses 'role'
                start_date=_parse_partial_date(exp.start_date) or datetime.now(),
                end_date=_parse_partial_date(exp.end_date),
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
                start_date=_parse_partial_date(edu.start_date) or datetime.now(),
                end_date=_parse_partial_date(edu.end_date),
                gpa=_parse_gpa_string(edu.gpa),
                relevant_courses=[],
            )
            for edu in db_profile.education
        ]

        # Convert certifications
        certifications = [
            Certification(
                name=cert.name,
                issuer=cert.issuer or "",
                date_obtained=_parse_partial_date(cert.date_obtained),
                expiry_date=_parse_partial_date(cert.expiry_date),
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
