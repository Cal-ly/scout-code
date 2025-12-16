"""Database service implementation."""

import json
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from src.services.database.completeness import calculate_completeness
from src.services.database.demo_data import (
    DEFAULT_ACTIVE_PROFILE_SLUG,
    DEMO_PROFILES,
    TEST_USER,
)
from src.services.database.exceptions import (
    ApplicationNotFoundError,
    DatabaseError,
    ProfileNotFoundError,
    UserNotFoundError,
)
from src.services.database.migrations import initialize_database, reset_database
from src.services.database.models import (
    Application,
    ApplicationCreate,
    ApplicationStatus,
    ApplicationUpdate,
    Certification,
    CertificationCreate,
    Education,
    EducationCreate,
    Experience,
    ExperienceCreate,
    Language,
    LanguageCreate,
    Profile,
    ProfileCompleteness,
    ProfileCreate,
    ProfileSummary,
    ProfileUpdate,
    Settings,
    Skill,
    SkillCreate,
    User,
    UserCreate,
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


def _make_unique_slug(
    conn: sqlite3.Connection, base_slug: str, exclude_id: int | None = None
) -> str:
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


def _parse_json_list(value: str | None) -> list[str]:
    """Parse JSON string to list, returning empty list if None or invalid."""
    if not value:
        return []
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


class DatabaseService:
    """
    SQLite database service for users, profiles, and applications.

    Provides full CRUD operations with connection management.
    Supports multi-profile per user architecture.
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
        """Initialize database connection, run migrations, and seed demo data."""
        if self._initialized:
            return

        self._conn = initialize_database(self._db_path)

        # Seed demo data if not already done
        await self._seed_demo_data_if_needed()

        self._initialized = True
        logger.info("DatabaseService initialized")

    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
        self._initialized = False
        logger.info("DatabaseService closed")

    async def reset(self) -> None:
        """Reset database to fresh state. WARNING: Deletes all data!"""
        if self._conn:
            reset_database(self._conn)
            await self._seed_demo_data_if_needed()
            logger.info("Database reset complete")

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection, raising if not initialized."""
        if not self._conn:
            raise DatabaseError("Database not initialized. Call initialize() first.")
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
                settings_dict[key] = int(value) if value and value != "None" else None
            elif key == "schema_version":
                settings_dict[key] = int(value) if value else 2
            elif key == "demo_data_loaded":
                settings_dict[key] = value and value.lower() == "true"
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
            (key, str_value, str_value),
        )
        conn.commit()

    # =========================================================================
    # USER OPERATIONS
    # =========================================================================

    async def get_user(self, user_id: int) -> User:
        """Get user by ID."""
        conn = self._get_conn()

        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()

        if row is None:
            raise UserNotFoundError(user_id)

        return self._row_to_user(row)

    async def get_user_by_username(self, username: str) -> User | None:
        """Get user by username. Returns None if not found."""
        conn = self._get_conn()

        cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_user(row)

    async def get_current_user(self) -> User:
        """
        Get the current user.

        For PoC, this returns the test user. In production, this would
        use session/auth context.
        """
        user = await self.get_user_by_username("test_user")
        if user is None:
            raise UserNotFoundError("test_user")
        return user

    async def create_user(self, data: UserCreate) -> User:
        """Create a new user."""
        conn = self._get_conn()

        cursor = conn.execute(
            """
            INSERT INTO users (username, email, display_name)
            VALUES (?, ?, ?)
            """,
            (data.username, data.email, data.display_name),
        )
        conn.commit()

        return await self.get_user(cursor.lastrowid)  # type: ignore

    def _row_to_user(self, row: sqlite3.Row) -> User:
        """Convert database row to User model."""
        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            display_name=row["display_name"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    # =========================================================================
    # PROFILE OPERATIONS
    # =========================================================================

    async def list_profiles(self, user_id: int | None = None) -> list[ProfileSummary]:
        """
        List profiles with summary stats.

        Args:
            user_id: Filter by user. If None, uses current user.

        Returns:
            List of ProfileSummary sorted by active first, then updated_at desc.
        """
        conn = self._get_conn()

        if user_id is None:
            user = await self.get_current_user()
            user_id = user.id

        cursor = conn.execute(
            """
            SELECT
                p.*,
                (SELECT COUNT(*) FROM profile_skills WHERE profile_id = p.id)
                    as skill_count,
                (SELECT COUNT(*) FROM profile_experiences WHERE profile_id = p.id)
                    as experience_count,
                (SELECT COUNT(*) FROM profile_education WHERE profile_id = p.id)
                    as education_count,
                (SELECT COUNT(*) FROM profile_certifications WHERE profile_id = p.id)
                    as certification_count,
                (SELECT COUNT(*) FROM profile_languages WHERE profile_id = p.id)
                    as language_count,
                (SELECT COUNT(*) FROM applications WHERE profile_id = p.id)
                    as application_count,
                (SELECT COUNT(*) FROM applications
                    WHERE profile_id = p.id AND status = 'completed')
                    as completed_application_count,
                (SELECT AVG(compatibility_score) FROM applications
                    WHERE profile_id = p.id AND compatibility_score IS NOT NULL)
                    as avg_compatibility_score
            FROM profiles p
            WHERE p.user_id = ?
            ORDER BY p.is_active DESC, p.updated_at DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()

        return [self._row_to_profile_summary(row) for row in rows]

    async def get_profile(self, profile_id: int) -> Profile:
        """Get full profile with all related data."""
        conn = self._get_conn()

        cursor = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
        row = cursor.fetchone()

        if row is None:
            raise ProfileNotFoundError(profile_id)

        return await self._load_full_profile(row)

    async def get_profile_by_slug(self, slug: str) -> Profile:
        """Get full profile by slug."""
        conn = self._get_conn()

        cursor = conn.execute("SELECT * FROM profiles WHERE slug = ?", (slug,))
        row = cursor.fetchone()

        if row is None:
            raise ProfileNotFoundError(slug)

        return await self._load_full_profile(row)

    async def get_active_profile(self, user_id: int | None = None) -> Profile | None:
        """Get the active profile for a user."""
        conn = self._get_conn()

        if user_id is None:
            user = await self.get_current_user()
            user_id = user.id

        cursor = conn.execute(
            "SELECT * FROM profiles WHERE user_id = ? AND is_active = 1 LIMIT 1",
            (user_id,),
        )
        row = cursor.fetchone()

        if row is None:
            return None

        return await self._load_full_profile(row)

    async def create_profile(self, user_id: int, data: ProfileCreate) -> Profile:
        """
        Create a new profile with all related data.

        Args:
            user_id: Owner user ID.
            data: Profile creation data including skills, experiences, etc.

        Returns:
            Created profile with all related data.
        """
        conn = self._get_conn()

        # Generate unique slug
        base_slug = data.slug if data.slug else _slugify(data.name)
        slug = _make_unique_slug(conn, base_slug)

        # Insert profile
        cursor = conn.execute(
            """
            INSERT INTO profiles
                (user_id, slug, name, title, email, phone, location, summary,
                 is_active, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
            """,
            (
                user_id,
                slug,
                data.name,
                data.title,
                data.email,
                data.phone,
                data.location,
                data.summary,
            ),
        )
        conn.commit()

        profile_id = cursor.lastrowid

        # Insert related data
        await self._save_profile_skills(profile_id, data.skills)  # type: ignore
        await self._save_profile_experiences(profile_id, data.experiences)  # type: ignore
        await self._save_profile_education(profile_id, data.education)  # type: ignore
        await self._save_profile_certifications(profile_id, data.certifications)  # type: ignore
        await self._save_profile_languages(profile_id, data.languages)  # type: ignore

        return await self.get_profile(profile_id)  # type: ignore

    async def update_profile(self, slug: str, data: ProfileUpdate) -> Profile:
        """
        Update a profile.

        If list fields (skills, experiences, etc.) are provided, they REPLACE
        existing data. If None, existing data is preserved.
        """
        conn = self._get_conn()

        # Get existing profile
        profile = await self.get_profile_by_slug(slug)

        # Build update query for basic fields
        updates: list[str] = []
        params: list[Any] = []

        if data.name is not None:
            updates.append("name = ?")
            params.append(data.name)

        if data.slug is not None and data.slug != slug:
            # Verify new slug is unique
            new_slug = _make_unique_slug(conn, data.slug, exclude_id=profile.id)
            updates.append("slug = ?")
            params.append(new_slug)

        if data.title is not None:
            updates.append("title = ?")
            params.append(data.title)

        if data.email is not None:
            updates.append("email = ?")
            params.append(data.email)

        if data.phone is not None:
            updates.append("phone = ?")
            params.append(data.phone)

        if data.location is not None:
            updates.append("location = ?")
            params.append(data.location)

        if data.summary is not None:
            updates.append("summary = ?")
            params.append(data.summary)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(profile.id)
            conn.execute(
                f"UPDATE profiles SET {', '.join(updates)} WHERE id = ?", params
            )
            conn.commit()

        # Update related data if provided (replace semantics)
        if data.skills is not None:
            await self._delete_profile_skills(profile.id)
            await self._save_profile_skills(profile.id, data.skills)

        if data.experiences is not None:
            await self._delete_profile_experiences(profile.id)
            await self._save_profile_experiences(profile.id, data.experiences)

        if data.education is not None:
            await self._delete_profile_education(profile.id)
            await self._save_profile_education(profile.id, data.education)

        if data.certifications is not None:
            await self._delete_profile_certifications(profile.id)
            await self._save_profile_certifications(profile.id, data.certifications)

        if data.languages is not None:
            await self._delete_profile_languages(profile.id)
            await self._save_profile_languages(profile.id, data.languages)

        # Return updated profile (use new slug if changed)
        new_slug = data.slug if data.slug and data.slug != slug else slug
        return await self.get_profile_by_slug(new_slug)

    async def delete_profile(self, slug: str) -> None:
        """Delete profile and all related data (cascades via FK)."""
        conn = self._get_conn()

        # Verify exists
        profile = await self.get_profile_by_slug(slug)

        # Delete (cascades to related tables and applications)
        conn.execute("DELETE FROM profiles WHERE id = ?", (profile.id,))
        conn.commit()

        logger.info(f"Deleted profile: {slug}")

    async def activate_profile(self, slug: str) -> Profile:
        """
        Set profile as active, deactivating others for the same user.

        Returns the activated profile.
        """
        conn = self._get_conn()

        # Get profile and user
        profile = await self.get_profile_by_slug(slug)

        # Deactivate all profiles for this user
        conn.execute(
            "UPDATE profiles SET is_active = 0 WHERE user_id = ?", (profile.user_id,)
        )

        # Activate this one
        conn.execute(
            "UPDATE profiles SET is_active = 1, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ?",
            (profile.id,),
        )
        conn.commit()

        # Update settings
        await self.set_setting("active_profile_id", profile.id)

        logger.info(f"Activated profile: {slug}")

        return await self.get_profile_by_slug(slug)

    async def get_profile_completeness(self, slug: str) -> ProfileCompleteness:
        """Calculate and return profile completeness score."""
        profile = await self.get_profile_by_slug(slug)
        return calculate_completeness(profile)

    # =========================================================================
    # PROFILE RELATED DATA (PRIVATE)
    # =========================================================================

    async def _load_full_profile(self, row: sqlite3.Row) -> Profile:
        """Load profile with all related data from a profile row."""
        profile_id = row["id"]

        return Profile(
            id=row["id"],
            user_id=row["user_id"],
            slug=row["slug"],
            name=row["name"],
            title=row["title"],
            email=row["email"],
            phone=row["phone"],
            location=row["location"],
            summary=row["summary"],
            is_active=bool(row["is_active"]),
            is_demo=bool(row["is_demo"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            skills=await self._load_profile_skills(profile_id),
            experiences=await self._load_profile_experiences(profile_id),
            education=await self._load_profile_education(profile_id),
            certifications=await self._load_profile_certifications(profile_id),
            languages=await self._load_profile_languages(profile_id),
        )

    def _row_to_profile_summary(self, row: sqlite3.Row) -> ProfileSummary:
        """Convert row with aggregates to ProfileSummary."""
        avg_score = row["avg_compatibility_score"]
        return ProfileSummary(
            id=row["id"],
            user_id=row["user_id"],
            slug=row["slug"],
            name=row["name"],
            title=row["title"],
            is_active=bool(row["is_active"]),
            is_demo=bool(row["is_demo"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            skill_count=row["skill_count"] or 0,
            experience_count=row["experience_count"] or 0,
            education_count=row["education_count"] or 0,
            certification_count=row["certification_count"] or 0,
            language_count=row["language_count"] or 0,
            application_count=row["application_count"] or 0,
            completed_application_count=row["completed_application_count"] or 0,
            avg_compatibility_score=round(avg_score, 1) if avg_score else None,
        )

    # --- Skills ---

    async def _load_profile_skills(self, profile_id: int) -> list[Skill]:
        """Load skills for a profile."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM profile_skills WHERE profile_id = ? ORDER BY sort_order",
            (profile_id,),
        )
        return [
            Skill(
                id=row["id"],
                profile_id=row["profile_id"],
                name=row["name"],
                level=row["level"],
                years=row["years"],
                category=row["category"],
                sort_order=row["sort_order"] or 0,
            )
            for row in cursor.fetchall()
        ]

    async def _save_profile_skills(
        self, profile_id: int, skills: list[SkillCreate]
    ) -> None:
        """Save skills for a profile."""
        conn = self._get_conn()
        for skill in skills:
            conn.execute(
                """
                INSERT INTO profile_skills
                    (profile_id, name, level, years, category, sort_order)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    skill.name,
                    skill.level.value if skill.level else None,
                    skill.years,
                    skill.category,
                    skill.sort_order,
                ),
            )
        conn.commit()

    async def _delete_profile_skills(self, profile_id: int) -> None:
        """Delete all skills for a profile."""
        conn = self._get_conn()
        conn.execute("DELETE FROM profile_skills WHERE profile_id = ?", (profile_id,))
        conn.commit()

    # --- Experiences ---

    async def _load_profile_experiences(self, profile_id: int) -> list[Experience]:
        """Load experiences for a profile."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM profile_experiences WHERE profile_id = ? ORDER BY sort_order",
            (profile_id,),
        )
        return [
            Experience(
                id=row["id"],
                profile_id=row["profile_id"],
                title=row["title"],
                company=row["company"],
                start_date=row["start_date"],
                end_date=row["end_date"],
                description=row["description"],
                achievements=_parse_json_list(row["achievements"]),
                sort_order=row["sort_order"] or 0,
            )
            for row in cursor.fetchall()
        ]

    async def _save_profile_experiences(
        self, profile_id: int, experiences: list[ExperienceCreate]
    ) -> None:
        """Save experiences for a profile."""
        conn = self._get_conn()
        for exp in experiences:
            conn.execute(
                """
                INSERT INTO profile_experiences
                    (profile_id, title, company, start_date, end_date,
                     description, achievements, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    exp.title,
                    exp.company,
                    exp.start_date,
                    exp.end_date,
                    exp.description,
                    json.dumps(exp.achievements),
                    exp.sort_order,
                ),
            )
        conn.commit()

    async def _delete_profile_experiences(self, profile_id: int) -> None:
        """Delete all experiences for a profile."""
        conn = self._get_conn()
        conn.execute(
            "DELETE FROM profile_experiences WHERE profile_id = ?", (profile_id,)
        )
        conn.commit()

    # --- Education ---

    async def _load_profile_education(self, profile_id: int) -> list[Education]:
        """Load education for a profile."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM profile_education WHERE profile_id = ? ORDER BY sort_order",
            (profile_id,),
        )
        return [
            Education(
                id=row["id"],
                profile_id=row["profile_id"],
                institution=row["institution"],
                degree=row["degree"],
                field=row["field"],
                start_date=row["start_date"],
                end_date=row["end_date"],
                gpa=row["gpa"],
                achievements=_parse_json_list(row["achievements"]),
                sort_order=row["sort_order"] or 0,
            )
            for row in cursor.fetchall()
        ]

    async def _save_profile_education(
        self, profile_id: int, education: list[EducationCreate]
    ) -> None:
        """Save education for a profile."""
        conn = self._get_conn()
        for edu in education:
            conn.execute(
                """
                INSERT INTO profile_education
                    (profile_id, institution, degree, field, start_date,
                     end_date, gpa, achievements, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    edu.institution,
                    edu.degree,
                    edu.field,
                    edu.start_date,
                    edu.end_date,
                    edu.gpa,
                    json.dumps(edu.achievements),
                    edu.sort_order,
                ),
            )
        conn.commit()

    async def _delete_profile_education(self, profile_id: int) -> None:
        """Delete all education for a profile."""
        conn = self._get_conn()
        conn.execute(
            "DELETE FROM profile_education WHERE profile_id = ?", (profile_id,)
        )
        conn.commit()

    # --- Certifications ---

    async def _load_profile_certifications(
        self, profile_id: int
    ) -> list[Certification]:
        """Load certifications for a profile."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM profile_certifications "
            "WHERE profile_id = ? ORDER BY sort_order",
            (profile_id,),
        )
        return [
            Certification(
                id=row["id"],
                profile_id=row["profile_id"],
                name=row["name"],
                issuer=row["issuer"],
                date_obtained=row["date_obtained"],
                expiry_date=row["expiry_date"],
                credential_url=row["credential_url"],
                sort_order=row["sort_order"] or 0,
            )
            for row in cursor.fetchall()
        ]

    async def _save_profile_certifications(
        self, profile_id: int, certifications: list[CertificationCreate]
    ) -> None:
        """Save certifications for a profile."""
        conn = self._get_conn()
        for cert in certifications:
            conn.execute(
                """
                INSERT INTO profile_certifications
                    (profile_id, name, issuer, date_obtained, expiry_date,
                     credential_url, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    cert.name,
                    cert.issuer,
                    cert.date_obtained,
                    cert.expiry_date,
                    cert.credential_url,
                    cert.sort_order,
                ),
            )
        conn.commit()

    async def _delete_profile_certifications(self, profile_id: int) -> None:
        """Delete all certifications for a profile."""
        conn = self._get_conn()
        conn.execute(
            "DELETE FROM profile_certifications WHERE profile_id = ?", (profile_id,)
        )
        conn.commit()

    # --- Languages ---

    async def _load_profile_languages(self, profile_id: int) -> list[Language]:
        """Load languages for a profile."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM profile_languages WHERE profile_id = ? ORDER BY sort_order",
            (profile_id,),
        )
        return [
            Language(
                id=row["id"],
                profile_id=row["profile_id"],
                language=row["language"],
                proficiency=row["proficiency"],
                sort_order=row["sort_order"] or 0,
            )
            for row in cursor.fetchall()
        ]

    async def _save_profile_languages(
        self, profile_id: int, languages: list[LanguageCreate]
    ) -> None:
        """Save languages for a profile."""
        conn = self._get_conn()
        for lang in languages:
            conn.execute(
                """
                INSERT INTO profile_languages
                    (profile_id, language, proficiency, sort_order)
                VALUES (?, ?, ?, ?)
                """,
                (
                    profile_id,
                    lang.language,
                    lang.proficiency.value if lang.proficiency else None,
                    lang.sort_order,
                ),
            )
        conn.commit()

    async def _delete_profile_languages(self, profile_id: int) -> None:
        """Delete all languages for a profile."""
        conn = self._get_conn()
        conn.execute(
            "DELETE FROM profile_languages WHERE profile_id = ?", (profile_id,)
        )
        conn.commit()

    # =========================================================================
    # APPLICATION OPERATIONS
    # =========================================================================

    async def list_applications(
        self,
        user_id: int | None = None,
        profile_id: int | None = None,
        status: ApplicationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Application], int]:
        """
        List applications with filtering and pagination.

        Args:
            user_id: Filter by user (all their applications).
            profile_id: Filter by specific profile.
            status: Filter by status.
            limit: Max results.
            offset: Pagination offset.

        Returns:
            Tuple of (applications, total_count).
        """
        conn = self._get_conn()

        where_clauses: list[str] = []
        params: list[Any] = []

        if user_id is not None:
            where_clauses.append("a.user_id = ?")
            params.append(user_id)

        if profile_id is not None:
            where_clauses.append("a.profile_id = ?")
            params.append(profile_id)

        if status is not None:
            where_clauses.append("a.status = ?")
            params.append(status.value)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Get total count
        count_cursor = conn.execute(
            f"SELECT COUNT(*) FROM applications a WHERE {where_sql}", params
        )
        total = count_cursor.fetchone()[0]

        # Get page
        query_params = params + [limit, offset]
        cursor = conn.execute(
            f"""
            SELECT a.*, p.name as profile_name, p.slug as profile_slug
            FROM applications a
            LEFT JOIN profiles p ON a.profile_id = p.id
            WHERE {where_sql}
            ORDER BY a.created_at DESC
            LIMIT ? OFFSET ?
            """,
            query_params,
        )
        rows = cursor.fetchall()

        return [self._row_to_application(row) for row in rows], total

    async def get_application(self, job_id: str) -> Application:
        """Get application by job_id."""
        conn = self._get_conn()

        cursor = conn.execute(
            """
            SELECT a.*, p.name as profile_name, p.slug as profile_slug
            FROM applications a
            LEFT JOIN profiles p ON a.profile_id = p.id
            WHERE a.job_id = ?
            """,
            (job_id,),
        )
        row = cursor.fetchone()

        if row is None:
            raise ApplicationNotFoundError(job_id)

        return self._row_to_application(row)

    async def get_application_by_id(self, app_id: int) -> Application:
        """Get application by internal ID."""
        conn = self._get_conn()

        cursor = conn.execute(
            """
            SELECT a.*, p.name as profile_name, p.slug as profile_slug
            FROM applications a
            LEFT JOIN profiles p ON a.profile_id = p.id
            WHERE a.id = ?
            """,
            (app_id,),
        )
        row = cursor.fetchone()

        if row is None:
            raise ApplicationNotFoundError(app_id)

        return self._row_to_application(row)

    async def create_application(self, data: ApplicationCreate) -> Application:
        """Create a new application record."""
        conn = self._get_conn()

        cursor = conn.execute(
            """
            INSERT INTO applications
                (job_id, user_id, profile_id, job_title, company_name, job_text, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.job_id,
                data.user_id,
                data.profile_id,
                data.job_title,
                data.company_name,
                data.job_text,
                ApplicationStatus.PENDING.value,
            ),
        )
        conn.commit()

        return await self.get_application_by_id(cursor.lastrowid)  # type: ignore

    async def update_application(
        self, job_id: str, data: ApplicationUpdate
    ) -> Application:
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
            return await self.get_application(job_id)

        params.append(job_id)

        conn.execute(
            f"UPDATE applications SET {', '.join(updates)} WHERE job_id = ?", params
        )
        conn.commit()

        return await self.get_application(job_id)

    async def delete_application(self, job_id: str) -> None:
        """Delete an application."""
        conn = self._get_conn()
        conn.execute("DELETE FROM applications WHERE job_id = ?", (job_id,))
        conn.commit()

    def _row_to_application(self, row: sqlite3.Row) -> Application:
        """Convert database row to Application model."""
        return Application(
            id=row["id"],
            job_id=row["job_id"],
            user_id=row["user_id"],
            profile_id=row["profile_id"],
            job_title=row["job_title"],
            company_name=row["company_name"],
            job_text=row["job_text"],
            status=ApplicationStatus(row["status"]),
            compatibility_score=row["compatibility_score"],
            cv_path=row["cv_path"],
            cover_letter_path=row["cover_letter_path"],
            analysis_data=(
                json.loads(row["analysis_data"]) if row["analysis_data"] else None
            ),
            pipeline_data=(
                json.loads(row["pipeline_data"]) if row["pipeline_data"] else None
            ),
            error_message=row["error_message"],
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=(
                datetime.fromisoformat(row["started_at"]) if row["started_at"] else None
            ),
            completed_at=(
                datetime.fromisoformat(row["completed_at"])
                if row["completed_at"]
                else None
            ),
            profile_name=row["profile_name"] if "profile_name" in row.keys() else None,
            profile_slug=row["profile_slug"] if "profile_slug" in row.keys() else None,
        )

    # =========================================================================
    # DEMO DATA SEEDING
    # =========================================================================

    async def _seed_demo_data_if_needed(self) -> None:
        """Seed test user and demo profiles if not already done."""
        settings = await self.get_settings()

        if settings.demo_data_loaded:
            logger.debug("Demo data already loaded")
            return

        logger.info("Seeding demo data...")

        # Create test user
        user = await self.get_user_by_username(TEST_USER.username)
        if user is None:
            user = await self.create_user(TEST_USER)
            logger.info(f"Created test user: {user.username}")

        # Create demo profiles
        for profile_data in DEMO_PROFILES:
            existing = None
            try:
                existing = await self.get_profile_by_slug(profile_data.slug or "")
            except ProfileNotFoundError:
                pass

            if existing is None:
                profile = await self._create_demo_profile(user.id, profile_data)
                logger.info(f"Created demo profile: {profile.name}")

        # Activate default profile
        try:
            await self.activate_profile(DEFAULT_ACTIVE_PROFILE_SLUG)
        except ProfileNotFoundError:
            logger.warning(
                f"Could not activate default profile: {DEFAULT_ACTIVE_PROFILE_SLUG}"
            )

        # Mark as done
        await self.set_setting("demo_data_loaded", True)
        logger.info("Demo data seeding complete")

    async def _create_demo_profile(
        self, user_id: int, data: ProfileCreate
    ) -> Profile:
        """Create a demo profile (sets is_demo=True)."""
        conn = self._get_conn()

        slug = data.slug or _slugify(data.name)

        cursor = conn.execute(
            """
            INSERT INTO profiles
                (user_id, slug, name, title, email, phone, location, summary,
                 is_active, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 1)
            """,
            (
                user_id,
                slug,
                data.name,
                data.title,
                data.email,
                data.phone,
                data.location,
                data.summary,
            ),
        )
        conn.commit()

        profile_id = cursor.lastrowid

        await self._save_profile_skills(profile_id, data.skills)  # type: ignore
        await self._save_profile_experiences(profile_id, data.experiences)  # type: ignore
        await self._save_profile_education(profile_id, data.education)  # type: ignore
        await self._save_profile_certifications(profile_id, data.certifications)  # type: ignore
        await self._save_profile_languages(profile_id, data.languages)  # type: ignore

        return await self.get_profile(profile_id)  # type: ignore


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
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule close for later
                asyncio.create_task(_instance.close())
            else:
                loop.run_until_complete(_instance.close())
        except RuntimeError:
            pass
    _instance = None
