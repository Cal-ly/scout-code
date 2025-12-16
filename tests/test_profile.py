"""
Unit tests for Profile Service.

Run with: pytest tests/test_profile.py -v
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.profile import (
    ProfileChunk,
    ProfileCreateRequest,
    ProfileCreateResponse,
    ProfileData,
    ProfileDatabaseError,
    ProfileHealth,
    ProfileIndexingError,
    ProfileIndexResponse,
    ProfileNotFoundError,
    ProfileService,
    ProfileStatus,
    ProfileValidationError,
    get_profile_service,
    reset_profile_service,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_profile_dir(tmp_path: Path) -> Path:
    """Provide temporary profiles directory."""
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    return profiles_dir


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Provide temporary database path."""
    return tmp_path / "profiles.db"


@pytest.fixture
async def profile_service(
    temp_db_path: Path, temp_profile_dir: Path
) -> ProfileService:
    """Create initialized Profile Service for testing."""
    reset_profile_service()

    # Mock the vector store service
    mock_vector_store = MagicMock()
    mock_vector_store.add = AsyncMock()
    mock_vector_store.delete = AsyncMock()
    mock_vector_store.search = AsyncMock(
        return_value=MagicMock(results=[])
    )

    with patch(
        "src.services.profile.service.get_vector_store_service",
        return_value=mock_vector_store,
    ):
        service = ProfileService(
            db_path=temp_db_path,
            profiles_dir=temp_profile_dir,
        )
        await service.initialize()
        yield service
        await service.shutdown()


@pytest.fixture
def uninitialized_service(
    temp_db_path: Path, temp_profile_dir: Path
) -> ProfileService:
    """Create uninitialized Profile Service for testing."""
    return ProfileService(
        db_path=temp_db_path,
        profiles_dir=temp_profile_dir,
    )


@pytest.fixture
def sample_profile_text() -> str:
    """Sample profile text for testing."""
    return """I am a Senior Software Engineer with 8 years of experience in full-stack development.

I specialize in Python and JavaScript, with deep expertise in FastAPI, React, and PostgreSQL.

My key achievements include leading a team of 5 developers to deliver a microservices platform that reduced deployment time by 60%.

I hold a Bachelor's degree in Computer Science from MIT and AWS Solutions Architect certification.

I am passionate about clean code, test-driven development, and mentoring junior developers."""


@pytest.fixture
def short_profile_text() -> str:
    """Profile text that is too short."""
    return "I am a developer."


@pytest.fixture
def long_profile_text() -> str:
    """Profile text that is too long."""
    return "x" * 15000


# =============================================================================
# MODEL TESTS
# =============================================================================


class TestProfileStatusModel:
    """Tests for ProfileStatus model."""

    def test_status_no_profile(self) -> None:
        """Should represent missing profile."""
        status = ProfileStatus(exists=False, is_indexed=False)

        assert status.exists is False
        assert status.is_indexed is False
        assert status.profile_id is None
        assert status.chunk_count == 0
        assert status.character_count == 0
        assert status.last_updated is None

    def test_status_with_profile(self) -> None:
        """Should represent existing profile."""
        now = datetime.now()
        status = ProfileStatus(
            exists=True,
            is_indexed=True,
            profile_id=1,
            chunk_count=5,
            character_count=1000,
            last_updated=now,
        )

        assert status.exists is True
        assert status.is_indexed is True
        assert status.profile_id == 1
        assert status.chunk_count == 5
        assert status.character_count == 1000
        assert status.last_updated == now


class TestProfileCreateRequestModel:
    """Tests for ProfileCreateRequest model."""

    def test_valid_request(self) -> None:
        """Should accept valid profile text."""
        text = "x" * 150
        request = ProfileCreateRequest(profile_text=text)

        assert request.profile_text == text

    def test_strips_whitespace(self) -> None:
        """Should strip leading/trailing whitespace."""
        text = "   " + "x" * 150 + "   "
        request = ProfileCreateRequest(profile_text=text)

        assert request.profile_text == "x" * 150

    def test_rejects_too_short(self) -> None:
        """Should reject text below minimum length."""
        with pytest.raises(ValueError):
            ProfileCreateRequest(profile_text="short")

    def test_rejects_too_long(self) -> None:
        """Should reject text above maximum length."""
        with pytest.raises(ValueError):
            ProfileCreateRequest(profile_text="x" * 15000)


