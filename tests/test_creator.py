"""
Unit tests for M4 Creator Module.

Run with: pytest tests/test_creator.py -v
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.modules.analyzer.models import (
    AnalysisResult,
    ApplicationStrategy,
    CompatibilityScore,
    ExperienceMatchResult,
    MatchLevel,
    QualificationGap,
    SkillMatchResult,
)
from src.modules.collector.models import (
    Education,
    Experience,
    Skill,
    SkillLevel,
    UserProfile,
)
from src.modules.creator import (
    CreatedContent,
    Creator,
    CreatorError,
    CoverLetterGenerationError,
    CVGenerationError,
    CVSection,
    GeneratedCoverLetter,
    GeneratedCV,
    ProfileNotAvailableError,
    reset_creator,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_profile() -> UserProfile:
    """Create sample user profile for testing."""
    return UserProfile(
        full_name="Jane Developer",
        email="jane@example.com",
        phone="+1-555-1234",
        location="San Francisco, CA",
        linkedin_url="https://linkedin.com/in/janedev",
        github_url="https://github.com/janedev",
        title="Senior Software Engineer",
        years_experience=6.0,
        summary="Experienced developer with Python expertise",
        skills=[
            Skill(
                name="Python",
                level=SkillLevel.EXPERT,
                years=6,
            ),
            Skill(
                name="FastAPI",
                level=SkillLevel.ADVANCED,
                years=3,
            ),
            Skill(
                name="PostgreSQL",
                level=SkillLevel.ADVANCED,
                years=4,
            ),
            Skill(
                name="Leadership",
                level=SkillLevel.INTERMEDIATE,
                years=2,
            ),
            Skill(
                name="Docker",
                level=SkillLevel.INTERMEDIATE,
                years=2,
            ),
        ],
        experiences=[
            Experience(
                company="TechCorp",
                role="Senior Developer",
                start_date=datetime(2020, 1, 1),
                current=True,
                description="Lead backend development for cloud platform",
                achievements=[
                    "Improved system performance by 40%",
                    "Led team of 5 developers",
                    "Built REST APIs serving 1M+ requests/day",
                ],
                technologies=["Python", "FastAPI", "PostgreSQL", "Docker"],
            ),
            Experience(
                company="StartupInc",
                role="Python Developer",
                start_date=datetime(2018, 1, 1),
                end_date=datetime(2019, 12, 31),
                description="Full-stack Python development",
                achievements=[
                    "Developed microservices architecture",
                    "Implemented CI/CD pipeline",
                ],
                technologies=["Python", "Django", "MySQL"],
            ),
        ],
        education=[
            Education(
                institution="UC Berkeley",
                degree="Bachelor's",
                field="Computer Science",
                start_date=datetime(2014, 9, 1),
                end_date=datetime(2018, 5, 15),
                relevant_courses=["Data Structures", "Algorithms", "Databases"],
            ),
        ],
    )


@pytest.fixture
def sample_analysis() -> AnalysisResult:
    """Create sample analysis result for testing."""
    return AnalysisResult(
        job_id="test-job-123",
        job_title="Senior Python Developer",
        company_name="TargetCorp",
        compatibility=CompatibilityScore(
            overall=78.0,
            level=MatchLevel.STRONG,
            technical_skills=80.0,
            experience_relevance=75.0,
            requirements_met=80.0,
            must_haves_met=2,
            must_haves_total=2,
            nice_to_haves_met=1,
            nice_to_haves_total=2,
        ),
        skill_matches=[
            SkillMatchResult(
                requirement_text="5+ years Python experience",
                requirement_priority="must_have",
                matched_skills=["Python - expert level, 6 years experience"],
                score=0.92,
                is_met=True,
            ),
            SkillMatchResult(
                requirement_text="FastAPI knowledge",
                requirement_priority="must_have",
                matched_skills=["FastAPI - advanced level"],
                score=0.85,
                is_met=True,
            ),
        ],
        experience_matches=[
            ExperienceMatchResult(
                responsibility_text="Design REST APIs",
                matched_experience="Senior Developer at TechCorp",
                relevance_score=0.88,
                matching_keywords=["API", "REST", "Python"],
            ),
        ],
        gaps=[
            QualificationGap(
                requirement="AWS certification",
                importance="nice_to_have",
                gap_type="certification",
                suggested_action="Mention cloud experience and willingness to learn AWS",
            ),
        ],
        strategy=ApplicationStrategy(
            positioning="Position as experienced Python backend developer with strong API expertise",
            key_strengths=[
                "6 years Python expertise",
                "REST API development experience",
                "Team leadership experience",
            ],
            address_gaps=[
                "Highlight Docker/containerization as foundation for cloud skills",
            ],
            tone="professional",
            keywords_to_use=["Python", "FastAPI", "API", "backend", "REST"],
            opening_hook="With 6 years of Python experience building high-performance APIs...",
        ),
    )


@pytest.fixture
def sample_analysis_no_strategy() -> AnalysisResult:
    """Create analysis result without strategy."""
    return AnalysisResult(
        job_id="test-job-456",
        job_title="Python Developer",
        company_name="AnotherCorp",
        compatibility=CompatibilityScore(
            overall=65.0,
            level=MatchLevel.MODERATE,
            must_haves_met=1,
            must_haves_total=2,
        ),
        skill_matches=[],
        experience_matches=[],
        gaps=[],
        strategy=None,
    )


@pytest.fixture
def mock_collector(sample_profile: UserProfile):
    """Create mock Collector module."""
    collector = Mock()
    collector.get_profile.return_value = sample_profile
    return collector


@pytest.fixture
def mock_collector_no_profile():
    """Create mock Collector with no profile loaded."""
    collector = Mock()
    collector.get_profile.side_effect = Exception("No profile loaded")
    return collector


@pytest.fixture
def mock_llm_service():
    """Create mock LLM Service."""
    llm = AsyncMock()

    # Mock health check
    llm.health_check.return_value = Mock(status="healthy")

    # Mock JSON generation for summary
    llm.generate_json.side_effect = [
        # CV Summary
        {
            "summary": (
                "Senior Python developer with 6+ years of experience "
                "building scalable backend systems. Expert in REST API development "
                "with FastAPI and team leadership. Proven track record of "
                "improving system performance and delivering high-quality software."
            )
        },
        # Experience section 1
        {
            "title": "Senior Developer",
            "company": "TechCorp",
            "duration": "4.0 years",
            "bullet_points": [
                "Improved system performance by 40% through optimization",
                "Led team of 5 developers in agile environment",
                "Built REST APIs serving 1M+ requests per day",
            ],
        },
        # Experience section 2
        {
            "title": "Python Developer",
            "company": "StartupInc",
            "duration": "2.0 years",
            "bullet_points": [
                "Developed microservices architecture for core platform",
                "Implemented CI/CD pipeline reducing deployment time by 50%",
            ],
        },
        # Cover letter
        {
            "opening": (
                "I am excited to apply for the Senior Python Developer "
                "position at TargetCorp. With 6 years of Python experience "
                "building high-performance APIs, I am confident I can contribute "
                "to your team's success."
            ),
            "body_paragraphs": [
                (
                    "In my current role at TechCorp, I lead backend development "
                    "for a cloud platform, where I've improved system performance "
                    "by 40% and led a team of 5 developers. My expertise in "
                    "FastAPI and REST API development aligns perfectly with "
                    "your requirements."
                ),
                (
                    "My background in Python development, combined with "
                    "experience in containerization with Docker, positions me "
                    "well to contribute to your backend systems. I'm eager to "
                    "bring my skills in building scalable APIs to TargetCorp."
                ),
            ],
            "closing": (
                "I look forward to the opportunity to discuss how my experience "
                "can benefit your team. Thank you for considering my application."
            ),
        },
    ]

    return llm


@pytest.fixture
def mock_llm_service_failing():
    """Create mock LLM Service that fails."""
    llm = AsyncMock()
    llm.health_check.return_value = Mock(status="healthy")
    llm.generate_json.side_effect = Exception("LLM API error")
    return llm


@pytest.fixture
def creator(mock_collector, mock_llm_service) -> Creator:
    """Create Creator instance for testing."""
    return Creator(mock_collector, mock_llm_service)


@pytest.fixture
async def initialized_creator(creator: Creator) -> Creator:
    """Create initialized Creator instance."""
    await creator.initialize()
    return creator


# =============================================================================
# MODEL TESTS
# =============================================================================


class TestCVSectionModel:
    """Tests for CVSection model."""

    def test_create_cv_section(self) -> None:
        """Should create CVSection with all fields."""
        section = CVSection(
            section_type="experience",
            title="Senior Developer | TechCorp",
            content="4 years",
            bullet_points=["Achievement 1", "Achievement 2"],
        )

        assert section.section_type == "experience"
        assert section.title == "Senior Developer | TechCorp"
        assert section.content == "4 years"
        assert len(section.bullet_points) == 2

    def test_create_cv_section_minimal(self) -> None:
        """Should create CVSection with minimal fields."""
        section = CVSection(
            section_type="education",
            title="BS Computer Science",
        )

        assert section.section_type == "education"
        assert section.title == "BS Computer Science"
        assert section.content == ""
        assert section.bullet_points == []


class TestGeneratedCVModel:
    """Tests for GeneratedCV model."""

    def test_create_generated_cv(self, sample_profile: UserProfile) -> None:
        """Should create GeneratedCV with all fields."""
        cv = GeneratedCV(
            full_name=sample_profile.full_name,
            email=sample_profile.email,
            phone=sample_profile.phone,
            location=sample_profile.location,
            professional_summary="Professional summary text",
            sections=[
                CVSection(section_type="experience", title="Experience 1"),
            ],
            technical_skills=["Python", "FastAPI"],
            soft_skills=["Leadership"],
            target_job_title="Senior Developer",
            target_company="TargetCorp",
        )

        assert cv.full_name == "Jane Developer"
        assert cv.email == "jane@example.com"
        assert len(cv.sections) == 1
        assert len(cv.technical_skills) == 2

    def test_get_section(self) -> None:
        """Should find section by type."""
        cv = GeneratedCV(
            full_name="Test",
            email="test@test.com",
            sections=[
                CVSection(section_type="experience", title="Exp"),
                CVSection(section_type="education", title="Edu"),
            ],
        )

        exp_section = cv.get_section("experience")
        assert exp_section is not None
        assert exp_section.title == "Exp"

        edu_section = cv.get_section("education")
        assert edu_section is not None
        assert edu_section.title == "Edu"

        missing = cv.get_section("skills")
        assert missing is None


class TestGeneratedCoverLetterModel:
    """Tests for GeneratedCoverLetter model."""

    def test_create_cover_letter(self) -> None:
        """Should create GeneratedCoverLetter with all fields."""
        letter = GeneratedCoverLetter(
            company_name="TargetCorp",
            job_title="Senior Developer",
            opening="Opening paragraph",
            body_paragraphs=["Body 1", "Body 2"],
            closing="Closing paragraph",
            tone="professional",
        )

        assert letter.company_name == "TargetCorp"
        assert letter.job_title == "Senior Developer"
        assert len(letter.body_paragraphs) == 2
        assert letter.tone == "professional"

    def test_full_text_property(self) -> None:
        """Should combine paragraphs into full text."""
        letter = GeneratedCoverLetter(
            company_name="TargetCorp",
            job_title="Developer",
            opening="Opening",
            body_paragraphs=["Body 1", "Body 2"],
            closing="Closing",
        )

        full_text = letter.full_text
        assert "Opening" in full_text
        assert "Body 1" in full_text
        assert "Body 2" in full_text
        assert "Closing" in full_text
        assert "\n\n" in full_text  # Paragraphs separated

    def test_full_text_handles_empty(self) -> None:
        """Should handle empty paragraphs in full text."""
        letter = GeneratedCoverLetter(
            company_name="TargetCorp",
            job_title="Developer",
            opening="Opening",
            body_paragraphs=[],
            closing="Closing",
        )

        full_text = letter.full_text
        assert "Opening" in full_text
        assert "Closing" in full_text


class TestCreatedContentModel:
    """Tests for CreatedContent model."""

    def test_create_content_model(self) -> None:
        """Should create CreatedContent with all fields."""
        cv = GeneratedCV(full_name="Test", email="test@test.com")
        letter = GeneratedCoverLetter(
            company_name="TargetCorp",
            job_title="Developer",
        )

        content = CreatedContent(
            job_id="test-123",
            job_title="Developer",
            company_name="TargetCorp",
            cv=cv,
            cover_letter=letter,
            compatibility_score=75.0,
        )

        assert content.job_id == "test-123"
        assert content.cv.full_name == "Test"
        assert content.cover_letter.company_name == "TargetCorp"
        assert content.compatibility_score == 75.0


# =============================================================================
# CREATOR INITIALIZATION TESTS
# =============================================================================


class TestCreatorInitialization:
    """Tests for Creator initialization."""

    def test_create_creator(self, mock_collector, mock_llm_service) -> None:
        """Should create Creator instance."""
        creator = Creator(mock_collector, mock_llm_service)

        assert creator._collector == mock_collector
        assert creator._llm == mock_llm_service
        assert not creator._initialized

    @pytest.mark.asyncio
    async def test_initialize(self, creator: Creator) -> None:
        """Should initialize Creator module."""
        await creator.initialize()

        assert creator._initialized

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(
        self, initialized_creator: Creator
    ) -> None:
        """Should handle double initialization gracefully."""
        await initialized_creator.initialize()  # Second call
        assert initialized_creator._initialized

    @pytest.mark.asyncio
    async def test_initialize_llm_unavailable(
        self, mock_collector
    ) -> None:
        """Should raise error if LLM service unavailable."""
        llm = AsyncMock()
        llm.health_check.return_value = Mock(status="unavailable")

        creator = Creator(mock_collector, llm)

        with pytest.raises(CreatorError, match="LLM Service not available"):
            await creator.initialize()

    @pytest.mark.asyncio
    async def test_shutdown(self, initialized_creator: Creator) -> None:
        """Should shutdown Creator module."""
        await initialized_creator.shutdown()

        assert not initialized_creator._initialized

    @pytest.mark.asyncio
    async def test_shutdown_not_initialized(self, creator: Creator) -> None:
        """Should handle shutdown when not initialized."""
        await creator.shutdown()  # Should not raise


# =============================================================================
# CV GENERATION TESTS
# =============================================================================


class TestCVGeneration:
    """Tests for CV generation."""

    @pytest.mark.asyncio
    async def test_generate_cv(
        self,
        initialized_creator: Creator,
        sample_analysis: AnalysisResult,
    ) -> None:
        """Should generate complete CV."""
        cv = await initialized_creator.generate_cv(sample_analysis)

        assert isinstance(cv, GeneratedCV)
        assert cv.full_name == "Jane Developer"
        assert cv.email == "jane@example.com"
        assert cv.professional_summary != ""
        assert len(cv.sections) > 0
        assert cv.target_job_title == "Senior Python Developer"
        assert cv.target_company == "TargetCorp"

    @pytest.mark.asyncio
    async def test_generate_cv_has_experience_sections(
        self,
        initialized_creator: Creator,
        sample_analysis: AnalysisResult,
    ) -> None:
        """Should include experience sections in CV."""
        cv = await initialized_creator.generate_cv(sample_analysis)

        experience_sections = [
            s for s in cv.sections if s.section_type == "experience"
        ]
        assert len(experience_sections) >= 1

    @pytest.mark.asyncio
    async def test_generate_cv_has_education_sections(
        self,
        initialized_creator: Creator,
        sample_analysis: AnalysisResult,
    ) -> None:
        """Should include education sections in CV."""
        cv = await initialized_creator.generate_cv(sample_analysis)

        education_sections = [
            s for s in cv.sections if s.section_type == "education"
        ]
        assert len(education_sections) >= 1
        assert "Computer Science" in education_sections[0].title

    @pytest.mark.asyncio
    async def test_generate_cv_has_skills(
        self,
        initialized_creator: Creator,
        sample_analysis: AnalysisResult,
    ) -> None:
        """Should include skills in CV."""
        cv = await initialized_creator.generate_cv(sample_analysis)

        assert len(cv.technical_skills) > 0
        assert "Python" in cv.technical_skills
        assert len(cv.soft_skills) > 0
        assert "Leadership" in cv.soft_skills

    @pytest.mark.asyncio
    async def test_generate_cv_prioritizes_keywords(
        self,
        initialized_creator: Creator,
        sample_analysis: AnalysisResult,
    ) -> None:
        """Should prioritize skills matching strategy keywords."""
        cv = await initialized_creator.generate_cv(sample_analysis)

        # Python and FastAPI are in keywords, should be prioritized
        assert "Python" in cv.technical_skills[:3]

    @pytest.mark.asyncio
    async def test_generate_cv_without_strategy(
        self,
        initialized_creator: Creator,
        sample_analysis_no_strategy: AnalysisResult,
    ) -> None:
        """Should handle analysis without strategy."""
        # Reset mock to handle the calls without strategy
        initialized_creator._llm.generate_json.side_effect = [
            {"summary": "Professional summary"},
            {"title": "Dev", "bullet_points": ["Did stuff"]},
            {"title": "Dev", "bullet_points": ["Did stuff"]},
            {
                "opening": "Hi",
                "body_paragraphs": ["Body"],
                "closing": "Bye",
            },
        ]

        cv = await initialized_creator.generate_cv(sample_analysis_no_strategy)

        assert cv is not None
        assert cv.professional_summary != ""

    @pytest.mark.asyncio
    async def test_generate_cv_not_initialized(
        self,
        creator: Creator,
        sample_analysis: AnalysisResult,
    ) -> None:
        """Should raise error if not initialized."""
        with pytest.raises(CreatorError, match="not initialized"):
            await creator.generate_cv(sample_analysis)

    @pytest.mark.asyncio
    async def test_generate_cv_no_profile(
        self,
        mock_collector_no_profile,
        mock_llm_service,
        sample_analysis: AnalysisResult,
    ) -> None:
        """Should raise error if no profile available."""
        creator = Creator(mock_collector_no_profile, mock_llm_service)
        await creator.initialize()

        with pytest.raises(ProfileNotAvailableError):
            await creator.generate_cv(sample_analysis)


class TestCVSummaryGeneration:
    """Tests for CV summary generation."""

    @pytest.mark.asyncio
    async def test_generate_summary_uses_llm(
        self,
        initialized_creator: Creator,
        sample_analysis: AnalysisResult,
    ) -> None:
        """Should use LLM for summary generation."""
        profile = initialized_creator._get_profile()

        summary = await initialized_creator._generate_summary(
            profile, sample_analysis
        )

        assert summary != ""
        initialized_creator._llm.generate_json.assert_called()

    @pytest.mark.asyncio
    async def test_generate_summary_fallback_on_error(
        self,
        mock_collector,
        sample_analysis: AnalysisResult,
    ) -> None:
        """Should use fallback on LLM error."""
        llm = AsyncMock()
        llm.health_check.return_value = Mock(status="healthy")
        llm.generate_json.side_effect = Exception("LLM error")

        creator = Creator(mock_collector, llm)
        await creator.initialize()

        profile = creator._get_profile()
        summary = await creator._generate_summary(profile, sample_analysis)

        # Should have fallback summary
        assert summary != ""
        assert "Professional" in summary or "experience" in summary.lower()


class TestExperienceGeneration:
    """Tests for experience section generation."""

    @pytest.mark.asyncio
    async def test_generate_experience_section(
        self,
        initialized_creator: Creator,
        sample_profile: UserProfile,
    ) -> None:
        """Should generate experience section."""
        exp = sample_profile.experiences[0]

        section = await initialized_creator._generate_experience_section(
            exp, "Senior Python Developer", ["Python", "API"]
        )

        assert isinstance(section, CVSection)
        assert section.section_type == "experience"
        assert "TechCorp" in section.title
        assert len(section.bullet_points) > 0

    @pytest.mark.asyncio
    async def test_generate_experience_section_fallback(
        self,
        mock_collector,
        sample_profile: UserProfile,
    ) -> None:
        """Should use original experience on LLM error."""
        llm = AsyncMock()
        llm.health_check.return_value = Mock(status="healthy")
        llm.generate_json.side_effect = Exception("LLM error")

        creator = Creator(mock_collector, llm)
        await creator.initialize()

        exp = sample_profile.experiences[0]
        section = await creator._generate_experience_section(
            exp, "Developer", ["Python"]
        )

        # Should have original content as fallback
        assert section is not None
        assert exp.role in section.title
        assert exp.company in section.title


# =============================================================================
# COVER LETTER GENERATION TESTS
# =============================================================================


class TestCoverLetterGeneration:
    """Tests for cover letter generation."""

    @pytest.mark.asyncio
    async def test_generate_cover_letter(
        self,
        initialized_creator: Creator,
        sample_analysis: AnalysisResult,
    ) -> None:
        """Should generate complete cover letter."""
        # Reset mock for cover letter generation
        initialized_creator._llm.generate_json.side_effect = None
        initialized_creator._llm.generate_json.return_value = {
            "opening": "Opening paragraph",
            "body_paragraphs": ["Body 1", "Body 2"],
            "closing": "Closing paragraph",
        }

        letter = await initialized_creator.generate_cover_letter(sample_analysis)

        assert isinstance(letter, GeneratedCoverLetter)
        assert letter.company_name == "TargetCorp"
        assert letter.job_title == "Senior Python Developer"
        assert letter.opening != ""
        assert len(letter.body_paragraphs) >= 1
        assert letter.closing != ""

    @pytest.mark.asyncio
    async def test_generate_cover_letter_has_word_count(
        self,
        initialized_creator: Creator,
        sample_analysis: AnalysisResult,
    ) -> None:
        """Should calculate word count."""
        initialized_creator._llm.generate_json.side_effect = None
        initialized_creator._llm.generate_json.return_value = {
            "opening": "Opening paragraph with some words",
            "body_paragraphs": ["Body paragraph one", "Body paragraph two"],
            "closing": "Closing paragraph",
        }

        letter = await initialized_creator.generate_cover_letter(sample_analysis)

        assert letter.word_count > 0

    @pytest.mark.asyncio
    async def test_generate_cover_letter_without_strategy(
        self,
        initialized_creator: Creator,
        sample_analysis_no_strategy: AnalysisResult,
    ) -> None:
        """Should handle analysis without strategy."""
        initialized_creator._llm.generate_json.side_effect = None
        initialized_creator._llm.generate_json.return_value = {
            "opening": "Opening",
            "body_paragraphs": ["Body"],
            "closing": "Closing",
        }

        letter = await initialized_creator.generate_cover_letter(
            sample_analysis_no_strategy
        )

        assert letter is not None
        assert letter.opening != ""

    @pytest.mark.asyncio
    async def test_generate_cover_letter_fallback(
        self,
        mock_collector,
        sample_analysis: AnalysisResult,
    ) -> None:
        """Should use fallback on LLM error."""
        llm = AsyncMock()
        llm.health_check.return_value = Mock(status="healthy")
        llm.generate_json.side_effect = Exception("LLM error")

        creator = Creator(mock_collector, llm)
        await creator.initialize()

        letter = await creator.generate_cover_letter(sample_analysis)

        # Should have fallback content
        assert letter.opening != ""
        assert "interest" in letter.opening.lower()
        assert len(letter.body_paragraphs) > 0
        assert letter.closing != ""

    @pytest.mark.asyncio
    async def test_generate_cover_letter_not_initialized(
        self,
        creator: Creator,
        sample_analysis: AnalysisResult,
    ) -> None:
        """Should raise error if not initialized."""
        with pytest.raises(CreatorError, match="not initialized"):
            await creator.generate_cover_letter(sample_analysis)


# =============================================================================
# CREATE CONTENT TESTS
# =============================================================================


class TestCreateContent:
    """Tests for complete content creation."""

    @pytest.mark.asyncio
    async def test_create_content(
        self,
        initialized_creator: Creator,
        sample_analysis: AnalysisResult,
    ) -> None:
        """Should create complete application content."""
        content = await initialized_creator.create_content(sample_analysis)

        assert isinstance(content, CreatedContent)
        assert content.job_id == "test-job-123"
        assert content.job_title == "Senior Python Developer"
        assert content.company_name == "TargetCorp"
        assert content.cv is not None
        assert content.cover_letter is not None
        assert content.compatibility_score == 78.0

    @pytest.mark.asyncio
    async def test_create_content_cv_and_cover_letter_match(
        self,
        initialized_creator: Creator,
        sample_analysis: AnalysisResult,
    ) -> None:
        """Should create consistent CV and cover letter."""
        content = await initialized_creator.create_content(sample_analysis)

        # Both should target same job/company
        assert content.cv.target_job_title == content.cover_letter.job_title
        assert content.cv.target_company == content.cover_letter.company_name

    @pytest.mark.asyncio
    async def test_create_content_not_initialized(
        self,
        creator: Creator,
        sample_analysis: AnalysisResult,
    ) -> None:
        """Should raise error if not initialized."""
        with pytest.raises(CreatorError, match="not initialized"):
            await creator.create_content(sample_analysis)


# =============================================================================
# SKILLS CATEGORIZATION TESTS
# =============================================================================


class TestSkillsCategorization:
    """Tests for skills categorization."""

    def test_is_soft_skill_true(self, creator: Creator) -> None:
        """Should identify soft skills."""
        assert creator._is_soft_skill("Leadership")
        assert creator._is_soft_skill("leadership")  # Case insensitive
        assert creator._is_soft_skill("Communication")
        assert creator._is_soft_skill("Teamwork")
        assert creator._is_soft_skill("Problem-solving")

    def test_is_soft_skill_false(self, creator: Creator) -> None:
        """Should not identify technical skills as soft skills."""
        assert not creator._is_soft_skill("Python")
        assert not creator._is_soft_skill("FastAPI")
        assert not creator._is_soft_skill("Docker")
        assert not creator._is_soft_skill("PostgreSQL")

    def test_build_skills_section(
        self,
        creator: Creator,
        sample_profile: UserProfile,
        sample_analysis: AnalysisResult,
    ) -> None:
        """Should categorize skills correctly."""
        creator._collector.get_profile.return_value = sample_profile

        technical, soft = creator._build_skills_section(
            sample_profile, sample_analysis.strategy
        )

        assert "Python" in technical
        assert "FastAPI" in technical
        assert "Leadership" in soft
        assert "Leadership" not in technical

    def test_build_skills_section_limits_count(
        self,
        creator: Creator,
    ) -> None:
        """Should limit number of skills."""
        # Create profile with many skills
        profile = UserProfile(
            full_name="Test",
            email="test@test.com",
            skills=[Skill(name=f"Skill{i}") for i in range(20)],
        )

        technical, soft = creator._build_skills_section(profile, None)

        assert len(technical) <= 15
        assert len(soft) <= 5


# =============================================================================
# HELPER METHOD TESTS
# =============================================================================


class TestHelperMethods:
    """Tests for helper methods."""

    def test_get_profile(
        self, creator: Creator, sample_profile: UserProfile
    ) -> None:
        """Should get profile from collector."""
        profile = creator._get_profile()

        assert profile == sample_profile
        creator._collector.get_profile.assert_called_once()

    def test_get_profile_not_available(
        self, mock_collector_no_profile, mock_llm_service
    ) -> None:
        """Should raise error if profile not available."""
        creator = Creator(mock_collector_no_profile, mock_llm_service)

        with pytest.raises(ProfileNotAvailableError):
            creator._get_profile()

    def test_get_current_experience(
        self, creator: Creator, sample_profile: UserProfile
    ) -> None:
        """Should find current experience."""
        exp = creator._get_current_experience(sample_profile)

        assert exp is not None
        assert exp.current is True
        assert exp.company == "TechCorp"

    def test_get_current_experience_none(self, creator: Creator) -> None:
        """Should return None for profile with no experiences."""
        profile = UserProfile(full_name="Test", email="test@test.com")

        exp = creator._get_current_experience(profile)

        assert exp is None

    def test_get_current_experience_most_recent(
        self, creator: Creator
    ) -> None:
        """Should return most recent if no current."""
        profile = UserProfile(
            full_name="Test",
            email="test@test.com",
            experiences=[
                Experience(
                    company="Old",
                    role="Dev",
                    start_date=datetime(2018, 1, 1),
                    end_date=datetime(2019, 12, 31),
                ),
                Experience(
                    company="Newer",
                    role="Senior Dev",
                    start_date=datetime(2020, 1, 1),
                    end_date=datetime(2022, 12, 31),
                ),
            ],
        )

        exp = creator._get_current_experience(profile)

        assert exp is not None
        assert exp.company == "Newer"  # Most recent by start_date


# =============================================================================
# DEPENDENCY INJECTION TESTS
# =============================================================================


class TestDependencyInjection:
    """Tests for singleton pattern and dependency injection."""

    def test_reset_creator(self) -> None:
        """Should reset global instance."""
        reset_creator()
        # Should not raise

    @pytest.mark.asyncio
    async def test_get_creator_creates_singleton(self) -> None:
        """Should create singleton on first call."""
        reset_creator()

        # Patch source modules per LL-021
        with (
            patch("src.modules.collector.get_collector") as mock_get_collector,
            patch("src.services.llm_service.get_llm_service") as mock_get_llm,
        ):
            # Setup mocks
            mock_collector = Mock()
            mock_collector.get_profile = Mock(return_value=Mock())
            mock_get_collector.return_value = mock_collector

            mock_llm = AsyncMock()
            mock_llm.health_check = AsyncMock(
                return_value=Mock(status="healthy")
            )
            mock_get_llm.return_value = mock_llm

            from src.modules.creator import get_creator

            creator = await get_creator()

            assert creator is not None
            mock_get_collector.assert_called_once()
            mock_get_llm.assert_called_once()

        reset_creator()


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_profile_with_no_experiences(
        self, mock_llm_service
    ) -> None:
        """Should handle profile with no experiences."""
        profile = UserProfile(
            full_name="New Grad",
            email="newgrad@test.com",
            title="Junior Developer",
            years_experience=0,
            skills=[Skill(name="Python")],
            education=[
                Education(
                    institution="University",
                    degree="BS",
                    field="CS",
                    start_date=datetime(2020, 9, 1),
                    end_date=datetime(2024, 5, 15),
                ),
            ],
        )

        collector = Mock()
        collector.get_profile.return_value = profile

        mock_llm_service.generate_json.side_effect = [
            {"summary": "New graduate summary"},
            {
                "opening": "Opening",
                "body_paragraphs": ["Body"],
                "closing": "Closing",
            },
        ]

        creator = Creator(collector, mock_llm_service)
        await creator.initialize()

        analysis = AnalysisResult(
            job_id="job-1",
            job_title="Junior Developer",
            company_name="StartupCo",
            compatibility=CompatibilityScore(overall=60.0, level=MatchLevel.MODERATE),
            skill_matches=[],
            experience_matches=[],
            gaps=[],
        )

        content = await creator.create_content(analysis)

        assert content.cv is not None
        # Should only have education sections
        exp_sections = [
            s for s in content.cv.sections if s.section_type == "experience"
        ]
        assert len(exp_sections) == 0

    @pytest.mark.asyncio
    async def test_profile_with_no_education(
        self, mock_llm_service
    ) -> None:
        """Should handle profile with no education."""
        profile = UserProfile(
            full_name="Self Taught",
            email="selftaught@test.com",
            title="Developer",
            years_experience=5,
            skills=[Skill(name="Python")],
            experiences=[
                Experience(
                    company="TechCo",
                    role="Developer",
                    start_date=datetime(2019, 1, 1),
                    current=True,
                    achievements=["Achievement 1"],
                ),
            ],
        )

        collector = Mock()
        collector.get_profile.return_value = profile

        mock_llm_service.generate_json.side_effect = [
            {"summary": "Self-taught developer summary"},
            {"title": "Dev", "bullet_points": ["Did stuff"]},
            {
                "opening": "Opening",
                "body_paragraphs": ["Body"],
                "closing": "Closing",
            },
        ]

        creator = Creator(collector, mock_llm_service)
        await creator.initialize()

        analysis = AnalysisResult(
            job_id="job-2",
            job_title="Developer",
            company_name="Co",
            compatibility=CompatibilityScore(overall=70.0, level=MatchLevel.STRONG),
            skill_matches=[],
            experience_matches=[],
            gaps=[],
        )

        content = await creator.create_content(analysis)

        assert content.cv is not None
        # Should only have experience sections
        edu_sections = [
            s for s in content.cv.sections if s.section_type == "education"
        ]
        assert len(edu_sections) == 0

    @pytest.mark.asyncio
    async def test_empty_strategy_fields(
        self, initialized_creator: Creator
    ) -> None:
        """Should handle empty strategy fields."""
        analysis = AnalysisResult(
            job_id="job-3",
            job_title="Developer",
            company_name="Co",
            compatibility=CompatibilityScore(overall=65.0, level=MatchLevel.MODERATE),
            skill_matches=[],
            experience_matches=[],
            gaps=[],
            strategy=ApplicationStrategy(
                positioning="",  # Empty positioning
                key_strengths=[],  # Empty strengths
                address_gaps=[],
                tone="professional",
                keywords_to_use=[],
                opening_hook=None,
            ),
        )

        initialized_creator._llm.generate_json.side_effect = [
            {"summary": "Summary"},
            {"title": "Dev", "bullet_points": ["Did stuff"]},
            {"title": "Dev", "bullet_points": ["Did stuff"]},
            {
                "opening": "Opening",
                "body_paragraphs": ["Body"],
                "closing": "Closing",
            },
        ]

        content = await initialized_creator.create_content(analysis)

        assert content is not None
        assert content.cv is not None
        assert content.cover_letter is not None
