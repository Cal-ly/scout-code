"""
M3 Analyzer Module

Semantic matching between user profile and job requirements.

Usage:
    from src.modules.analyzer import Analyzer, get_analyzer

    # Singleton access (for FastAPI)
    analyzer = await get_analyzer()
    result = await analyzer.analyze(processed_job)

    # Manual instantiation (for testing)
    analyzer = Analyzer(collector, llm_service)
    await analyzer.initialize()
"""

from src.modules.analyzer.analyzer import (
    Analyzer,
    get_analyzer,
    reset_analyzer,
    shutdown_analyzer,
)
from src.modules.analyzer.exceptions import (
    AnalyzerError,
    MatchingError,
    ProfileNotLoadedError,
    ScoringError,
    StrategyGenerationError,
)
from src.modules.analyzer.models import (
    AnalysisInput,
    AnalysisResult,
    ApplicationStrategy,
    CompatibilityScore,
    ExperienceMatchResult,
    MatchLevel,
    QualificationGap,
    SkillMatchResult,
)

__all__ = [
    # Module
    "Analyzer",
    "get_analyzer",
    "shutdown_analyzer",
    "reset_analyzer",
    # Models
    "AnalysisResult",
    "AnalysisInput",
    "CompatibilityScore",
    "MatchLevel",
    "SkillMatchResult",
    "ExperienceMatchResult",
    "QualificationGap",
    "ApplicationStrategy",
    # Exceptions
    "AnalyzerError",
    "MatchingError",
    "ScoringError",
    "StrategyGenerationError",
    "ProfileNotLoadedError",
]
