"""Database service implementation."""

import json
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from src.services.database.exceptions import (
    ApplicationNotFoundError,
    DatabaseError,
    ProfileExistsError,
    ProfileNotFoundError,
)
from src.services.database.migrations import initialize_database, run_migrations
from src.services.database.models import (
    Application,
    ApplicationCreate,
    ApplicationStatus,
    ApplicationUpdate,
    Profile,
    ProfileCreate,
    ProfileUpdate,
    Settings,
)

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = Path("data/scout.db")


def _slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text or "profile"


def _make_unique_slug(conn: sqlite3.Connection, base_slug: str, exclude_id: int | None = None) -> str:
    """Ensure slug is unique by appending number if needed."""
    slug = base_slug
    counter = 1

    while True:
        query = "SELECT id FROM profiles WHERE slug = ?"
        params: list[Any] = [slug]

        if exclude_id:
            query += " AND id != ?"
            params.append(exclude_id)

        cursor = conn.execute(query, params)
        if cursor.fetchone() is None:
            return slug

        counter += 1
        slug = f"{base_slug}-{counter}"


class DatabaseService:
    """
    SQLite database service for profiles and applications.

    Provides CRUD operations with connection pooling.
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        """
        Initialize database service.

        Args:
            db_path: Path to SQLite database file.
        """
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize database connection and run migrations."""
        if self._initialized:
            return

        self._conn = initialize_database(self._db_path)
        run_migrations(self._conn)
        self._initialized = True
        logger.info("DatabaseService initialized")

    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
        self._initialized = False

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection, raising if not initialized."""
        if not self._conn:
            raise DatabaseError("Database not initialized")
        return self._conn

    # =========================================================================
    # SETTINGS
    # =========================================================================

    async def get_settings(self) -> Settings:
        """Get application settings."""
        conn = self._get_conn()

        cursor = conn.execute("SELECT key, value FROM settings")
        rows = cursor.fetchall()

        settings_dict: dict[str, Any] = {}
        for row in rows:
            key, value = row["key"], row["value"]
            if key == "active_profile_id":
                settings_dict[key] = int(value) if value else None
            elif key == "schema_version":
                settings_dict[key] = int(value)
            elif key == "demo_data_loaded":
                settings_dict[key] = value.lower() == "true"
            else:
                settings_dict[key] = value

        return Settings(**settings_dict)

    async def set_setting(self, key: str, value: Any) -> None:
        """Set a setting value."""
        conn = self._get_conn()

        str_value = str(value).lower() if isinstance(value, bool) else str(value)

        conn.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
            """,
            (key, str_value, str_value)
        )
        conn.commit()

    # =========================================================================
    # PROFILES
    # =========================================================================

    async def create_profile(self, data: ProfileCreate) -> Profile:
        """
        Create a new profile.

        Args:
            data: Profile creation data.

        Returns:
            Created profile.

        Raises:
            ProfileExistsError: If slug already exists.
        """
        conn = self._get_conn()

        # Generate unique slug
        base_slug = _slugify(data.name)
        slug = _make_unique_slug(conn, base_slug)

        # If this should be active, deactivate others first
        if data.is_active:
            conn.execute("UPDATE profiles SET is_active = 0")

        # Insert profile
        cursor = conn.execute(
            """
            INSERT INTO profiles (name, slug, full_name, email, title, profile_data, is_active, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.name,
                slug,
                data.full_name,
                data.email,
                data.title,
                json.dumps(data.profile_data),
                1 if data.is_active else 0,
                1 if data.is_demo else 0,
            )
        )
        conn.commit()

        profile_id = cursor.lastrowid
        return await self.get_profile(profile_id)  # type: ignore

    async def get_profile(self, profile_id: int) -> Profile:
        """Get profile by ID."""
        conn = self._get_conn()

        cursor = conn.execute(
            "SELECT * FROM profiles WHERE id = ?",
            (profile_id,)
        )
        row = cursor.fetchone()

        if row is None:
            raise ProfileNotFoundError(f"Profile {profile_id} not found")

        return self._row_to_profile(row)

    async def get_profile_by_slug(self, slug: str) -> Profile:
        """Get profile by slug."""
        conn = self._get_conn()

        cursor = conn.execute(
            "SELECT * FROM profiles WHERE slug = ?",
            (slug,)
        )
        row = cursor.fetchone()

        if row is None:
            raise ProfileNotFoundError(f"Profile '{slug}' not found")

        return self._row_to_profile(row)

    async def get_active_profile(self) -> Profile | None:
        """Get the currently active profile."""
        conn = self._get_conn()

        cursor = conn.execute(
            "SELECT * FROM profiles WHERE is_active = 1 LIMIT 1"
        )
        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_profile(row)

    async def list_profiles(self, include_demo: bool = True) -> list[Profile]:
        """
        List all profiles.

        Args:
            include_demo: Include demo profiles in results.

        Returns:
            List of profiles, active first.
        """
        conn = self._get_conn()

        query = "SELECT * FROM profiles"
        if not include_demo:
            query += " WHERE is_demo = 0"
        query += " ORDER BY is_active DESC, updated_at DESC"

        cursor = conn.execute(query)
        rows = cursor.fetchall()

        return [self._row_to_profile(row) for row in rows]

    async def update_profile(self, profile_id: int, data: ProfileUpdate) -> Profile:
        """Update a profile."""
        conn = self._get_conn()

        # Build update query dynamically
        updates: list[str] = []
        params: list[Any] = []

        if data.name is not None:
            updates.append("name = ?")
            params.append(data.name)
            # Update slug too
            new_slug = _make_unique_slug(conn, _slugify(data.name), exclude_id=profile_id)
            updates.append("slug = ?")
            params.append(new_slug)

        if data.full_name is not None:
            updates.append("full_name = ?")
            params.append(data.full_name)

        if data.email is not None:
            updates.append("email = ?")
            params.append(data.email)

        if data.title is not None:
            updates.append("title = ?")
            params.append(data.title)

        if data.profile_data is not None:
            updates.append("profile_data = ?")
            params.append(json.dumps(data.profile_data))
            updates.append("is_indexed = 0")  # Mark as needing re-index

        if data.is_active is not None:
            if data.is_active:
                # Deactivate all others first
                conn.execute("UPDATE profiles SET is_active = 0")
            updates.append("is_active = ?")
            params.append(1 if data.is_active else 0)

        if not updates:
            return await self.get_profile(profile_id)

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(profile_id)

        conn.execute(
            f"UPDATE profiles SET {', '.join(updates)} WHERE id = ?",
            params
        )
        conn.commit()

        return await self.get_profile(profile_id)

    async def delete_profile(self, profile_id: int) -> None:
        """Delete a profile and its applications."""
        conn = self._get_conn()

        # Check profile exists
        await self.get_profile(profile_id)

        # Delete applications first (foreign key)
        conn.execute("DELETE FROM applications WHERE profile_id = ?", (profile_id,))

        # Delete profile
        conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        conn.commit()

    async def activate_profile(self, profile_id: int) -> Profile:
        """
        Set a profile as active.

        Deactivates all other profiles.
        """
        conn = self._get_conn()

        # Verify profile exists
        await self.get_profile(profile_id)

        # Deactivate all
        conn.execute("UPDATE profiles SET is_active = 0")

        # Activate this one
        conn.execute(
            "UPDATE profiles SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (profile_id,)
        )
        conn.commit()

        # Update settings
        await self.set_setting("active_profile_id", profile_id)

        return await self.get_profile(profile_id)

    async def set_profile_indexed(self, profile_id: int, indexed: bool = True) -> None:
        """Mark profile as indexed/not indexed."""
        conn = self._get_conn()

        conn.execute(
            "UPDATE profiles SET is_indexed = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (1 if indexed else 0, profile_id)
        )
        conn.commit()

    def _row_to_profile(self, row: sqlite3.Row) -> Profile:
        """Convert database row to Profile model."""
        return Profile(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            full_name=row["full_name"],
            email=row["email"],
            title=row["title"],
            profile_data=json.loads(row["profile_data"]),
            is_active=bool(row["is_active"]),
            is_indexed=bool(row["is_indexed"]),
            is_demo=bool(row["is_demo"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    # =========================================================================
    # APPLICATIONS
    # =========================================================================

    async def create_application(self, data: ApplicationCreate) -> Application:
        """Create a new application record."""
        conn = self._get_conn()

        cursor = conn.execute(
            """
            INSERT INTO applications (job_id, profile_id, job_title, company_name, job_text, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data.job_id,
                data.profile_id,
                data.job_title,
                data.company_name,
                data.job_text,
                ApplicationStatus.PENDING.value,
            )
        )
        conn.commit()

        return await self.get_application(cursor.lastrowid)  # type: ignore

    async def get_application(self, app_id: int) -> Application:
        """Get application by ID."""
        conn = self._get_conn()

        cursor = conn.execute(
            """
            SELECT a.*, p.name as profile_name
            FROM applications a
            LEFT JOIN profiles p ON a.profile_id = p.id
            WHERE a.id = ?
            """,
            (app_id,)
        )
        row = cursor.fetchone()

        if row is None:
            raise ApplicationNotFoundError(f"Application {app_id} not found")

        return self._row_to_application(row)

    async def get_application_by_job_id(self, job_id: str) -> Application | None:
        """Get application by job_id."""
        conn = self._get_conn()

        cursor = conn.execute(
            """
            SELECT a.*, p.name as profile_name
            FROM applications a
            LEFT JOIN profiles p ON a.profile_id = p.id
            WHERE a.job_id = ?
            """,
            (job_id,)
        )
        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_application(row)

    async def list_applications(
        self,
        profile_id: int | None = None,
        status: ApplicationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Application], int]:
        """
        List applications with filtering and pagination.

        Returns:
            Tuple of (applications, total_count).
        """
        conn = self._get_conn()

        # Build query
        where_clauses: list[str] = []
        params: list[Any] = []

        if profile_id is not None:
            where_clauses.append("a.profile_id = ?")
            params.append(profile_id)

        if status is not None:
            where_clauses.append("a.status = ?")
            params.append(status.value)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Get total count
        count_cursor = conn.execute(
            f"SELECT COUNT(*) FROM applications a WHERE {where_sql}",
            params
        )
        total = count_cursor.fetchone()[0]

        # Get page
        query_params = params + [limit, offset]
        cursor = conn.execute(
            f"""
            SELECT a.*, p.name as profile_name
            FROM applications a
            LEFT JOIN profiles p ON a.profile_id = p.id
            WHERE {where_sql}
            ORDER BY a.created_at DESC
            LIMIT ? OFFSET ?
            """,
            query_params
        )
        rows = cursor.fetchall()

        return [self._row_to_application(row) for row in rows], total

    async def update_application(self, job_id: str, data: ApplicationUpdate) -> Application:
        """Update an application by job_id."""
        conn = self._get_conn()

        updates: list[str] = []
        params: list[Any] = []

        if data.job_title is not None:
            updates.append("job_title = ?")
            params.append(data.job_title)

        if data.company_name is not None:
            updates.append("company_name = ?")
            params.append(data.company_name)

        if data.status is not None:
            updates.append("status = ?")
            params.append(data.status.value)

        if data.compatibility_score is not None:
            updates.append("compatibility_score = ?")
            params.append(data.compatibility_score)

        if data.cv_path is not None:
            updates.append("cv_path = ?")
            params.append(data.cv_path)

        if data.cover_letter_path is not None:
            updates.append("cover_letter_path = ?")
            params.append(data.cover_letter_path)

        if data.analysis_data is not None:
            updates.append("analysis_data = ?")
            params.append(json.dumps(data.analysis_data))

        if data.pipeline_data is not None:
            updates.append("pipeline_data = ?")
            params.append(json.dumps(data.pipeline_data))

        if data.error_message is not None:
            updates.append("error_message = ?")
            params.append(data.error_message)

        if data.started_at is not None:
            updates.append("started_at = ?")
            params.append(data.started_at.isoformat())

        if data.completed_at is not None:
            updates.append("completed_at = ?")
            params.append(data.completed_at.isoformat())

        if not updates:
            app = await self.get_application_by_job_id(job_id)
            if app is None:
                raise ApplicationNotFoundError(f"Application {job_id} not found")
            return app

        params.append(job_id)

        conn.execute(
            f"UPDATE applications SET {', '.join(updates)} WHERE job_id = ?",
            params
        )
        conn.commit()

        app = await self.get_application_by_job_id(job_id)
        if app is None:
            raise ApplicationNotFoundError(f"Application {job_id} not found")
        return app

    async def delete_application(self, job_id: str) -> None:
        """Delete an application."""
        conn = self._get_conn()
        conn.execute("DELETE FROM applications WHERE job_id = ?", (job_id,))
        conn.commit()

    async def get_profile_stats(self, profile_id: int) -> dict[str, Any]:
        """Get statistics for a profile."""
        conn = self._get_conn()

        cursor = conn.execute(
            """
            SELECT
                COUNT(*) as total_apps,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_apps,
                AVG(CASE WHEN compatibility_score IS NOT NULL THEN compatibility_score END) as avg_score
            FROM applications
            WHERE profile_id = ?
            """,
            (profile_id,)
        )
        row = cursor.fetchone()

        return {
            "total_applications": row["total_apps"] or 0,
            "completed_applications": row["completed_apps"] or 0,
            "avg_compatibility_score": round(row["avg_score"], 1) if row["avg_score"] else None,
        }

    def _row_to_application(self, row: sqlite3.Row) -> Application:
        """Convert database row to Application model."""
        return Application(
            id=row["id"],
            job_id=row["job_id"],
            profile_id=row["profile_id"],
            job_title=row["job_title"],
            company_name=row["company_name"],
            job_text=row["job_text"],
            status=ApplicationStatus(row["status"]),
            compatibility_score=row["compatibility_score"],
            cv_path=row["cv_path"],
            cover_letter_path=row["cover_letter_path"],
            analysis_data=json.loads(row["analysis_data"]) if row["analysis_data"] else None,
            pipeline_data=json.loads(row["pipeline_data"]) if row["pipeline_data"] else None,
            error_message=row["error_message"],
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            profile_name=row["profile_name"],
        )


# =============================================================================
# SINGLETON
# =============================================================================

_instance: DatabaseService | None = None


async def get_database_service() -> DatabaseService:
    """Get singleton DatabaseService instance."""
    global _instance
    if _instance is None:
        _instance = DatabaseService()
        await _instance.initialize()
    return _instance


def reset_database_service() -> None:
    """Reset singleton (for testing)."""
    global _instance
    if _instance:
        import asyncio
        try:
            asyncio.get_event_loop().run_until_complete(_instance.close())
        except RuntimeError:
            pass
    _instance = None
