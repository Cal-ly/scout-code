"""
M1 Collector Module

Manages user profile data, making it searchable for tailored application generation.
Uses VectorStoreService for semantic search capabilities.

Usage:
    from src.modules.collector import Collector, get_collector

    # Singleton access
    collector = await get_collector()

    # Load and index profile
    profile = await collector.load_profile()

    # Search for relevant experiences
    results = await collector.search_experiences("Python development")
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.modules.collector.assessment import ProfileAssessment, assess_profile
from src.modules.collector.exceptions import (
    CollectorError,
    IndexingError,
    ProfileLoadError,
    ProfileNotFoundError,
    ProfileValidationError,
    SearchError,
)
from src.modules.collector.models import (
    ProfileSummary,
    SearchMatch,
    SkillMatch,
    UserProfile,
)
from src.modules.collector.skill_aliases import (
    expand_skill_query,
    normalize_skill_name,
)
from src.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_PROFILE_PATH = Path("data/profile.yaml")
COLLECTION_NAME = "user_profiles"  # PoC uses single collection


class Collector:
    """
    Collector module for user profile management.

    Loads user profile from YAML, indexes it in vector store,
    and provides semantic search for matching against job requirements.

    Attributes:
        profile_path: Path to the user profile YAML file.
        profile: Loaded and validated user profile.
        profile_hash: MD5 hash for change detection.

    Example:
        >>> collector = Collector(vector_store)
        >>> await collector.initialize()
        >>> await collector.load_profile()
        >>> results = await collector.search_experiences("Python")
    """

    def __init__(
        self,
        vector_store: VectorStoreService,
        profile_path: Path | None = None,
    ):
        """
        Initialize the Collector module.

        Args:
            vector_store: VectorStoreService instance for semantic search.
            profile_path: Path to user profile YAML (default: data/profile.yaml).
        """
        self._vector_store = vector_store
        self._profile_path = profile_path or DEFAULT_PROFILE_PATH
        self._profile: UserProfile | None = None
        self._profile_hash: str | None = None
        self._initialized = False
        self._indexed = False

    async def initialize(self) -> None:
        """
        Initialize the Collector module.

        Verifies vector store is ready.

        Raises:
            CollectorError: If initialization fails.
        """
        if self._initialized:
            logger.warning("Collector already initialized")
            return

        # Verify vector store is available
        health = await self._vector_store.health_check()
        if health.status != "healthy":
            raise CollectorError(
                f"Vector store not healthy: {health.status}"
            )

        self._initialized = True
        logger.info("Collector module initialized")

    async def shutdown(self) -> None:
        """Gracefully shutdown the Collector module."""
        if not self._initialized:
            return

        self._profile = None
        self._profile_hash = None
        self._indexed = False
        self._initialized = False
        logger.info("Collector module shutdown complete")

    # =========================================================================
    # PROFILE LOADING
    # =========================================================================

    async def load_profile(self, path: Path | None = None) -> UserProfile:
        """
        Load and validate user profile from YAML file.

        Args:
            path: Optional path override (uses configured path if None).

        Returns:
            Validated UserProfile instance.

        Raises:
            ProfileNotFoundError: If profile file doesn't exist.
            ProfileLoadError: If YAML parsing fails.
            ProfileValidationError: If profile data is invalid.
        """
        profile_path = path or self._profile_path

        if not profile_path.exists():
            raise ProfileNotFoundError(
                f"Profile not found at {profile_path}"
            )

        try:
            with open(profile_path) as f:
                profile_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ProfileLoadError(f"Failed to parse YAML: {e}") from e
        except OSError as e:
            raise ProfileLoadError(f"Failed to read file: {e}") from e

        if not profile_data:
            raise ProfileValidationError("Profile file is empty")

        try:
            self._profile = UserProfile(**profile_data)
        except Exception as e:
            raise ProfileValidationError(
                f"Profile validation failed: {e}"
            ) from e

        # Calculate hash for change detection
        profile_str = json.dumps(profile_data, sort_keys=True, default=str)
        self._profile_hash = hashlib.md5(profile_str.encode()).hexdigest()

        logger.info(
            f"Loaded profile for {self._profile.full_name} "
            f"(hash: {self._profile_hash[:8]})"
        )

        return self._profile

    def get_profile(self) -> UserProfile:
        """
        Get the currently loaded profile.

        Returns:
            The loaded UserProfile.

        Raises:
            CollectorError: If no profile is loaded.
        """
        if self._profile is None:
            raise CollectorError("No profile loaded. Call load_profile() first.")
        return self._profile

    def get_profile_summary(self) -> ProfileSummary:
        """
        Get a summary of the loaded profile.

        Returns:
            ProfileSummary with key statistics.

        Raises:
            CollectorError: If no profile is loaded.
        """
        profile = self.get_profile()

        return ProfileSummary(
            name=profile.full_name,
            title=profile.title,
            years_experience=profile.years_experience,
            skill_count=len(profile.skills),
            experience_count=len(profile.experiences),
            education_count=len(profile.education),
            certification_count=len(profile.certifications),
            last_updated=profile.last_updated,
        )

    def assess_profile_completeness(self) -> ProfileAssessment:
        """
        Assess the completeness and quality of the loaded profile.

        Returns:
            ProfileAssessment with scores and improvement suggestions.

        Raises:
            CollectorError: If no profile is loaded.
        """
        if not self._profile:
            raise CollectorError("No profile loaded. Call load_profile() first.")

        return assess_profile(self._profile)

    # =========================================================================
    # INDEXING
    # =========================================================================

    async def index_profile(self) -> int:
        """
        Index all profile content in vector store.

        Creates searchable embeddings for skills, experiences,
        education, and certifications.

        Returns:
            Number of documents indexed.

        Raises:
            CollectorError: If no profile is loaded.
            IndexingError: If indexing fails.
        """
        profile = self.get_profile()
        documents_indexed = 0

        try:
            # Index skills with alias information
            for i, skill in enumerate(profile.skills):
                doc_id = f"skill_{self._profile_hash}_{i}"

                # Normalize skill name and get aliases for better matching
                canonical_name = normalize_skill_name(skill.name)
                aliases = expand_skill_query(skill.name)

                # Create enhanced searchable text that includes aliases
                searchable_text = skill.to_searchable_text()
                if len(aliases) > 1:
                    alias_text = f" Also known as: {', '.join(aliases)}"
                    enhanced_text = searchable_text + alias_text
                else:
                    enhanced_text = searchable_text

                await self._vector_store.add(
                    collection_name=COLLECTION_NAME,
                    document_id=doc_id,
                    content=enhanced_text,
                    metadata={
                        "type": "skill",
                        "name": skill.name,
                        "canonical_name": canonical_name,
                        "aliases": ",".join(aliases),
                        "level": skill.level.value,
                        "years": skill.years or 0.0,
                        "profile_hash": self._profile_hash or "",
                    },
                )
                documents_indexed += 1

            # Index experiences
            for exp in profile.experiences:
                doc_id = f"exp_{self._profile_hash}_{exp.id}"
                await self._vector_store.add(
                    collection_name=COLLECTION_NAME,
                    document_id=doc_id,
                    content=exp.to_searchable_text(),
                    metadata={
                        "type": "experience",
                        "company": exp.company,
                        "role": exp.role,
                        "current": exp.current,
                        "profile_hash": self._profile_hash or "",
                    },
                )
                documents_indexed += 1

            # Index education
            for i, edu in enumerate(profile.education):
                doc_id = f"edu_{self._profile_hash}_{i}"
                await self._vector_store.add(
                    collection_name=COLLECTION_NAME,
                    document_id=doc_id,
                    content=edu.to_searchable_text(),
                    metadata={
                        "type": "education",
                        "institution": edu.institution,
                        "degree": edu.degree,
                        "field": edu.field,
                        "profile_hash": self._profile_hash or "",
                    },
                )
                documents_indexed += 1

            # Index certifications
            for i, cert in enumerate(profile.certifications):
                doc_id = f"cert_{self._profile_hash}_{i}"
                await self._vector_store.add(
                    collection_name=COLLECTION_NAME,
                    document_id=doc_id,
                    content=cert.to_searchable_text(),
                    metadata={
                        "type": "certification",
                        "name": cert.name,
                        "issuer": cert.issuer,
                        "profile_hash": self._profile_hash or "",
                    },
                )
                documents_indexed += 1

            self._indexed = True
            logger.info(f"Indexed {documents_indexed} documents from profile")

            return documents_indexed

        except Exception as e:
            raise IndexingError(f"Failed to index profile: {e}") from e

    async def clear_index(self) -> int:
        """
        Clear all indexed profile data from vector store.

        Returns:
            Number of documents cleared.
        """
        try:
            count = await self._vector_store.clear_collection(COLLECTION_NAME)
            self._indexed = False
            logger.info(f"Cleared {count} documents from index")
            return count
        except Exception as e:
            logger.error(f"Failed to clear index: {e}")
            return 0

    # =========================================================================
    # SEARCH OPERATIONS
    # =========================================================================

    async def search_experiences(
        self,
        query: str,
        n_results: int = 5,
    ) -> list[SearchMatch]:
        """
        Search for relevant experiences.

        Args:
            query: Search query (e.g., "Python development").
            n_results: Maximum number of results.

        Returns:
            List of SearchMatch objects sorted by relevance.

        Raises:
            SearchError: If search fails.
        """
        return await self._search_by_type(query, "experience", n_results)

    async def search_skills(
        self,
        query: str,
        n_results: int = 5,
    ) -> list[SearchMatch]:
        """
        Search for relevant skills.

        Expands the query to include skill aliases for better matching
        (e.g., "k8s" will also match "kubernetes").

        Args:
            query: Search query (e.g., "machine learning", "k8s").
            n_results: Maximum number of results.

        Returns:
            List of SearchMatch objects sorted by relevance.

        Raises:
            SearchError: If search fails.
        """
        # Expand query to include aliases for better matching
        expanded_terms = expand_skill_query(query)

        # Create enhanced query with all variants
        if len(expanded_terms) > 1:
            enhanced_query = f"{query} ({', '.join(expanded_terms)})"
        else:
            enhanced_query = query

        return await self._search_by_type(enhanced_query, "skill", n_results)

    async def search_education(
        self,
        query: str,
        n_results: int = 5,
    ) -> list[SearchMatch]:
        """
        Search for relevant education.

        Args:
            query: Search query (e.g., "computer science").
            n_results: Maximum number of results.

        Returns:
            List of SearchMatch objects sorted by relevance.

        Raises:
            SearchError: If search fails.
        """
        return await self._search_by_type(query, "education", n_results)

    async def search_certifications(
        self,
        query: str,
        n_results: int = 5,
    ) -> list[SearchMatch]:
        """
        Search for relevant certifications.

        Args:
            query: Search query (e.g., "AWS").
            n_results: Maximum number of results.

        Returns:
            List of SearchMatch objects sorted by relevance.

        Raises:
            SearchError: If search fails.
        """
        return await self._search_by_type(query, "certification", n_results)

    async def search_all(
        self,
        query: str,
        n_results: int = 10,
    ) -> list[SearchMatch]:
        """
        Search all profile content.

        Args:
            query: Search query.
            n_results: Maximum number of results.

        Returns:
            List of SearchMatch objects sorted by relevance.

        Raises:
            SearchError: If search fails.
        """
        try:
            response = await self._vector_store.search(
                collection_name=COLLECTION_NAME,
                query=query,
                top_k=n_results,
            )

            return [
                SearchMatch(
                    id=result.id,
                    content=result.content,
                    match_type=str(result.metadata.get("type", "unknown")),
                    score=result.score,
                    metadata=self._convert_metadata(result.metadata),
                )
                for result in response.results
            ]

        except Exception as e:
            raise SearchError(f"Search failed: {e}") from e

    async def match_requirements(
        self,
        requirements: list[str],
        threshold: float = 0.5,
    ) -> list[SkillMatch]:
        """
        Match job requirements against user skills.

        Expands requirements to include skill aliases for better matching
        (e.g., "k8s" will also match "kubernetes").

        Args:
            requirements: List of skill requirements to match.
            threshold: Minimum similarity score (0-1).

        Returns:
            List of SkillMatch objects with matched skills for each requirement.

        Raises:
            SearchError: If matching fails.
        """
        matches: list[SkillMatch] = []

        for requirement in requirements:
            try:
                # Expand requirement to include aliases
                expanded_terms = expand_skill_query(requirement)
                if len(expanded_terms) > 1:
                    enhanced_query = f"{requirement} ({', '.join(expanded_terms)})"
                else:
                    enhanced_query = requirement

                # Search skills for this requirement
                response = await self._vector_store.search(
                    collection_name=COLLECTION_NAME,
                    query=enhanced_query,
                    top_k=3,
                    metadata_filter={"type": "skill"},
                )

                # Filter by threshold
                matched_skills = [
                    SearchMatch(
                        id=result.id,
                        content=result.content,
                        match_type="skill",
                        score=result.score,
                        metadata=self._convert_metadata(result.metadata),
                    )
                    for result in response.results
                    if result.score >= threshold
                ]

                matches.append(SkillMatch(
                    requirement=requirement,
                    matched_skills=matched_skills,
                ))

            except Exception as e:
                logger.warning(f"Failed to match requirement '{requirement}': {e}")
                matches.append(SkillMatch(requirement=requirement, matched_skills=[]))

        return matches

    async def _search_by_type(
        self,
        query: str,
        content_type: str,
        n_results: int,
    ) -> list[SearchMatch]:
        """
        Search for content of a specific type.

        Args:
            query: Search query.
            content_type: Type to filter by (skill, experience, education, certification).
            n_results: Maximum number of results.

        Returns:
            List of SearchMatch objects.
        """
        try:
            response = await self._vector_store.search(
                collection_name=COLLECTION_NAME,
                query=query,
                top_k=n_results,
                metadata_filter={"type": content_type},
            )

            return [
                SearchMatch(
                    id=result.id,
                    content=result.content,
                    match_type=content_type,
                    score=result.score,
                    metadata=self._convert_metadata(result.metadata),
                )
                for result in response.results
            ]

        except Exception as e:
            raise SearchError(f"Search failed: {e}") from e

    def _convert_metadata(
        self,
        metadata: dict[str, Any],
    ) -> dict[str, str | float | int | bool | None]:
        """Convert metadata to compatible types."""
        result: dict[str, str | float | int | bool | None] = {}
        for key, value in metadata.items():
            if isinstance(value, (str, float, int, bool)) or value is None:
                result[key] = value
            else:
                result[key] = str(value)
        return result

    # =========================================================================
    # PROFILE UPDATES
    # =========================================================================

    async def save_profile(self, path: Path | None = None) -> None:
        """
        Save the current profile to YAML file.

        Args:
            path: Optional path override.

        Raises:
            CollectorError: If no profile is loaded.
            ProfileLoadError: If save fails.
        """
        profile = self.get_profile()
        save_path = path or self._profile_path

        # Update timestamp
        profile.last_updated = datetime.now()

        try:
            profile_dict = profile.model_dump(mode="json")
            with open(save_path, "w") as f:
                yaml.dump(profile_dict, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Saved profile to {save_path}")

        except Exception as e:
            raise ProfileLoadError(f"Failed to save profile: {e}") from e

    async def update_and_reindex(self) -> int:
        """
        Reload profile and re-index if changed.

        Returns:
            Number of documents indexed (0 if unchanged).

        Raises:
            Various profile/indexing errors.
        """
        old_hash = self._profile_hash
        await self.load_profile()

        if self._profile_hash != old_hash:
            await self.clear_index()
            return await self.index_profile()

        return 0


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

_collector_instance: Collector | None = None


async def get_collector() -> Collector:
    """
    Get the Collector module instance.

    Creates and initializes singleton on first call.
    Use as FastAPI dependency.

    Returns:
        Initialized Collector instance.
    """
    from src.services.vector_store import get_vector_store_service

    global _collector_instance

    if _collector_instance is None:
        vector_store = await get_vector_store_service()
        _collector_instance = Collector(vector_store)
        await _collector_instance.initialize()

    return _collector_instance


async def shutdown_collector() -> None:
    """Shutdown the global Collector instance."""
    global _collector_instance

    if _collector_instance is not None:
        await _collector_instance.shutdown()
        _collector_instance = None


def reset_collector() -> None:
    """Reset the global instance (for testing)."""
    global _collector_instance
    _collector_instance = None
