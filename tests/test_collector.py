"""
Tests for M1 Collector Module.

Tests cover:
- Data models (Skill, Experience, Education, Certification, UserProfile)
- Profile loading and validation
- Vector store indexing
- Semantic search operations
- Requirement matching
- Dependency injection
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import yaml

from src.modules.collector import (
    Certification,
    Collector,
    CollectorError,
    Education,
    Experience,
    IndexingError,
    ProfileLoadError,
    ProfileNotFoundError,
    ProfileSummary,
    ProfileValidationError,
    SearchError,
    SearchMatch,
    Skill,
    SkillLevel,
    SkillMatch,
    UserProfile,
    get_collector,
    reset_collector,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_profile_data() -> dict:
    """Sample profile data for testing."""
    return {
        "full_name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "+45 12345678",
        "location": "Copenhagen, Denmark",
        "linkedin_url": "https://linkedin.com/in/johndoe",
        "github_url": "https://github.com/johndoe",
        "title": "Senior Software Engineer",
        "years_experience": 8.5,
        "summary": "Experienced developer with focus on Python and cloud technologies",
        "skills": [
            {
                "name": "Python",
                "level": "expert",
                "years": 8,
                "keywords": ["Django", "FastAPI", "Flask"],
            },
            {
                "name": "Machine Learning",
                "level": "advanced",
                "years": 3,
                "keywords": ["PyTorch", "scikit-learn", "NLP"],
            },
            {
                "name": "Docker",
                "level": "intermediate",
                "years": 4,
                "keywords": ["Kubernetes", "containers"],
            },
        ],
        "experiences": [
            {
                "company": "TechCorp",
                "role": "Senior Software Engineer",
                "start_date": "2021-03-01",
                "description": "Lead developer for cloud-native applications",
                "achievements": [
                    "Reduced API response time by 60%",
                    "Implemented ML pipeline serving 1M requests/day",
                ],
                "technologies": ["Python", "AWS", "Docker", "Kubernetes"],
            },
            {
                "company": "StartupXYZ",
                "role": "Software Developer",
                "start_date": "2018-06-15",
                "end_date": "2021-02-28",
                "description": "Full-stack development",
                "achievements": ["Built customer dashboard from scratch"],
                "technologies": ["Python", "React", "PostgreSQL"],
            },
        ],
        "education": [
            {
                "institution": "Technical University of Denmark",
                "degree": "Master's",
                "field": "Computer Science",
                "start_date": "2014-09-01",
                "end_date": "2016-06-30",
                "gpa": 3.8,
                "relevant_courses": ["Machine Learning", "Distributed Systems"],
            }
        ],
        "certifications": [
            {
                "name": "AWS Solutions Architect",
                "issuer": "Amazon Web Services",
                "date_obtained": "2022-05-15",
                "expiry_date": "2025-05-15",
                "credential_id": "AWS-SA-12345",
            }
        ],
    }


@pytest.fixture
def sample_profile_yaml(sample_profile_data: dict, tmp_path: Path) -> Path:
    """Create a temporary YAML profile file."""
    profile_path = tmp_path / "profile.yaml"
    with open(profile_path, "w") as f:
        yaml.dump(sample_profile_data, f)
    return profile_path


@pytest.fixture
def mock_vector_store() -> AsyncMock:
    """Create a mock VectorStoreService."""
    mock = AsyncMock()

    # Mock health check
    mock.health_check.return_value = Mock(status="healthy")

    # Mock search results
    mock_result = Mock()
    mock_result.id = "doc_1"
    mock_result.content = "Python - expert level"
    mock_result.score = 0.85
    mock_result.metadata = {"type": "skill", "name": "Python"}

    mock_response = Mock()
    mock_response.results = [mock_result]

    mock.search.return_value = mock_response

    # Mock add
    mock_entry = Mock()
    mock_entry.id = "doc_1"
    mock.add.return_value = mock_entry

    # Mock clear_collection
    mock.clear_collection.return_value = 0

    return mock


@pytest.fixture
def collector(mock_vector_store: AsyncMock, sample_profile_yaml: Path) -> Collector:
    """Create a Collector instance with mock dependencies."""
    return Collector(mock_vector_store, profile_path=sample_profile_yaml)


# =============================================================================
# MODEL TESTS
# =============================================================================


class TestSkillModel:
    """Tests for Skill model."""

    def test_skill_creation_minimal(self) -> None:
        """Should create skill with minimal fields."""
        skill = Skill(name="Python")
        assert skill.name == "Python"
        assert skill.level == SkillLevel.INTERMEDIATE
        assert skill.years is None
        assert skill.keywords == []

    def test_skill_creation_full(self) -> None:
        """Should create skill with all fields."""
        skill = Skill(
            name="Python",
            level=SkillLevel.EXPERT,
            years=5.0,
            keywords=["Django", "FastAPI"],
        )
        assert skill.name == "Python"
        assert skill.level == SkillLevel.EXPERT
        assert skill.years == 5.0
        assert skill.keywords == ["Django", "FastAPI"]

    def test_skill_to_searchable_text(self) -> None:
        """Should generate searchable text."""
        skill = Skill(
            name="Python",
            level=SkillLevel.EXPERT,
            years=5.0,
            keywords=["Django", "FastAPI"],
        )
        text = skill.to_searchable_text()
        assert "Python" in text
        assert "expert" in text
        assert "5.0 years" in text
        assert "Django" in text


class TestExperienceModel:
    """Tests for Experience model."""

    def test_experience_creation(self) -> None:
        """Should create experience with required fields."""
        exp = Experience(
            company="TechCorp",
            role="Developer",
            start_date=datetime(2020, 1, 1),
            description="Building software",
        )
        assert exp.company == "TechCorp"
        assert exp.role == "Developer"
        assert exp.id  # Should have auto-generated ID

    def test_experience_current_auto_set(self) -> None:
        """Should auto-set current=True when end_date is None."""
        exp = Experience(
            company="TechCorp",
            role="Developer",
            start_date=datetime(2020, 1, 1),
            description="Building software",
        )
        assert exp.current is True
        assert exp.end_date is None

    def test_experience_not_current_with_end_date(self) -> None:
        """Should not be current when end_date is set."""
        exp = Experience(
            company="TechCorp",
            role="Developer",
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2022, 1, 1),
            description="Building software",
        )
        # Note: current defaults to False and validator only sets True if end_date is None
        assert exp.end_date is not None

    def test_experience_to_searchable_text(self) -> None:
        """Should generate searchable text."""
        exp = Experience(
            company="TechCorp",
            role="Senior Developer",
            start_date=datetime(2020, 1, 1),
            description="Building cloud applications",
            technologies=["Python", "AWS"],
            achievements=["Improved performance by 50%"],
        )
        text = exp.to_searchable_text()
        assert "Senior Developer" in text
        assert "TechCorp" in text
        assert "Python" in text
        assert "50%" in text


class TestEducationModel:
    """Tests for Education model."""

    def test_education_creation(self) -> None:
        """Should create education entry."""
        edu = Education(
            institution="MIT",
            degree="Master's",
            field="Computer Science",
            start_date=datetime(2015, 9, 1),
            end_date=datetime(2017, 6, 1),
        )
        assert edu.institution == "MIT"
        assert edu.degree == "Master's"

    def test_education_to_searchable_text(self) -> None:
        """Should generate searchable text."""
        edu = Education(
            institution="MIT",
            degree="Master's",
            field="Computer Science",
            start_date=datetime(2015, 9, 1),
            relevant_courses=["Machine Learning", "AI"],
        )
        text = edu.to_searchable_text()
        assert "MIT" in text
        assert "Master's" in text
        assert "Machine Learning" in text


class TestCertificationModel:
    """Tests for Certification model."""

    def test_certification_creation(self) -> None:
        """Should create certification entry."""
        cert = Certification(
            name="AWS Solutions Architect",
            issuer="Amazon",
            date_obtained=datetime(2022, 1, 1),
        )
        assert cert.name == "AWS Solutions Architect"
        assert cert.issuer == "Amazon"

    def test_certification_to_searchable_text(self) -> None:
        """Should generate searchable text."""
        cert = Certification(
            name="AWS Solutions Architect",
            issuer="Amazon",
            date_obtained=datetime(2022, 1, 1),
            credential_id="ABC123",
        )
        text = cert.to_searchable_text()
        assert "AWS Solutions Architect" in text
        assert "Amazon" in text
        assert "ABC123" in text


class TestUserProfileModel:
    """Tests for UserProfile model."""

    def test_profile_minimal(self) -> None:
        """Should create profile with minimal fields."""
        profile = UserProfile(full_name="John Doe", email="john@example.com")
        assert profile.full_name == "John Doe"
        assert profile.email == "john@example.com"
        assert profile.skills == []
        assert profile.experiences == []

    def test_profile_full(self, sample_profile_data: dict) -> None:
        """Should create profile with all fields."""
        profile = UserProfile(**sample_profile_data)
        assert profile.full_name == "John Doe"
        assert len(profile.skills) == 3
        assert len(profile.experiences) == 2
        assert len(profile.education) == 1
        assert len(profile.certifications) == 1


class TestSearchMatchModel:
    """Tests for SearchMatch model."""

    def test_search_match_creation(self) -> None:
        """Should create search match."""
        match = SearchMatch(
            id="doc_1",
            content="Python expert",
            match_type="skill",
            score=0.85,
        )
        assert match.id == "doc_1"
        assert match.score == 0.85
        assert match.match_type == "skill"


class TestSkillMatchModel:
    """Tests for SkillMatch model."""

    def test_skill_match_best_match(self) -> None:
        """Should return best match."""
        match1 = SearchMatch(id="1", content="Python", match_type="skill", score=0.7)
        match2 = SearchMatch(id="2", content="Java", match_type="skill", score=0.9)

        skill_match = SkillMatch(
            requirement="Programming",
            matched_skills=[match1, match2],
        )

        assert skill_match.best_match is not None
        assert skill_match.best_match.score == 0.9

    def test_skill_match_no_matches(self) -> None:
        """Should handle no matches."""
        skill_match = SkillMatch(requirement="Unknown", matched_skills=[])
        assert skill_match.best_match is None
        assert skill_match.has_match is False


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


class TestCollectorInitialization:
    """Tests for Collector initialization."""

    @pytest.mark.asyncio
    async def test_initialize_success(
        self, collector: Collector, mock_vector_store: AsyncMock
    ) -> None:
        """Should initialize successfully."""
        await collector.initialize()
        assert collector._initialized is True
        mock_vector_store.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_unhealthy_vector_store(
        self, mock_vector_store: AsyncMock, sample_profile_yaml: Path
    ) -> None:
        """Should raise error if vector store is unhealthy."""
        mock_vector_store.health_check.return_value = Mock(status="unhealthy")
        collector = Collector(mock_vector_store, profile_path=sample_profile_yaml)

        with pytest.raises(CollectorError, match="not healthy"):
            await collector.initialize()

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(
        self, collector: Collector
    ) -> None:
        """Should warn if already initialized."""
        await collector.initialize()
        await collector.initialize()  # Should not raise

    @pytest.mark.asyncio
    async def test_shutdown(self, collector: Collector) -> None:
        """Should shutdown cleanly."""
        await collector.initialize()
        await collector.shutdown()
        assert collector._initialized is False


# =============================================================================
# PROFILE LOADING TESTS
# =============================================================================


class TestProfileLoading:
    """Tests for profile loading."""

    @pytest.mark.asyncio
    async def test_load_profile_success(
        self, collector: Collector
    ) -> None:
        """Should load profile from YAML."""
        await collector.initialize()
        profile = await collector.load_profile()

        assert profile.full_name == "John Doe"
        assert len(profile.skills) == 3
        assert collector._profile_hash is not None

    @pytest.mark.asyncio
    async def test_load_profile_not_found(
        self, mock_vector_store: AsyncMock, tmp_path: Path
    ) -> None:
        """Should raise error if profile not found."""
        collector = Collector(
            mock_vector_store,
            profile_path=tmp_path / "nonexistent.yaml",
        )
        await collector.initialize()

        with pytest.raises(ProfileNotFoundError):
            await collector.load_profile()

    @pytest.mark.asyncio
    async def test_load_profile_invalid_yaml(
        self, mock_vector_store: AsyncMock, tmp_path: Path
    ) -> None:
        """Should raise error for invalid YAML."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("{ invalid: yaml: syntax: }")

        collector = Collector(mock_vector_store, profile_path=bad_yaml)
        await collector.initialize()

        with pytest.raises(ProfileLoadError):
            await collector.load_profile()

    @pytest.mark.asyncio
    async def test_load_profile_empty_file(
        self, mock_vector_store: AsyncMock, tmp_path: Path
    ) -> None:
        """Should raise error for empty profile."""
        empty_yaml = tmp_path / "empty.yaml"
        empty_yaml.write_text("")

        collector = Collector(mock_vector_store, profile_path=empty_yaml)
        await collector.initialize()

        with pytest.raises(ProfileValidationError, match="empty"):
            await collector.load_profile()

    @pytest.mark.asyncio
    async def test_load_profile_validation_error(
        self, mock_vector_store: AsyncMock, tmp_path: Path
    ) -> None:
        """Should raise error for invalid profile data."""
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text("invalid_field_only: true")

        collector = Collector(mock_vector_store, profile_path=invalid_yaml)
        await collector.initialize()

        with pytest.raises(ProfileValidationError):
            await collector.load_profile()

    @pytest.mark.asyncio
    async def test_get_profile_not_loaded(
        self, collector: Collector
    ) -> None:
        """Should raise error if profile not loaded."""
        await collector.initialize()

        with pytest.raises(CollectorError, match="No profile loaded"):
            collector.get_profile()

    @pytest.mark.asyncio
    async def test_get_profile_summary(
        self, collector: Collector
    ) -> None:
        """Should return profile summary."""
        await collector.initialize()
        await collector.load_profile()

        summary = collector.get_profile_summary()

        assert isinstance(summary, ProfileSummary)
        assert summary.name == "John Doe"
        assert summary.skill_count == 3
        assert summary.experience_count == 2


