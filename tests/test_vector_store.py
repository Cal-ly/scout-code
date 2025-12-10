"""
Unit tests for Vector Store Service.

Run with: pytest tests/test_vector_store.py -v

Note: First run may be slow due to embedding model download.
"""

import shutil
from pathlib import Path

import pytest

from src.services.vector_store import (
    CollectionNotFoundError,
    CollectionStats,
    DocumentNotFoundError,
    EmbeddingError,
    SearchResponse,
    SearchResult,
    VectorEntry,
    VectorStoreError,
    VectorStoreHealth,
    VectorStoreService,
    get_vector_store_service,
    reset_vector_store_service,
    shutdown_vector_store_service,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_vector_dir(tmp_path: Path) -> Path:
    """Provide temporary vector storage directory."""
    vector_dir = tmp_path / "vectors"
    vector_dir.mkdir()
    return vector_dir


@pytest.fixture
async def store(temp_vector_dir: Path) -> VectorStoreService:
    """Create initialized Vector Store Service for testing."""
    reset_vector_store_service()
    service = VectorStoreService(persist_directory=temp_vector_dir)
    await service.initialize()
    yield service
    await service.shutdown()


@pytest.fixture
def uninitialized_store(temp_vector_dir: Path) -> VectorStoreService:
    """Create uninitialized Vector Store Service for testing."""
    return VectorStoreService(persist_directory=temp_vector_dir)


# =============================================================================
# MODEL TESTS
# =============================================================================


class TestVectorEntryModel:
    """Tests for VectorEntry model."""

    def test_vector_entry_creation(self) -> None:
        """Should create a valid vector entry."""
        entry = VectorEntry(
            id="doc_1",
            content="Python developer with 5 years experience",
            metadata={"category": "developer"},
        )

        assert entry.id == "doc_1"
        assert "Python" in entry.content
        assert entry.metadata["category"] == "developer"
        assert entry.created_at is not None

    def test_vector_entry_default_metadata(self) -> None:
        """Should have empty dict as default metadata."""
        entry = VectorEntry(id="doc_1", content="test content")

        assert entry.metadata == {}


class TestSearchResultModel:
    """Tests for SearchResult model."""

    def test_search_result_creation(self) -> None:
        """Should create a valid search result."""
        result = SearchResult(
            id="doc_1",
            content="Python developer",
            score=0.85,
            metadata={"category": "developer"},
            distance=0.3,
        )

        assert result.id == "doc_1"
        assert result.score == 0.85
        assert result.is_relevant is True

    def test_search_result_relevance_threshold(self) -> None:
        """Should correctly detect relevance based on score."""
        relevant = SearchResult(id="r1", content="test", score=0.5)
        irrelevant = SearchResult(id="r2", content="test", score=0.49)

        assert relevant.is_relevant is True
        assert irrelevant.is_relevant is False


class TestSearchResponseModel:
    """Tests for SearchResponse model."""

    def test_search_response_creation(self) -> None:
        """Should create a valid search response."""
        results = [
            SearchResult(id="d1", content="test1", score=0.9),
            SearchResult(id="d2", content="test2", score=0.8),
        ]
        response = SearchResponse(
            query="test query",
            results=results,
            collection="user_profiles",
            total_results=2,
        )

        assert response.query == "test query"
        assert len(response.results) == 2
        assert response.total_results == 2


class TestCollectionStatsModel:
    """Tests for CollectionStats model."""

    def test_collection_stats_creation(self) -> None:
        """Should create valid collection stats."""
        stats = CollectionStats(
            name="user_profiles",
            count=10,
            embedding_dimension=384,
        )

        assert stats.name == "user_profiles"
        assert stats.count == 10
        assert stats.embedding_dimension == 384


class TestVectorStoreHealthModel:
    """Tests for VectorStoreHealth model."""

    def test_health_default_values(self) -> None:
        """Should have correct default values."""
        health = VectorStoreHealth()

        assert health.status == "healthy"
        assert health.initialized is False
        assert health.embedding_model == "all-MiniLM-L6-v2"
        assert health.total_documents == 0

    def test_health_is_healthy_property(self) -> None:
        """Should correctly determine healthy status."""
        healthy = VectorStoreHealth(status="healthy", initialized=True)
        unhealthy = VectorStoreHealth(status="degraded", initialized=True)
        not_init = VectorStoreHealth(status="healthy", initialized=False)

        assert healthy.is_healthy is True
        assert unhealthy.is_healthy is False
        assert not_init.is_healthy is False


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


class TestInitialization:
    """Tests for service initialization."""

    @pytest.mark.asyncio
    async def test_initialize_creates_directory(self, tmp_path: Path) -> None:
        """Should create persist directory if needed."""
        vector_dir = tmp_path / "new_vectors"
        assert not vector_dir.exists()

        store = VectorStoreService(persist_directory=vector_dir)
        await store.initialize()

        assert vector_dir.exists()
        await store.shutdown()

    @pytest.mark.asyncio
    async def test_initialize_creates_collections(
        self, store: VectorStoreService
    ) -> None:
        """Should create PoC collections."""
        collections = store.list_collections()

        assert "user_profiles" in collections
        assert "job_requirements" in collections
        assert len(collections) == 2

    @pytest.mark.asyncio
    async def test_double_initialize_warning(
        self, store: VectorStoreService, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Should warn on double initialization."""
        await store.initialize()
        assert "already initialized" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_operation_before_init_raises(
        self, uninitialized_store: VectorStoreService
    ) -> None:
        """Should raise error if not initialized."""
        with pytest.raises(VectorStoreError, match="not initialized"):
            await uninitialized_store.add(
                "user_profiles", "doc_1", "test content"
            )

    @pytest.mark.asyncio
    async def test_shutdown_clears_state(self, store: VectorStoreService) -> None:
        """Should clear state on shutdown."""
        assert store._initialized is True

        await store.shutdown()

        assert store._initialized is False
        assert store._client is None

    @pytest.mark.asyncio
    async def test_shutdown_when_not_initialized(
        self, uninitialized_store: VectorStoreService
    ) -> None:
        """Should handle shutdown when not initialized."""
        # Should not raise
        await uninitialized_store.shutdown()


# =============================================================================
# DOCUMENT OPERATIONS TESTS
# =============================================================================


class TestAddDocument:
    """Tests for adding documents."""

    @pytest.mark.asyncio
    async def test_add_document(self, store: VectorStoreService) -> None:
        """Should add a document to collection."""
        entry = await store.add(
            "user_profiles",
            "profile_1",
            "Senior Python developer with 5 years of experience",
        )

        assert entry.id == "profile_1"
        assert "Python" in entry.content
        assert entry.metadata["content_length"] == len(entry.content)

    @pytest.mark.asyncio
    async def test_add_with_metadata(self, store: VectorStoreService) -> None:
        """Should store custom metadata."""
        entry = await store.add(
            "user_profiles",
            "profile_2",
            "Java developer",
            metadata={"skill_level": "senior", "years": 10},
        )

        assert entry.metadata["skill_level"] == "senior"
        assert entry.metadata["years"] == 10

    @pytest.mark.asyncio
    async def test_add_to_invalid_collection(
        self, store: VectorStoreService
    ) -> None:
        """Should raise error for invalid collection."""
        with pytest.raises(CollectionNotFoundError, match="not found"):
            await store.add("invalid_collection", "doc_1", "content")


class TestGetDocument:
    """Tests for retrieving documents."""

    @pytest.mark.asyncio
    async def test_get_document(self, store: VectorStoreService) -> None:
        """Should retrieve a document by ID."""
        await store.add("user_profiles", "get_doc_1", "Test content for retrieval")

        entry = await store.get("user_profiles", "get_doc_1")

        assert entry.id == "get_doc_1"
        assert entry.content == "Test content for retrieval"

    @pytest.mark.asyncio
    async def test_get_nonexistent_document(
        self, store: VectorStoreService
    ) -> None:
        """Should raise error for nonexistent document."""
        with pytest.raises(DocumentNotFoundError, match="not found"):
            await store.get("user_profiles", "nonexistent_id")

    @pytest.mark.asyncio
    async def test_get_from_invalid_collection(
        self, store: VectorStoreService
    ) -> None:
        """Should raise error for invalid collection."""
        with pytest.raises(CollectionNotFoundError, match="not found"):
            await store.get("invalid_collection", "doc_1")


class TestUpdateDocument:
    """Tests for updating documents."""

    @pytest.mark.asyncio
    async def test_update_document(self, store: VectorStoreService) -> None:
        """Should update document content."""
        await store.add("user_profiles", "update_doc", "Original content")

        updated = await store.update(
            "user_profiles", "update_doc", "Updated content"
        )

        assert updated.content == "Updated content"

        # Verify in storage
        retrieved = await store.get("user_profiles", "update_doc")
        assert retrieved.content == "Updated content"

    @pytest.mark.asyncio
    async def test_update_adds_metadata(
        self, store: VectorStoreService
    ) -> None:
        """Should add new metadata on update (ChromaDB merges metadata)."""
        await store.add(
            "user_profiles",
            "meta_doc",
            "content",
            metadata={"old_key": "old_value"},
        )

        await store.update(
            "user_profiles",
            "meta_doc",
            "new content",
            metadata={"new_key": "new_value"},
        )

        retrieved = await store.get("user_profiles", "meta_doc")
        # New metadata is added
        assert "new_key" in retrieved.metadata
        # Note: ChromaDB merges metadata, old keys persist
        assert retrieved.content == "new content"

    @pytest.mark.asyncio
    async def test_update_nonexistent_document(
        self, store: VectorStoreService
    ) -> None:
        """Should raise error for nonexistent document."""
        with pytest.raises(DocumentNotFoundError, match="not found"):
            await store.update("user_profiles", "nonexistent", "content")


class TestDeleteDocument:
    """Tests for deleting documents."""

    @pytest.mark.asyncio
    async def test_delete_document(self, store: VectorStoreService) -> None:
        """Should delete a document."""
        await store.add("user_profiles", "delete_doc", "To be deleted")

        deleted = await store.delete("user_profiles", "delete_doc")

        assert deleted is True

        with pytest.raises(DocumentNotFoundError):
            await store.get("user_profiles", "delete_doc")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(
        self, store: VectorStoreService
    ) -> None:
        """Should return False for nonexistent document."""
        deleted = await store.delete("user_profiles", "nonexistent")
        assert deleted is False


# =============================================================================
# SEARCH TESTS
# =============================================================================


class TestSearch:
    """Tests for similarity search."""

    @pytest.mark.asyncio
    async def test_search_returns_results(self, store: VectorStoreService) -> None:
        """Should return relevant search results."""
        await store.add(
            "user_profiles",
            "python_dev",
            "Senior Python developer with Django and FastAPI experience",
        )
        await store.add(
            "user_profiles",
            "java_dev",
            "Java developer with Spring Boot experience",
        )
        await store.add(
            "user_profiles",
            "js_dev",
            "JavaScript frontend developer with React",
        )

        response = await store.search("user_profiles", "Python programming", top_k=3)

        assert response.total_results == 3
        assert response.query == "Python programming"
        # Python dev should be most relevant
        assert response.results[0].id == "python_dev"

    @pytest.mark.asyncio
    async def test_search_empty_collection(self, store: VectorStoreService) -> None:
        """Should return empty results for empty collection."""
        response = await store.search("user_profiles", "test query")

        assert response.total_results == 0
        assert response.results == []

    @pytest.mark.asyncio
    async def test_search_with_top_k(self, store: VectorStoreService) -> None:
        """Should respect top_k parameter."""
        # Add 5 documents
        for i in range(5):
            await store.add("user_profiles", f"doc_{i}", f"Developer profile {i}")

        response = await store.search("user_profiles", "developer", top_k=2)

        assert response.total_results == 2
        assert len(response.results) == 2

    @pytest.mark.asyncio
    async def test_search_with_metadata_filter(
        self, store: VectorStoreService
    ) -> None:
        """Should filter results by metadata."""
        await store.add(
            "user_profiles",
            "senior_python",
            "Python developer",
            metadata={"level": "senior"},
        )
        await store.add(
            "user_profiles",
            "junior_python",
            "Python developer",
            metadata={"level": "junior"},
        )

        response = await store.search(
            "user_profiles",
            "Python developer",
            metadata_filter={"level": "senior"},
        )

        assert response.total_results == 1
        assert response.results[0].id == "senior_python"

    @pytest.mark.asyncio
    async def test_search_score_range(self, store: VectorStoreService) -> None:
        """Should return scores in valid range."""
        await store.add("user_profiles", "doc_1", "Python developer")

        response = await store.search("user_profiles", "Python")

        for result in response.results:
            assert 0.0 <= result.score <= 1.0

    @pytest.mark.asyncio
    async def test_search_invalid_collection(
        self, store: VectorStoreService
    ) -> None:
        """Should raise error for invalid collection."""
        with pytest.raises(CollectionNotFoundError, match="not found"):
            await store.search("invalid_collection", "query")


class TestSearchSemanticSimilarity:
    """Tests for semantic understanding in search."""

    @pytest.mark.asyncio
    async def test_semantic_similarity(self, store: VectorStoreService) -> None:
        """Should find semantically similar content."""
        await store.add(
            "job_requirements",
            "job_1",
            "Looking for a software engineer with coding skills",
        )
        await store.add(
            "job_requirements",
            "job_2",
            "Need a marketing specialist for campaigns",
        )

        # Search with different wording but same meaning
        response = await store.search(
            "job_requirements", "programmer developer position"
        )

        # Software engineer should rank higher than marketing
        assert response.results[0].id == "job_1"

    @pytest.mark.asyncio
    async def test_different_collections_isolated(
        self, store: VectorStoreService
    ) -> None:
        """Should search only within specified collection."""
        await store.add("user_profiles", "profile_1", "Python developer")
        await store.add("job_requirements", "job_1", "Python developer needed")

        response = await store.search("user_profiles", "Python")

        assert response.collection == "user_profiles"
        assert all(r.id.startswith("profile") for r in response.results)


# =============================================================================
# COLLECTION OPERATIONS TESTS
# =============================================================================


class TestCollectionOperations:
    """Tests for collection management."""

    @pytest.mark.asyncio
    async def test_list_collections(self, store: VectorStoreService) -> None:
        """Should list all collections."""
        collections = store.list_collections()

        assert len(collections) == 2
        assert "user_profiles" in collections
        assert "job_requirements" in collections

    @pytest.mark.asyncio
    async def test_get_collection_stats(self, store: VectorStoreService) -> None:
        """Should return accurate collection statistics."""
        await store.add("user_profiles", "stat_doc_1", "Content 1")
        await store.add("user_profiles", "stat_doc_2", "Content 2")

        stats = await store.get_collection_stats("user_profiles")

        assert stats.name == "user_profiles"
        assert stats.count == 2
        assert stats.embedding_dimension == 384

    @pytest.mark.asyncio
    async def test_get_stats_empty_collection(
        self, store: VectorStoreService
    ) -> None:
        """Should return zero count for empty collection."""
        stats = await store.get_collection_stats("job_requirements")

        assert stats.count == 0

    @pytest.mark.asyncio
    async def test_clear_collection(self, store: VectorStoreService) -> None:
        """Should remove all documents from collection."""
        await store.add("user_profiles", "clear_1", "Content 1")
        await store.add("user_profiles", "clear_2", "Content 2")
        await store.add("user_profiles", "clear_3", "Content 3")

        count = await store.clear_collection("user_profiles")

        assert count == 3

        stats = await store.get_collection_stats("user_profiles")
        assert stats.count == 0

    @pytest.mark.asyncio
    async def test_clear_empty_collection(self, store: VectorStoreService) -> None:
        """Should handle clearing empty collection."""
        count = await store.clear_collection("user_profiles")
        assert count == 0


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================


class TestHealthCheck:
    """Tests for health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_initialized(
        self, store: VectorStoreService
    ) -> None:
        """Should report healthy when initialized."""
        health = await store.health_check()

        assert health.status == "healthy"
        assert health.initialized is True
        assert health.is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_uninitialized(
        self, uninitialized_store: VectorStoreService
    ) -> None:
        """Should report unhealthy when not initialized."""
        health = await uninitialized_store.health_check()

        assert health.status == "unhealthy"
        assert health.initialized is False
        assert health.is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_includes_collections(
        self, store: VectorStoreService
    ) -> None:
        """Should include collection stats in health."""
        await store.add("user_profiles", "health_doc", "Content")

        health = await store.health_check()

        assert len(health.collections) == 2
        assert health.total_documents == 1

    @pytest.mark.asyncio
    async def test_health_check_persist_directory(
        self, store: VectorStoreService, temp_vector_dir: Path
    ) -> None:
        """Should report persist directory."""
        health = await store.health_check()

        assert str(temp_vector_dir) in health.persist_directory


# =============================================================================
# DEPENDENCY INJECTION TESTS
# =============================================================================


class TestDependencyInjection:
    """Tests for singleton pattern."""

    @pytest.mark.asyncio
    async def test_get_vector_store_service_singleton(
        self, tmp_path: Path
    ) -> None:
        """Should return same instance."""
        reset_vector_store_service()

        # Monkey-patch the default directory for testing
        from src.services.vector_store import service as vector_module

        original_default = vector_module.DEFAULT_PERSIST_DIR
        vector_module.DEFAULT_PERSIST_DIR = tmp_path / "singleton_vectors"

        try:
            store1 = await get_vector_store_service()
            store2 = await get_vector_store_service()

            assert store1 is store2

            await shutdown_vector_store_service()
        finally:
            vector_module.DEFAULT_PERSIST_DIR = original_default

    @pytest.mark.asyncio
    async def test_shutdown_vector_store_service(self, tmp_path: Path) -> None:
        """Should shutdown and clear instance."""
        reset_vector_store_service()

        from src.services.vector_store import service as vector_module

        original_default = vector_module.DEFAULT_PERSIST_DIR
        vector_module.DEFAULT_PERSIST_DIR = tmp_path / "shutdown_vectors"

        try:
            store = await get_vector_store_service()
            assert store._initialized is True

            await shutdown_vector_store_service()

            # Getting service again should create new instance
            store2 = await get_vector_store_service()
            assert store2 is not store

            await shutdown_vector_store_service()
        finally:
            vector_module.DEFAULT_PERSIST_DIR = original_default

    @pytest.mark.asyncio
    async def test_reset_vector_store_service(self) -> None:
        """Should reset global instance."""
        reset_vector_store_service()

        from src.services.vector_store import service as vector_module

        assert vector_module._vector_store_instance is None


# =============================================================================
# PERSISTENCE TESTS
# =============================================================================


class TestPersistence:
    """Tests for data persistence across restarts."""

    @pytest.mark.asyncio
    async def test_data_persists_after_shutdown(
        self, temp_vector_dir: Path
    ) -> None:
        """Should persist data across service restarts."""
        # First service instance
        store1 = VectorStoreService(persist_directory=temp_vector_dir)
        await store1.initialize()
        await store1.add("user_profiles", "persist_doc", "Persistent content")
        await store1.shutdown()

        # Second service instance (simulating restart)
        store2 = VectorStoreService(persist_directory=temp_vector_dir)
        await store2.initialize()

        # Data should still be there
        entry = await store2.get("user_profiles", "persist_doc")
        assert entry.content == "Persistent content"

        await store2.shutdown()

    @pytest.mark.asyncio
    async def test_document_count_persists(self, temp_vector_dir: Path) -> None:
        """Should maintain document count across restarts."""
        # First instance
        store1 = VectorStoreService(persist_directory=temp_vector_dir)
        await store1.initialize()
        await store1.add("user_profiles", "doc_1", "Content 1")
        await store1.add("user_profiles", "doc_2", "Content 2")
        await store1.shutdown()

        # Second instance
        store2 = VectorStoreService(persist_directory=temp_vector_dir)
        await store2.initialize()

        stats = await store2.get_collection_stats("user_profiles")
        assert stats.count == 2

        await store2.shutdown()


# =============================================================================
# EDGE CASES TESTS
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_add_duplicate_id_overwrites(
        self, store: VectorStoreService
    ) -> None:
        """Should overwrite when adding with same ID."""
        await store.add("user_profiles", "dup_doc", "Original content")
        await store.add("user_profiles", "dup_doc", "New content")

        entry = await store.get("user_profiles", "dup_doc")
        assert entry.content == "New content"

    @pytest.mark.asyncio
    async def test_empty_content(self, store: VectorStoreService) -> None:
        """Should handle empty content string."""
        entry = await store.add("user_profiles", "empty_doc", "")

        assert entry.content == ""
        assert entry.metadata["content_length"] == 0

    @pytest.mark.asyncio
    async def test_long_content(self, store: VectorStoreService) -> None:
        """Should handle long content strings."""
        long_content = "Python developer. " * 1000

        entry = await store.add("user_profiles", "long_doc", long_content)

        assert len(entry.content) == len(long_content)

    @pytest.mark.asyncio
    async def test_special_characters_in_content(
        self, store: VectorStoreService
    ) -> None:
        """Should handle special characters in content."""
        special_content = "Developer with skills: C++, C#, .NET\n\tPython & Java"

        entry = await store.add("user_profiles", "special_doc", special_content)

        retrieved = await store.get("user_profiles", "special_doc")
        assert retrieved.content == special_content

    @pytest.mark.asyncio
    async def test_unicode_content(self, store: VectorStoreService) -> None:
        """Should handle unicode content."""
        unicode_content = "开发者 Developer 開發者 разработчик"

        entry = await store.add("user_profiles", "unicode_doc", unicode_content)

        retrieved = await store.get("user_profiles", "unicode_doc")
        assert retrieved.content == unicode_content

    @pytest.mark.asyncio
    async def test_search_with_special_query(
        self, store: VectorStoreService
    ) -> None:
        """Should handle special characters in search query."""
        await store.add("user_profiles", "doc_1", "C++ programmer")

        # Should not raise
        response = await store.search("user_profiles", "C++ & C#")

        assert response.total_results >= 0


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_full_crud_workflow(self, store: VectorStoreService) -> None:
        """Should support complete CRUD workflow."""
        # Create
        entry = await store.add(
            "user_profiles",
            "crud_doc",
            "Initial profile",
            metadata={"version": 1},
        )
        assert entry.id == "crud_doc"

        # Read
        retrieved = await store.get("user_profiles", "crud_doc")
        assert retrieved.content == "Initial profile"

        # Update
        updated = await store.update(
            "user_profiles",
            "crud_doc",
            "Updated profile",
            metadata={"version": 2},
        )
        assert updated.metadata["version"] == 2

        # Delete
        deleted = await store.delete("user_profiles", "crud_doc")
        assert deleted is True

        # Verify deleted
        with pytest.raises(DocumentNotFoundError):
            await store.get("user_profiles", "crud_doc")

    @pytest.mark.asyncio
    async def test_job_matching_scenario(self, store: VectorStoreService) -> None:
        """Should support job matching use case."""
        # Add user profiles
        await store.add(
            "user_profiles",
            "candidate_1",
            "5 years Python experience, Django, REST APIs, PostgreSQL",
        )
        await store.add(
            "user_profiles",
            "candidate_2",
            "3 years Java experience, Spring Boot, microservices",
        )

        # Add job requirement
        await store.add(
            "job_requirements",
            "job_1",
            "Looking for Python backend developer with API experience",
        )

        # Search for matching candidates
        job = await store.get("job_requirements", "job_1")
        matches = await store.search("user_profiles", job.content, top_k=2)

        # Python candidate should match better
        assert matches.results[0].id == "candidate_1"
        assert matches.results[0].score > matches.results[1].score
