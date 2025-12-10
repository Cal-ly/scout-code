"""
Vector Store Service - Exceptions

Custom exceptions for vector storage operations.
"""


class VectorStoreError(Exception):
    """
    Base exception for Vector Store operations.

    Raised when vector operations fail due to:
    - Service not initialized
    - ChromaDB errors
    - Embedding generation failures
    - Configuration errors
    """

    pass


class CollectionNotFoundError(VectorStoreError):
    """
    Collection does not exist.

    Raised when:
    - Requested collection name is not found
    - Collection was deleted
    """

    pass


class EmbeddingError(VectorStoreError):
    """
    Embedding generation failed.

    Raised when:
    - Sentence transformer model fails
    - Input text is invalid
    - Model loading fails
    """

    pass


class DocumentNotFoundError(VectorStoreError):
    """
    Document not found in collection.

    Raised when:
    - Document ID doesn't exist
    - Document was deleted
    """

    pass
