"""
Vector Store Service

ChromaDB-based vector storage for semantic search.
PoC scope: 2 collections (user_profiles, job_requirements), cosine similarity.

Usage:
    from src.services.vector_store import VectorStoreService, get_vector_store_service

    # Singleton access (for FastAPI)
    store = await get_vector_store_service()

    # Manual instantiation
    store = VectorStoreService()
    await store.initialize()
"""

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
from src.services.vector_store.service import (
    VectorStoreService,
    get_vector_store_service,
    reset_vector_store_service,
    shutdown_vector_store_service,
)

__all__ = [
    # Service
    "VectorStoreService",
    "get_vector_store_service",
    "shutdown_vector_store_service",
    "reset_vector_store_service",
    # Models
    "VectorEntry",
    "SearchResult",
    "SearchResponse",
    "CollectionStats",
    "VectorStoreHealth",
    # Exceptions
    "VectorStoreError",
    "CollectionNotFoundError",
    "DocumentNotFoundError",
    "EmbeddingError",
]
