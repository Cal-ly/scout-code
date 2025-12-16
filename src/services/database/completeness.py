"""Profile completeness scoring algorithm.

This module calculates profile completeness scores to help users understand
how complete their profile is and what they can do to improve it.

Scoring weights (total = 100 points):
- Basic Info (name, title, email, location): 15 points
- Summary: 10 points
- Skills: 25 points (min 5 recommended, max credit at 10+)
- Experience: 25 points (min 2 recommended, max credit at 4+)
- Education: 10 points (min 1 recommended)
- Certifications: 10 points (bonus, 0 required but adds value)
- Languages: 5 points (bonus)

Levels:
- 90-100: "excellent" - Ready for any application
- 70-89: "good" - Solid profile, minor improvements possible
- 50-69: "fair" - Functional but could be stronger
- 0-49: "needs_work" - Missing critical information
"""

from .models import CompletenessSection, Profile, ProfileCompleteness


def calculate_completeness(profile: Profile) -> ProfileCompleteness:
    """Calculate profile completeness with actionable suggestions.

    Args:
        profile: Full Profile with all related data loaded.

    Returns:
        ProfileCompleteness with section scores and suggestions.
    """
    sections: list[CompletenessSection] = []
    suggestions: list[str] = []

    # Basic Info (15 points)
    basic_info = _score_basic_info(profile)
    sections.append(basic_info)
    suggestions.extend(basic_info.suggestions)

    # Summary (10 points)
    summary = _score_summary(profile)
    sections.append(summary)
    suggestions.extend(summary.suggestions)

    # Skills (25 points)
    skills = _score_skills(profile)
    sections.append(skills)
    suggestions.extend(skills.suggestions)

    # Experience (25 points)
    experience = _score_experience(profile)
    sections.append(experience)
    suggestions.extend(experience.suggestions)

    # Education (10 points)
    education = _score_education(profile)
    sections.append(education)
    suggestions.extend(education.suggestions)

    # Certifications (10 points bonus)
    certifications = _score_certifications(profile)
    sections.append(certifications)
    suggestions.extend(certifications.suggestions)

    # Languages (5 points bonus)
    languages = _score_languages(profile)
    sections.append(languages)
    suggestions.extend(languages.suggestions)

    # Calculate overall percentage
    total_score = sum(s.score for s in sections)
    max_score = sum(s.max_score for s in sections)
    overall_score = int((total_score / max_score) * 100) if max_score > 0 else 0

    level = _get_level(overall_score)
    top_suggestions = suggestions[:3]  # Top 3 most impactful

    return ProfileCompleteness(
        overall_score=overall_score,
        level=level,
        sections=sections,
        top_suggestions=top_suggestions,
    )


def _score_basic_info(profile: Profile) -> CompletenessSection:
    """Score basic info fields (15 points max).

    Fields scored:
    - name: 5 points (required)
    - title: 4 points
    - email: 3 points
    - location: 3 points
    """
    max_score = 15
    fields = [
        (profile.name, 5, "Add your full name"),
        (profile.title, 4, "Add a professional title"),
        (profile.email, 3, "Add contact email"),
        (profile.location, 3, "Add your location"),
    ]

    score = sum(points for value, points, _ in fields if value)
    present = sum(1 for value, _, _ in fields if value)
    field_suggestions = [msg for value, _, msg in fields if not value]

    return CompletenessSection(
        name="Basic Info",
        score=score,
        max_score=max_score,
        items_present=present,
        items_recommended=4,
        suggestions=field_suggestions[:2],  # Max 2 suggestions
    )


def _score_summary(profile: Profile) -> CompletenessSection:
    """Score professional summary (10 points max).

    Scoring:
    - 200+ characters: 10 points
    - 100-199 characters: 7 points
    - 50-99 characters: 4 points
    - <50 characters: 2 points
    - Missing: 0 points
    """
    max_score = 10
    score = 0
    suggestions: list[str] = []

    if profile.summary:
        length = len(profile.summary)
        if length >= 200:
            score = 10
        elif length >= 100:
            score = 7
            suggestions.append("Expand summary to 200+ characters for better impact")
        elif length >= 50:
            score = 4
            suggestions.append("Summary is brief - aim for 200+ characters")
        else:
            score = 2
            suggestions.append("Summary too short - describe your professional background")
    else:
        suggestions.append("Add a professional summary highlighting your expertise")

    return CompletenessSection(
        name="Summary",
        score=score,
        max_score=max_score,
        items_present=1 if profile.summary else 0,
        items_recommended=1,
        suggestions=suggestions[:2],
    )