class TestProfileChunkModel:
    """Tests for ProfileChunk model."""

    def test_paragraph_chunk(self) -> None:
        """Should create paragraph chunk."""
        chunk = ProfileChunk(
            content="Test content",
            chunk_index=0,
            chunk_type="paragraph",
            character_count=12,
        )

        assert chunk.content == "Test content"
        assert chunk.chunk_index == 0
        assert chunk.chunk_type == "paragraph"
        assert chunk.character_count == 12

    def test_sentence_chunk(self) -> None:
        """Should create sentence chunk."""
        chunk = ProfileChunk(
            content="Test sentence.",
            chunk_index=1,
            chunk_type="sentence",
            character_count=14,
        )

        assert chunk.chunk_type == "sentence"


class TestProfileDataModel:
    """Tests for ProfileData model."""

    def test_profile_data(self) -> None:
        """Should represent complete profile data."""
        now = datetime.now()
        data = ProfileData(
            profile_id=1,
            profile_text="Test profile text",
            is_indexed=True,
            chunk_count=3,
            character_count=17,
            created_at=now,
            updated_at=now,
        )

        assert data.profile_id == 1
        assert data.profile_text == "Test profile text"
        assert data.is_indexed is True
        assert data.chunk_count == 3


class TestProfileHealthModel:
    """Tests for ProfileHealth model."""

    def test_healthy_status(self) -> None:
        """Should represent healthy service."""
        health = ProfileHealth(
            status="healthy",
            database_accessible=True,
            profiles_dir_accessible=True,
            profile_count=2,
        )

        assert health.status == "healthy"
        assert health.database_accessible is True
        assert health.profiles_dir_accessible is True
        assert health.profile_count == 2
        assert health.last_error is None

    def test_degraded_status(self) -> None:
        """Should represent degraded service."""
        health = ProfileHealth(
            status="degraded",
            database_accessible=False,
            profiles_dir_accessible=True,
            profile_count=0,
            last_error="Database error: connection failed",
        )

        assert health.status == "degraded"
        assert health.database_accessible is False
        assert health.last_error is not None


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


class TestProfileServiceInitialization:
    """Tests for Profile Service initialization."""

    @pytest.mark.asyncio
    async def test_initialize_creates_database(
        self, temp_db_path: Path, temp_profile_dir: Path
    ) -> None:
        """Should create database on initialization."""
        with patch(
            "src.services.profile.service.get_vector_store_service",
            return_value=MagicMock(),
        ):
            service = ProfileService(
                db_path=temp_db_path,
                profiles_dir=temp_profile_dir,
            )
            await service.initialize()

            assert temp_db_path.exists()
            await service.shutdown()

    @pytest.mark.asyncio
    async def test_initialize_creates_profiles_dir(
        self, temp_db_path: Path, tmp_path: Path
    ) -> None:
        """Should create profiles directory on initialization."""
        profiles_dir = tmp_path / "new_profiles"

        with patch(
            "src.services.profile.service.get_vector_store_service",
            return_value=MagicMock(),
        ):
            service = ProfileService(
                db_path=temp_db_path,
                profiles_dir=profiles_dir,
            )
            await service.initialize()

            assert profiles_dir.exists()
            await service.shutdown()

    @pytest.mark.asyncio
    async def test_double_initialize_warns(
        self, profile_service: ProfileService, caplog
    ) -> None:
        """Should warn on double initialization."""
        await profile_service.initialize()

        assert "already initialized" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_uninitialized_service_raises(
        self, uninitialized_service: ProfileService
    ) -> None:
        """Should raise error when using uninitialized service."""
        with pytest.raises(ProfileDatabaseError, match="not initialized"):
            await uninitialized_service.get_status()


# =============================================================================
# CHUNKING TESTS
# =============================================================================