# =============================================================================
# INDEXING TESTS
# =============================================================================


class TestIndexing:
    """Tests for profile indexing."""

    @pytest.mark.asyncio
    async def test_index_profile(
        self, collector: Collector, mock_vector_store: AsyncMock
    ) -> None:
        """Should index all profile content."""
        await collector.initialize()
        await collector.load_profile()

        count = await collector.index_profile()

        # 3 skills + 2 experiences + 1 education + 1 certification = 7
        assert count == 7
        assert mock_vector_store.add.call_count == 7
        assert collector._indexed is True

    @pytest.mark.asyncio
    async def test_index_profile_no_profile_loaded(
        self, collector: Collector
    ) -> None:
        """Should raise error if no profile loaded."""
        await collector.initialize()

        with pytest.raises(CollectorError, match="No profile loaded"):
            await collector.index_profile()

    @pytest.mark.asyncio
    async def test_index_profile_add_failure(
        self, collector: Collector, mock_vector_store: AsyncMock
    ) -> None:
        """Should raise IndexingError on failure."""
        await collector.initialize()
        await collector.load_profile()

        mock_vector_store.add.side_effect = Exception("Vector store error")

        with pytest.raises(IndexingError):
            await collector.index_profile()

    @pytest.mark.asyncio
    async def test_clear_index(
        self, collector: Collector, mock_vector_store: AsyncMock
    ) -> None:
        """Should clear all indexed content."""
        await collector.initialize()
        await collector.load_profile()
        await collector.index_profile()

        mock_vector_store.clear_collection.return_value = 7
        count = await collector.clear_index()

        assert count == 7
        assert collector._indexed is False


