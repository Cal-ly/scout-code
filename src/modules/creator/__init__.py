"""
M4 Creator Module

Generates tailored CV and cover letter content using LLM.

Usage:
    from src.modules.creator import Creator, get_creator

    # Singleton access (for FastAPI)
    creator = await get_creator()
    content = await creator.create_content(analysis_result)

    # Manual instantiation (for testing)
    creator = Creator(collector, llm_service)
    await creator.initialize()
"""

from src.modules.creator.creator import (
    Creator,
    get_creator,
    reset_creator,
    shutdown_creator,
)
from src.modules.creator.exceptions import (
    AnalysisNotAvailableError,
    CoverLetterGenerationError,
    CreatorError,
    CVGenerationError,
    GenerationError,
    ProfileNotAvailableError,
)
from src.modules.creator.models import (
    CreatedContent,
    CreatorConfig,
    CVSection,
    DEFAULT_SOFT_SKILLS,
    GeneratedCoverLetter,
    GeneratedCV,
)

__all__ = [
    # Module
    "Creator",
    "get_creator",
    "shutdown_creator",
    "reset_creator",
    # Models
    "CreatedContent",
    "CreatorConfig",
    "GeneratedCV",
    "GeneratedCoverLetter",
    "CVSection",
    "DEFAULT_SOFT_SKILLS",
    # Exceptions
    "CreatorError",
    "GenerationError",
    "CVGenerationError",
    "CoverLetterGenerationError",
    "ProfileNotAvailableError",
    "AnalysisNotAvailableError",
]