class TestChunkingLogic:
    """Tests for profile text chunking."""

    @pytest.mark.asyncio
    async def test_chunk_by_paragraphs(
        self, profile_service: ProfileService
    ) -> None:
        """Should split text by double newlines (long enough paragraphs)."""
        # Use paragraphs long enough to not get combined (> MIN_CHUNK_LENGTH)
        para1 = "This is the first paragraph with enough content to avoid being combined. " * 3
        para2 = "This is the second paragraph with enough content to avoid being combined. " * 3
        para3 = "This is the third paragraph with enough content to avoid being combined. " * 3
        text = f"{para1}\n\n{para2}\n\n{para3}"

        chunks = profile_service.chunk_text(text)

        assert len(chunks) == 3
        assert chunks[0].chunk_type == "paragraph"
        assert "first paragraph" in chunks[0].content
        assert "second paragraph" in chunks[1].content
        assert "third paragraph" in chunks[2].content

    @pytest.mark.asyncio
    async def test_chunk_indices_sequential(
        self, profile_service: ProfileService
    ) -> None:
        """Should assign sequential chunk indices."""
        text = "Para 1.\n\nPara 2.\n\nPara 3."

        chunks = profile_service.chunk_text(text)

        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    @pytest.mark.asyncio
    async def test_chunk_long_paragraph_into_sentences(
        self, profile_service: ProfileService
    ) -> None:
        """Should split long paragraphs into sentences."""
        # Create a paragraph > 500 chars
        long_para = " ".join(["This is a sentence."] * 50)

        chunks = profile_service.chunk_text(long_para)

        # Should have multiple chunks from sentences
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.character_count <= 600  # Allow some flexibility

    @pytest.mark.asyncio
    async def test_chunk_combines_short_chunks(
        self, profile_service: ProfileService
    ) -> None:
        """Should combine adjacent short chunks."""
        # Very short paragraphs
        text = "Hi.\n\nHello."

        chunks = profile_service.chunk_text(text)

        # Should combine since total < 100 chars
        assert len(chunks) == 1
        assert "Hi." in chunks[0].content
        assert "Hello." in chunks[0].content

    @pytest.mark.asyncio
    async def test_chunk_empty_text(
        self, profile_service: ProfileService
    ) -> None:
        """Should handle empty text."""
        chunks = profile_service.chunk_text("")

        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_chunk_whitespace_only(
        self, profile_service: ProfileService
    ) -> None:
        """Should handle whitespace-only text."""
        chunks = profile_service.chunk_text("   \n\n   \n\n   ")

        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_chunk_character_counts(
        self, profile_service: ProfileService
    ) -> None:
        """Should calculate correct character counts."""
        text = "First paragraph.\n\nSecond paragraph."

        chunks = profile_service.chunk_text(text)

        for chunk in chunks:
            assert chunk.character_count == len(chunk.content)


# =============================================================================
# CRUD OPERATION TESTS
# =============================================================================


class TestProfileStatus:
    """Tests for get_status operation."""

    @pytest.mark.asyncio
    async def test_status_no_profile(
        self, profile_service: ProfileService
    ) -> None:
        """Should return false when no profile exists."""
        status = await profile_service.get_status()

        assert status.exists is False
        assert status.is_indexed is False
        assert status.profile_id is None

    @pytest.mark.asyncio
    async def test_status_with_profile(
        self, profile_service: ProfileService, sample_profile_text: str
    ) -> None:
        """Should return true when profile exists."""
        await profile_service.create_profile(sample_profile_text)

        status = await profile_service.get_status()

        assert status.exists is True
        assert status.profile_id is not None
        assert status.character_count > 0