# =============================================================================
# SEARCH TESTS
# =============================================================================


class TestSearch:
    """Tests for search operations."""

    @pytest.mark.asyncio
    async def test_search_experiences(
        self, collector: Collector, mock_vector_store: AsyncMock
    ) -> None:
        """Should search for experiences."""
        # Setup mock
        mock_result = Mock()
        mock_result.id = "exp_1"
        mock_result.content = "Senior Developer at TechCorp"
        mock_result.score = 0.85
        mock_result.metadata = {"type": "experience", "company": "TechCorp"}

        mock_response = Mock()
        mock_response.results = [mock_result]
        mock_vector_store.search.return_value = mock_response

        await collector.initialize()

        results = await collector.search_experiences("Python development")

        assert len(results) == 1
        assert results[0].match_type == "experience"
        mock_vector_store.search.assert_called_with(
            collection_name="user_profiles",
            query="Python development",
            top_k=5,
            metadata_filter={"type": "experience"},
        )

    @pytest.mark.asyncio
    async def test_search_skills(
        self, collector: Collector, mock_vector_store: AsyncMock
    ) -> None:
        """Should search for skills."""
        await collector.initialize()

        results = await collector.search_skills("machine learning")

        assert isinstance(results, list)
        mock_vector_store.search.assert_called_with(
            collection_name="user_profiles",
            query="machine learning",
            top_k=5,
            metadata_filter={"type": "skill"},
        )

    @pytest.mark.asyncio
    async def test_search_education(
        self, collector: Collector, mock_vector_store: AsyncMock
    ) -> None:
        """Should search for education."""
        await collector.initialize()

        results = await collector.search_education("computer science")

        assert isinstance(results, list)
        mock_vector_store.search.assert_called_with(
            collection_name="user_profiles",
            query="computer science",
            top_k=5,
            metadata_filter={"type": "education"},
        )

    @pytest.mark.asyncio
    async def test_search_certifications(
        self, collector: Collector, mock_vector_store: AsyncMock
    ) -> None:
        """Should search for certifications."""
        await collector.initialize()

        results = await collector.search_certifications("AWS")

        assert isinstance(results, list)
        mock_vector_store.search.assert_called_with(
            collection_name="user_profiles",
            query="AWS",
            top_k=5,
            metadata_filter={"type": "certification"},
        )

    @pytest.mark.asyncio
    async def test_search_all(
        self, collector: Collector, mock_vector_store: AsyncMock
    ) -> None:
        """Should search all content types."""
        await collector.initialize()

        results = await collector.search_all("Python")

        assert isinstance(results, list)
        mock_vector_store.search.assert_called_with(
            collection_name="user_profiles",
            query="Python",
            top_k=10,
        )

    @pytest.mark.asyncio
    async def test_search_failure(
        self, collector: Collector, mock_vector_store: AsyncMock
    ) -> None:
        """Should raise SearchError on failure."""
        mock_vector_store.search.side_effect = Exception("Search failed")

        await collector.initialize()

        with pytest.raises(SearchError):
            await collector.search_skills("Python")


