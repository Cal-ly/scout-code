"""
Profile completeness assessment and scoring.

Evaluates user profiles and provides actionable improvement suggestions.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from src.modules.collector.models import UserProfile


class SectionScore(BaseModel):
    """Score for a single profile section."""

    section: str
    score: int = Field(ge=0, le=100, description="Section score 0-100")
    max_score: int = Field(ge=0, le=100, description="Maximum possible score")
    weight: float = Field(ge=0, le=1, description="Weight in overall score")
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ProfileGrade(str, Enum):
    """Overall profile grade."""

    EXCELLENT = "excellent"  # 90-100
    GOOD = "good"  # 75-89
    FAIR = "fair"  # 60-74
    NEEDS_WORK = "needs_work"  # 40-59
    INCOMPLETE = "incomplete"  # 0-39


class ProfileAssessment(BaseModel):
    """Complete profile assessment result."""

    overall_score: int = Field(ge=0, le=100, description="Overall completeness score")
    grade: ProfileGrade
    section_scores: list[SectionScore] = Field(default_factory=list)
    top_suggestions: list[str] = Field(default_factory=list, max_length=5)
    strengths: list[str] = Field(default_factory=list, max_length=3)

    @property
    def is_job_ready(self) -> bool:
        """Profile is ready for job matching (score >= 60)."""
        return self.overall_score >= 60


# Section weights (must sum to 1.0)
SECTION_WEIGHTS = {
    "basic_info": 0.10,
    "summary": 0.15,
    "skills": 0.25,
    "experience": 0.30,
    "education": 0.10,
    "certifications": 0.10,
}


def assess_basic_info(profile: UserProfile) -> SectionScore:
    """Assess basic contact information completeness."""
    score = 0
    max_score = 100
    issues: list[str] = []
    suggestions: list[str] = []

    # Required fields (60 points)
    if profile.full_name and len(profile.full_name) >= 2:
        score += 20
    else:
        issues.append("Missing or invalid full name")
        suggestions.append("Add your full professional name")

    if profile.email and "@" in profile.email:
        score += 20
    else:
        issues.append("Missing or invalid email")
        suggestions.append("Add a professional email address")

    if profile.location and len(profile.location) >= 2:
        score += 20
    else:
        issues.append("Missing location")
        suggestions.append("Add your city/region for location-based matching")

    # Optional but valuable (40 points)
    if profile.phone:
        score += 10
    else:
        suggestions.append("Consider adding a phone number")

    if profile.linkedin_url:
        score += 15
    else:
        suggestions.append("Add your LinkedIn profile URL")

    if profile.github_url:
        score += 15
    else:
        suggestions.append("Add your GitHub profile URL (valuable for tech roles)")

    return SectionScore(
        section="basic_info",
        score=score,
        max_score=max_score,
        weight=SECTION_WEIGHTS["basic_info"],
        issues=issues,
        suggestions=suggestions,
    )


def assess_summary(profile: UserProfile) -> SectionScore:
    """Assess professional summary quality."""
    score = 0
    max_score = 100
    issues: list[str] = []
    suggestions: list[str] = []

    summary = profile.summary or ""
    word_count = len(summary.split())

    # Length scoring
    if word_count >= 50:
        score += 40
    elif word_count >= 30:
        score += 25
        suggestions.append("Expand your summary to 50+ words for better matching")
    elif word_count >= 10:
        score += 10
        suggestions.append("Your summary is too short. Aim for 50-100 words")
    else:
        issues.append("Summary is missing or too short")
        suggestions.append("Add a professional summary (50-100 words)")

    # Title present
    if profile.title and len(profile.title) >= 3:
        score += 20
    else:
        issues.append("Professional title is missing")
        suggestions.append("Add a professional title (e.g., 'Senior Software Engineer')")

    # Years experience specified
    if profile.years_experience and profile.years_experience > 0:
        score += 20
    else:
        suggestions.append("Specify your total years of experience")

    # Quality indicators (keywords that suggest good content)
    quality_keywords = [
        "experience",
        "expertise",
        "skills",
        "developed",
        "led",
        "built",
        "managed",
    ]
    keyword_matches = sum(1 for kw in quality_keywords if kw.lower() in summary.lower())
    if keyword_matches >= 3:
        score += 20
    elif keyword_matches >= 1:
        score += 10
    else:
        suggestions.append("Include action words and achievements in your summary")

    return SectionScore(
        section="summary",
        score=min(score, max_score),
        max_score=max_score,
        weight=SECTION_WEIGHTS["summary"],
        issues=issues,
        suggestions=suggestions,
    )


def assess_skills(profile: UserProfile) -> SectionScore:
    """Assess skills section completeness and quality."""
    score = 0
    max_score = 100
    issues: list[str] = []
    suggestions: list[str] = []

    skills = profile.skills or []
    skill_count = len(skills)

    # Quantity scoring (40 points)
    if skill_count >= 10:
        score += 40
    elif skill_count >= 7:
        score += 30
    elif skill_count >= 5:
        score += 20
        suggestions.append(f"Add more skills (you have {skill_count}, aim for 10-15)")
    elif skill_count >= 3:
        score += 10
        suggestions.append("Your skills list is short. Add more relevant skills")
    else:
        issues.append("Too few skills listed")
        suggestions.append("Add at least 5-10 relevant technical skills")

    if skill_count == 0:
        return SectionScore(
            section="skills",
            score=score,
            max_score=max_score,
            weight=SECTION_WEIGHTS["skills"],
            issues=issues,
            suggestions=suggestions,
        )

    # Level diversity (20 points) - mix of expert/advanced/intermediate
    levels = [s.level.value for s in skills]
    unique_levels = set(levels)
    if len(unique_levels) >= 3:
        score += 20
    elif len(unique_levels) >= 2:
        score += 10
        suggestions.append("Include skills at different proficiency levels")
    else:
        suggestions.append("Differentiate skill levels (expert, advanced, intermediate)")

    # Years specified (20 points)
    skills_with_years = sum(1 for s in skills if s.years and s.years > 0)
    years_ratio = skills_with_years / skill_count
    if years_ratio >= 0.8:
        score += 20
    elif years_ratio >= 0.5:
        score += 10
        suggestions.append("Add years of experience to more skills")
    else:
        suggestions.append("Specify years of experience for each skill")

    # Keywords present (20 points)
    skills_with_keywords = sum(1 for s in skills if s.keywords and len(s.keywords) >= 1)
    keywords_ratio = skills_with_keywords / skill_count
    if keywords_ratio >= 0.5:
        score += 20
    elif keywords_ratio >= 0.25:
        score += 10
        suggestions.append("Add related keywords to more skills for better matching")
    else:
        suggestions.append("Add keywords/aliases to skills (e.g., 'k8s' for Kubernetes)")

    return SectionScore(
        section="skills",
        score=min(score, max_score),
        max_score=max_score,
        weight=SECTION_WEIGHTS["skills"],
        issues=issues,
        suggestions=suggestions,
    )


def assess_experience(profile: UserProfile) -> SectionScore:
    """Assess work experience section completeness."""
    score = 0
    max_score = 100
    issues: list[str] = []
    suggestions: list[str] = []

    experiences = profile.experiences or []
    exp_count = len(experiences)

    # Quantity (30 points)
    if exp_count >= 3:
        score += 30
    elif exp_count >= 2:
        score += 20
    elif exp_count >= 1:
        score += 10
        suggestions.append("Add more work experience entries if available")
    else:
        issues.append("No work experience listed")
        suggestions.append("Add your work experience history")

    if exp_count == 0:
        return SectionScore(
            section="experience",
            score=score,
            max_score=max_score,
            weight=SECTION_WEIGHTS["experience"],
            issues=issues,
            suggestions=suggestions,
        )

    # Current role indicator (10 points)
    has_current = any(exp.current for exp in experiences)
    if has_current:
        score += 10
    else:
        suggestions.append("Mark your current position as 'current: true'")

    # Description quality (25 points)
    descriptions_quality: list[float] = []
    for exp in experiences:
        desc_words = len((exp.description or "").split())
        if desc_words >= 30:
            descriptions_quality.append(1.0)
        elif desc_words >= 15:
            descriptions_quality.append(0.5)
        else:
            descriptions_quality.append(0.0)

    avg_desc_quality = (
        sum(descriptions_quality) / len(descriptions_quality) if descriptions_quality else 0
    )
    score += int(avg_desc_quality * 25)
    if avg_desc_quality < 0.7:
        suggestions.append("Expand job descriptions (aim for 30+ words each)")

    # Achievements present (20 points)
    exps_with_achievements = sum(
        1 for exp in experiences if exp.achievements and len(exp.achievements) >= 2
    )
    achievement_ratio = exps_with_achievements / exp_count
    score += int(achievement_ratio * 20)
    if achievement_ratio < 0.5:
        suggestions.append("Add 2-4 achievements per role (quantify where possible)")

    # Technologies listed (15 points)
    exps_with_tech = sum(
        1 for exp in experiences if exp.technologies and len(exp.technologies) >= 3
    )
    tech_ratio = exps_with_tech / exp_count
    score += int(tech_ratio * 15)
    if tech_ratio < 0.7:
        suggestions.append("List technologies used in each role for better skill matching")

    return SectionScore(
        section="experience",
        score=min(score, max_score),
        max_score=max_score,
        weight=SECTION_WEIGHTS["experience"],
        issues=issues,
        suggestions=suggestions,
    )


def assess_education(profile: UserProfile) -> SectionScore:
    """Assess education section completeness."""
    score = 0
    max_score = 100
    issues: list[str] = []
    suggestions: list[str] = []

    education = profile.education or []
    edu_count = len(education)

    # Has education entry (50 points)
    if edu_count >= 1:
        score += 50
    else:
        issues.append("No education listed")
        suggestions.append("Add your educational background")
        return SectionScore(
            section="education",
            score=score,
            max_score=max_score,
            weight=SECTION_WEIGHTS["education"],
            issues=issues,
            suggestions=suggestions,
        )

    # Multiple entries bonus (10 points)
    if edu_count >= 2:
        score += 10

    # Fields properly filled (40 points)
    complete_entries = 0
    for edu in education:
        entry_complete = all(
            [
                edu.institution,
                edu.degree,
                edu.field,
                edu.start_date,
            ]
        )
        if entry_complete:
            complete_entries += 1

    completeness_ratio = complete_entries / edu_count
    score += int(completeness_ratio * 30)
    if completeness_ratio < 1.0:
        suggestions.append("Complete all fields for education entries")

    # Relevant courses (10 points bonus)
    has_courses = any(
        edu.relevant_courses and len(edu.relevant_courses) >= 2 for edu in education
    )
    if has_courses:
        score += 10
    else:
        suggestions.append("Add relevant courses to strengthen technical background")

    return SectionScore(
        section="education",
        score=min(score, max_score),
        max_score=max_score,
        weight=SECTION_WEIGHTS["education"],
        issues=issues,
        suggestions=suggestions,
    )


def assess_certifications(profile: UserProfile) -> SectionScore:
    """Assess certifications section."""
    score = 0
    max_score = 100
    issues: list[str] = []
    suggestions: list[str] = []

    certs = profile.certifications or []
    cert_count = len(certs)

    # Having certifications is optional but valuable
    if cert_count >= 3:
        score += 100
    elif cert_count >= 2:
        score += 80
    elif cert_count >= 1:
        score += 60
    else:
        score += 40  # No certs is okay, not a penalty
        suggestions.append("Consider adding relevant certifications (AWS, K8s, etc.)")

    # Check for expired certs
    now = datetime.now()
    expired = [c for c in certs if c.expiry_date and c.expiry_date < now]
    if expired:
        score -= 10
        issues.append(f"{len(expired)} certification(s) have expired")
        suggestions.append("Update or remove expired certifications")

    return SectionScore(
        section="certifications",
        score=max(0, min(score, max_score)),
        max_score=max_score,
        weight=SECTION_WEIGHTS["certifications"],
        issues=issues,
        suggestions=suggestions,
    )


def calculate_grade(score: int) -> ProfileGrade:
    """Convert numeric score to letter grade."""
    if score >= 90:
        return ProfileGrade.EXCELLENT
    elif score >= 75:
        return ProfileGrade.GOOD
    elif score >= 60:
        return ProfileGrade.FAIR
    elif score >= 40:
        return ProfileGrade.NEEDS_WORK
    else:
        return ProfileGrade.INCOMPLETE


def assess_profile(profile: UserProfile) -> ProfileAssessment:
    """
    Perform complete profile assessment.

    Args:
        profile: UserProfile to assess

    Returns:
        ProfileAssessment with scores and suggestions
    """
    # Assess each section
    section_scores = [
        assess_basic_info(profile),
        assess_summary(profile),
        assess_skills(profile),
        assess_experience(profile),
        assess_education(profile),
        assess_certifications(profile),
    ]

    # Calculate weighted overall score
    overall_score = sum(section.score * section.weight for section in section_scores)
    overall_score = int(round(overall_score))

    # Collect top suggestions (prioritize from lower-scoring sections)
    all_suggestions: list[str] = []
    for section in sorted(section_scores, key=lambda s: s.score):
        for suggestion in section.suggestions:
            if suggestion not in all_suggestions:
                all_suggestions.append(suggestion)

    top_suggestions = all_suggestions[:5]

    # Identify strengths (sections scoring >= 80)
    strengths: list[str] = []
    strength_labels = {
        "basic_info": "Complete contact information",
        "summary": "Strong professional summary",
        "skills": "Comprehensive skills list",
        "experience": "Well-documented experience",
        "education": "Solid educational background",
        "certifications": "Valuable certifications",
    }
    for section in section_scores:
        if section.score >= 80:
            strengths.append(strength_labels.get(section.section, section.section))

    return ProfileAssessment(
        overall_score=overall_score,
        grade=calculate_grade(overall_score),
        section_scores=section_scores,
        top_suggestions=top_suggestions,
        strengths=strengths[:3],
    )
