"""
Tests for M2 Rinser Module.

Run with: pytest tests/test_rinser.py -v
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.modules.rinser import (
    Rinser,
    RinserError,
    ExtractionError,
    IndexingError,
    ProcessedJob,
    Requirement,
    RequirementPriority,
    RequirementCategory,
    Responsibility,
    CompanyInfo,
    JobInput,
    ProcessingResult,
    get_rinser,
    reset_rinser,
    shutdown_rinser,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_job_text() -> str:
    """Sample job posting for testing."""
    return """
    Senior Python Developer
    TechCorp Inc - San Francisco, CA

    About Us:
    TechCorp is a leading technology company specializing in cloud solutions.

    Requirements:
    - 5+ years of Python experience (required)
    - Strong knowledge of FastAPI or Django
    - AWS experience preferred
    - Bachelor's degree in Computer Science or related field

    Responsibilities:
    - Design and implement REST APIs
    - Mentor junior developers
    - Participate in code reviews

    Benefits:
    - Competitive salary ($150,000 - $200,000)
    - Health insurance
    - Remote work options
    """


@pytest.fixture
def sample_extracted_data() -> dict:
    """Sample LLM extraction result."""
    return {
        "title": "Senior Python Developer",
        "company": {
            "name": "TechCorp Inc",
            "industry": "Technology",
            "size": None,
            "culture_notes": "Leading technology company",
        },
        "location": "San Francisco, CA",
        "employment_type": "Full-time",
        "salary_range": "$150,000 - $200,000",
        "requirements": [
            {
                "text": "5+ years of Python experience",
                "priority": "must_have",
                "category": "technical",
                "years_required": 5,
            },
            {
                "text": "Strong knowledge of FastAPI or Django",
                "priority": "must_have",
                "category": "technical",
                "years_required": None,
            },
            {
                "text": "AWS experience preferred",
                "priority": "nice_to_have",
                "category": "technical",
                "years_required": None,
            },
            {
                "text": "Bachelor's degree in Computer Science",
                "priority": "nice_to_have",
                "category": "education",
                "years_required": None,
            },
        ],
        "responsibilities": [
            {"text": "Design and implement REST APIs", "category": "technical"},
            {"text": "Mentor junior developers", "category": "soft_skill"},
            {"text": "Participate in code reviews", "category": "technical"},
        ],
        "benefits": ["Health insurance", "Remote work options"],
        "summary": "Senior Python Developer role at TechCorp",
    }


@pytest.fixture
def mock_llm_service(sample_extracted_data: dict) -> AsyncMock:
    """Create mock LLM Service."""
    llm = AsyncMock()
    llm.generate_json.return_value = sample_extracted_data
    llm.health_check.return_value = Mock(status="healthy")
    return llm


@pytest.fixture
def mock_vector_store() -> AsyncMock:
    """Create mock Vector Store."""
    store = AsyncMock()
    store.add.return_value = Mock(id="test_id")
    store.health_check.return_value = Mock(status="healthy")
    return store


@pytest.fixture
def rinser(mock_llm_service: AsyncMock, mock_vector_store: AsyncMock) -> Rinser:
    """Create Rinser for testing (not initialized)."""
    return Rinser(mock_llm_service, mock_vector_store)


@pytest.fixture
async def initialized_rinser(
    mock_llm_service: AsyncMock, mock_vector_store: AsyncMock
) -> Rinser:
    """Create initialized Rinser for testing."""
    rinser = Rinser(mock_llm_service, mock_vector_store)
    await rinser.initialize()
    return rinser


# =============================================================================
# MODEL TESTS
# =============================================================================


class TestRequirementModel:
    """Tests for Requirement model."""

    def test_create_requirement(self) -> None:
        """Should create requirement with defaults."""
        req = Requirement(text="Python experience")

        assert req.text == "Python experience"
        assert req.priority == RequirementPriority.NICE_TO_HAVE
        assert req.category == RequirementCategory.OTHER
        assert req.years_required is None

    def test_create_requirement_with_all_fields(self) -> None:
        """Should create requirement with all fields."""
        req = Requirement(
            text="5+ years Python",
            priority=RequirementPriority.MUST_HAVE,
            category=RequirementCategory.TECHNICAL,
            years_required=5,
        )

        assert req.text == "5+ years Python"
        assert req.priority == RequirementPriority.MUST_HAVE
        assert req.category == RequirementCategory.TECHNICAL
        assert req.years_required == 5

    def test_to_searchable_text(self) -> None:
        """Should generate searchable text."""
        req = Requirement(
            text="Python experience",
            years_required=5,
        )

        searchable = req.to_searchable_text()

        assert "Python experience" in searchable
        assert "5 years" in searchable

    def test_to_searchable_text_no_years(self) -> None:
        """Should handle no years in searchable text."""
        req = Requirement(text="Python experience")

        searchable = req.to_searchable_text()

        assert searchable == "Python experience"


class TestResponsibilityModel:
    """Tests for Responsibility model."""

    def test_create_responsibility(self) -> None:
        """Should create responsibility."""
        resp = Responsibility(text="Build APIs")

        assert resp.text == "Build APIs"
        assert resp.category == RequirementCategory.OTHER

    def test_to_searchable_text(self) -> None:
        """Should return text as searchable."""
        resp = Responsibility(text="Build APIs")

        assert resp.to_searchable_text() == "Build APIs"


class TestCompanyInfoModel:
    """Tests for CompanyInfo model."""

    def test_create_company_info(self) -> None:
        """Should create company info."""
        company = CompanyInfo(
            name="TechCorp",
            industry="Technology",
            size="50-200",
            culture_notes="Fast-paced",
        )

        assert company.name == "TechCorp"
        assert company.industry == "Technology"
        assert company.size == "50-200"
        assert company.culture_notes == "Fast-paced"

    def test_create_company_info_minimal(self) -> None:
        """Should create with just name."""
        company = CompanyInfo(name="TechCorp")

        assert company.name == "TechCorp"
        assert company.industry is None
        assert company.size is None
        assert company.culture_notes is None


class TestProcessedJobModel:
    """Tests for ProcessedJob model."""

    def test_create_processed_job(self) -> None:
        """Should create processed job."""
        job = ProcessedJob(
            title="Developer",
            company=CompanyInfo(name="TechCorp"),
            requirements=[Requirement(text="Python")],
            raw_text="Test job posting text...",
        )

        assert job.title == "Developer"
        assert job.company.name == "TechCorp"
        assert len(job.requirements) == 1
        assert job.id is not None

    def test_processed_job_requires_requirements(self) -> None:
        """Should require at least one requirement."""
        with pytest.raises(ValueError, match="at least one requirement"):
            ProcessedJob(
                title="Developer",
                company=CompanyInfo(name="TechCorp"),
                requirements=[],
                raw_text="Test job posting text...",
            )

    def test_get_must_have_requirements(self) -> None:
        """Should filter must-have requirements."""
        job = ProcessedJob(
            title="Developer",
            company=CompanyInfo(name="TechCorp"),
            requirements=[
                Requirement(text="Python", priority=RequirementPriority.MUST_HAVE),
                Requirement(text="AWS", priority=RequirementPriority.NICE_TO_HAVE),
                Requirement(text="Docker", priority=RequirementPriority.MUST_HAVE),
            ],
            raw_text="Test job posting text...",
        )

        must_haves = job.get_must_have_requirements()

        assert len(must_haves) == 2
        assert all(r.priority == RequirementPriority.MUST_HAVE for r in must_haves)

    def test_get_nice_to_have_requirements(self) -> None:
        """Should filter nice-to-have requirements."""
        job = ProcessedJob(
            title="Developer",
            company=CompanyInfo(name="TechCorp"),
            requirements=[
                Requirement(text="Python", priority=RequirementPriority.MUST_HAVE),
                Requirement(text="AWS", priority=RequirementPriority.NICE_TO_HAVE),
            ],
            raw_text="Test job posting text...",
        )

        nice_to_haves = job.get_nice_to_have_requirements()

        assert len(nice_to_haves) == 1
        assert nice_to_haves[0].text == "AWS"

    def test_get_technical_requirements(self) -> None:
        """Should filter technical requirements."""
        job = ProcessedJob(
            title="Developer",
            company=CompanyInfo(name="TechCorp"),
            requirements=[
                Requirement(text="Python", category=RequirementCategory.TECHNICAL),
                Requirement(text="3 years", category=RequirementCategory.EXPERIENCE),
                Requirement(text="FastAPI", category=RequirementCategory.TECHNICAL),
            ],
            raw_text="Test job posting text...",
        )

        technical = job.get_technical_requirements()

        assert len(technical) == 2
        assert all(r.category == RequirementCategory.TECHNICAL for r in technical)

    def test_get_experience_requirements(self) -> None:
        """Should filter experience requirements."""
        job = ProcessedJob(
            title="Developer",
            company=CompanyInfo(name="TechCorp"),
            requirements=[
                Requirement(text="Python", category=RequirementCategory.TECHNICAL),
                Requirement(text="3 years", category=RequirementCategory.EXPERIENCE),
            ],
            raw_text="Test job posting text...",
        )

        experience = job.get_experience_requirements()

        assert len(experience) == 1
        assert experience[0].text == "3 years"

    def test_get_requirements_by_category(self) -> None:
        """Should filter by any category."""
        job = ProcessedJob(
            title="Developer",
            company=CompanyInfo(name="TechCorp"),
            requirements=[
                Requirement(text="BS in CS", category=RequirementCategory.EDUCATION),
                Requirement(text="Python", category=RequirementCategory.TECHNICAL),
            ],
            raw_text="Test job posting text...",
        )

        education = job.get_requirements_by_category(RequirementCategory.EDUCATION)

        assert len(education) == 1
        assert education[0].text == "BS in CS"


class TestJobInputModel:
    """Tests for JobInput model."""

    def test_create_job_input(self) -> None:
        """Should create job input."""
        job_input = JobInput(
            raw_text="A" * 150,
            source="linkedin",
            url="https://example.com/job",
        )

        assert len(job_input.raw_text) == 150
        assert job_input.source == "linkedin"
        assert job_input.url == "https://example.com/job"

    def test_job_input_requires_min_length(self) -> None:
        """Should require minimum text length."""
        with pytest.raises(ValueError):
            JobInput(raw_text="Too short")


class TestProcessingResultModel:
    """Tests for ProcessingResult model."""

    def test_create_success_result(self) -> None:
        """Should create success result."""
        job = ProcessedJob(
            title="Developer",
            company=CompanyInfo(name="TechCorp"),
            requirements=[Requirement(text="Python")],
            raw_text="Test job posting text...",
        )

        result = ProcessingResult(
            success=True,
            job=job,
            processing_time_ms=500,
        )

        assert result.success is True
        assert result.job is not None
        assert result.error is None
        assert result.processing_time_ms == 500

    def test_create_failure_result(self) -> None:
        """Should create failure result."""
        result = ProcessingResult(
            success=False,
            error="Extraction failed",
            processing_time_ms=100,
        )

        assert result.success is False
        assert result.job is None
        assert result.error == "Extraction failed"


# =============================================================================
# SANITIZATION TESTS
# =============================================================================


class TestSanitization:
    """Tests for text sanitization."""

    def test_sanitize_removes_html(self, rinser: Rinser) -> None:
        """Should remove HTML tags."""
        text = "<div><p>Job <b>Title</b></p></div>"

        result = rinser.sanitize_text(text)

        assert "<" not in result
        assert ">" not in result
        assert "Job Title" in result

    def test_sanitize_removes_scripts(self, rinser: Rinser) -> None:
        """Should remove script tags and content."""
        text = "Job Title<script>alert('xss')</script>End"

        result = rinser.sanitize_text(text)

        assert "<script>" not in result
        assert "alert" not in result
        assert "xss" not in result
        assert "Job Title" in result
        assert "End" in result

    def test_sanitize_removes_styles(self, rinser: Rinser) -> None:
        """Should remove style tags."""
        text = "Job Title<style>body{color:red}</style>Description"

        result = rinser.sanitize_text(text)

        assert "style" not in result.lower()
        assert "color:red" not in result

    def test_sanitize_normalizes_whitespace(self, rinser: Rinser) -> None:
        """Should normalize excessive whitespace."""
        text = "Job    Title\n\n\n\nDescription"

        result = rinser.sanitize_text(text)

        assert "    " not in result

    def test_sanitize_handles_html_entities(self, rinser: Rinser) -> None:
        """Should convert HTML entities."""
        text = "Python &amp; Django &lt;test&gt;"

        result = rinser.sanitize_text(text)

        assert "Python & Django" in result
        assert "<test>" in result

    def test_sanitize_handles_nbsp(self, rinser: Rinser) -> None:
        """Should convert &nbsp; to space."""
        text = "Python&nbsp;Developer"

        result = rinser.sanitize_text(text)

        assert "Python Developer" in result

    def test_sanitize_handles_quotes(self, rinser: Rinser) -> None:
        """Should convert quote entities."""
        text = "Use &quot;Python&quot; and &#39;Django&#39;"

        result = rinser.sanitize_text(text)

        assert '"Python"' in result
        assert "'Django'" in result

    def test_sanitize_strips_whitespace(self, rinser: Rinser) -> None:
        """Should strip leading/trailing whitespace."""
        text = "   Job Title   "

        result = rinser.sanitize_text(text)

        assert result == "Job Title"

    def test_sanitize_preserves_newlines(self, rinser: Rinser) -> None:
        """Should preserve reasonable newlines."""
        text = "Title\n\nDescription\n\nRequirements"

        result = rinser.sanitize_text(text)

        assert "\n" in result


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


class TestInitialization:
    """Tests for Rinser initialization."""

    @pytest.mark.asyncio
    async def test_initialize_success(self, rinser: Rinser) -> None:
        """Should initialize successfully."""
        await rinser.initialize()

        # Should not raise

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, rinser: Rinser) -> None:
        """Should handle multiple initialize calls."""
        await rinser.initialize()
        await rinser.initialize()  # Should not raise

    @pytest.mark.asyncio
    async def test_initialize_fails_unhealthy_vector_store(
        self, mock_llm_service: AsyncMock
    ) -> None:
        """Should fail if vector store unhealthy."""
        mock_vs = AsyncMock()
        mock_vs.health_check.return_value = Mock(status="unavailable")

        rinser = Rinser(mock_llm_service, mock_vs)

        with pytest.raises(RinserError, match="not healthy"):
            await rinser.initialize()

    @pytest.mark.asyncio
    async def test_initialize_fails_unhealthy_llm(
        self, mock_vector_store: AsyncMock
    ) -> None:
        """Should fail if LLM service unavailable."""
        mock_llm = AsyncMock()
        mock_llm.health_check.return_value = Mock(status="unavailable")

        rinser = Rinser(mock_llm, mock_vector_store)

        with pytest.raises(RinserError, match="not available"):
            await rinser.initialize()

    @pytest.mark.asyncio
    async def test_shutdown(self, initialized_rinser: Rinser) -> None:
        """Should shutdown gracefully."""
        await initialized_rinser.shutdown()

        # Should handle repeated shutdown
        await initialized_rinser.shutdown()


# =============================================================================
# EXTRACTION TESTS
# =============================================================================


class TestExtraction:
    """Tests for LLM extraction."""

    @pytest.mark.asyncio
    async def test_extract_structure_calls_llm(
        self, initialized_rinser: Rinser, mock_llm_service: AsyncMock
    ) -> None:
        """Should call LLM with correct parameters."""
        await initialized_rinser._extract_structure("Test job posting")

        mock_llm_service.generate_json.assert_called_once()
        call_kwargs = mock_llm_service.generate_json.call_args[1]
        assert call_kwargs["module"] == "rinser"
        assert call_kwargs["purpose"] == "extract_job_structure"

    @pytest.mark.asyncio
    async def test_extract_structure_returns_dict(
        self, initialized_rinser: Rinser, sample_extracted_data: dict
    ) -> None:
        """Should return extracted data as dict."""
        result = await initialized_rinser._extract_structure("Test job posting")

        assert "title" in result
        assert "requirements" in result
        assert "company" in result

    @pytest.mark.asyncio
    async def test_extract_structure_raises_on_llm_error(
        self, initialized_rinser: Rinser, mock_llm_service: AsyncMock
    ) -> None:
        """Should raise ExtractionError on LLM failure."""
        mock_llm_service.generate_json.side_effect = Exception("LLM error")

        with pytest.raises(ExtractionError, match="Failed to extract"):
            await initialized_rinser._extract_structure("Test job posting")


# =============================================================================
# PARSING TESTS
# =============================================================================


class TestParsing:
    """Tests for data parsing."""

    def test_parse_requirements(self, rinser: Rinser) -> None:
        """Should parse requirement dicts into objects."""
        data = [
            {
                "text": "Python required",
                "priority": "must_have",
                "category": "technical",
                "years_required": 3,
            }
        ]

        requirements = rinser._parse_requirements(data)

        assert len(requirements) == 1
        assert requirements[0].text == "Python required"
        assert requirements[0].priority == RequirementPriority.MUST_HAVE
        assert requirements[0].category == RequirementCategory.TECHNICAL
        assert requirements[0].years_required == 3

    def test_parse_requirements_handles_invalid_priority(self, rinser: Rinser) -> None:
        """Should handle invalid priority gracefully."""
        data = [
            {
                "text": "Test requirement",
                "priority": "invalid_priority",
                "category": "technical",
            }
        ]

        requirements = rinser._parse_requirements(data)

        assert len(requirements) == 1
        assert requirements[0].priority == RequirementPriority.NICE_TO_HAVE

    def test_parse_requirements_handles_invalid_category(self, rinser: Rinser) -> None:
        """Should handle invalid category gracefully."""
        data = [
            {
                "text": "Test requirement",
                "priority": "must_have",
                "category": "invalid_category",
            }
        ]

        requirements = rinser._parse_requirements(data)

        assert len(requirements) == 1
        assert requirements[0].category == RequirementCategory.OTHER

    def test_parse_requirements_skips_empty_text(self, rinser: Rinser) -> None:
        """Should skip requirements with empty text."""
        data = [
            {"text": "", "priority": "must_have", "category": "technical"},
            {"text": "Valid requirement", "priority": "must_have", "category": "technical"},
        ]

        requirements = rinser._parse_requirements(data)

        assert len(requirements) == 1
        assert requirements[0].text == "Valid requirement"

    def test_parse_requirements_handles_none(self, rinser: Rinser) -> None:
        """Should handle None input."""
        requirements = rinser._parse_requirements(None)

        assert requirements == []

    def test_parse_responsibilities(self, rinser: Rinser) -> None:
        """Should parse responsibility dicts."""
        data = [{"text": "Build APIs", "category": "technical"}]

        responsibilities = rinser._parse_responsibilities(data)

        assert len(responsibilities) == 1
        assert responsibilities[0].text == "Build APIs"
        assert responsibilities[0].category == RequirementCategory.TECHNICAL

    def test_parse_responsibilities_handles_none(self, rinser: Rinser) -> None:
        """Should handle None input."""
        responsibilities = rinser._parse_responsibilities(None)

        assert responsibilities == []

    def test_parse_company(self, rinser: Rinser) -> None:
        """Should parse company info."""
        data = {
            "name": "TechCorp",
            "industry": "Technology",
            "size": "50-200",
            "culture_notes": "Fast-paced",
        }

        company = rinser._parse_company(data)

        assert company.name == "TechCorp"
        assert company.industry == "Technology"

    def test_parse_company_handles_none(self, rinser: Rinser) -> None:
        """Should handle None input."""
        company = rinser._parse_company(None)

        assert company.name == "Unknown Company"

    def test_parse_company_handles_missing_name(self, rinser: Rinser) -> None:
        """Should use default for missing name."""
        company = rinser._parse_company({})

        assert company.name == "Unknown Company"


# =============================================================================
# INDEXING TESTS
# =============================================================================


class TestIndexing:
    """Tests for vector indexing."""

    @pytest.mark.asyncio
    async def test_index_job_indexes_requirements(
        self, initialized_rinser: Rinser, mock_vector_store: AsyncMock
    ) -> None:
        """Should index all requirements."""
        job = ProcessedJob(
            id="test123",
            title="Developer",
            company=CompanyInfo(name="TechCorp"),
            requirements=[
                Requirement(text="Python"),
                Requirement(text="Django"),
            ],
            responsibilities=[],
            raw_text="Test job posting text...",
        )

        count = await initialized_rinser._index_job(job)

        assert count == 2
        assert mock_vector_store.add.call_count == 2

    @pytest.mark.asyncio
    async def test_index_job_indexes_responsibilities(
        self, initialized_rinser: Rinser, mock_vector_store: AsyncMock
    ) -> None:
        """Should index responsibilities."""
        job = ProcessedJob(
            id="test123",
            title="Developer",
            company=CompanyInfo(name="TechCorp"),
            requirements=[Requirement(text="Python")],
            responsibilities=[
                Responsibility(text="Build APIs"),
                Responsibility(text="Code review"),
            ],
            raw_text="Test job posting text...",
        )

        count = await initialized_rinser._index_job(job)

        assert count == 3  # 1 requirement + 2 responsibilities

    @pytest.mark.asyncio
    async def test_index_job_uses_correct_collection(
        self, initialized_rinser: Rinser, mock_vector_store: AsyncMock
    ) -> None:
        """Should use job_requirements collection."""
        job = ProcessedJob(
            id="test123",
            title="Developer",
            company=CompanyInfo(name="TechCorp"),
            requirements=[Requirement(text="Python")],
            raw_text="Test job posting text...",
        )

        await initialized_rinser._index_job(job)

        call_kwargs = mock_vector_store.add.call_args[1]
        assert call_kwargs["collection_name"] == "job_requirements"

    @pytest.mark.asyncio
    async def test_index_job_includes_metadata(
        self, initialized_rinser: Rinser, mock_vector_store: AsyncMock
    ) -> None:
        """Should include metadata in index."""
        job = ProcessedJob(
            id="test123",
            title="Developer",
            company=CompanyInfo(name="TechCorp"),
            requirements=[
                Requirement(
                    text="Python",
                    priority=RequirementPriority.MUST_HAVE,
                    category=RequirementCategory.TECHNICAL,
                    years_required=5,
                )
            ],
            raw_text="Test job posting text...",
        )

        await initialized_rinser._index_job(job)

        call_kwargs = mock_vector_store.add.call_args[1]
        metadata = call_kwargs["metadata"]
        assert metadata["type"] == "requirement"
        assert metadata["job_id"] == "test123"
        assert metadata["priority"] == "must_have"
        assert metadata["category"] == "technical"
        assert metadata["years_required"] == 5

    @pytest.mark.asyncio
    async def test_index_job_raises_on_error(
        self, initialized_rinser: Rinser, mock_vector_store: AsyncMock
    ) -> None:
        """Should raise IndexingError on failure."""
        mock_vector_store.add.side_effect = Exception("Index error")

        job = ProcessedJob(
            id="test123",
            title="Developer",
            company=CompanyInfo(name="TechCorp"),
            requirements=[Requirement(text="Python")],
            raw_text="Test job posting text...",
        )

        with pytest.raises(IndexingError, match="Failed to index"):
            await initialized_rinser._index_job(job)


# =============================================================================
# PROCESSING TESTS
# =============================================================================


class TestProcessJob:
    """Tests for main processing flow."""

    @pytest.mark.asyncio
    async def test_process_job_success(
        self, initialized_rinser: Rinser, sample_job_text: str
    ) -> None:
        """Should process job posting successfully."""
        job = await initialized_rinser.process_job(sample_job_text)

        assert isinstance(job, ProcessedJob)
        assert job.title == "Senior Python Developer"
        assert job.company.name == "TechCorp Inc"
        assert len(job.requirements) == 4
        assert len(job.responsibilities) == 3

    @pytest.mark.asyncio
    async def test_process_job_indexes(
        self,
        initialized_rinser: Rinser,
        sample_job_text: str,
        mock_vector_store: AsyncMock,
    ) -> None:
        """Should index job in Vector Store."""
        job = await initialized_rinser.process_job(sample_job_text, index=True)

        assert job.indexed is True
        assert job.index_count > 0
        assert mock_vector_store.add.call_count > 0

    @pytest.mark.asyncio
    async def test_process_job_skip_index(
        self,
        initialized_rinser: Rinser,
        sample_job_text: str,
        mock_vector_store: AsyncMock,
    ) -> None:
        """Should skip indexing when disabled."""
        job = await initialized_rinser.process_job(sample_job_text, index=False)

        assert job.indexed is False
        mock_vector_store.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_job_too_short_raises(
        self, initialized_rinser: Rinser
    ) -> None:
        """Should raise for very short text."""
        with pytest.raises(RinserError, match="too short"):
            await initialized_rinser.process_job("Too short")

    @pytest.mark.asyncio
    async def test_process_job_no_requirements_raises(
        self, initialized_rinser: Rinser, mock_llm_service: AsyncMock
    ) -> None:
        """Should raise if no requirements extracted."""
        mock_llm_service.generate_json.return_value = {
            "title": "Test",
            "company": {"name": "Test"},
            "requirements": [],
            "responsibilities": [],
        }

        with pytest.raises(ExtractionError, match="No requirements"):
            await initialized_rinser.process_job("A" * 200)

    @pytest.mark.asyncio
    async def test_process_job_updates_stats(
        self, initialized_rinser: Rinser, sample_job_text: str
    ) -> None:
        """Should update processing stats."""
        initial_stats = initialized_rinser.get_stats()

        await initialized_rinser.process_job(sample_job_text)

        stats = initialized_rinser.get_stats()
        assert stats["total_jobs_processed"] == initial_stats["total_jobs_processed"] + 1

    @pytest.mark.asyncio
    async def test_process_job_input(
        self, initialized_rinser: Rinser, sample_job_text: str
    ) -> None:
        """Should process JobInput model."""
        job_input = JobInput(
            raw_text=sample_job_text,
            source="test",
        )

        job = await initialized_rinser.process_job_input(job_input)

        assert isinstance(job, ProcessedJob)
        assert job.title == "Senior Python Developer"


# =============================================================================
# SAFE PROCESSING TESTS
# =============================================================================


class TestProcessJobSafe:
    """Tests for safe processing with error handling."""

    @pytest.mark.asyncio
    async def test_process_job_safe_success(
        self, initialized_rinser: Rinser, sample_job_text: str
    ) -> None:
        """Should return success result."""
        result = await initialized_rinser.process_job_safe(sample_job_text)

        assert result.success is True
        assert result.job is not None
        assert result.error is None
        assert result.processing_time_ms >= 0  # May be 0 with fast mock execution

    @pytest.mark.asyncio
    async def test_process_job_safe_failure(
        self, initialized_rinser: Rinser
    ) -> None:
        """Should return failure result on error."""
        result = await initialized_rinser.process_job_safe("Too short")

        assert result.success is False
        assert result.job is None
        assert result.error is not None
        assert "too short" in result.error.lower()


# =============================================================================
# PROCESSED JOB FILTER TESTS
# =============================================================================


class TestProcessedJobFilters:
    """Tests for ProcessedJob filter methods."""

    @pytest.mark.asyncio
    async def test_get_must_have_requirements(
        self, initialized_rinser: Rinser, sample_job_text: str
    ) -> None:
        """Should filter must-have requirements."""
        job = await initialized_rinser.process_job(sample_job_text)

        must_haves = job.get_must_have_requirements()

        assert len(must_haves) == 2
        assert all(r.priority == RequirementPriority.MUST_HAVE for r in must_haves)

    @pytest.mark.asyncio
    async def test_get_technical_requirements(
        self, initialized_rinser: Rinser, sample_job_text: str
    ) -> None:
        """Should filter technical requirements."""
        job = await initialized_rinser.process_job(sample_job_text)

        technical = job.get_technical_requirements()

        assert len(technical) == 3
        assert all(r.category == RequirementCategory.TECHNICAL for r in technical)


# =============================================================================
# STATS TESTS
# =============================================================================


class TestStats:
    """Tests for statistics tracking."""

    @pytest.mark.asyncio
    async def test_get_stats(self, initialized_rinser: Rinser) -> None:
        """Should return stats dict."""
        stats = initialized_rinser.get_stats()

        assert "total_jobs_processed" in stats
        assert "total_requirements_indexed" in stats

    @pytest.mark.asyncio
    async def test_stats_increment(
        self, initialized_rinser: Rinser, sample_job_text: str
    ) -> None:
        """Should increment stats on processing."""
        await initialized_rinser.process_job(sample_job_text)

        stats = initialized_rinser.get_stats()

        assert stats["total_jobs_processed"] >= 1
        assert stats["total_requirements_indexed"] >= 1


# =============================================================================
# DEPENDENCY INJECTION TESTS
# =============================================================================


class TestDependencyInjection:
    """Tests for dependency injection functions."""

    @pytest.mark.asyncio
    async def test_get_rinser_creates_singleton(self) -> None:
        """Should create singleton instance."""
        reset_rinser()

        with patch("src.services.llm_service.get_llm_service") as mock_get_llm:
            with patch("src.services.vector_store.get_vector_store_service") as mock_get_vs:
                mock_llm = AsyncMock()
                mock_llm.health_check.return_value = Mock(status="healthy")
                mock_get_llm.return_value = mock_llm

                mock_vs = AsyncMock()
                mock_vs.health_check.return_value = Mock(status="healthy")
                mock_get_vs.return_value = mock_vs

                rinser1 = await get_rinser()
                rinser2 = await get_rinser()

                assert rinser1 is rinser2

        reset_rinser()

    @pytest.mark.asyncio
    async def test_reset_rinser(self) -> None:
        """Should reset singleton instance."""
        reset_rinser()

        with patch("src.services.llm_service.get_llm_service") as mock_get_llm:
            with patch("src.services.vector_store.get_vector_store_service") as mock_get_vs:
                mock_llm = AsyncMock()
                mock_llm.health_check.return_value = Mock(status="healthy")
                mock_get_llm.return_value = mock_llm

                mock_vs = AsyncMock()
                mock_vs.health_check.return_value = Mock(status="healthy")
                mock_get_vs.return_value = mock_vs

                rinser1 = await get_rinser()
                reset_rinser()
                rinser2 = await get_rinser()

                assert rinser1 is not rinser2

        reset_rinser()

    @pytest.mark.asyncio
    async def test_shutdown_rinser(self) -> None:
        """Should shutdown singleton instance."""
        reset_rinser()

        with patch("src.services.llm_service.get_llm_service") as mock_get_llm:
            with patch("src.services.vector_store.get_vector_store_service") as mock_get_vs:
                mock_llm = AsyncMock()
                mock_llm.health_check.return_value = Mock(status="healthy")
                mock_get_llm.return_value = mock_llm

                mock_vs = AsyncMock()
                mock_vs.health_check.return_value = Mock(status="healthy")
                mock_get_vs.return_value = mock_vs

                await get_rinser()
                await shutdown_rinser()

                # Should be able to shutdown again without error
                await shutdown_rinser()

        reset_rinser()


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_process_minimal_valid_job(
        self, initialized_rinser: Rinser, mock_llm_service: AsyncMock
    ) -> None:
        """Should process job with minimal valid data."""
        mock_llm_service.generate_json.return_value = {
            "title": "Developer",
            "company": {"name": "Corp"},
            "requirements": [{"text": "Python", "priority": "must_have", "category": "technical"}],
            "responsibilities": [],
        }

        job = await initialized_rinser.process_job("A" * 150)

        assert job.title == "Developer"
        assert len(job.requirements) == 1

    @pytest.mark.asyncio
    async def test_sanitize_empty_string(self, rinser: Rinser) -> None:
        """Should handle empty string."""
        result = rinser.sanitize_text("")

        assert result == ""

    @pytest.mark.asyncio
    async def test_sanitize_only_html(self, rinser: Rinser) -> None:
        """Should handle text that is only HTML tags."""
        result = rinser.sanitize_text("<div><span></span></div>")

        assert result == ""

    @pytest.mark.asyncio
    async def test_process_with_special_characters(
        self, initialized_rinser: Rinser, mock_llm_service: AsyncMock
    ) -> None:
        """Should handle special characters in text."""
        mock_llm_service.generate_json.return_value = {
            "title": "C++ Developer",
            "company": {"name": "Corp & Co."},
            "requirements": [{"text": "C++", "priority": "must_have", "category": "technical"}],
            "responsibilities": [],
        }

        job = await initialized_rinser.process_job("Special chars: C++ & @#$% " + "A" * 100)

        assert job.title == "C++ Developer"
        assert job.company.name == "Corp & Co."
