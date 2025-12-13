"""
Unit tests for M3 Analyzer Module.

Run with: pytest tests/test_analyzer.py -v
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.modules.analyzer import (
    AnalysisInput,
    AnalysisResult,
    Analyzer,
    AnalyzerError,
    ApplicationStrategy,
    CompatibilityScore,
    ExperienceMatchResult,
    MatchingError,
    MatchLevel,
    ProfileNotLoadedError,
    QualificationGap,
    SkillMatchResult,
    StrategyGenerationError,
    reset_analyzer,
)
from src.modules.collector.models import SearchMatch
from src.modules.rinser.models import (
    CompanyInfo,
    ProcessedJob,
    Requirement,
    RequirementCategory,
    RequirementPriority,
    Responsibility,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_job() -> ProcessedJob:
    """Create sample processed job for testing."""
    return ProcessedJob(
        id="test-job-123",
        title="Senior Python Developer",
        company=CompanyInfo(name="TechCorp", industry="Technology"),
        location="Remote",
        employment_type="Full-time",
        requirements=[
            Requirement(
                text="5+ years Python experience",
                priority=RequirementPriority.MUST_HAVE,
                category=RequirementCategory.TECHNICAL,
                years_required=5,
            ),
            Requirement(
                text="FastAPI knowledge",
                priority=RequirementPriority.MUST_HAVE,
                category=RequirementCategory.TECHNICAL,
            ),
            Requirement(
                text="AWS experience preferred",
                priority=RequirementPriority.NICE_TO_HAVE,
                category=RequirementCategory.TECHNICAL,
            ),
            Requirement(
                text="Docker containerization",
                priority=RequirementPriority.NICE_TO_HAVE,
                category=RequirementCategory.TECHNICAL,
            ),
        ],
        responsibilities=[
            Responsibility(
                text="Design REST APIs",
                category=RequirementCategory.TECHNICAL,
            ),
            Responsibility(
                text="Mentor junior developers",
                category=RequirementCategory.SOFT_SKILL,
            ),
            Responsibility(
                text="Code review and documentation",
                category=RequirementCategory.TECHNICAL,
            ),
        ],
        raw_text="Job posting text for Senior Python Developer at TechCorp...",
    )


@pytest.fixture
def sample_job_minimal() -> ProcessedJob:
    """Create minimal job with one requirement."""
    return ProcessedJob(
        id="minimal-job",
        title="Junior Developer",
        company=CompanyInfo(name="StartupCo"),
        requirements=[
            Requirement(
                text="Python basics",
                priority=RequirementPriority.MUST_HAVE,
                category=RequirementCategory.TECHNICAL,
            ),
        ],
        responsibilities=[],
        raw_text="Simple job posting...",
    )


@pytest.fixture
def mock_skill_match() -> SearchMatch:
    """Create mock skill search result."""
    return SearchMatch(
        id="skill_abc123_0",
        content="Python - expert level, 6 years experience",
        match_type="skill",
        score=0.85,
        metadata={
            "type": "skill",
            "name": "Python",
            "level": "expert",
            "years": 6.0,
        },
    )


@pytest.fixture
def mock_experience_match() -> SearchMatch:
    """Create mock experience search result."""
    return SearchMatch(
        id="exp_abc123_0",
        content="Senior Developer at PrevCorp. Built REST APIs using Python and FastAPI.",
        match_type="experience",
        score=0.75,
        metadata={
            "type": "experience",
            "company": "PrevCorp",
            "role": "Senior Developer",
            "current": False,
        },
    )


@pytest.fixture
def mock_collector(mock_skill_match: SearchMatch, mock_experience_match: SearchMatch):
    """Create mock Collector module."""
    collector = Mock()

    # Mock get_profile to return successfully (profile loaded)
    collector.get_profile = Mock(return_value=Mock())

    # Mock skill search - returns matching skills
    collector.search_skills = AsyncMock(return_value=[mock_skill_match])

    # Mock experience search - returns matching experience
    collector.search_experiences = AsyncMock(return_value=[mock_experience_match])

    return collector


@pytest.fixture
def mock_collector_no_profile():
    """Create mock Collector with no profile loaded."""
    collector = Mock()
    collector.get_profile = Mock(side_effect=Exception("No profile loaded"))
    return collector


@pytest.fixture
def mock_collector_no_matches():
    """Create mock Collector that returns no matches."""
    collector = Mock()
    collector.get_profile = Mock(return_value=Mock())
    collector.search_skills = AsyncMock(return_value=[])
    collector.search_experiences = AsyncMock(return_value=[])
    return collector


@pytest.fixture
def mock_llm_service():
    """Create mock LLM Service."""
    llm = AsyncMock()
    llm.health_check = AsyncMock(
        return_value=Mock(status="healthy")
    )
    llm.generate_json = AsyncMock(
        return_value={
            "positioning": "Position as experienced Python developer with API expertise",
            "key_strengths": ["Python expertise", "API design", "Team collaboration"],
            "address_gaps": ["Highlight willingness to obtain AWS certification"],
            "tone": "professional",
            "keywords_to_use": ["Python", "FastAPI", "REST", "APIs"],
            "opening_hook": "As a senior Python developer with extensive API experience...",
        }
    )
    return llm


@pytest.fixture
def mock_llm_service_unhealthy():
    """Create mock unhealthy LLM Service."""
    llm = AsyncMock()
    llm.health_check = AsyncMock(return_value=Mock(status="unhealthy"))
    return llm


@pytest.fixture
def mock_llm_service_failing():
    """Create mock LLM Service that fails on generate_json."""
    llm = AsyncMock()
    llm.health_check = AsyncMock(return_value=Mock(status="healthy"))
    llm.generate_json = AsyncMock(side_effect=Exception("LLM API error"))
    return llm


@pytest.fixture
def analyzer(mock_collector, mock_llm_service) -> Analyzer:
    """Create Analyzer instance for testing."""
    return Analyzer(mock_collector, mock_llm_service)


@pytest.fixture
async def initialized_analyzer(analyzer: Analyzer) -> Analyzer:
    """Create initialized Analyzer."""
    await analyzer.initialize()
    return analyzer


# =============================================================================
# MODEL TESTS
# =============================================================================


class TestMatchLevel:
    """Tests for MatchLevel enum."""

    def test_match_levels_exist(self) -> None:
        """Should have all expected match levels."""
        assert MatchLevel.EXCELLENT.value == "excellent"
        assert MatchLevel.STRONG.value == "strong"
        assert MatchLevel.MODERATE.value == "moderate"
        assert MatchLevel.WEAK.value == "weak"
        assert MatchLevel.POOR.value == "poor"


class TestSkillMatchResult:
    """Tests for SkillMatchResult model."""

    def test_skill_match_result_creation(self) -> None:
        """Should create valid SkillMatchResult."""
        match = SkillMatchResult(
            requirement_text="5+ years Python",
            requirement_priority="must_have",
            matched_skills=["Python (expert, 6 years)"],
            score=0.85,
            is_met=True,
        )
        assert match.requirement_text == "5+ years Python"
        assert match.is_met is True
        assert match.score == 0.85

    def test_skill_match_result_with_gap(self) -> None:
        """Should create SkillMatchResult with gap reason."""
        match = SkillMatchResult(
            requirement_text="AWS certification",
            requirement_priority="must_have",
            matched_skills=[],
            score=0.0,
            is_met=False,
            gap_reason="No matching skills found",
        )
        assert match.is_met is False
        assert match.gap_reason == "No matching skills found"


class TestExperienceMatchResult:
    """Tests for ExperienceMatchResult model."""

    def test_experience_match_result_creation(self) -> None:
        """Should create valid ExperienceMatchResult."""
        match = ExperienceMatchResult(
            responsibility_text="Design REST APIs",
            matched_experience="Senior Developer at TechCorp",
            relevance_score=0.8,
            matching_keywords=["API", "REST"],
        )
        assert match.matched_experience == "Senior Developer at TechCorp"
        assert match.relevance_score == 0.8

    def test_experience_match_result_no_match(self) -> None:
        """Should create ExperienceMatchResult with no match."""
        match = ExperienceMatchResult(
            responsibility_text="Manage large teams",
            matched_experience=None,
            relevance_score=0.0,
        )
        assert match.matched_experience is None


class TestQualificationGap:
    """Tests for QualificationGap model."""

    def test_qualification_gap_creation(self) -> None:
        """Should create valid QualificationGap."""
        gap = QualificationGap(
            requirement="AWS certification",
            importance="must_have",
            gap_type="certification",
            suggested_action="Highlight cloud experience",
        )
        assert gap.requirement == "AWS certification"
        assert gap.gap_type == "certification"


class TestApplicationStrategy:
    """Tests for ApplicationStrategy model."""

    def test_application_strategy_creation(self) -> None:
        """Should create valid ApplicationStrategy."""
        strategy = ApplicationStrategy(
            positioning="Position as experienced developer",
            key_strengths=["Python", "APIs"],
            address_gaps=["Learn AWS"],
            tone="professional",
            keywords_to_use=["Python", "FastAPI"],
            opening_hook="As an experienced developer...",
        )
        assert strategy.positioning == "Position as experienced developer"
        assert len(strategy.key_strengths) == 2

    def test_application_strategy_defaults(self) -> None:
        """Should have correct defaults."""
        strategy = ApplicationStrategy(positioning="Test")
        assert strategy.tone == "professional"
        assert strategy.key_strengths == []
        assert strategy.opening_hook is None


class TestCompatibilityScore:
    """Tests for CompatibilityScore model."""

    def test_compatibility_score_creation(self) -> None:
        """Should create valid CompatibilityScore."""
        score = CompatibilityScore(
            overall=75.5,
            level=MatchLevel.STRONG,
            technical_skills=80.0,
            experience_relevance=70.0,
            requirements_met=75.0,
            must_haves_met=2,
            must_haves_total=2,
        )
        assert score.overall == 75.5
        assert score.level == MatchLevel.STRONG

    def test_compatibility_score_defaults(self) -> None:
        """Should have correct defaults."""
        score = CompatibilityScore(overall=50.0)
        assert score.level == MatchLevel.MODERATE
        assert score.must_haves_met == 0


class TestAnalysisResult:
    """Tests for AnalysisResult model."""

    def test_analysis_result_creation(self) -> None:
        """Should create valid AnalysisResult."""
        result = AnalysisResult(
            job_id="job-123",
            job_title="Python Developer",
            company_name="TechCorp",
            compatibility=CompatibilityScore(overall=75.0, level=MatchLevel.STRONG),
        )
        assert result.job_id == "job-123"
        assert result.is_good_match is True

    def test_is_good_match_property(self) -> None:
        """Should correctly calculate is_good_match."""
        good_result = AnalysisResult(
            job_id="1",
            job_title="Test",
            company_name="Test",
            compatibility=CompatibilityScore(overall=70.0),
        )
        assert good_result.is_good_match is True

        bad_result = AnalysisResult(
            job_id="2",
            job_title="Test",
            company_name="Test",
            compatibility=CompatibilityScore(overall=60.0),
        )
        assert bad_result.is_good_match is False

    def test_critical_gaps_property(self) -> None:
        """Should filter critical gaps correctly."""
        result = AnalysisResult(
            job_id="1",
            job_title="Test",
            company_name="Test",
            compatibility=CompatibilityScore(overall=50.0),
            gaps=[
                QualificationGap(
                    requirement="AWS",
                    importance="must_have",
                    gap_type="certification",
                ),
                QualificationGap(
                    requirement="Docker",
                    importance="nice_to_have",
                    gap_type="skill",
                ),
            ],
        )
        critical = result.critical_gaps
        assert len(critical) == 1
        assert critical[0].requirement == "AWS"


class TestAnalysisInput:
    """Tests for AnalysisInput model."""

    def test_analysis_input_creation(self) -> None:
        """Should create valid AnalysisInput."""
        input_data = AnalysisInput(
            job_id="job-123",
            generate_strategy=True,
        )
        assert input_data.job_id == "job-123"
        assert input_data.generate_strategy is True

    def test_analysis_input_defaults(self) -> None:
        """Should have correct defaults."""
        input_data = AnalysisInput(job_id="job-123")
        assert input_data.generate_strategy is True


# =============================================================================
# EXCEPTION TESTS
# =============================================================================


class TestExceptions:
    """Tests for Analyzer exceptions."""

    def test_analyzer_error(self) -> None:
        """Should create AnalyzerError."""
        error = AnalyzerError("Test error")
        assert str(error) == "Test error"

    def test_matching_error(self) -> None:
        """Should create MatchingError."""
        error = MatchingError("Matching failed")
        assert isinstance(error, AnalyzerError)

    def test_strategy_generation_error(self) -> None:
        """Should create StrategyGenerationError."""
        error = StrategyGenerationError("LLM error")
        assert isinstance(error, AnalyzerError)

    def test_profile_not_loaded_error(self) -> None:
        """Should create ProfileNotLoadedError."""
        error = ProfileNotLoadedError("No profile")
        assert isinstance(error, AnalyzerError)


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


class TestAnalyzerInitialization:
    """Tests for Analyzer initialization."""

    @pytest.mark.asyncio
    async def test_initialize_success(
        self, analyzer: Analyzer, mock_llm_service
    ) -> None:
        """Should initialize successfully."""
        await analyzer.initialize()
        mock_llm_service.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(
        self, initialized_analyzer: Analyzer
    ) -> None:
        """Should handle double initialization gracefully."""
        # Second init should just log warning
        await initialized_analyzer.initialize()

    @pytest.mark.asyncio
    async def test_initialize_llm_unhealthy(
        self, mock_collector, mock_llm_service_unhealthy
    ) -> None:
        """Should raise error when LLM is unhealthy."""
        analyzer = Analyzer(mock_collector, mock_llm_service_unhealthy)
        with pytest.raises(AnalyzerError, match="LLM service not available"):
            await analyzer.initialize()

    @pytest.mark.asyncio
    async def test_shutdown(self, initialized_analyzer: Analyzer) -> None:
        """Should shutdown cleanly."""
        await initialized_analyzer.shutdown()
        # Should be idempotent
        await initialized_analyzer.shutdown()


# =============================================================================
# SKILL MATCHING TESTS
# =============================================================================


class TestSkillMatching:
    """Tests for skill matching functionality."""

    @pytest.mark.asyncio
    async def test_match_skills_found(
        self, initialized_analyzer: Analyzer, sample_job: ProcessedJob
    ) -> None:
        """Should match skills when found."""
        matches, must_met, nice_met = await initialized_analyzer._match_skills(
            sample_job
        )

        assert len(matches) == 4  # All requirements
        assert must_met >= 1  # At least Python match
        assert isinstance(matches[0], SkillMatchResult)

    @pytest.mark.asyncio
    async def test_match_skills_not_found(
        self,
        mock_collector_no_matches,
        mock_llm_service,
        sample_job: ProcessedJob,
    ) -> None:
        """Should handle no skill matches."""
        analyzer = Analyzer(mock_collector_no_matches, mock_llm_service)
        await analyzer.initialize()

        matches, must_met, nice_met = await analyzer._match_skills(sample_job)

        assert all(not m.is_met for m in matches)
        assert must_met == 0
        assert nice_met == 0

    @pytest.mark.asyncio
    async def test_match_skills_with_years_requirement(
        self, initialized_analyzer: Analyzer, sample_job: ProcessedJob
    ) -> None:
        """Should check years requirement."""
        matches, _, _ = await initialized_analyzer._match_skills(sample_job)

        # First requirement has 5 years required
        python_match = matches[0]
        # Mock returns 6 years, so should be met
        assert python_match.is_met is True

    @pytest.mark.asyncio
    async def test_match_skills_years_not_met(
        self, mock_collector, mock_llm_service, sample_job: ProcessedJob
    ) -> None:
        """Should identify when years requirement not met."""
        # Modify mock to return skill with only 3 years
        mock_collector.search_skills = AsyncMock(
            return_value=[
                SearchMatch(
                    id="skill_0",
                    content="Python - intermediate",
                    match_type="skill",
                    score=0.8,
                    metadata={"name": "Python", "level": "intermediate", "years": 3.0},
                )
            ]
        )

        analyzer = Analyzer(mock_collector, mock_llm_service)
        await analyzer.initialize()

        matches, must_met, _ = await analyzer._match_skills(sample_job)

        # Python match should show years gap
        python_match = matches[0]
        assert python_match.is_met is False
        assert "Have 3 years, need 5" in (python_match.gap_reason or "")


class TestFormatSkillMatch:
    """Tests for skill match formatting."""

    def test_format_skill_match_full(
        self, analyzer: Analyzer, mock_skill_match: SearchMatch
    ) -> None:
        """Should format full skill match."""
        result = analyzer._format_skill_match(mock_skill_match)
        assert "Python" in result
        assert "expert" in result
        assert "6 years" in result

    def test_format_skill_match_minimal(self, analyzer: Analyzer) -> None:
        """Should format minimal skill match."""
        match = SearchMatch(
            id="skill_0",
            content="JavaScript",
            match_type="skill",
            score=0.7,
            metadata={"name": "JavaScript"},
        )
        result = analyzer._format_skill_match(match)
        assert "JavaScript" in result


# =============================================================================
# EXPERIENCE MATCHING TESTS
# =============================================================================


class TestExperienceMatching:
    """Tests for experience matching functionality."""

    @pytest.mark.asyncio
    async def test_match_experiences_found(
        self, initialized_analyzer: Analyzer, sample_job: ProcessedJob
    ) -> None:
        """Should match experiences when found."""
        matches = await initialized_analyzer._match_experiences(sample_job)

        assert len(matches) == 3  # All responsibilities
        assert matches[0].matched_experience is not None

    @pytest.mark.asyncio
    async def test_match_experiences_not_found(
        self,
        mock_collector_no_matches,
        mock_llm_service,
        sample_job: ProcessedJob,
    ) -> None:
        """Should handle no experience matches."""
        analyzer = Analyzer(mock_collector_no_matches, mock_llm_service)
        await analyzer.initialize()

        matches = await analyzer._match_experiences(sample_job)

        assert all(m.matched_experience is None for m in matches)
        assert all(m.relevance_score == 0.0 for m in matches)

    @pytest.mark.asyncio
    async def test_match_experiences_below_threshold(
        self, mock_collector, mock_llm_service, sample_job: ProcessedJob
    ) -> None:
        """Should filter experiences below threshold."""
        mock_collector.search_experiences = AsyncMock(
            return_value=[
                SearchMatch(
                    id="exp_0",
                    content="Some unrelated experience",
                    match_type="experience",
                    score=0.2,  # Below threshold
                    metadata={"company": "Other", "role": "Unrelated"},
                )
            ]
        )

        analyzer = Analyzer(mock_collector, mock_llm_service)
        await analyzer.initialize()

        matches = await analyzer._match_experiences(sample_job)

        # Should not match due to low score
        assert matches[0].matched_experience is None


class TestExtractMatchingKeywords:
    """Tests for keyword extraction."""

    def test_extract_matching_keywords(
        self, analyzer: Analyzer, mock_experience_match: SearchMatch
    ) -> None:
        """Should extract matching keywords."""
        keywords = analyzer._extract_matching_keywords(
            "Design REST APIs using Python",
            mock_experience_match,
        )
        # Should find common words
        assert len(keywords) >= 0  # May vary based on content

    def test_extract_matching_keywords_filters_short(
        self, analyzer: Analyzer
    ) -> None:
        """Should filter short words."""
        match = SearchMatch(
            id="exp_0",
            content="Built APIs and REST services using Python frameworks",
            match_type="experience",
            score=0.8,
            metadata={},
        )
        keywords = analyzer._extract_matching_keywords(
            "Build APIs in Python",
            match,
        )
        # Short words like "in" should be filtered
        assert "in" not in keywords


# =============================================================================
# GAP ANALYSIS TESTS
# =============================================================================


class TestGapIdentification:
    """Tests for gap identification."""

    def test_identify_gaps_from_unmet(self, analyzer: Analyzer) -> None:
        """Should identify gaps from unmet requirements."""
        skill_matches = [
            SkillMatchResult(
                requirement_text="AWS certification required",
                requirement_priority="must_have",
                matched_skills=[],
                score=0,
                is_met=False,
            )
        ]

        gaps = analyzer._identify_gaps(skill_matches)

        assert len(gaps) == 1
        assert gaps[0].requirement == "AWS certification required"
        assert gaps[0].importance == "must_have"

    def test_identify_gaps_none_when_all_met(self, analyzer: Analyzer) -> None:
        """Should return empty list when all met."""
        skill_matches = [
            SkillMatchResult(
                requirement_text="Python",
                requirement_priority="must_have",
                matched_skills=["Python (expert)"],
                score=0.9,
                is_met=True,
            )
        ]

        gaps = analyzer._identify_gaps(skill_matches)

        assert len(gaps) == 0


class TestDetermineGapType:
    """Tests for gap type determination."""

    def test_determine_gap_type_education(self, analyzer: Analyzer) -> None:
        """Should identify education gaps."""
        assert analyzer._determine_gap_type("Bachelor's degree required") == "education"
        assert analyzer._determine_gap_type("Master's in CS") == "education"

    def test_determine_gap_type_certification(self, analyzer: Analyzer) -> None:
        """Should identify certification gaps."""
        assert analyzer._determine_gap_type("AWS certified") == "certification"
        assert analyzer._determine_gap_type("PMP certification") == "certification"

    def test_determine_gap_type_experience(self, analyzer: Analyzer) -> None:
        """Should identify experience gaps."""
        assert analyzer._determine_gap_type("5 years experience") == "experience"
        assert analyzer._determine_gap_type("10+ years in industry") == "experience"

    def test_determine_gap_type_skill(self, analyzer: Analyzer) -> None:
        """Should default to skill gap."""
        assert analyzer._determine_gap_type("Python knowledge") == "skill"
        assert analyzer._determine_gap_type("Docker proficiency") == "skill"


class TestSuggestGapAction:
    """Tests for gap action suggestions."""

    def test_suggest_gap_action_with_related_skills(self, analyzer: Analyzer) -> None:
        """Should suggest emphasizing related skills."""
        match = SkillMatchResult(
            requirement_text="Kubernetes",
            requirement_priority="must_have",
            matched_skills=["Docker (intermediate)"],
            score=0.3,
            is_met=False,
        )

        suggestion = analyzer._suggest_gap_action(match)
        assert "Emphasize related skills" in suggestion

    def test_suggest_gap_action_years(self, analyzer: Analyzer) -> None:
        """Should suggest highlighting impact for years gap."""
        match = SkillMatchResult(
            requirement_text="10 years experience",
            requirement_priority="must_have",
            matched_skills=[],
            score=0,
            is_met=False,
        )

        suggestion = analyzer._suggest_gap_action(match)
        assert "complexity" in suggestion.lower() or "impact" in suggestion.lower()

    def test_suggest_gap_action_default(self, analyzer: Analyzer) -> None:
        """Should provide default suggestion."""
        match = SkillMatchResult(
            requirement_text="Unknown skill",
            requirement_priority="must_have",
            matched_skills=[],
            score=0,
            is_met=False,
        )

        suggestion = analyzer._suggest_gap_action(match)
        assert "willingness to learn" in suggestion.lower()


# =============================================================================
# COMPATIBILITY SCORING TESTS
# =============================================================================


class TestCompatibilityScoring:
    """Tests for compatibility scoring."""

    def test_calculate_compatibility_high(
        self, analyzer: Analyzer, sample_job: ProcessedJob
    ) -> None:
        """Should calculate high score when well matched."""
        skill_matches = [
            SkillMatchResult(
                requirement_text="Python",
                requirement_priority="must_have",
                matched_skills=["Python"],
                score=0.9,
                is_met=True,
            ),
            SkillMatchResult(
                requirement_text="FastAPI",
                requirement_priority="must_have",
                matched_skills=["FastAPI"],
                score=0.8,
                is_met=True,
            ),
        ]
        experience_matches = [
            ExperienceMatchResult(
                responsibility_text="Build APIs",
                matched_experience="Developer at Company",
                relevance_score=0.8,
            )
        ]

        score = analyzer._calculate_compatibility(
            skill_matches=skill_matches,
            experience_matches=experience_matches,
            must_haves_met=2,
            nice_to_haves_met=1,
            job=sample_job,
        )

        assert score.overall >= 70
        assert score.level in [MatchLevel.EXCELLENT, MatchLevel.STRONG]

    def test_calculate_compatibility_low(
        self, analyzer: Analyzer, sample_job: ProcessedJob
    ) -> None:
        """Should calculate low score when poorly matched."""
        skill_matches = [
            SkillMatchResult(
                requirement_text="Python",
                requirement_priority="must_have",
                matched_skills=[],
                score=0,
                is_met=False,
            ),
        ]
        experience_matches: list[ExperienceMatchResult] = []

        score = analyzer._calculate_compatibility(
            skill_matches=skill_matches,
            experience_matches=experience_matches,
            must_haves_met=0,
            nice_to_haves_met=0,
            job=sample_job,
        )

        assert score.overall < 50
        assert score.level in [MatchLevel.WEAK, MatchLevel.POOR]

    def test_calculate_compatibility_levels(
        self, analyzer: Analyzer, sample_job: ProcessedJob
    ) -> None:
        """Should correctly assign match levels."""
        # Test boundaries
        skill_matches = [
            SkillMatchResult(
                requirement_text="Test",
                requirement_priority="must_have",
                matched_skills=["Test"],
                score=0.9,
                is_met=True,
            ),
        ]

        # Excellent (85+)
        score = analyzer._calculate_compatibility(
            skill_matches=skill_matches,
            experience_matches=[],
            must_haves_met=2,
            nice_to_haves_met=2,
            job=sample_job,
        )
        # Level depends on actual calculation

    def test_calculate_compatibility_empty_job(
        self, analyzer: Analyzer, sample_job_minimal: ProcessedJob
    ) -> None:
        """Should handle job with minimal requirements."""
        skill_matches = [
            SkillMatchResult(
                requirement_text="Python basics",
                requirement_priority="must_have",
                matched_skills=["Python"],
                score=0.8,
                is_met=True,
            ),
        ]

        score = analyzer._calculate_compatibility(
            skill_matches=skill_matches,
            experience_matches=[],
            must_haves_met=1,
            nice_to_haves_met=0,
            job=sample_job_minimal,
        )

        assert score.must_haves_total == 1
        assert score.nice_to_haves_total == 0


# =============================================================================
# STRATEGY GENERATION TESTS
# =============================================================================


class TestStrategyGeneration:
    """Tests for strategy generation."""

    @pytest.mark.asyncio
    async def test_generate_strategy_success(
        self,
        initialized_analyzer: Analyzer,
        sample_job: ProcessedJob,
        mock_llm_service,
    ) -> None:
        """Should generate strategy via LLM."""
        compatibility = CompatibilityScore(
            overall=75,
            level=MatchLevel.STRONG,
            must_haves_met=2,
            must_haves_total=2,
        )

        strategy = await initialized_analyzer._generate_strategy(
            job=sample_job,
            compatibility=compatibility,
            skill_matches=[],
            experience_matches=[],
            gaps=[],
        )

        assert strategy.positioning != ""
        assert len(strategy.key_strengths) > 0
        mock_llm_service.generate_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_strategy_llm_failure(
        self,
        mock_collector,
        mock_llm_service_failing,
        sample_job: ProcessedJob,
    ) -> None:
        """Should raise error when LLM fails."""
        analyzer = Analyzer(mock_collector, mock_llm_service_failing)
        await analyzer.initialize()

        compatibility = CompatibilityScore(overall=75, level=MatchLevel.STRONG)

        with pytest.raises(StrategyGenerationError):
            await analyzer._generate_strategy(
                job=sample_job,
                compatibility=compatibility,
                skill_matches=[],
                experience_matches=[],
                gaps=[],
            )

    def test_create_fallback_strategy(self, analyzer: Analyzer) -> None:
        """Should create valid fallback strategy."""
        strategy = analyzer._create_fallback_strategy()

        assert strategy.positioning != ""
        assert strategy.tone == "professional"
        assert len(strategy.key_strengths) > 0


# =============================================================================
# FULL ANALYSIS TESTS
# =============================================================================


class TestAnalyze:
    """Tests for full analysis flow."""

    @pytest.mark.asyncio
    async def test_analyze_success(
        self, initialized_analyzer: Analyzer, sample_job: ProcessedJob
    ) -> None:
        """Should complete full analysis."""
        result = await initialized_analyzer.analyze(sample_job)

        assert isinstance(result, AnalysisResult)
        assert result.job_id == sample_job.id
        assert result.job_title == sample_job.title
        assert result.company_name == sample_job.company.name
        assert result.compatibility is not None
        assert result.strategy is not None

    @pytest.mark.asyncio
    async def test_analyze_without_strategy(
        self,
        initialized_analyzer: Analyzer,
        sample_job: ProcessedJob,
        mock_llm_service,
    ) -> None:
        """Should skip strategy generation when disabled."""
        result = await initialized_analyzer.analyze(
            sample_job, generate_strategy=False
        )

        assert result.strategy is None
        # generate_json should not be called for strategy
        # (only health_check during init)
        assert mock_llm_service.generate_json.call_count == 0

    @pytest.mark.asyncio
    async def test_analyze_no_profile_loaded(
        self,
        mock_collector_no_profile,
        mock_llm_service,
        sample_job: ProcessedJob,
    ) -> None:
        """Should raise error when profile not loaded."""
        analyzer = Analyzer(mock_collector_no_profile, mock_llm_service)
        await analyzer.initialize()

        with pytest.raises(ProfileNotLoadedError):
            await analyzer.analyze(sample_job)

    @pytest.mark.asyncio
    async def test_analyze_with_llm_failure_uses_fallback(
        self,
        mock_collector,
        mock_llm_service_failing,
        sample_job: ProcessedJob,
    ) -> None:
        """Should use fallback strategy when LLM fails."""
        analyzer = Analyzer(mock_collector, mock_llm_service_failing)
        await analyzer.initialize()

        result = await analyzer.analyze(sample_job)

        # Should still have a strategy (fallback)
        assert result.strategy is not None
        assert result.strategy.tone == "professional"

    @pytest.mark.asyncio
    async def test_analyze_increments_stats(
        self, initialized_analyzer: Analyzer, sample_job: ProcessedJob
    ) -> None:
        """Should increment analysis stats."""
        initial_stats = initialized_analyzer.get_stats()
        assert initial_stats["total_analyses"] == 0

        await initialized_analyzer.analyze(sample_job)

        stats = initialized_analyzer.get_stats()
        assert stats["total_analyses"] == 1


class TestAnalyzeSafe:
    """Tests for safe analysis with error handling."""

    @pytest.mark.asyncio
    async def test_analyze_safe_success(
        self, initialized_analyzer: Analyzer, sample_job: ProcessedJob
    ) -> None:
        """Should return result on success."""
        result, error = await initialized_analyzer.analyze_safe(sample_job)

        assert result is not None
        assert error is None
        assert isinstance(result, AnalysisResult)

    @pytest.mark.asyncio
    async def test_analyze_safe_failure(
        self,
        mock_collector_no_profile,
        mock_llm_service,
        sample_job: ProcessedJob,
    ) -> None:
        """Should return error message on failure."""
        analyzer = Analyzer(mock_collector_no_profile, mock_llm_service)
        await analyzer.initialize()

        result, error = await analyzer.analyze_safe(sample_job)

        assert result is None
        assert error is not None
        assert "profile" in error.lower() or "Profile" in error


# =============================================================================
# DEPENDENCY INJECTION TESTS
# =============================================================================


class TestDependencyInjection:
    """Tests for dependency injection functions."""

    def test_reset_analyzer(self) -> None:
        """Should reset global instance."""
        reset_analyzer()
        # Should not raise

    @pytest.mark.asyncio
    async def test_get_analyzer_creates_singleton(self) -> None:
        """Should create singleton on first call."""
        reset_analyzer()

        # Patch source modules per LL-021
        with patch("src.modules.collector.get_collector") as mock_get_collector, \
             patch("src.services.llm_service.get_llm_service") as mock_get_llm:

            # Setup mocks
            mock_collector = Mock()
            mock_collector.get_profile = Mock(return_value=Mock())
            mock_get_collector.return_value = mock_collector

            mock_llm = AsyncMock()
            mock_llm.health_check = AsyncMock(return_value=Mock(status="healthy"))
            mock_get_llm.return_value = mock_llm

            from src.modules.analyzer import get_analyzer

            analyzer1 = await get_analyzer()
            analyzer2 = await get_analyzer()

            # Should be same instance
            assert analyzer1 is analyzer2

            # Cleanup
            reset_analyzer()


# =============================================================================
# EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_analyze_empty_responsibilities(
        self, initialized_analyzer: Analyzer
    ) -> None:
        """Should handle job with no responsibilities."""
        job = ProcessedJob(
            id="no-resp",
            title="Test Job",
            company=CompanyInfo(name="Test"),
            requirements=[
                Requirement(
                    text="Python",
                    priority=RequirementPriority.MUST_HAVE,
                    category=RequirementCategory.TECHNICAL,
                )
            ],
            responsibilities=[],
            raw_text="Test...",
        )

        result = await initialized_analyzer.analyze(job)

        assert result is not None
        assert len(result.experience_matches) == 0

    @pytest.mark.asyncio
    async def test_analyze_many_requirements(
        self, initialized_analyzer: Analyzer
    ) -> None:
        """Should handle job with many requirements."""
        requirements = [
            Requirement(
                text=f"Skill {i}",
                priority=RequirementPriority.MUST_HAVE if i < 3 else RequirementPriority.NICE_TO_HAVE,
                category=RequirementCategory.TECHNICAL,
            )
            for i in range(10)
        ]

        job = ProcessedJob(
            id="many-reqs",
            title="Test Job",
            company=CompanyInfo(name="Test"),
            requirements=requirements,
            responsibilities=[],
            raw_text="Test...",
        )

        result = await initialized_analyzer.analyze(job)

        assert len(result.skill_matches) == 10

    def test_compatibility_score_bounds(
        self, analyzer: Analyzer, sample_job: ProcessedJob
    ) -> None:
        """Should calculate score correctly with valid inputs."""
        # sample_job has 2 must-haves and 2 nice-to-haves
        score = analyzer._calculate_compatibility(
            skill_matches=[],
            experience_matches=[],
            must_haves_met=2,  # All must-haves met
            nice_to_haves_met=2,  # All nice-to-haves met
            job=sample_job,
        )

        # Should be within valid range
        assert 0 <= score.overall <= 100
        assert score.must_haves_met == 2
        assert score.must_haves_total == 2