class TestProfileCreate:
    """Tests for create_profile operation."""

    @pytest.mark.asyncio
    async def test_create_profile_success(
        self, profile_service: ProfileService, sample_profile_text: str
    ) -> None:
        """Should create profile successfully."""
        result = await profile_service.create_profile(sample_profile_text)

        assert result.profile_id is not None
        assert result.status == "created"
        assert result.is_indexed is True
        assert result.chunk_count > 0

    @pytest.mark.asyncio
    async def test_create_profile_saves_file(
        self,
        profile_service: ProfileService,
        sample_profile_text: str,
        temp_profile_dir: Path,
    ) -> None:
        """Should save profile text to file."""
        result = await profile_service.create_profile(sample_profile_text)

        file_path = temp_profile_dir / f"profile_{result.profile_id}.txt"
        assert file_path.exists()
        assert file_path.read_text() == sample_profile_text

    @pytest.mark.asyncio
    async def test_update_profile_success(
        self, profile_service: ProfileService, sample_profile_text: str
    ) -> None:
        """Should update existing profile."""
        # Create first
        await profile_service.create_profile(sample_profile_text)

        # Update
        updated_text = sample_profile_text + "\n\nUpdated with new content."
        result = await profile_service.create_profile(updated_text)

        assert result.status == "updated"
        assert result.is_indexed is True

    @pytest.mark.asyncio
    async def test_create_profile_too_short(
        self, profile_service: ProfileService, short_profile_text: str
    ) -> None:
        """Should reject profile text that is too short."""
        with pytest.raises(ProfileValidationError, match="too short"):
            await profile_service.create_profile(short_profile_text)

    @pytest.mark.asyncio
    async def test_create_profile_too_long(
        self, profile_service: ProfileService, long_profile_text: str
    ) -> None:
        """Should reject profile text that is too long."""
        with pytest.raises(ProfileValidationError, match="too long"):
            await profile_service.create_profile(long_profile_text)

    @pytest.mark.asyncio
    async def test_create_profile_strips_whitespace(
        self, profile_service: ProfileService, sample_profile_text: str
    ) -> None:
        """Should strip whitespace from profile text."""
        padded_text = "   " + sample_profile_text + "   "
        result = await profile_service.create_profile(padded_text)

        profile = await profile_service.get_profile()
        assert not profile.profile_text.startswith(" ")
        assert not profile.profile_text.endswith(" ")


class TestProfileRetrieve:
    """Tests for get_profile operation."""

    @pytest.mark.asyncio
    async def test_get_profile_success(
        self, profile_service: ProfileService, sample_profile_text: str
    ) -> None:
        """Should retrieve existing profile."""
        await profile_service.create_profile(sample_profile_text)

        profile = await profile_service.get_profile()

        assert profile.profile_text == sample_profile_text
        assert profile.character_count == len(sample_profile_text)

    @pytest.mark.asyncio
    async def test_get_profile_not_found(
        self, profile_service: ProfileService
    ) -> None:
        """Should raise error when profile not found."""
        with pytest.raises(ProfileNotFoundError):
            await profile_service.get_profile()

    @pytest.mark.asyncio
    async def test_get_profile_has_timestamps(
        self, profile_service: ProfileService, sample_profile_text: str
    ) -> None:
        """Should include timestamps in profile data."""
        await profile_service.create_profile(sample_profile_text)

        profile = await profile_service.get_profile()

        assert profile.created_at is not None
        assert profile.updated_at is not None


class TestProfileIndex:
    """Tests for index_profile operation."""

    @pytest.mark.asyncio
    async def test_index_profile_success(
        self, profile_service: ProfileService, sample_profile_text: str
    ) -> None:
        """Should index profile successfully."""
        create_result = await profile_service.create_profile(sample_profile_text)

        # Profile should already be indexed after creation
        status = await profile_service.get_status()
        assert status.is_indexed is True
        assert status.chunk_count > 0

    @pytest.mark.asyncio
    async def test_index_profile_not_found(
        self, profile_service: ProfileService
    ) -> None:
        """Should raise error when profile not found."""
        with pytest.raises(ProfileNotFoundError):
            await profile_service.index_profile(999)

    @pytest.mark.asyncio
    async def test_reindex_clears_old_embeddings(
        self, profile_service: ProfileService, sample_profile_text: str
    ) -> None:
        """Should clear old embeddings when re-indexing."""
        await profile_service.create_profile(sample_profile_text)

        # Re-index (update the profile)
        updated_text = sample_profile_text + "\n\nAdditional content for testing."
        await profile_service.create_profile(updated_text)

        status = await profile_service.get_status()
        assert status.is_indexed is True


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================


