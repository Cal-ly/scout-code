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
    content = await creator.create_content(analysis_result)
"""

import logging
from datetime import datetime

from src.modules.analyzer.models import AnalysisResult, ApplicationStrategy
from src.modules.collector import Collector
from src.modules.collector.models import Experience, UserProfile
from src.modules.creator.exceptions import (
    AnalysisNotAvailableError,
    CoverLetterGenerationError,
    CreatorError,
    CVGenerationError,
    ProfileNotAvailableError,
)
from src.modules.creator.models import (
    CreatedContent,
    CVSection,
    GeneratedCoverLetter,
    GeneratedCV,
)
from src.modules.creator.prompts import (
    COVER_LETTER_PROMPT,
    COVER_LETTER_SYSTEM_PROMPT,
    CV_EXPERIENCE_PROMPT,
    CV_SUMMARY_PROMPT,
    CV_SYSTEM_PROMPT,
)
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# Soft skills keywords for categorization (PoC simplification)
SOFT_SKILL_KEYWORDS = {
    "leadership",
    "communication",
    "teamwork",
    "problem-solving",
    "problem solving",
    "collaboration",
    "mentoring",
    "management",
    "presentation",
    "negotiation",
    "critical thinking",
    "time management",
    "adaptability",
    "creativity",
    "emotional intelligence",
}


class Creator:
    """
    Creator Module - generates tailored application content.

    Responsibilities:
    - Generate tailored CV content based on analysis strategy
    - Generate personalized cover letter
    - Use analysis strategy for positioning and keywords

    Attributes:
        collector: Collector module for profile access.
        llm: LLM Service for content generation.

    Example:
        >>> creator = Creator(collector, llm_service)
        >>> await creator.initialize()
        >>> content = await creator.create_content(analysis)
        >>> print(content.cv.professional_summary)
        "Senior Python developer with 6+ years..."
    """

    def __init__(
        self,
        collector: Collector,
        llm_service: LLMService,
    ):
        """
        Initialize Creator.

        Args:
            collector: Collector with loaded profile.
            llm_service: LLM Service for generation.
        """
        self._collector = collector
        self._llm = llm_service
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the Creator module.

        Verifies that dependencies are ready.

        Raises:
            CreatorError: If initialization fails.
        """
        if self._initialized:
            logger.warning("Creator already initialized")
            return

        # Verify LLM service health
        health = await self._llm.health_check()
        if health.status == "unavailable":
            raise CreatorError("LLM Service not available")

        self._initialized = True
        logger.info("Creator module initialized")

    async def shutdown(self) -> None:
        """Gracefully shutdown the Creator module."""
        if not self._initialized:
            return

        self._initialized = False
        logger.info("Creator module shutdown complete")

    def _ensure_initialized(self) -> None:
        """Raise error if module not initialized."""
        if not self._initialized:
            raise CreatorError("Creator not initialized. Call initialize() first.")

    def _get_profile(self) -> UserProfile:
        """
        Get user profile from collector.

        Returns:
            UserProfile instance.

        Raises:
            ProfileNotAvailableError: If no profile is loaded.
        """
        try:
            return self._collector.get_profile()
        except Exception as e:
            raise ProfileNotAvailableError(
                f"Profile not available: {e}"
            ) from e

    def _get_current_experience(self, profile: UserProfile) -> Experience | None:
        """
        Get the user's current (or most recent) experience.

        Args:
            profile: User profile.

        Returns:
            Current Experience or None if no experiences.
        """
        if not profile.experiences:
            return None

        # Find current experience (where current=True)
        for exp in profile.experiences:
            if exp.current:
                return exp

        # If no current, return most recent by start_date
        return max(profile.experiences, key=lambda e: e.start_date)

    def _is_soft_skill(self, skill_name: str) -> bool:
        """Check if a skill is a soft skill based on name."""
        return skill_name.lower() in SOFT_SKILL_KEYWORDS

    # =========================================================================
    # CV GENERATION
    # =========================================================================

    async def _generate_summary(
        self,
        profile: UserProfile,
        analysis: AnalysisResult,
    ) -> str:
        """
        Generate professional summary.

        Args:
            profile: User profile.
            analysis: Analysis result with strategy.

        Returns:
            Professional summary text.
        """
        strategy = analysis.strategy or ApplicationStrategy(
            positioning="Highlight relevant experience and skills",
            key_strengths=["Technical expertise", "Professional experience"],
            address_gaps=[],
            tone="professional",
            keywords_to_use=[],
        )

        current_exp = self._get_current_experience(profile)
        current_title = current_exp.role if current_exp else profile.title

        prompt = CV_SUMMARY_PROMPT.format(
            job_title=analysis.job_title,
            company_name=analysis.company_name,
            full_name=profile.full_name,
            current_title=current_title or "Professional",
            years_experience=profile.years_experience,
            key_strengths="\n".join(f"- {s}" for s in strategy.key_strengths),
            positioning=strategy.positioning,
        )

        try:
            result = await self._llm.generate_json(
                prompt=prompt,
                system=CV_SYSTEM_PROMPT,
                module="creator",
                purpose="generate_cv_summary",
            )
            summary_value = result.get("summary", "")
            if not summary_value:
                # Fallback if JSON parsing gives empty result
                raise ValueError("Empty summary in response")
            return str(summary_value).strip()

        except Exception as e:
            logger.warning(f"Summary generation failed: {e}, using fallback")
            # Fallback summary
            return (
                f"{profile.title or 'Professional'} with "
                f"{profile.years_experience:.0f} years of experience. "
                f"{strategy.positioning}"
            )

    async def _generate_experience_section(
        self,
        experience: Experience,
        job_title: str,
        keywords: list[str],
    ) -> CVSection:
        """
        Generate tailored experience section.

        Args:
            experience: Experience to tailor.
            job_title: Target job title.
            keywords: Keywords to incorporate.

        Returns:
            CVSection with tailored content.
        """
        # Calculate duration
        end_date = experience.end_date or datetime.now()
        months = (
            (end_date.year - experience.start_date.year) * 12
            + (end_date.month - experience.start_date.month)
        )
        years = months / 12

        if years >= 1:
            duration = f"{years:.1f} years"
        else:
            duration = f"{months} months"

        prompt = CV_EXPERIENCE_PROMPT.format(
            job_title=job_title,
            keywords=", ".join(keywords[:10]),
            company=experience.company,
            title=experience.role,
            duration=duration,
            description=experience.description,
            achievements="\n".join(f"- {a}" for a in experience.achievements),
            technologies=", ".join(experience.technologies),
        )

        try:
            result = await self._llm.generate_json(
                prompt=prompt,
                system=CV_SYSTEM_PROMPT,
                module="creator",
                purpose="generate_experience",
            )

            return CVSection(
                section_type="experience",
                title=f"{result.get('title', experience.role)} | {experience.company}",
                content=result.get("duration", duration),
                bullet_points=result.get(
                    "bullet_points", experience.achievements[:4]
                ),
            )

        except Exception as e:
            logger.warning(f"Experience generation failed: {e}, using original")
            return CVSection(
                section_type="experience",
                title=f"{experience.role} | {experience.company}",
                content=duration,
                bullet_points=experience.achievements[:4],
            )

    def _build_skills_section(
        self,
        profile: UserProfile,
        strategy: ApplicationStrategy | None,
    ) -> tuple[list[str], list[str]]:
        """
        Build skills lists prioritized by strategy.

        Args:
            profile: User profile.
            strategy: Application strategy with keywords.

        Returns:
            Tuple of (technical_skills, soft_skills).
        """
        keywords = set(
            k.lower() for k in (strategy.keywords_to_use if strategy else [])
        )

        technical: list[str] = []
        soft: list[str] = []

        for skill in profile.skills:
            skill_name = skill.name

            # Categorize by soft skill keywords
            if self._is_soft_skill(skill_name):
                soft.append(skill_name)
            else:
                # Prioritize skills in keywords (put at front)
                if skill_name.lower() in keywords:
                    technical.insert(0, skill_name)
                else:
                    technical.append(skill_name)

        return technical[:15], soft[:5]  # Limit counts

    async def generate_cv(
        self,
        analysis: AnalysisResult,
    ) -> GeneratedCV:
        """
        Generate complete CV.

        Args:
            analysis: Analysis result for tailoring.

        Returns:
            GeneratedCV with all content.

        Raises:
            CVGenerationError: If generation fails.
        """
        self._ensure_initialized()

        logger.info(f"Generating CV for {analysis.job_title}")

        try:
            profile = self._get_profile()

            # Generate summary
            summary = await self._generate_summary(profile, analysis)

            # Generate experience sections
            sections: list[CVSection] = []
            keywords = (
                analysis.strategy.keywords_to_use if analysis.strategy else []
            )

            for exp in profile.experiences[:3]:  # Top 3 experiences
                section = await self._generate_experience_section(
                    exp, analysis.job_title, keywords
                )
                sections.append(section)

            # Add education sections
            for edu in profile.education:
                sections.append(
                    CVSection(
                        section_type="education",
                        title=f"{edu.degree} in {edu.field}",
                        content=edu.institution,
                        bullet_points=(
                            edu.relevant_courses[:3] if edu.relevant_courses else []
                        ),
                    )
                )

            # Build skills
            technical_skills, soft_skills = self._build_skills_section(
                profile, analysis.strategy
            )

            return GeneratedCV(
                full_name=profile.full_name,
                email=profile.email,
                phone=profile.phone,
                location=profile.location,
                linkedin_url=profile.linkedin_url,
                github_url=profile.github_url,
                professional_summary=summary,
                sections=sections,
                technical_skills=technical_skills,
                soft_skills=soft_skills,
                target_job_title=analysis.job_title,
                target_company=analysis.company_name,
            )

        except ProfileNotAvailableError:
            raise
        except Exception as e:
            raise CVGenerationError(f"Failed to generate CV: {e}") from e

    # =========================================================================
    # COVER LETTER GENERATION
    # =========================================================================

    async def generate_cover_letter(
        self,
        analysis: AnalysisResult,
    ) -> GeneratedCoverLetter:
        """
        Generate cover letter.

        Args:
            analysis: Analysis result for tailoring.

        Returns:
            GeneratedCoverLetter.

        Raises:
            CoverLetterGenerationError: If generation fails.
        """
        self._ensure_initialized()

        logger.info(f"Generating cover letter for {analysis.job_title}")

        try:
            profile = self._get_profile()

            strategy = analysis.strategy or ApplicationStrategy(
                positioning="Highlight relevant experience",
                key_strengths=["Technical expertise"],
                address_gaps=["Express enthusiasm to learn"],
                tone="professional",
                keywords_to_use=[],
                opening_hook=None,
            )

            current_exp = self._get_current_experience(profile)
            current_title = current_exp.role if current_exp else profile.title

            # Build relevant experiences text
            relevant_exp_text: list[str] = []
            for exp in profile.experiences[:2]:
                achievement = (
                    exp.achievements[0]
                    if exp.achievements
                    else exp.description[:100]
                )
                relevant_exp_text.append(
                    f"- {exp.role} at {exp.company}: {achievement}"
                )

            prompt = COVER_LETTER_PROMPT.format(
                job_title=analysis.job_title,
                company_name=analysis.company_name,
                full_name=profile.full_name,
                current_title=current_title or "Professional",
                positioning=strategy.positioning,
                key_strengths="\n".join(f"- {s}" for s in strategy.key_strengths),
                address_gaps=(
                    "\n".join(f"- {g}" for g in strategy.address_gaps)
                    or "None identified"
                ),
                opening_hook=(
                    strategy.opening_hook or "Express genuine interest in the role"
                ),
                relevant_experiences="\n".join(relevant_exp_text),
            )

            try:
                result = await self._llm.generate_json(
                    prompt=prompt,
                    system=COVER_LETTER_SYSTEM_PROMPT,
                    module="creator",
                    purpose="generate_cover_letter",
                )

                letter = GeneratedCoverLetter(
                    company_name=analysis.company_name,
                    job_title=analysis.job_title,
                    opening=result.get("opening", ""),
                    body_paragraphs=result.get("body_paragraphs", []),
                    closing=result.get("closing", ""),
                    tone=strategy.tone,
                )

            except Exception as e:
                logger.warning(
                    f"Cover letter generation failed: {e}, using fallback"
                )
                letter = GeneratedCoverLetter(
                    company_name=analysis.company_name,
                    job_title=analysis.job_title,
                    opening=(
                        f"I am writing to express my interest in the "
                        f"{analysis.job_title} position at {analysis.company_name}."
                    ),
                    body_paragraphs=[
                        f"With {profile.years_experience:.0f} years of experience, "
                        f"I am confident I can contribute to your team.",
                        "My background aligns well with the requirements of this role.",
                    ],
                    closing=(
                        "I look forward to the opportunity to discuss how I can "
                        "contribute to your team. Thank you for your consideration."
                    ),
                )

            # Calculate word count
            letter.word_count = len(letter.full_text.split())

            return letter

        except ProfileNotAvailableError:
            raise
        except Exception as e:
            raise CoverLetterGenerationError(
                f"Failed to generate cover letter: {e}"
            ) from e

    # =========================================================================
    # MAIN GENERATION
    # =========================================================================

    async def create_content(
        self,
        analysis: AnalysisResult | None,
    ) -> CreatedContent:
        """
        Create complete application content.

        Main entry point for the Creator module.

        Args:
            analysis: Analysis result from Analyzer.

        Returns:
            CreatedContent with CV and cover letter.

        Raises:
            AnalysisNotAvailableError: If analysis is None or missing required data.
            CreatorError: If content generation fails.

        Example:
            >>> content = await creator.create_content(analysis)
            >>> print(content.cv.professional_summary)
            >>> print(content.cover_letter.full_text)
        """
        self._ensure_initialized()

        # Validate analysis is available
        if analysis is None:
            raise AnalysisNotAvailableError(
                "Analysis result is required for content generation"
            )

        if not analysis.job_title:
            raise AnalysisNotAvailableError(
                "Analysis is missing job title - cannot generate content"
            )

        if not analysis.compatibility:
            raise AnalysisNotAvailableError(
                "Analysis is missing compatibility data - cannot tailor content"
            )

        logger.info(
            f"Creating application content for {analysis.job_title} "
            f"at {analysis.company_name}"
        )

        # Generate CV
        cv = await self.generate_cv(analysis)

        # Generate cover letter
        cover_letter = await self.generate_cover_letter(analysis)

        content = CreatedContent(
            job_id=analysis.job_id,
            job_title=analysis.job_title,
            company_name=analysis.company_name,
            cv=cv,
            cover_letter=cover_letter,
            compatibility_score=analysis.compatibility.overall,
        )

        logger.info(
            f"Application content created: "
            f"CV ({len(cv.sections)} sections), "
            f"Cover letter ({cover_letter.word_count} words)"
        )

        return content


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

_creator_instance: Creator | None = None


async def get_creator() -> Creator:
    """
    Get the Creator instance.

    Creates and initializes singleton on first call.
    Requires Collector and LLM Service.

    Returns:
        Initialized Creator.
    """
    global _creator_instance

    if _creator_instance is None:
        from src.modules.collector import get_collector
        from src.services.llm_service import get_llm_service

        collector = await get_collector()
        llm_service = await get_llm_service()

        _creator_instance = Creator(collector, llm_service)
        await _creator_instance.initialize()

    return _creator_instance


async def shutdown_creator() -> None:
    """Shutdown the global Creator instance."""
    global _creator_instance

    if _creator_instance is not None:
        await _creator_instance.shutdown()
        _creator_instance = None


def reset_creator() -> None:
    """Reset the global instance (for testing)."""
    global _creator_instance
    _creator_instance = None
