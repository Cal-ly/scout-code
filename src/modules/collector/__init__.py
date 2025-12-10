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
    # Exceptions
    "CollectorError",
    "ProfileNotFoundError",
    "ProfileValidationError",
    "ProfileLoadError",
    "IndexingError",
    "SearchError",
]
