"""
M1 Collector Module

User profile management and semantic search for job matching.

Usage:
    from src.modules.collector import Collector, get_collector

    # Singleton access (for FastAPI)
    collector = await get_collector()
    await collector.load_profile()
    results = await collector.search_experiences("Python")

    # Manual instantiation (for testing)
    collector = Collector(vector_store)
    await collector.initialize()
"""

from src.modules.collector.assessment import (
    ProfileAssessment,
    ProfileGrade,
    SectionScore,
    assess_profile,
)
from src.modules.collector.collector import (
    Collector,
    get_collector,
    reset_collector,
    shutdown_collector,
)
from src.modules.collector.exceptions import (
    CollectorError,
    IndexingError,
    ProfileLoadError,
    ProfileNotFoundError,
    ProfileValidationError,
    SearchError,
)
from src.modules.collector.models import (
    Certification,
    Education,
    Experience,
    ProfileSummary,
    SearchMatch,
    Skill,
    SkillLevel,
    SkillMatch,
    UserProfile,
)
from src.modules.collector.skill_aliases import (
    SKILL_ALIASES,
    expand_skill_query,
    get_all_canonical_skills,
    get_canonical_name,
    is_known_skill,
    normalize_skill_name,
)

__all__ = [
    # Module
    "Collector",
    "get_collector",
    "shutdown_collector",
    "reset_collector",
    # Models
    "UserProfile",
    "Skill",
    "SkillLevel",
    "Experience",
    "Education",
    "Certification",
    "ProfileSummary",
    "SearchMatch",
    "SkillMatch",
    # Assessment
    "ProfileAssessment",
    "ProfileGrade",
    "SectionScore",
    "assess_profile",
    # Skill Aliases
    "SKILL_ALIASES",
    "normalize_skill_name",
    "expand_skill_query",
    "get_all_canonical_skills",
    "get_canonical_name",
    "is_known_skill",
    # Exceptions
    "CollectorError",
    "ProfileNotFoundError",
    "ProfileValidationError",
    "ProfileLoadError",
    "IndexingError",
    "SearchError",
]