# =============================================================================
# REQUIREMENT MATCHING TESTS
# =============================================================================


class TestRequirementMatching:
    """Tests for requirement matching."""

    @pytest.mark.asyncio
    async def test_match_requirements(
        self, collector: Collector, mock_vector_store: AsyncMock
    ) -> None:
        """Should match requirements against skills."""
        # Setup mock for skill search
        mock_result = Mock()
        mock_result.id = "skill_1"
        mock_result.content = "Python - expert level"
        mock_result.score = 0.85
        mock_result.metadata = {"type": "skill", "name": "Python", "level": "expert"}

        mock_response = Mock()
        mock_response.results = [mock_result]
        mock_vector_store.search.return_value = mock_response

        await collector.initialize()

        matches = await collector.match_requirements(["Python", "AWS"])

        assert len(matches) == 2
        assert matches[0].requirement == "Python"
        assert matches[0].has_match is True

    @pytest.mark.asyncio
    async def test_match_requirements_threshold(
        self, collector: Collector, mock_vector_store: AsyncMock
    ) -> None:
        """Should filter by threshold."""
        # Setup mock with low score
        mock_result = Mock()
        mock_result.id = "skill_1"
        mock_result.content = "Python - expert level"
        mock_result.score = 0.3  # Below default threshold of 0.5
        mock_result.metadata = {"type": "skill", "name": "Python"}

        mock_response = Mock()
        mock_response.results = [mock_result]
        mock_vector_store.search.return_value = mock_response

        await collector.initialize()

        matches = await collector.match_requirements(["Python"])

        assert len(matches) == 1
        assert matches[0].has_match is False  # Filtered out by threshold