def _score_skills(profile: Profile) -> CompletenessSection:
    """Score skills section (25 points max).

    Scoring:
    - 10+ skills: 25 points
    - 5-9 skills: 15 + (count - 5) * 2 points
    - 1-4 skills: count * 3 points
    - 0 skills: 0 points
    """
    max_score = 25
    count = len(profile.skills)
    suggestions: list[str] = []

    # Calculate score based on count
    if count >= 10:
        score = 25
    elif count >= 5:
        score = 15 + ((count - 5) * 2)  # 15-25 points
    elif count >= 1:
        score = count * 3  # 3-12 points
    else:
        score = 0
        suggestions.append("Add at least 5 relevant skills")

    # Check for skill levels
    skills_with_level = sum(1 for s in profile.skills if s.level)
    if count > 0 and skills_with_level < count * 0.5:
        suggestions.append("Add proficiency levels to your skills")

    # Check for years of experience
    skills_with_years = sum(1 for s in profile.skills if s.years)
    if count > 0 and skills_with_years < count * 0.3:
        suggestions.append("Add years of experience to key skills")

    return CompletenessSection(
        name="Skills",
        score=min(score, max_score),
        max_score=max_score,
        items_present=count,
        items_recommended=10,
        suggestions=suggestions[:2],  # Max 2 suggestions
    )


def _score_experience(profile: Profile) -> CompletenessSection:
    """Score experience section (25 points max).

    Scoring:
    - 4+ entries: 25 points
    - 2-3 entries: 15 + (count - 2) * 5 points
    - 1 entry: 8 points
    - 0 entries: 0 points
    """
    max_score = 25
    count = len(profile.experiences)
    suggestions: list[str] = []

    # Calculate score based on count
    if count >= 4:
        score = 25
    elif count >= 2:
        score = 15 + ((count - 2) * 5)  # 15-25 points
    elif count == 1:
        score = 8
        suggestions.append("Add more work experience entries")
    else:
        score = 0
        suggestions.append("Add your work experience")

    # Check for descriptions
    with_desc = sum(1 for e in profile.experiences if e.description)
    if count > 0 and with_desc < count:
        suggestions.append("Add descriptions to all experience entries")

    # Check for achievements
    with_achievements = sum(1 for e in profile.experiences if e.achievements)
    if count > 0 and with_achievements < count * 0.5:
        suggestions.append("Add achievements to highlight your impact")

    return CompletenessSection(
        name="Experience",
        score=min(score, max_score),
        max_score=max_score,
        items_present=count,
        items_recommended=4,
        suggestions=suggestions[:2],
    )


def _score_education(profile: Profile) -> CompletenessSection:
    """Score education section (10 points max).

    Scoring:
    - 1+ entries: 10 points
    - 0 entries: 0 points
    """
    max_score = 10
    count = len(profile.education)
    suggestions: list[str] = []

    if count >= 1:
        score = 10
    else:
        score = 0
        suggestions.append("Add your educational background")

    return CompletenessSection(
        name="Education",
        score=score,
        max_score=max_score,
        items_present=count,
        items_recommended=1,
        suggestions=suggestions,
    )


def _score_certifications(profile: Profile) -> CompletenessSection:
    """Score certifications section (10 points bonus).

    This is a bonus section - not required but adds value.

    Scoring:
    - 3+ certs: 10 points
    - 1-2 certs: count * 3 points
    - 0 certs: 0 points (not penalized)
    """
    max_score = 10
    count = len(profile.certifications)
    suggestions: list[str] = []

    if count >= 3:
        score = 10
    elif count >= 1:
        score = count * 3  # 3-6 points
    else:
        score = 0
        suggestions.append("Consider adding relevant certifications")

    return CompletenessSection(
        name="Certifications",
        score=score,
        max_score=max_score,
        items_present=count,
        items_recommended=3,
        suggestions=suggestions,
    )


def _score_languages(profile: Profile) -> CompletenessSection:
    """Score languages section (5 points bonus).

    This is a bonus section - not required but adds value.

    Scoring:
    - 1+ languages: 5 points
    - 0 languages: 0 points (not penalized)
    """
    max_score = 5
    count = len(profile.languages)
    suggestions: list[str] = []

    if count >= 1:
        score = 5
    else:
        score = 0
        suggestions.append("Add languages you speak")

    return CompletenessSection(
        name="Languages",
        score=score,
        max_score=max_score,
        items_present=count,
        items_recommended=1,
        suggestions=suggestions,
    )


def _get_level(score: int) -> str:
    """Convert percentage score to level string.

    Returns:
        - "excellent" for 90-100
        - "good" for 70-89
        - "fair" for 50-69
        - "needs_work" for 0-49
    """
    if score >= 90:
        return "excellent"
    elif score >= 70:
        return "good"
    elif score >= 50:
        return "fair"
    else:
        return "needs_work"
