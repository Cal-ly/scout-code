"""
Profile Service

Manages user profiles with database storage, file backup, and vector indexing.

Usage:
    profile_service = ProfileService()
    await profile_service.initialize()

    # Create profile
    result = await profile_service.create_profile("My professional experience...")

    # Get status
    status = await profile_service.get_status()

    # Index profile for semantic search
    index_result = await profile_service.index_profile(profile_id)
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

import aiosqlite

from src.services.profile.exceptions import (
    ProfileDatabaseError,
    ProfileIndexingError,
    ProfileNotFoundError,
    ProfileValidationError,
)
from src.services.profile.models import (
    ProfileChunk,
    ProfileCreateResponse,
    ProfileData,
    ProfileHealth,
    ProfileIndexResponse,
    ProfileStatus,
)
from src.services.vector_store import VectorStoreService, get_vector_store_service

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_DB_PATH = Path("data/profiles.db")
DEFAULT_PROFILES_DIR = Path("data/profiles")
DEFAULT_USER_ID = 1  # Single user for PoC

# Chunking configuration
MAX_PARAGRAPH_LENGTH = 500
MIN_CHUNK_LENGTH = 100

# Vector store collection name
PROFILE_COLLECTION = "user_profiles"


class ProfileService:
    """
    Profile management service with database, file, and vector store integration.

    Attributes:
        db_path: Path to SQLite database.
        profiles_dir: Directory for profile text file backups.

    Example:
        >>> service = ProfileService()
        >>> await service.initialize()
        >>> result = await service.create_profile("My experience...")
        >>> print(result.profile_id)
        1
    """

    def __init__(
        self,
        db_path: Path | None = None,
        profiles_dir: Path | None = None,
    ):
        """
        Initialize Profile Service.

        Args:
            db_path: Path to SQLite database (default: data/profiles.db).
            profiles_dir: Directory for profile backups (default: data/profiles).
        """
        self._initialized = False
        self._db_path = db_path or DEFAULT_DB_PATH
        self._profiles_dir = profiles_dir or DEFAULT_PROFILES_DIR
        self._vector_store: VectorStoreService | None = None

    async def initialize(self) -> None:
        """
        Initialize the Profile Service.

        Creates database, tables, and ensures directories exist.

        Raises:
            ProfileDatabaseError: If initialization fails.
        """
        if self._initialized:
            logger.warning("Profile Service already initialized")
            return

        try:
            # Ensure directories exist
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._profiles_dir.mkdir(parents=True, exist_ok=True)

            # Initialize database
            await self._init_database()

            # Get vector store service
            self._vector_store = await get_vector_store_service()

            self._initialized = True
            logger.info(
                f"Profile Service initialized: db={self._db_path}, "
                f"profiles_dir={self._profiles_dir}"
            )

        except Exception as e:
            error_msg = f"Failed to initialize Profile Service: {e}"
            logger.error(error_msg)
            raise ProfileDatabaseError(error_msg) from e

    async def shutdown(self) -> None:
        """Gracefully shutdown the Profile Service."""
        if not self._initialized:
            return

        self._initialized = False
        logger.info("Profile Service shutdown complete")

    def _ensure_initialized(self) -> None:
        """Raise error if service not initialized."""
        if not self._initialized:
            raise ProfileDatabaseError(
                "Profile Service not initialized. Call initialize() first."
            )

    # =========================================================================
    # DATABASE OPERATIONS
    # =========================================================================

    async def _init_database(self) -> None:
        """Create database and tables if they don't exist."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL DEFAULT 1,
                    raw_text TEXT NOT NULL,
                    is_indexed BOOLEAN DEFAULT 0,
                    chunk_count INTEGER DEFAULT 0,
                    character_count INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id)
                )
            """)
            await db.commit()
            logger.debug("Database initialized")

    async def _get_profile_row(
        self, user_id: int = DEFAULT_USER_ID
    ) -> dict | None:
        """Get profile row from database."""
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM user_profiles WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def _insert_profile(
        self, user_id: int, raw_text: str, char_count: int
    ) -> int:
        """Insert new profile and return ID."""
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO user_profiles (user_id, raw_text, character_count)
                VALUES (?, ?, ?)
                """,
                (user_id, raw_text, char_count),
            )
            await db.commit()
            profile_id = cursor.lastrowid
            if profile_id is None:
                raise ProfileDatabaseError("Failed to get inserted profile ID")
            return profile_id

    async def _update_profile(
        self, profile_id: int, raw_text: str, char_count: int
    ) -> None:
        """Update existing profile."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                UPDATE user_profiles
                SET raw_text = ?, character_count = ?, is_indexed = 0,
                    chunk_count = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (raw_text, char_count, profile_id),
            )
            await db.commit()

    async def _update_index_status(
        self, profile_id: int, is_indexed: bool, chunk_count: int
    ) -> None:
        """Update profile indexing status."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                UPDATE user_profiles
                SET is_indexed = ?, chunk_count = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (is_indexed, chunk_count, profile_id),
            )
            await db.commit()

    # =========================================================================
    # FILE OPERATIONS
    # =========================================================================

    def _get_profile_file_path(self, profile_id: int) -> Path:
        """Get file path for profile backup."""
        return self._profiles_dir / f"profile_{profile_id}.txt"

    async def _save_profile_file(self, profile_id: int, text: str) -> None:
        """Save profile text to file backup."""
        file_path = self._get_profile_file_path(profile_id)
        try:
            file_path.write_text(text, encoding="utf-8")
            logger.debug(f"Profile saved to {file_path}")
        except OSError as e:
            # Non-critical - log warning but continue
            logger.warning(f"Failed to save profile file {file_path}: {e}")

    # =========================================================================
    # CHUNKING LOGIC
    # =========================================================================

    def chunk_text(self, text: str) -> list[ProfileChunk]:
        """
        Split profile text into chunks for embedding.

        Primary strategy: Split by double newlines (paragraphs).
        Secondary strategy: Split long paragraphs by sentences.

        Args:
            text: Profile text to chunk.

        Returns:
            List of ProfileChunk objects.
        """
        chunks: list[ProfileChunk] = []

        # Split by double newlines (paragraphs)
        paragraphs = text.split("\n\n")
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunk_index = 0

        for paragraph in paragraphs:
            if len(paragraph) <= MAX_PARAGRAPH_LENGTH:
                # Paragraph fits within limit
                chunks.append(
                    ProfileChunk(
                        content=paragraph,
                        chunk_index=chunk_index,
                        chunk_type="paragraph",
                        character_count=len(paragraph),
                    )
                )
                chunk_index += 1
            else:
                # Split long paragraph into sentences
                sentence_chunks = self._split_into_sentences(paragraph)
                for sentence_chunk in sentence_chunks:
                    chunks.append(
                        ProfileChunk(
                            content=sentence_chunk,
                            chunk_index=chunk_index,
                            chunk_type="sentence",
                            character_count=len(sentence_chunk),
                        )
                    )
                    chunk_index += 1

        # Combine very short chunks
        chunks = self._combine_short_chunks(chunks)

        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentence-based chunks (200-500 chars target)."""
        # Simple sentence splitting by common endings
        sentence_pattern = r"(?<=[.!?])\s+"
        sentences = re.split(sentence_pattern, text)

        chunks: list[str] = []
        current_chunk = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(current_chunk) + len(sentence) + 1 <= MAX_PARAGRAPH_LENGTH:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _combine_short_chunks(
        self, chunks: list[ProfileChunk]
    ) -> list[ProfileChunk]:
        """Combine adjacent chunks if total < MIN_CHUNK_LENGTH."""
        if not chunks:
            return chunks

        combined: list[ProfileChunk] = []
        current: ProfileChunk | None = None

        for chunk in chunks:
            if current is None:
                current = chunk
            elif (
                current.character_count + chunk.character_count < MIN_CHUNK_LENGTH
            ):
                # Combine with current
                new_content = current.content + "\n\n" + chunk.content
                current = ProfileChunk(
                    content=new_content,
                    chunk_index=current.chunk_index,
                    chunk_type="paragraph",  # Combined becomes paragraph
                    character_count=len(new_content),
                )
            else:
                combined.append(current)
                current = chunk

        if current:
            combined.append(current)

        # Re-index chunks
        for i, chunk in enumerate(combined):
            chunk.chunk_index = i

        return combined

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    async def get_status(self, user_id: int = DEFAULT_USER_ID) -> ProfileStatus:
        """
        Get profile status for a user.

        Args:
            user_id: User ID (default: 1 for PoC).

        Returns:
            ProfileStatus with existence and indexing info.
        """
        self._ensure_initialized()

        row = await self._get_profile_row(user_id)

        if row is None:
            return ProfileStatus(
                exists=False,
                is_indexed=False,
            )

        # Parse updated_at timestamp
        updated_at = None
        if row["updated_at"]:
            try:
                updated_at = datetime.fromisoformat(row["updated_at"])
            except ValueError:
                pass

        return ProfileStatus(
            exists=True,
            is_indexed=bool(row["is_indexed"]),
            profile_id=row["id"],
            chunk_count=row["chunk_count"] or 0,
            character_count=row["character_count"] or 0,
            last_updated=updated_at,
        )

    async def create_profile(
        self,
        profile_text: str,
        user_id: int = DEFAULT_USER_ID,
    ) -> ProfileCreateResponse:
        """
        Create or update a user profile.

        Args:
            profile_text: Profile text (100-10,000 characters).
            user_id: User ID (default: 1 for PoC).

        Returns:
            ProfileCreateResponse with profile ID and status.

        Raises:
            ProfileValidationError: If text validation fails.
            ProfileDatabaseError: If database operation fails.
        """
        self._ensure_initialized()

        # Validate
        text = profile_text.strip()
        if len(text) < 100:
            raise ProfileValidationError(
                f"Profile text too short: {len(text)} chars (minimum 100)"
            )
        if len(text) > 10000:
            raise ProfileValidationError(
                f"Profile text too long: {len(text)} chars (maximum 10,000)"
            )

        char_count = len(text)

        # Check if profile exists
        existing = await self._get_profile_row(user_id)

        try:
            status: Literal["created", "updated"]
            if existing:
                # Update existing profile
                profile_id = existing["id"]
                await self._update_profile(profile_id, text, char_count)
                status = "updated"
                logger.info(f"Updated profile {profile_id} ({char_count} chars)")
            else:
                # Create new profile
                profile_id = await self._insert_profile(user_id, text, char_count)
                status = "created"
                logger.info(f"Created profile {profile_id} ({char_count} chars)")

            # Save file backup
            await self._save_profile_file(profile_id, text)

            # Auto-index the profile
            index_result = await self.index_profile(profile_id)

            return ProfileCreateResponse(
                profile_id=profile_id,
                status=status,
                is_indexed=index_result.success,
                chunk_count=index_result.chunks_created,
            )

        except Exception as e:
            if isinstance(e, ProfileValidationError):
                raise
            error_msg = f"Failed to create/update profile: {e}"
            logger.error(error_msg)
            raise ProfileDatabaseError(error_msg) from e

    async def index_profile(
        self, profile_id: int
    ) -> ProfileIndexResponse:
        """
        Index profile text into vector store.

        Chunks the profile text and stores embeddings in ChromaDB.

        Args:
            profile_id: Profile ID to index.

        Returns:
            ProfileIndexResponse with success status and chunk count.

        Raises:
            ProfileNotFoundError: If profile not found.
            ProfileIndexingError: If indexing fails.
        """
        self._ensure_initialized()

        # Get profile data
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM user_profiles WHERE id = ?",
                (profile_id,),
            )
            row = await cursor.fetchone()

        if not row:
            raise ProfileNotFoundError(f"Profile {profile_id} not found")

        profile_text = row["raw_text"]
        was_indexed = bool(row["is_indexed"])

        try:
            # Clear old embeddings if re-indexing
            if was_indexed:
                await self._clear_profile_embeddings(profile_id)
                logger.debug(f"Cleared old embeddings for profile {profile_id}")

            # Chunk the text
            chunks = self.chunk_text(profile_text)

            if not chunks:
                logger.warning(f"No chunks generated for profile {profile_id}")
                await self._update_index_status(profile_id, True, 0)
                return ProfileIndexResponse(
                    success=True,
                    chunks_created=0,
                    profile_id=profile_id,
                )

            # Store chunks in vector store
            assert self._vector_store is not None, "Vector store not initialized"
            for chunk in chunks:
                doc_id = f"profile_{profile_id}_chunk_{chunk.chunk_index}"
                metadata = {
                    "profile_id": profile_id,
                    "chunk_index": chunk.chunk_index,
                    "chunk_type": chunk.chunk_type,
                    "character_count": chunk.character_count,
                    "created_at": datetime.now().isoformat(),
                    "type": "profile",
                }

                await self._vector_store.add(
                    collection_name=PROFILE_COLLECTION,
                    document_id=doc_id,
                    content=chunk.content,
                    metadata=metadata,
                )

            # Update database
            await self._update_index_status(profile_id, True, len(chunks))

            logger.info(
                f"Indexed profile {profile_id}: {len(chunks)} chunks created"
            )

            return ProfileIndexResponse(
                success=True,
                chunks_created=len(chunks),
                profile_id=profile_id,
            )

        except Exception as e:
            # Rollback on failure
            await self._update_index_status(profile_id, False, 0)
            error_msg = f"Failed to index profile {profile_id}: {e}"
            logger.error(error_msg)
            raise ProfileIndexingError(error_msg) from e

    async def _clear_profile_embeddings(self, profile_id: int) -> None:
        """Clear all embeddings for a profile from vector store."""
        if self._vector_store is None:
            logger.warning("Vector store not available, skipping embedding cleanup")
            return

        try:
            # Get all documents for this profile
            results = await self._vector_store.search(
                collection_name=PROFILE_COLLECTION,
                query="",  # Empty query to get all
                top_k=1000,  # Get all chunks
                metadata_filter={"profile_id": profile_id},
            )

            # Delete each document
            for result in results.results:
                await self._vector_store.delete(
                    collection_name=PROFILE_COLLECTION,
                    document_id=result.id,
                )

        except Exception as e:
            logger.warning(f"Error clearing profile embeddings: {e}")

    async def get_profile(
        self, user_id: int = DEFAULT_USER_ID
    ) -> ProfileData:
        """
        Get full profile data.

        Args:
            user_id: User ID (default: 1 for PoC).

        Returns:
            ProfileData with full profile information.

        Raises:
            ProfileNotFoundError: If profile not found.
        """
        self._ensure_initialized()

        row = await self._get_profile_row(user_id)

        if not row:
            raise ProfileNotFoundError(f"No profile found for user {user_id}")

        # Parse timestamps
        created_at = datetime.fromisoformat(row["created_at"])
        updated_at = datetime.fromisoformat(row["updated_at"])

        return ProfileData(
            profile_id=row["id"],
            profile_text=row["raw_text"],
            is_indexed=bool(row["is_indexed"]),
            chunk_count=row["chunk_count"] or 0,
            character_count=row["character_count"],
            created_at=created_at,
            updated_at=updated_at,
        )

    async def health_check(self) -> ProfileHealth:
        """
        Check health of Profile Service.

        Returns:
            ProfileHealth with status and diagnostics.
        """
        db_ok = True
        dir_ok = True
        profile_count = 0
        last_error = None

        # Check database
        try:
            async with aiosqlite.connect(self._db_path) as db:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM user_profiles"
                )
                result = await cursor.fetchone()
                profile_count = result[0] if result else 0
        except Exception as e:
            db_ok = False
            last_error = f"Database error: {e}"

        # Check profiles directory
        try:
            test_file = self._profiles_dir / ".health_check"
            test_file.write_text("ok")
            test_file.unlink()
        except Exception as e:
            dir_ok = False
            last_error = f"Directory error: {e}"

        status = "healthy" if (db_ok and dir_ok) else "degraded"

        return ProfileHealth(
            status=status,
            database_accessible=db_ok,
            profiles_dir_accessible=dir_ok,
            profile_count=profile_count,
            last_error=last_error,
        )


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

_profile_instance: ProfileService | None = None


async def get_profile_service() -> ProfileService:
    """
    Get the Profile Service instance.

    Creates and initializes singleton on first call.
    Use as FastAPI dependency.

    Returns:
        Initialized ProfileService.
    """
    global _profile_instance

    if _profile_instance is None:
        _profile_instance = ProfileService()
        await _profile_instance.initialize()

    return _profile_instance


async def shutdown_profile_service() -> None:
    """Shutdown the global Profile Service instance."""
    global _profile_instance

    if _profile_instance is not None:
        await _profile_instance.shutdown()
        _profile_instance = None


def reset_profile_service() -> None:
    """Reset the global instance (for testing)."""
    global _profile_instance
    _profile_instance = None