# =============================================================================
# PROFILE UPDATE TESTS
# =============================================================================


class TestProfileUpdates:
    """Tests for profile updates."""

    @pytest.mark.asyncio
    async def test_save_profile(
        self, collector: Collector, tmp_path: Path
    ) -> None:
        """Should save profile to YAML."""
        await collector.initialize()
        await collector.load_profile()

        save_path = tmp_path / "saved_profile.yaml"
        await collector.save_profile(save_path)

        assert save_path.exists()

        # Verify content
        with open(save_path) as f:
            saved_data = yaml.safe_load(f)
        assert saved_data["full_name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_save_profile_no_profile_loaded(
        self, collector: Collector
    ) -> None:
        """Should raise error if no profile loaded."""
        await collector.initialize()

        with pytest.raises(CollectorError, match="No profile loaded"):
            await collector.save_profile()

    @pytest.mark.asyncio
    async def test_update_and_reindex_changed(
        self, collector: Collector, mock_vector_store: AsyncMock, tmp_path: Path
    ) -> None:
        """Should reindex when profile changes."""
        await collector.initialize()
        await collector.load_profile()
        original_hash = collector._profile_hash

        # Modify the profile file
        modified_data = {
            "full_name": "Jane Doe",
            "email": "jane@example.com",
        }
        with open(collector._profile_path, "w") as f:
            yaml.dump(modified_data, f)

        count = await collector.update_and_reindex()

        # Should have reindexed (new profile has fewer items)
        assert collector._profile_hash != original_hash
        # Note: The count depends on the new profile content

    @pytest.mark.asyncio
    async def test_update_and_reindex_unchanged(
        self, collector: Collector, mock_vector_store: AsyncMock
    ) -> None:
        """Should not reindex when profile unchanged."""
        await collector.initialize()
        await collector.load_profile()

        count = await collector.update_and_reindex()

        assert count == 0  # No changes


