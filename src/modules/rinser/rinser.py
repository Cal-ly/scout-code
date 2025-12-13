"""
M2 Rinser Module

Processes raw job postings into structured, searchable data.

Usage:
    from src.modules.rinser import Rinser, get_rinser

    # Singleton access (for FastAPI)
    rinser = await get_rinser()

    # Process a job posting
    job = await rinser.process_job(raw_text)
    print(job.title)
    print(job.requirements)
"""

import logging
import re
import time
from typing import Any

import bleach

from src.modules.rinser.exceptions import (
    ExtractionError,
    IndexingError,
    RinserError,
    SanitizationError,
)
from src.modules.rinser.models import (
    CompanyInfo,
    JobInput,
    ProcessedJob,
    ProcessingResult,
    Requirement,
    RequirementCategory,
    RequirementPriority,
    Responsibility,
)
from src.modules.rinser.prompts import JOB_EXTRACTION_PROMPT, SYSTEM_PROMPT
from src.services.llm_service import LLMService
from src.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

# PoC collection name for job requirements
COLLECTION_NAME = "job_requirements"

# Minimum text length for processing
MIN_TEXT_LENGTH = 100


class Rinser:
    """
    Rinser Module - processes raw job postings.

    Responsibilities:
    - Sanitize raw text (remove HTML, scripts)
    - Extract structured data via LLM
    - Index in Vector Store for matching

    Attributes:
        llm: LLM Service for extraction.
        vector_store: Vector Store for indexing.

    Example:
        >>> rinser = Rinser(llm_service, vector_store)
        >>> await rinser.initialize()
        >>> job = await rinser.process_job('''
        ...     Senior Python Developer
        ...     Requirements:
        ...     - 5+ years Python experience
        ...     - AWS knowledge preferred
        ... ''')
        >>> print(job.title)
        "Senior Python Developer"
    """

    # Tags allowed after sanitization (none for text extraction)
    ALLOWED_TAGS: list[str] = []
    ALLOWED_ATTRIBUTES: dict[str, list[str]] = {}

    def __init__(
        self,
        llm_service: LLMService,
        vector_store: VectorStoreService,
    ):
        """
        Initialize Rinser.

        Args:
            llm_service: LLM Service for extraction.
            vector_store: Vector Store for indexing.
        """
        self._llm = llm_service
        self._vector_store = vector_store
        self._initialized = False

        # Stats
        self._total_jobs_processed = 0
        self._total_requirements_indexed = 0

    async def initialize(self) -> None:
        """
        Initialize the Rinser module.

        Verifies dependencies are ready.

        Raises:
            RinserError: If initialization fails.
        """
        if self._initialized:
            logger.warning("Rinser already initialized")
            return

        # Verify vector store is available
        health = await self._vector_store.health_check()
        if health.status != "healthy":
            raise RinserError(f"Vector store not healthy: {health.status}")

        # Verify LLM service is available
        llm_health = await self._llm.health_check()
        if llm_health.status not in ("healthy", "degraded"):
            raise RinserError(f"LLM service not available: {llm_health.status}")

        self._initialized = True
        logger.info("Rinser module initialized")

    async def shutdown(self) -> None:
        """Gracefully shutdown the Rinser module."""
        if not self._initialized:
            return

        self._initialized = False
        logger.info("Rinser module shutdown complete")

    # =========================================================================
    # TEXT SANITIZATION
    # =========================================================================

    def sanitize_text(self, raw_text: str) -> str:
        """
        Sanitize raw job posting text.

        Removes HTML tags, scripts, and normalizes whitespace.

        Args:
            raw_text: Raw input text (may contain HTML).

        Returns:
            Cleaned plain text.

        Raises:
            SanitizationError: If input is empty or sanitization produces no content.
        """
        # Validate input
        if not raw_text or not raw_text.strip():
            raise SanitizationError("Input text is empty or contains only whitespace")

        # Remove script/style content BEFORE bleach (which only strips tags)
        text = re.sub(
            r"<script[^>]*>.*?</script>", "", raw_text, flags=re.DOTALL | re.IGNORECASE
        )
        text = re.sub(
            r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE
        )

        # Remove HTML tags
        text = bleach.clean(
            text,
            tags=self.ALLOWED_TAGS,
            attributes=self.ALLOWED_ATTRIBUTES,
            strip=True,
        )

        # Normalize whitespace
        text = re.sub(r"[ \t]+", " ", text)  # Collapse horizontal whitespace
        text = re.sub(r"\n\s*\n+", "\n\n", text)  # Collapse vertical whitespace

        # Clean up common HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")

        result = text.strip()

        # Validate output - ensure we have meaningful content
        if not result or len(result) < 50:
            raise SanitizationError(
                f"Sanitization produced insufficient content ({len(result)} chars). "
                "Input may be mostly HTML/scripts with no readable text."
            )

        return result

    # =========================================================================
    # LLM EXTRACTION
    # =========================================================================

    async def _extract_structure(self, clean_text: str) -> dict[str, Any]:
        """
        Extract structured data from job text using LLM.

        Args:
            clean_text: Sanitized job posting text.

        Returns:
            Dictionary with extracted job data.

        Raises:
            ExtractionError: If extraction fails.
        """
        prompt = JOB_EXTRACTION_PROMPT.format(raw_text=clean_text)

        try:
            result = await self._llm.generate_json(
                prompt=prompt,
                system=SYSTEM_PROMPT,
                module="rinser",
                purpose="extract_job_structure",
            )

            logger.debug(f"Extracted structure: {list(result.keys())}")
            return result

        except Exception as e:
            raise ExtractionError(f"Failed to extract job structure: {e}") from e

    def _parse_requirements(self, data: list[dict[str, Any]] | None) -> list[Requirement]:
        """Parse requirement dictionaries into Requirement objects."""
        requirements: list[Requirement] = []
        for item in data or []:
            try:
                # Handle priority
                priority_str = item.get("priority", "nice_to_have")
                try:
                    priority = RequirementPriority(priority_str)
                except ValueError:
                    priority = RequirementPriority.NICE_TO_HAVE

                # Handle category
                category_str = item.get("category", "other")
                try:
                    category = RequirementCategory(category_str)
                except ValueError:
                    category = RequirementCategory.OTHER

                req = Requirement(
                    text=item.get("text", ""),
                    priority=priority,
                    category=category,
                    years_required=item.get("years_required"),
                )
                if req.text:  # Only add if text is not empty
                    requirements.append(req)
            except Exception as e:
                logger.warning(f"Failed to parse requirement: {e}")
                continue

        return requirements

    def _parse_responsibilities(
        self, data: list[dict[str, Any]] | None
    ) -> list[Responsibility]:
        """Parse responsibility dictionaries into Responsibility objects."""
        responsibilities: list[Responsibility] = []
        for item in data or []:
            try:
                category_str = item.get("category", "other")
                try:
                    category = RequirementCategory(category_str)
                except ValueError:
                    category = RequirementCategory.OTHER

                resp = Responsibility(
                    text=item.get("text", ""),
                    category=category,
                )
                if resp.text:  # Only add if text is not empty
                    responsibilities.append(resp)
            except Exception as e:
                logger.warning(f"Failed to parse responsibility: {e}")
                continue

        return responsibilities

    def _parse_company(self, data: dict[str, Any] | None) -> CompanyInfo:
        """Parse company info from extracted data."""
        if data is None:
            data = {}
        return CompanyInfo(
            name=data.get("name", "Unknown Company"),
            industry=data.get("industry"),
            size=data.get("size"),
            culture_notes=data.get("culture_notes"),
        )

    # =========================================================================
    # VECTOR INDEXING
    # =========================================================================

    async def _index_job(self, job: ProcessedJob) -> int:
        """
        Index job requirements in Vector Store.

        Args:
            job: Processed job to index.

        Returns:
            Number of entries indexed.

        Raises:
            IndexingError: If indexing fails.
        """
        indexed_count = 0

        try:
            # Index requirements
            for i, req in enumerate(job.requirements):
                doc_id = f"job_{job.id}_req_{i}"
                await self._vector_store.add(
                    collection_name=COLLECTION_NAME,
                    document_id=doc_id,
                    content=req.to_searchable_text(),
                    metadata={
                        "type": "requirement",
                        "job_id": job.id,
                        "job_title": job.title,
                        "priority": req.priority.value,
                        "category": req.category.value,
                        "years_required": req.years_required or 0,
                    },
                )
                indexed_count += 1

            # Index responsibilities
            for i, resp in enumerate(job.responsibilities):
                doc_id = f"job_{job.id}_resp_{i}"
                await self._vector_store.add(
                    collection_name=COLLECTION_NAME,
                    document_id=doc_id,
                    content=resp.to_searchable_text(),
                    metadata={
                        "type": "responsibility",
                        "job_id": job.id,
                        "job_title": job.title,
                        "category": resp.category.value,
                    },
                )
                indexed_count += 1

            logger.info(f"Indexed {indexed_count} entries for job {job.id}")
            self._total_requirements_indexed += indexed_count

            return indexed_count

        except Exception as e:
            raise IndexingError(f"Failed to index job: {e}") from e

    # =========================================================================
    # MAIN PROCESSING
    # =========================================================================

    async def process_job(
        self,
        raw_text: str,
        source: str | None = None,
        index: bool = True,
    ) -> ProcessedJob:
        """
        Process a raw job posting.

        Main entry point for the Rinser module.

        Args:
            raw_text: Raw job posting text.
            source: Optional source identifier.
            index: Whether to index in Vector Store.

        Returns:
            ProcessedJob with extracted structure.

        Raises:
            RinserError: If processing fails.

        Example:
            >>> job = await rinser.process_job('''
            ...     Software Engineer at TechCorp
            ...
            ...     Requirements:
            ...     - 3+ years Python
            ...     - AWS experience preferred
            ...
            ...     Responsibilities:
            ...     - Build APIs
            ...     - Code review
            ... ''')
        """
        if len(raw_text) < MIN_TEXT_LENGTH:
            raise RinserError(
                f"Job posting too short (minimum {MIN_TEXT_LENGTH} characters)"
            )

        logger.info(f"Processing job posting ({len(raw_text)} chars)")

        # Step 1: Sanitize
        clean_text = self.sanitize_text(raw_text)
        logger.debug(f"Sanitized text: {len(clean_text)} chars")

        # Step 2: Extract structure via LLM
        extracted = await self._extract_structure(clean_text)

        # Step 3: Parse into models
        requirements = self._parse_requirements(extracted.get("requirements"))
        responsibilities = self._parse_responsibilities(extracted.get("responsibilities"))
        company = self._parse_company(extracted.get("company"))

        if not requirements:
            raise ExtractionError("No requirements could be extracted from job posting")

        # Step 4: Build ProcessedJob
        job = ProcessedJob(
            title=extracted.get("title", "Unknown Position"),
            company=company,
            location=extracted.get("location"),
            employment_type=extracted.get("employment_type"),
            salary_range=extracted.get("salary_range"),
            requirements=requirements,
            responsibilities=responsibilities,
            benefits=extracted.get("benefits", []),
            raw_text=raw_text,
            summary=extracted.get("summary"),
        )

        logger.info(
            f"Processed job: {job.title} at {job.company.name} - "
            f"{len(requirements)} requirements, {len(responsibilities)} responsibilities"
        )

        # Step 5: Index in Vector Store
        if index:
            index_count = await self._index_job(job)
            job.indexed = True
            job.index_count = index_count

        self._total_jobs_processed += 1

        return job

    async def process_job_input(
        self,
        job_input: JobInput,
        index: bool = True,
    ) -> ProcessedJob:
        """
        Process a JobInput model.

        Args:
            job_input: JobInput with raw text.
            index: Whether to index in Vector Store.

        Returns:
            ProcessedJob.
        """
        return await self.process_job(
            raw_text=job_input.raw_text,
            source=job_input.source,
            index=index,
        )

    async def process_job_safe(
        self,
        raw_text: str,
        source: str | None = None,
        index: bool = True,
    ) -> ProcessingResult:
        """
        Process a job posting with error handling.

        Returns a ProcessingResult instead of raising exceptions.

        Args:
            raw_text: Raw job posting text.
            source: Optional source identifier.
            index: Whether to index in Vector Store.

        Returns:
            ProcessingResult with success status.
        """
        start_time = time.time()

        try:
            job = await self.process_job(raw_text, source, index)
            processing_time = int((time.time() - start_time) * 1000)

            return ProcessingResult(
                success=True,
                job=job,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"Job processing failed: {e}")

            return ProcessingResult(
                success=False,
                error=str(e),
                processing_time_ms=processing_time,
            )

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> dict[str, int]:
        """Get processing statistics."""
        return {
            "total_jobs_processed": self._total_jobs_processed,
            "total_requirements_indexed": self._total_requirements_indexed,
        }


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

_rinser_instance: Rinser | None = None


async def get_rinser() -> Rinser:
    """
    Get the Rinser module instance.

    Creates and initializes singleton on first call.
    Use as FastAPI dependency.

    Returns:
        Initialized Rinser instance.
    """
    from src.services.llm_service import get_llm_service
    from src.services.vector_store import get_vector_store_service

    global _rinser_instance

    if _rinser_instance is None:
        llm_service = await get_llm_service()
        vector_store = await get_vector_store_service()

        _rinser_instance = Rinser(llm_service, vector_store)
        await _rinser_instance.initialize()

    return _rinser_instance


async def shutdown_rinser() -> None:
    """Shutdown the global Rinser instance."""
    global _rinser_instance

    if _rinser_instance is not None:
        await _rinser_instance.shutdown()
        _rinser_instance = None


def reset_rinser() -> None:
    """Reset the global instance (for testing)."""
    global _rinser_instance
    _rinser_instance = None
