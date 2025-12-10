"""
Vector Store Service

ChromaDB-based vector storage for semantic search.
PoC scope: 2 collections, sequential processing, cosine similarity.

Usage:
    store = VectorStoreService()
    await store.initialize()

    # Add document
    await store.add("user_profiles", "doc_1", "Python developer with 5 years experience")

    # Search
    results = await store.search("user_profiles", "Python programming", top_k=5)

    # Get document
    doc = await store.get("user_profiles", "doc_1")
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

if TYPE_CHECKING:
    from chromadb.api import ClientAPI

from src.services.vector_store.exceptions import (
    CollectionNotFoundError,
    DocumentNotFoundError,
    EmbeddingError,
    VectorStoreError,
)
from src.services.vector_store.models import (
    CollectionStats,
    SearchResponse,
    SearchResult,
    VectorEntry,
    VectorStoreHealth,
)

logger = logging.getLogger(__name__)

# Default configuration values
DEFAULT_PERSIST_DIR = Path("data/vectors")
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_TOP_K = 10

# PoC collections (only 2 for PoC scope)
POC_COLLECTIONS = ["user_profiles", "job_requirements"]


class VectorStoreService:
    """
    Vector store service using ChromaDB and sentence-transformers.

    Provides semantic search capabilities for user profiles and job requirements.
    Uses all-MiniLM-L6-v2 for embeddings (384 dimensions).

    Attributes:
        embedding_model_name: Name of the sentence transformer model.
        persist_directory: Path to ChromaDB storage.

    Example:
        >>> store = VectorStoreService()
        >>> await store.initialize()
        >>> await store.add("user_profiles", "p1", "Senior Python developer")
        >>> results = await store.search("user_profiles", "Python expert")
        >>> print(results.results[0].score)
        0.85
    """

    def __init__(
        self,
        persist_directory: Path | None = None,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ):
        """
        Initialize the Vector Store Service.

        Args:
            persist_directory: Path for ChromaDB storage (default: data/vectors).
            embedding_model: Sentence transformer model name.
        """
        self._initialized = False
        self._persist_dir = persist_directory or DEFAULT_PERSIST_DIR
        self._embedding_model_name = embedding_model
        self._client: "ClientAPI | None" = None
        self._embedding_model: SentenceTransformer | None = None
        self._collections: dict[str, Any] = {}  # chromadb.Collection

    async def initialize(self) -> None:
        """
        Initialize the Vector Store Service.

        Creates persist directory, loads embedding model, and initializes ChromaDB.

        Raises:
            VectorStoreError: If initialization fails.
        """
        if self._initialized:
            logger.warning("Vector Store Service already initialized")
            return

        try:
            # Create persist directory
            self._persist_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Vector store directory: {self._persist_dir}")

            # Load embedding model
            logger.info(f"Loading embedding model: {self._embedding_model_name}")
            self._embedding_model = SentenceTransformer(self._embedding_model_name)

            # Initialize ChromaDB client
            self._client = chromadb.PersistentClient(
                path=str(self._persist_dir),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )

            # Initialize PoC collections
            for collection_name in POC_COLLECTIONS:
                self._collections[collection_name] = (
                    self._client.get_or_create_collection(
                        name=collection_name,
                        metadata={"hnsw:space": "cosine"},
                    )
                )
                logger.debug(f"Collection initialized: {collection_name}")

            self._initialized = True
            logger.info(
                f"Vector Store Service initialized: "
                f"{len(self._collections)} collections"
            )

        except Exception as e:
            error_msg = f"Failed to initialize Vector Store: {e}"
            logger.error(error_msg)
            raise VectorStoreError(error_msg) from e

    async def shutdown(self) -> None:
        """Gracefully shutdown the Vector Store Service."""
        if not self._initialized:
            return

        self._collections.clear()
        self._client = None
        self._embedding_model = None
        self._initialized = False
        logger.info("Vector Store Service shutdown complete")

    def _ensure_initialized(self) -> None:
        """Raise error if service not initialized."""
        if not self._initialized:
            raise VectorStoreError(
                "Vector Store Service not initialized. Call initialize() first."
            )

    def _get_collection(self, collection_name: str) -> Any:
        """Get collection by name, raise if not found."""
        if collection_name not in self._collections:
            raise CollectionNotFoundError(
                f"Collection '{collection_name}' not found. "
                f"Available: {list(self._collections.keys())}"
            )
        return self._collections[collection_name]

    def _generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for text.

        Args:
            text: Text to embed.

        Returns:
            List of floats representing the embedding.

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        if self._embedding_model is None:
            raise EmbeddingError("Embedding model not loaded")

        try:
            embedding = self._embedding_model.encode(text, convert_to_numpy=True)
            return cast(list[float], embedding.tolist())
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embedding: {e}") from e

    # =========================================================================
    # DOCUMENT OPERATIONS
    # =========================================================================

    async def add(
        self,
        collection_name: str,
        document_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> VectorEntry:
        """
        Add a document to a collection.

        Args:
            collection_name: Target collection (user_profiles or job_requirements).
            document_id: Unique identifier for the document.
            content: Text content to embed and store.
            metadata: Optional metadata dictionary.

        Returns:
            VectorEntry with document details.

        Raises:
            CollectionNotFoundError: If collection doesn't exist.
            EmbeddingError: If embedding generation fails.
        """
        self._ensure_initialized()
        collection = self._get_collection(collection_name)

        # Generate embedding
        embedding = self._generate_embedding(content)

        # Prepare metadata
        doc_metadata = metadata.copy() if metadata else {}
        doc_metadata["content_length"] = len(content)

        # Add to ChromaDB (using upsert to handle duplicates gracefully)
        collection.upsert(
            ids=[document_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[doc_metadata],
        )

        logger.debug(f"Added document '{document_id}' to '{collection_name}'")

        return VectorEntry(
            id=document_id,
            content=content,
            metadata=doc_metadata,
        )

    async def get(
        self,
        collection_name: str,
        document_id: str,
    ) -> VectorEntry:
        """
        Get a document by ID.

        Args:
            collection_name: Collection to search.
            document_id: Document ID to retrieve.

        Returns:
            VectorEntry with document details.

        Raises:
            CollectionNotFoundError: If collection doesn't exist.
            DocumentNotFoundError: If document doesn't exist.
        """
        self._ensure_initialized()
        collection = self._get_collection(collection_name)

        result = collection.get(ids=[document_id], include=["documents", "metadatas"])

        if not result["ids"]:
            raise DocumentNotFoundError(
                f"Document '{document_id}' not found in '{collection_name}'"
            )

        metadata = result["metadatas"][0] if result["metadatas"] else {}
        return VectorEntry(
            id=result["ids"][0],
            content=result["documents"][0] if result["documents"] else "",
            metadata=dict(metadata),  # Cast to standard dict
        )

    async def update(
        self,
        collection_name: str,
        document_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> VectorEntry:
        """
        Update an existing document.

        Args:
            collection_name: Collection containing the document.
            document_id: Document ID to update.
            content: New text content.
            metadata: New metadata (replaces existing).

        Returns:
            Updated VectorEntry.

        Raises:
            CollectionNotFoundError: If collection doesn't exist.
            DocumentNotFoundError: If document doesn't exist.
        """
        self._ensure_initialized()
        collection = self._get_collection(collection_name)

        # Check document exists
        existing = collection.get(ids=[document_id])
        if not existing["ids"]:
            raise DocumentNotFoundError(
                f"Document '{document_id}' not found in '{collection_name}'"
            )

        # Generate new embedding
        embedding = self._generate_embedding(content)

        # Prepare metadata
        doc_metadata = metadata.copy() if metadata else {}
        doc_metadata["content_length"] = len(content)

        # Update in ChromaDB (using upsert to fully replace metadata)
        collection.upsert(
            ids=[document_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[doc_metadata],
        )

        logger.debug(f"Updated document '{document_id}' in '{collection_name}'")

        return VectorEntry(
            id=document_id,
            content=content,
            metadata=doc_metadata,
        )

    async def delete(
        self,
        collection_name: str,
        document_id: str,
    ) -> bool:
        """
        Delete a document from a collection.

        Args:
            collection_name: Collection containing the document.
            document_id: Document ID to delete.

        Returns:
            True if document was deleted.

        Raises:
            CollectionNotFoundError: If collection doesn't exist.
        """
        self._ensure_initialized()
        collection = self._get_collection(collection_name)

        # Check if exists
        existing = collection.get(ids=[document_id])
        if not existing["ids"]:
            return False

        collection.delete(ids=[document_id])
        logger.debug(f"Deleted document '{document_id}' from '{collection_name}'")
        return True

    # =========================================================================
    # SEARCH OPERATIONS
    # =========================================================================

    async def search(
        self,
        collection_name: str,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        metadata_filter: dict[str, Any] | None = None,
    ) -> SearchResponse:
        """
        Search for similar documents.

        Args:
            collection_name: Collection to search.
            query: Query text for similarity search.
            top_k: Number of results to return (default: 10).
            metadata_filter: Optional metadata filter (exact match).

        Returns:
            SearchResponse with matching documents and scores.

        Raises:
            CollectionNotFoundError: If collection doesn't exist.
            EmbeddingError: If query embedding fails.
        """
        self._ensure_initialized()
        collection = self._get_collection(collection_name)

        # Check if collection is empty
        if collection.count() == 0:
            return SearchResponse(
                query=query,
                results=[],
                collection=collection_name,
                total_results=0,
            )

        # Generate query embedding
        query_embedding = self._generate_embedding(query)

        # Build query parameters
        query_params: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }

        if metadata_filter:
            query_params["where"] = metadata_filter

        # Execute search
        results = collection.query(**query_params)

        # Convert to SearchResult objects
        search_results: list[SearchResult] = []

        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                # Convert distance to similarity score
                # Cosine distance: 0 = identical, 2 = opposite
                # Score: 1 - (distance / 2) gives 0-1 range
                distance = results["distances"][0][i] if results["distances"] else 0.0
                score = 1.0 - (distance / 2.0)

                result_metadata = (
                    results["metadatas"][0][i] if results["metadatas"] else {}
                )
                search_results.append(
                    SearchResult(
                        id=doc_id,
                        content=(
                            results["documents"][0][i] if results["documents"] else ""
                        ),
                        score=score,
                        metadata=dict(result_metadata),  # Cast to standard dict
                        distance=distance,
                    )
                )

        return SearchResponse(
            query=query,
            results=search_results,
            collection=collection_name,
            total_results=len(search_results),
        )

    # =========================================================================
    # COLLECTION OPERATIONS
    # =========================================================================

    def list_collections(self) -> list[str]:
        """
        List available collection names.

        Returns:
            List of collection names.
        """
        self._ensure_initialized()
        return list(self._collections.keys())

    async def get_collection_stats(
        self,
        collection_name: str,
    ) -> CollectionStats:
        """
        Get statistics for a collection.

        Args:
            collection_name: Collection to query.

        Returns:
            CollectionStats with document count and metadata.

        Raises:
            CollectionNotFoundError: If collection doesn't exist.
        """
        self._ensure_initialized()
        collection = self._get_collection(collection_name)

        return CollectionStats(
            name=collection_name,
            count=collection.count(),
            embedding_dimension=384,  # MiniLM dimension
        )

    async def clear_collection(self, collection_name: str) -> int:
        """
        Remove all documents from a collection.

        Args:
            collection_name: Collection to clear.

        Returns:
            Number of documents removed.

        Raises:
            CollectionNotFoundError: If collection doesn't exist.
        """
        self._ensure_initialized()
        collection = self._get_collection(collection_name)

        count: int = collection.count()
        if count == 0:
            return 0

        # Get all IDs and delete
        all_docs = collection.get()
        if all_docs["ids"]:
            collection.delete(ids=all_docs["ids"])

        logger.info(f"Cleared {count} documents from '{collection_name}'")
        return count

    # =========================================================================
    # HEALTH CHECK
    # =========================================================================

    async def health_check(self) -> VectorStoreHealth:
        """
        Check health of Vector Store Service.

        Returns:
            VectorStoreHealth with status and diagnostics.
        """
        if not self._initialized:
            return VectorStoreHealth(
                status="unhealthy",
                initialized=False,
            )

        # Check each collection
        collection_stats: list[CollectionStats] = []
        total_docs = 0

        try:
            for name in self._collections:
                stats = await self.get_collection_stats(name)
                collection_stats.append(stats)
                total_docs += stats.count

            status = "healthy"
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            status = "degraded"

        return VectorStoreHealth(
            status=status,
            initialized=self._initialized,
            embedding_model=self._embedding_model_name,
            collections=collection_stats,
            persist_directory=str(self._persist_dir),
            total_documents=total_docs,
        )


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

_vector_store_instance: VectorStoreService | None = None


async def get_vector_store_service() -> VectorStoreService:
    """
    Get the Vector Store Service instance.

    Creates and initializes singleton on first call.
    Use as FastAPI dependency.

    Returns:
        Initialized VectorStoreService.
    """
    global _vector_store_instance

    if _vector_store_instance is None:
        _vector_store_instance = VectorStoreService()
        await _vector_store_instance.initialize()

    return _vector_store_instance


async def shutdown_vector_store_service() -> None:
    """Shutdown the global Vector Store Service instance."""
    global _vector_store_instance

    if _vector_store_instance is not None:
        await _vector_store_instance.shutdown()
        _vector_store_instance = None


def reset_vector_store_service() -> None:
    """Reset the global instance (for testing)."""
    global _vector_store_instance
    _vector_store_instance = None