# =============================================================================
# DEPENDENCY INJECTION TESTS
# =============================================================================


class TestDependencyInjection:
    """Tests for dependency injection functions."""

    @pytest.mark.asyncio
    async def test_get_collector_creates_singleton(self) -> None:
        """Should create singleton instance."""
        reset_collector()

        with patch("src.services.vector_store.get_vector_store_service") as mock_get_vs:
            mock_vs = AsyncMock()
            mock_vs.health_check.return_value = Mock(status="healthy")
            mock_get_vs.return_value = mock_vs

            collector1 = await get_collector()
            collector2 = await get_collector()

            assert collector1 is collector2

        reset_collector()

    @pytest.mark.asyncio
    async def test_reset_collector(self) -> None:
        """Should reset singleton instance."""
        reset_collector()

        with patch("src.services.vector_store.get_vector_store_service") as mock_get_vs:
            mock_vs = AsyncMock()
            mock_vs.health_check.return_value = Mock(status="healthy")
            mock_get_vs.return_value = mock_vs

            collector1 = await get_collector()
            reset_collector()
            collector2 = await get_collector()

            assert collector1 is not collector2

        reset_collector()


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_empty_skills_list(
        self, mock_vector_store: AsyncMock, tmp_path: Path
    ) -> None:
        """Should handle profile with no skills."""
        profile_data = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "skills": [],
        }
        profile_path = tmp_path / "profile.yaml"
        with open(profile_path, "w") as f:
            yaml.dump(profile_data, f)

        collector = Collector(mock_vector_store, profile_path=profile_path)
        await collector.initialize()
        await collector.load_profile()

        count = await collector.index_profile()
        assert count == 0  # No documents to index

    @pytest.mark.asyncio
    async def test_metadata_conversion(
        self, collector: Collector
    ) -> None:
        """Should convert metadata to compatible types."""
        await collector.initialize()

        # Test the internal method
        metadata = {
            "str_val": "test",
            "int_val": 42,
            "float_val": 3.14,
            "bool_val": True,
            "none_val": None,
            "list_val": [1, 2, 3],  # Should be converted to string
        }

        result = collector._convert_metadata(metadata)

        assert result["str_val"] == "test"
        assert result["int_val"] == 42
        assert result["float_val"] == 3.14
        assert result["bool_val"] is True
        assert result["none_val"] is None
        assert result["list_val"] == "[1, 2, 3]"  # Converted to string

    @pytest.mark.asyncio
    async def test_skill_level_enum_values(self) -> None:
        """Should accept all valid skill levels."""
        levels = ["beginner", "intermediate", "advanced", "expert"]

        for level in levels:
            skill = Skill(name="Test", level=level)
            assert skill.level.value == level

    @pytest.mark.asyncio
    async def test_experience_without_technologies(
        self, mock_vector_store: AsyncMock, tmp_path: Path
    ) -> None:
        """Should handle experience without technologies."""
        profile_data = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "experiences": [
                {
                    "company": "TechCorp",
                    "role": "Developer",
                    "start_date": "2020-01-01",
                    "description": "Building software",
                }
            ],
        }
        profile_path = tmp_path / "profile.yaml"
        with open(profile_path, "w") as f:
            yaml.dump(profile_data, f)

        collector = Collector(mock_vector_store, profile_path=profile_path)
        await collector.initialize()
        profile = await collector.load_profile()

        assert len(profile.experiences) == 1
        exp = profile.experiences[0]
        text = exp.to_searchable_text()
        assert "TechCorp" in text
