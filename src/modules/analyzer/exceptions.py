"""
M3 Analyzer Exceptions

Custom exceptions for the Analyzer module.
"""


class AnalyzerError(Exception):
    """Base exception for Analyzer module operations."""

    pass


class MatchingError(AnalyzerError):
    """Error during skill/experience matching."""

    pass


class ScoringError(AnalyzerError):
    """Error during compatibility scoring."""

    pass


class StrategyGenerationError(AnalyzerError):
    """Error during LLM strategy generation."""

    pass


class ProfileNotLoadedError(AnalyzerError):
    """Error when profile is not loaded in Collector."""

    pass
