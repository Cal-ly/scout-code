"""
Vector Store Service - Data Models

Models for ChromaDB vector storage and retrieval.
PoC scope: 2 collections (user_profiles, job_requirements)
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class VectorEntry(BaseModel):
    """
    A document entry for vector storage.

    Represents a document stored in ChromaDB with its metadata.

    Attributes:
        id: Unique identifier for the document.
        content: The text content that was embedded.
        metadata: Additional metadata (e.g., source, type, timestamp).
        created_at: When the entry was created.
    """

    id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class SearchResult(BaseModel):
    """
    A single result from similarity search.

    Attributes:
        id: Document identifier.
        content: The matched document content.
        score: Similarity score (0-1, higher is more similar).
        metadata: Document metadata.
        distance: Raw distance from query vector (lower is better).
    """

    id: str
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    distance: float = 0.0

    @property
    def is_relevant(self) -> bool:
        """Check if result is considered relevant (score >= 0.5)."""
        return self.score >= 0.5


class SearchResponse(BaseModel):
    """
    Response from a similarity search query.

    Attributes:
        query: The original search query text.
        results: List of matching documents.
        collection: Collection that was searched.
        total_results: Number of results returned.
    """

    query: str
    results: list[SearchResult] = Field(default_factory=list)
    collection: str = ""
    total_results: int = 0


class CollectionStats(BaseModel):
    """
    Statistics for a single collection.

    Attributes:
        name: Collection name.
        count: Number of documents in collection.
        embedding_dimension: Dimension of embeddings (384 for MiniLM).
    """

    name: str
    count: int = 0
    embedding_dimension: int = 384


class VectorStoreHealth(BaseModel):
    """
    Health status for the Vector Store Service.

    Attributes:
        status: Health status ("healthy", "degraded", or "unhealthy").
        initialized: Whether service is initialized.
        embedding_model: Name of the embedding model.
        collections: Stats for each collection.
        persist_directory: Path to ChromaDB storage.
        total_documents: Total documents across all collections.
    """

    status: str = "healthy"
    initialized: bool = False
    embedding_model: str = "all-MiniLM-L6-v2"
    collections: list[CollectionStats] = Field(default_factory=list)
    persist_directory: str = ""
    total_documents: int = 0

    @property
    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        return self.status == "healthy" and self.initialized
