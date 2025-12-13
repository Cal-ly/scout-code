"""
M3 Analyzer Module

Compares user profile to job requirements and generates application strategy.

Usage:
    from src.modules.analyzer import Analyzer, get_analyzer

    # Singleton access (for FastAPI)
    analyzer = await get_analyzer()

    # Analyze a processed job
    result = await analyzer.analyze(processed_job)
    print(f"Compatibility: {result.compatibility.overall}%")
    print(f"Strategy: {result.strategy.positioning}")
"""

import logging
from typing import Any

from src.modules.analyzer.exceptions import (
    AnalyzerError,
    MatchingError,
    ProfileNotLoadedError,
    StrategyGenerationError,
)
from src.modules.analyzer.models import (
    AnalysisResult,
    ApplicationStrategy,
    CompatibilityScore,
    ExperienceMatchResult,
    MatchLevel,
    QualificationGap,
    SkillMatchResult,
)
from src.modules.analyzer.prompts import (
    STRATEGY_GENERATION_PROMPT,
    STRATEGY_SYSTEM_PROMPT,
)
from src.modules.collector import Collector
from src.modules.collector.models import SearchMatch
from src.modules.rinser.models import ProcessedJob, RequirementPriority
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class Analyzer:
    """
    Analyzer Module - matches profile to job and generates strategy.

    Responsibilities:
    - Match skills to requirements semantically
    - Match experiences to responsibilities
    - Identify qualification gaps
    - Calculate compatibility score
    - Generate application strategy via LLM

    Attributes:
        collector: Collector module for profile search.
        llm: LLM Service for strategy generation.

    Example:
        >>> analyzer = Analyzer(collector, llm_service)
        >>> await analyzer.initialize()
        >>> result = await analyzer.analyze(job)
        >>> print(f"Match: {result.compatibility.level.value}")
        "Match: strong"
        >>> print(result.strategy.positioning)
        "Position yourself as an experienced Python developer..."
    """

    # Thresholds for matching
    SKILL_MATCH_THRESHOLD = 0.5  # Minimum similarity for skill match
    EXPERIENCE_MATCH_THRESHOLD = 0.4  # Minimum for experience match

    # Weights for compatibility calculation
    WEIGHT_MUST_HAVE = 0.5
    WEIGHT_NICE_TO_HAVE = 0.2
    WEIGHT_EXPERIENCE = 0.3

    def __init__(
        self,
        collector: Collector,
        llm_service: LLMService,
    ):
        """
        Initialize Analyzer.

        Args:
            collector: Collector with loaded profile.
            llm_service: LLM Service for strategy generation.
        """
        self._collector = collector
        self._llm = llm_service
        self._initialized = False

        # Stats
        self._total_analyses = 0

    async def initialize(self) -> None:
        """
        Initialize the Analyzer module.

        Verifies dependencies are ready.

        Raises:
            AnalyzerError: If initialization fails.
        """
        if self._initialized:
            logger.warning("Analyzer already initialized")
            return

        # Verify LLM service is available
        llm_health = await self._llm.health_check()
        if llm_health.status not in ("healthy", "degraded"):
            raise AnalyzerError(f"LLM service not available: {llm_health.status}")

        self._initialized = True
        logger.info("Analyzer module initialized")

    async def shutdown(self) -> None:
        """Gracefully shutdown the Analyzer module."""
        if not self._initialized:
            return

        self._initialized = False
        logger.info("Analyzer module shutdown complete")

    # =========================================================================
    # SKILL MATCHING
    # =========================================================================

    async def _match_skills(
        self,
        job: ProcessedJob,
    ) -> tuple[list[SkillMatchResult], int, int]:
        """
        Match user skills against job requirements.

        Args:
            job: Processed job with requirements.

        Returns:
            Tuple of (skill_matches, must_haves_met, nice_to_haves_met)

        Raises:
            MatchingError: If skill matching fails.
        """
        matches: list[SkillMatchResult] = []
        must_haves_met = 0
        nice_to_haves_met = 0

        try:
            for req in job.requirements:
                # Search for matching skills using Collector
                skill_results = await self._collector.search_skills(
                    query=req.text,
                    n_results=3,
                )

                # Filter by threshold
                matched_results = [
                    s for s in skill_results if s.score >= self.SKILL_MATCH_THRESHOLD
                ]

                # Build match result
                matched_skill_names = [
                    self._format_skill_match(s) for s in matched_results
                ]

                # Determine if requirement is met
                is_met = len(matched_results) > 0
                best_score = matched_results[0].score if matched_results else 0.0

                # Check years requirement if present
                gap_reason: str | None = None
                if not is_met:
                    gap_reason = "No matching skills found"
                elif req.years_required:
                    # Check if years requirement is met from metadata
                    max_years = max(
                        (
                            float(s.metadata.get("years") or 0)
                            for s in matched_results
                        ),
                        default=0.0,
                    )
                    if max_years < req.years_required:
                        gap_reason = (
                            f"Have {max_years:.0f} years, need {req.years_required}"
                        )
                        is_met = False

                match = SkillMatchResult(
                    requirement_text=req.text,
                    requirement_priority=req.priority.value,
                    matched_skills=matched_skill_names,
                    score=best_score,
                    is_met=is_met,
                    gap_reason=gap_reason,
                )
                matches.append(match)

                # Count met requirements
                if is_met:
                    if req.priority == RequirementPriority.MUST_HAVE:
                        must_haves_met += 1
                    else:
                        nice_to_haves_met += 1

            return matches, must_haves_met, nice_to_haves_met

        except Exception as e:
            raise MatchingError(f"Skill matching failed: {e}") from e

    def _format_skill_match(self, match: SearchMatch) -> str:
        """Format a skill match for display."""
        name = match.metadata.get("name", "Unknown")
        level = match.metadata.get("level", "")
        years = match.metadata.get("years", 0)

        parts = [str(name)]
        if level:
            parts.append(f"({level}")
            if years and float(years) > 0:
                parts[-1] += f", {float(years):.0f} years)"
            else:
                parts[-1] += ")"
        elif years and float(years) > 0:
            parts.append(f"({float(years):.0f} years)")

        return " ".join(parts)

    # =========================================================================
    # EXPERIENCE MATCHING
    # =========================================================================

    async def _match_experiences(
        self,
        job: ProcessedJob,
    ) -> list[ExperienceMatchResult]:
        """
        Match user experiences against job responsibilities.

        Args:
            job: Processed job with responsibilities.

        Returns:
            List of experience matches.

        Raises:
            MatchingError: If experience matching fails.
        """
        matches: list[ExperienceMatchResult] = []

        try:
            for resp in job.responsibilities:
                # Search for relevant experiences
                exp_results = await self._collector.search_experiences(
                    query=resp.text,
                    n_results=1,
                )

                # Filter by threshold
                matched_results = [
                    e
                    for e in exp_results
                    if e.score >= self.EXPERIENCE_MATCH_THRESHOLD
                ]

                if matched_results:
                    exp = matched_results[0]
                    # Extract matching keywords
                    keywords = self._extract_matching_keywords(resp.text, exp)

                    match = ExperienceMatchResult(
                        responsibility_text=resp.text,
                        matched_experience=self._format_experience_match(exp),
                        relevance_score=exp.score,
                        matching_keywords=keywords,
                    )
                else:
                    match = ExperienceMatchResult(
                        responsibility_text=resp.text,
                        matched_experience=None,
                        relevance_score=0.0,
                        matching_keywords=[],
                    )

                matches.append(match)

            return matches

        except Exception as e:
            raise MatchingError(f"Experience matching failed: {e}") from e

    def _format_experience_match(self, match: SearchMatch) -> str:
        """Format an experience match for display."""
        role = match.metadata.get("role", "")
        company = match.metadata.get("company", "")
        if role and company:
            return f"{role} at {company}"
        return match.content[:50] + "..." if len(match.content) > 50 else match.content

    def _extract_matching_keywords(
        self,
        responsibility_text: str,
        experience: SearchMatch,
    ) -> list[str]:
        """Extract keywords that appear in both texts."""
        resp_words = set(responsibility_text.lower().split())
        exp_text = experience.content.lower()

        # Find meaningful words that appear in both
        keywords: list[str] = []
        for word in resp_words:
            if len(word) > 3 and word in exp_text:
                keywords.append(word)

        return list(set(keywords))[:5]  # Limit to 5

    # =========================================================================
    # GAP ANALYSIS
    # =========================================================================

    def _identify_gaps(
        self,
        skill_matches: list[SkillMatchResult],
    ) -> list[QualificationGap]:
        """
        Identify qualification gaps.

        Args:
            skill_matches: Results from skill matching.

        Returns:
            List of gaps.
        """
        gaps: list[QualificationGap] = []

        for match in skill_matches:
            if not match.is_met:
                gap = QualificationGap(
                    requirement=match.requirement_text,
                    importance=match.requirement_priority,
                    gap_type=self._determine_gap_type(match.requirement_text),
                    current_level=(
                        ", ".join(match.matched_skills) if match.matched_skills else None
                    ),
                    suggested_action=self._suggest_gap_action(match),
                )
                gaps.append(gap)

        return gaps

    def _determine_gap_type(self, requirement_text: str) -> str:
        """Determine the type of gap based on requirement text."""
        text_lower = requirement_text.lower()

        if any(word in text_lower for word in ["degree", "bachelor", "master", "phd"]):
            return "education"
        elif any(word in text_lower for word in ["certified", "certification"]):
            return "certification"
        elif any(word in text_lower for word in ["years", "experience"]):
            return "experience"
        else:
            return "skill"

    def _suggest_gap_action(self, match: SkillMatchResult) -> str:
        """Suggest how to address a gap."""
        if match.matched_skills:
            return f"Emphasize related skills: {', '.join(match.matched_skills[:2])}"
        elif "years" in match.requirement_text.lower():
            return "Highlight project complexity and impact over raw years"
        else:
            return "Mention willingness to learn and any adjacent experience"

    # =========================================================================
    # COMPATIBILITY SCORING
    # =========================================================================

    def _calculate_compatibility(
        self,
        skill_matches: list[SkillMatchResult],
        experience_matches: list[ExperienceMatchResult],
        must_haves_met: int,
        nice_to_haves_met: int,
        job: ProcessedJob,
    ) -> CompatibilityScore:
        """
        Calculate overall compatibility score.

        Args:
            skill_matches: Skill match results.
            experience_matches: Experience match results.
            must_haves_met: Count of must-haves met.
            nice_to_haves_met: Count of nice-to-haves met.
            job: Processed job.

        Returns:
            CompatibilityScore.
        """
        must_haves = job.get_must_have_requirements()
        nice_to_haves = [
            r for r in job.requirements if r.priority != RequirementPriority.MUST_HAVE
        ]

        # Calculate component scores
        must_have_score = (
            (must_haves_met / len(must_haves) * 100) if must_haves else 100
        )
        nice_to_have_score = (
            (nice_to_haves_met / len(nice_to_haves) * 100) if nice_to_haves else 100
        )

        # Experience score
        matched_exp = [m for m in experience_matches if m.matched_experience]
        experience_score = (
            (len(matched_exp) / len(experience_matches) * 100)
            if experience_matches
            else 50
        )

        # Technical skills average
        tech_scores = [m.score * 100 for m in skill_matches]
        technical_score = sum(tech_scores) / len(tech_scores) if tech_scores else 50

        # Weighted overall score
        overall = (
            must_have_score * self.WEIGHT_MUST_HAVE
            + nice_to_have_score * self.WEIGHT_NICE_TO_HAVE
            + experience_score * self.WEIGHT_EXPERIENCE
        )

        # Determine level
        if overall >= 85:
            level = MatchLevel.EXCELLENT
        elif overall >= 70:
            level = MatchLevel.STRONG
        elif overall >= 50:
            level = MatchLevel.MODERATE
        elif overall >= 30:
            level = MatchLevel.WEAK
        else:
            level = MatchLevel.POOR

        return CompatibilityScore(
            overall=round(overall, 1),
            level=level,
            technical_skills=round(technical_score, 1),
            experience_relevance=round(experience_score, 1),
            requirements_met=round(must_have_score, 1),
            must_haves_met=must_haves_met,
            must_haves_total=len(must_haves),
            nice_to_haves_met=nice_to_haves_met,
            nice_to_haves_total=len(nice_to_haves),
        )

    # =========================================================================
    # STRATEGY GENERATION
    # =========================================================================

    async def _generate_strategy(
        self,
        job: ProcessedJob,
        compatibility: CompatibilityScore,
        skill_matches: list[SkillMatchResult],
        experience_matches: list[ExperienceMatchResult],
        gaps: list[QualificationGap],
    ) -> ApplicationStrategy:
        """
        Generate application strategy via LLM.

        Args:
            job: Processed job.
            compatibility: Compatibility score.
            skill_matches: Skill matches.
            experience_matches: Experience matches.
            gaps: Identified gaps.

        Returns:
            ApplicationStrategy.
        """
        # Format matches for prompt
        skill_text = "\n".join(
            [
                f"- {m.requirement_text}: {'Met' if m.is_met else 'Gap'} "
                f"(matched: {', '.join(m.matched_skills) or 'none'})"
                for m in skill_matches[:5]
            ]
        )

        exp_text = "\n".join(
            [
                f"- {m.responsibility_text}: {m.matched_experience or 'No match'}"
                for m in experience_matches[:5]
            ]
        )

        gaps_text = (
            "\n".join(
                [f"- [{g.importance}] {g.requirement}: {g.gap_type}" for g in gaps[:5]]
            )
            or "No significant gaps"
        )

        prompt = STRATEGY_GENERATION_PROMPT.format(
            job_title=job.title,
            company_name=job.company.name,
            overall_score=compatibility.overall,
            must_haves_met=compatibility.must_haves_met,
            must_haves_total=compatibility.must_haves_total,
            skill_matches_text=skill_text,
            experience_matches_text=exp_text,
            gaps_text=gaps_text,
        )

        try:
            result: dict[str, Any] = await self._llm.generate_json(
                prompt=prompt,
                system=STRATEGY_SYSTEM_PROMPT,
                module="analyzer",
                purpose="generate_strategy",
            )

            return ApplicationStrategy(
                positioning=result.get("positioning", ""),
                key_strengths=result.get("key_strengths", []),
                address_gaps=result.get("address_gaps", []),
                tone=result.get("tone", "professional"),
                keywords_to_use=result.get("keywords_to_use", []),
                opening_hook=result.get("opening_hook"),
            )

        except Exception as e:
            logger.warning(f"Strategy generation failed: {e}, using fallback")
            raise StrategyGenerationError(f"Strategy generation failed: {e}") from e

    def _create_fallback_strategy(self) -> ApplicationStrategy:
        """Create a fallback strategy when LLM fails."""
        return ApplicationStrategy(
            positioning="Highlight relevant experience and transferable skills.",
            key_strengths=["Technical proficiency", "Relevant experience"],
            address_gaps=["Mention willingness to learn new technologies"],
            tone="professional",
            keywords_to_use=[],
        )

    # =========================================================================
    # MAIN ANALYSIS
    # =========================================================================

    async def analyze(
        self,
        job: ProcessedJob,
        generate_strategy: bool = True,
    ) -> AnalysisResult:
        """
        Analyze job-profile compatibility.

        Main entry point for the Analyzer module.

        Args:
            job: Processed job from Rinser.
            generate_strategy: Whether to generate LLM strategy.

        Returns:
            AnalysisResult with compatibility and strategy.

        Raises:
            AnalyzerError: If analysis fails.
            ProfileNotLoadedError: If profile is not loaded.

        Example:
            >>> result = await analyzer.analyze(job)
            >>> print(f"Compatibility: {result.compatibility.overall}%")
            >>> print(f"Level: {result.compatibility.level.value}")
            >>> if result.is_good_match:
            ...     print("Good match! Proceed with application.")
        """
        logger.info(f"Analyzing job: {job.title} at {job.company.name}")

        # Verify profile is loaded
        try:
            self._collector.get_profile()
        except Exception as e:
            raise ProfileNotLoadedError(
                f"Profile not loaded in Collector: {e}"
            ) from e

        # Step 1: Match skills to requirements
        skill_matches, must_haves_met, nice_to_haves_met = await self._match_skills(job)
        logger.debug(
            f"Skill matches: {must_haves_met} must-haves, {nice_to_haves_met} nice-to-haves"
        )

        # Step 2: Match experiences to responsibilities
        experience_matches = await self._match_experiences(job)
        matched_exp_count = len([m for m in experience_matches if m.matched_experience])
        logger.debug(f"Experience matches: {matched_exp_count}/{len(experience_matches)}")

        # Step 3: Identify gaps
        gaps = self._identify_gaps(skill_matches)
        logger.debug(f"Gaps identified: {len(gaps)}")

        # Step 4: Calculate compatibility score
        compatibility = self._calculate_compatibility(
            skill_matches=skill_matches,
            experience_matches=experience_matches,
            must_haves_met=must_haves_met,
            nice_to_haves_met=nice_to_haves_met,
            job=job,
        )
        logger.info(f"Compatibility: {compatibility.overall}% ({compatibility.level.value})")

        # Step 5: Generate strategy (optional)
        strategy: ApplicationStrategy | None = None
        if generate_strategy:
            try:
                strategy = await self._generate_strategy(
                    job=job,
                    compatibility=compatibility,
                    skill_matches=skill_matches,
                    experience_matches=experience_matches,
                    gaps=gaps,
                )
            except StrategyGenerationError:
                logger.warning("Using fallback strategy due to LLM error")
                strategy = self._create_fallback_strategy()

        self._total_analyses += 1

        return AnalysisResult(
            job_id=job.id,
            job_title=job.title,
            company_name=job.company.name,
            compatibility=compatibility,
            skill_matches=skill_matches,
            experience_matches=experience_matches,
            gaps=gaps,
            strategy=strategy,
        )

    async def analyze_safe(
        self,
        job: ProcessedJob,
        generate_strategy: bool = True,
    ) -> tuple[AnalysisResult | None, str | None]:
        """
        Analyze job-profile compatibility with error handling.

        Returns a tuple of (result, error) instead of raising exceptions.

        Args:
            job: Processed job from Rinser.
            generate_strategy: Whether to generate LLM strategy.

        Returns:
            Tuple of (AnalysisResult, None) on success or (None, error_message) on failure.
        """
        try:
            result = await self.analyze(job, generate_strategy)
            return result, None
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return None, str(e)

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> dict[str, int]:
        """Get analysis statistics."""
        return {
            "total_analyses": self._total_analyses,
        }


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

_analyzer_instance: Analyzer | None = None


async def get_analyzer() -> Analyzer:
    """
    Get the Analyzer module instance.

    Creates and initializes singleton on first call.
    Use as FastAPI dependency.

    Returns:
        Initialized Analyzer instance.
    """
    from src.modules.collector import get_collector
    from src.services.llm_service import get_llm_service

    global _analyzer_instance

    if _analyzer_instance is None:
        collector = await get_collector()
        llm_service = await get_llm_service()

        _analyzer_instance = Analyzer(collector, llm_service)
        await _analyzer_instance.initialize()

    return _analyzer_instance


async def shutdown_analyzer() -> None:
    """Shutdown the global Analyzer instance."""
    global _analyzer_instance

    if _analyzer_instance is not None:
        await _analyzer_instance.shutdown()
        _analyzer_instance = None


def reset_analyzer() -> None:
    """Reset the global instance (for testing)."""
    global _analyzer_instance
    _analyzer_instance = None