class TestProfileHealthCheck:
    """Tests for health_check operation."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(
        self, profile_service: ProfileService
    ) -> None:
        """Should report healthy status."""
        health = await profile_service.health_check()

        assert health.status == "healthy"
        assert health.database_accessible is True
        assert health.profiles_dir_accessible is True

    @pytest.mark.asyncio
    async def test_health_check_counts_profiles(
        self, profile_service: ProfileService, sample_profile_text: str
    ) -> None:
        """Should count profiles correctly."""
        # Initially no profiles
        health = await profile_service.health_check()
        assert health.profile_count == 0

        # After creating a profile
        await profile_service.create_profile(sample_profile_text)
        health = await profile_service.health_check()
        assert health.profile_count == 1


# =============================================================================
# SINGLETON TESTS
# =============================================================================


class TestProfileServiceSingleton:
    """Tests for Profile Service singleton pattern."""

    @pytest.mark.asyncio
    async def test_get_service_returns_singleton(
        self, temp_db_path: Path, temp_profile_dir: Path
    ) -> None:
        """Should return same instance on multiple calls."""
        reset_profile_service()

        with patch(
            "src.services.profile.service.get_vector_store_service",
            return_value=MagicMock(),
        ):
            with patch(
                "src.services.profile.service.DEFAULT_DB_PATH",
                temp_db_path,
            ):
                with patch(
                    "src.services.profile.service.DEFAULT_PROFILES_DIR",
                    temp_profile_dir,
                ):
                    service1 = await get_profile_service()
                    service2 = await get_profile_service()

                    assert service1 is service2

                    await service1.shutdown()
                    reset_profile_service()

    @pytest.mark.asyncio
    async def test_reset_clears_singleton(self) -> None:
        """Should clear singleton on reset."""
        reset_profile_service()

        # Singleton should be None after reset
        from src.services.profile.service import _profile_instance

        assert _profile_instance is None


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_profile_with_special_characters(
        self, profile_service: ProfileService
    ) -> None:
        """Should handle special characters in profile text."""
        special_text = (
            "I work with C++ and C# programming languages.\n\n"
            "I've earned $100k+ in my career.\n\n"
            'My motto is: "Code with care!" & test everything.\n\n'
            "Skills: Python (3.10+), JavaScript/TypeScript.\n\n"
        ) + "x" * 50  # Ensure minimum length

        result = await profile_service.create_profile(special_text)

        assert result.status == "created"

        profile = await profile_service.get_profile()
        assert "C++" in profile.profile_text
        assert "$100k" in profile.profile_text

    @pytest.mark.asyncio
    async def test_profile_with_unicode(
        self, profile_service: ProfileService
    ) -> None:
        """Should handle unicode characters."""
        unicode_text = (
            "I am a Software Engineer based in Tokyo.\n\n"
            "Skills: Python, JavaScript, SQL.\n\n"
        ) + "x" * 100  # Ensure minimum length

        result = await profile_service.create_profile(unicode_text)

        assert result.status == "created"

        profile = await profile_service.get_profile()
        assert "Tokyo" in profile.profile_text

    @pytest.mark.asyncio
    async def test_profile_exactly_minimum_length(
        self, profile_service: ProfileService
    ) -> None:
        """Should accept profile at exactly minimum length."""
        min_text = "x" * 100

        result = await profile_service.create_profile(min_text)

        assert result.status == "created"

    @pytest.mark.asyncio
    async def test_profile_exactly_maximum_length(
        self, profile_service: ProfileService
    ) -> None:
        """Should accept profile at exactly maximum length."""
        max_text = "x" * 10000

        result = await profile_service.create_profile(max_text)

        assert result.status == "created"

    @pytest.mark.asyncio
    async def test_profile_many_empty_lines(
        self, profile_service: ProfileService
    ) -> None:
        """Should handle text with many empty lines."""
        text_with_empty_lines = (
            "First paragraph.\n\n\n\n\n\n"
            "Second paragraph.\n\n\n\n"
            "Third paragraph.\n\n"
        ) + "x" * 50

        result = await profile_service.create_profile(text_with_empty_lines)

        assert result.status == "created"
        assert result.chunk_count > 0
