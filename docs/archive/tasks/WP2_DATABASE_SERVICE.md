# Work Package 2: Database Service Implementation

## Overview

This work package implements the DatabaseService with full CRUD operations for the new schema, demo data seeding, and migration logic.

**Prerequisites:** Work Package 1 must be complete (schemas.py, models.py, completeness.py, exceptions.py)

**Reference:** See `docs/tasks/REFACTOR_GUIDE.md` for architectural context.

**Time Estimate:** 3-4 hours

---

## Pre-Implementation Checklist

Before starting, verify WP1 is complete:
```bash
cd /home/user/scout-code  # Or appropriate path
git status  # Should show WP1 changes

# Verify WP1 imports work
python -c "from src.services.database.schemas import SCHEMA_SQL, SCHEMA_VERSION"
python -c "from src.services.database.models import User, Profile, ProfileCreate"
python -c "from src.services.database.completeness import calculate_completeness"
```

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `src/services/database/service.py` | REWRITE | Full DatabaseService implementation |
| `src/services/database/demo_data.py` | REWRITE | Test User + 3 demo profiles |
| `src/services/database/migrations.py` | UPDATE | Use new schema, add migration logic |

---

## Part 1: Demo Data (`demo_data.py`)

**Rewrite file:** `src/services/database/demo_data.py`

### Structure

```python
"""
Demo data for Scout - Test User with 3 profile personas.

These profiles demonstrate different career positioning strategies:
1. Backend Focus - Emphasizes backend/infrastructure skills
2. Full Stack - Balanced frontend + backend
3. DevOps Specialist - Infrastructure and automation focus

All profiles share the same "Test User" owner, demonstrating
multi-profile capability for a single user.
"""

from src.services.database.models import (
    UserCreate,
    ProfileCreate,
    SkillCreate,
    ExperienceCreate,
    EducationCreate,
    CertificationCreate,
    LanguageCreate,
    SkillLevel,
    LanguageProficiency,
)

# =============================================================================
# TEST USER
# =============================================================================

TEST_USER = UserCreate(
    username="test_user",
    email="test@scout.local",
    display_name="Test User",
)

# =============================================================================
# DEMO PROFILES
# =============================================================================

BACKEND_FOCUS_PROFILE = ProfileCreate(
    slug="backend-focus",
    name="Backend Focus",
    title="Senior Backend Engineer",
    email="backend.dev@example.com",
    phone="+1-555-0101",
    location="San Francisco, CA",
    summary=(
        "Backend engineer with 8+ years of experience building scalable distributed systems. "
        "Specialized in Python and Go, with deep expertise in API design, database optimization, "
        "and cloud infrastructure. Proven track record of improving system performance and "
        "reliability at scale. Passionate about clean architecture and mentoring junior engineers."
    ),
    skills=[
        SkillCreate(name="Python", level=SkillLevel.EXPERT, years=8, category="Programming", sort_order=0),
        SkillCreate(name="Go", level=SkillLevel.ADVANCED, years=4, category="Programming", sort_order=1),
        SkillCreate(name="PostgreSQL", level=SkillLevel.EXPERT, years=7, category="Database", sort_order=2),
        SkillCreate(name="Redis", level=SkillLevel.ADVANCED, years=5, category="Database", sort_order=3),
        SkillCreate(name="MongoDB", level=SkillLevel.INTERMEDIATE, years=3, category="Database", sort_order=4),
        SkillCreate(name="Docker", level=SkillLevel.ADVANCED, years=5, category="DevOps", sort_order=5),
        SkillCreate(name="Kubernetes", level=SkillLevel.INTERMEDIATE, years=2, category="DevOps", sort_order=6),
        SkillCreate(name="AWS", level=SkillLevel.ADVANCED, years=5, category="Cloud", sort_order=7),
        SkillCreate(name="REST API Design", level=SkillLevel.EXPERT, years=7, category="Architecture", sort_order=8),
        SkillCreate(name="gRPC", level=SkillLevel.ADVANCED, years=3, category="Architecture", sort_order=9),
        SkillCreate(name="Message Queues", level=SkillLevel.ADVANCED, years=4, category="Architecture", sort_order=10),
        SkillCreate(name="System Design", level=SkillLevel.ADVANCED, years=5, category="Architecture", sort_order=11),
    ],
    experiences=[
        ExperienceCreate(
            title="Senior Backend Engineer",
            company="TechScale Inc.",
            start_date="2021-03",
            end_date=None,  # Current position
            description=(
                "Lead backend engineer for core platform services handling 10M+ daily requests. "
                "Architecting and implementing high-performance microservices in Python and Go."
            ),
            achievements=[
                "Reduced API latency by 60% through query optimization and caching strategies",
                "Designed and implemented event-driven architecture processing 5M events/day",
                "Mentored team of 4 junior engineers on best practices and code review",
                "Led migration from monolith to microservices, improving deployment frequency 10x",
            ],
            sort_order=0,
        ),
        ExperienceCreate(
            title="Backend Engineer",
            company="DataFlow Systems",
            start_date="2018-06",
            end_date="2021-02",
            description=(
                "Built and maintained data pipeline infrastructure for analytics platform "
                "serving Fortune 500 clients."
            ),
            achievements=[
                "Developed real-time data ingestion system handling 100K events/second",
                "Implemented automated testing pipeline reducing bug escape rate by 40%",
                "Optimized database queries reducing average response time from 2s to 200ms",
            ],
            sort_order=1,
        ),
        ExperienceCreate(
            title="Software Developer",
            company="StartupHub",
            start_date="2016-01",
            end_date="2018-05",
            description="Full-stack development for B2B SaaS platform with focus on backend services.",
            achievements=[
                "Built RESTful API serving 50+ enterprise clients",
                "Implemented OAuth 2.0 authentication system",
                "Reduced deployment time from 2 hours to 15 minutes with CI/CD pipeline",
            ],
            sort_order=2,
        ),
    ],
    education=[
        EducationCreate(
            institution="University of California, Berkeley",
            degree="B.S.",
            field="Computer Science",
            start_date="2012-08",
            end_date="2016-05",
            gpa="3.7",
            achievements=["Dean's List - 6 semesters", "Senior thesis on distributed systems"],
            sort_order=0,
        ),
    ],
    certifications=[
        CertificationCreate(
            name="AWS Solutions Architect - Associate",
            issuer="Amazon Web Services",
            date_obtained="2022-03",
            expiry_date="2025-03",
            sort_order=0,
        ),
        CertificationCreate(
            name="Certified Kubernetes Administrator (CKA)",
            issuer="Cloud Native Computing Foundation",
            date_obtained="2023-01",
            expiry_date="2026-01",
            sort_order=1,
        ),
    ],
    languages=[
        LanguageCreate(language="English", proficiency=LanguageProficiency.NATIVE, sort_order=0),
        LanguageCreate(language="Spanish", proficiency=LanguageProficiency.CONVERSATIONAL, sort_order=1),
    ],
)

FULLSTACK_FOCUS_PROFILE = ProfileCreate(
    slug="fullstack-focus",
    name="Full Stack",
    title="Full Stack Developer",
    email="fullstack.dev@example.com",
    phone="+1-555-0102",
    location="Austin, TX",
    summary=(
        "Versatile full-stack developer with 6 years of experience building end-to-end web "
        "applications. Strong expertise in React/TypeScript frontend and Python/Node.js backend. "
        "Passionate about creating intuitive user experiences backed by robust, scalable systems. "
        "Experience leading small teams and delivering projects from concept to production."
    ),
    skills=[
        SkillCreate(name="TypeScript", level=SkillLevel.EXPERT, years=5, category="Programming", sort_order=0),
        SkillCreate(name="JavaScript", level=SkillLevel.EXPERT, years=6, category="Programming", sort_order=1),
        SkillCreate(name="Python", level=SkillLevel.ADVANCED, years=4, category="Programming", sort_order=2),
        SkillCreate(name="React", level=SkillLevel.EXPERT, years=5, category="Frontend", sort_order=3),
        SkillCreate(name="Next.js", level=SkillLevel.ADVANCED, years=3, category="Frontend", sort_order=4),
        SkillCreate(name="Vue.js", level=SkillLevel.INTERMEDIATE, years=2, category="Frontend", sort_order=5),
        SkillCreate(name="Node.js", level=SkillLevel.ADVANCED, years=4, category="Backend", sort_order=6),
        SkillCreate(name="FastAPI", level=SkillLevel.ADVANCED, years=2, category="Backend", sort_order=7),
        SkillCreate(name="PostgreSQL", level=SkillLevel.ADVANCED, years=4, category="Database", sort_order=8),
        SkillCreate(name="GraphQL", level=SkillLevel.ADVANCED, years=3, category="API", sort_order=9),
        SkillCreate(name="Tailwind CSS", level=SkillLevel.EXPERT, years=3, category="Frontend", sort_order=10),
        SkillCreate(name="Testing (Jest/Pytest)", level=SkillLevel.ADVANCED, years=4, category="Quality", sort_order=11),
    ],
    experiences=[
        ExperienceCreate(
            title="Full Stack Developer",
            company="WebCraft Studios",
            start_date="2020-08",
            end_date=None,
            description=(
                "Lead developer for client projects ranging from e-commerce platforms to "
                "SaaS applications. Responsible for full project lifecycle from requirements "
                "to deployment."
            ),
            achievements=[
                "Delivered 15+ production applications for clients across various industries",
                "Implemented reusable component library reducing development time by 30%",
                "Built real-time collaboration features using WebSockets and Redis",
                "Achieved 95+ Lighthouse performance scores on all delivered projects",
            ],
            sort_order=0,
        ),
        ExperienceCreate(
            title="Frontend Developer",
            company="DigitalFirst Agency",
            start_date="2018-03",
            end_date="2020-07",
            description=(
                "Frontend specialist building responsive, accessible web applications "
                "for agency clients."
            ),
            achievements=[
                "Migrated legacy jQuery codebase to React, improving performance 3x",
                "Introduced TypeScript adoption across team of 8 developers",
                "Created accessibility-first component patterns meeting WCAG 2.1 AA standards",
            ],
            sort_order=1,
        ),
    ],
    education=[
        EducationCreate(
            institution="University of Texas at Austin",
            degree="B.S.",
            field="Computer Science",
            start_date="2014-08",
            end_date="2018-05",
            gpa="3.5",
            achievements=["Undergraduate Teaching Assistant - Web Development"],
            sort_order=0,
        ),
    ],
    certifications=[
        CertificationCreate(
            name="Meta Frontend Developer Professional Certificate",
            issuer="Meta",
            date_obtained="2022-06",
            sort_order=0,
        ),
    ],
    languages=[
        LanguageCreate(language="English", proficiency=LanguageProficiency.NATIVE, sort_order=0),
    ],
)

DEVOPS_FOCUS_PROFILE = ProfileCreate(
    slug="devops-focus",
    name="DevOps Specialist",
    title="DevOps Engineer",
    email="devops.eng@example.com",
    phone="+1-555-0103",
    location="Seattle, WA",
    summary=(
        "DevOps engineer with 5 years of experience building and maintaining cloud infrastructure. "
        "Expert in Kubernetes, Terraform, and CI/CD pipelines. Focused on reliability, automation, "
        "and enabling development teams to ship faster with confidence. Strong background in "
        "security best practices and cost optimization."
    ),
    skills=[
        SkillCreate(name="Kubernetes", level=SkillLevel.EXPERT, years=4, category="Orchestration", sort_order=0),
        SkillCreate(name="Terraform", level=SkillLevel.EXPERT, years=4, category="IaC", sort_order=1),
        SkillCreate(name="AWS", level=SkillLevel.EXPERT, years=5, category="Cloud", sort_order=2),
        SkillCreate(name="GCP", level=SkillLevel.ADVANCED, years=3, category="Cloud", sort_order=3),
        SkillCreate(name="Docker", level=SkillLevel.EXPERT, years=5, category="Containers", sort_order=4),
        SkillCreate(name="Python", level=SkillLevel.ADVANCED, years=4, category="Programming", sort_order=5),
        SkillCreate(name="Bash/Shell", level=SkillLevel.EXPERT, years=6, category="Programming", sort_order=6),
        SkillCreate(name="GitHub Actions", level=SkillLevel.EXPERT, years=3, category="CI/CD", sort_order=7),
        SkillCreate(name="ArgoCD", level=SkillLevel.ADVANCED, years=2, category="CI/CD", sort_order=8),
        SkillCreate(name="Prometheus/Grafana", level=SkillLevel.ADVANCED, years=3, category="Monitoring", sort_order=9),
        SkillCreate(name="Helm", level=SkillLevel.ADVANCED, years=3, category="Orchestration", sort_order=10),
        SkillCreate(name="Linux Administration", level=SkillLevel.EXPERT, years=6, category="Systems", sort_order=11),
    ],
    experiences=[
        ExperienceCreate(
            title="Senior DevOps Engineer",
            company="CloudNative Corp",
            start_date="2022-01",
            end_date=None,
            description=(
                "Lead infrastructure engineer for multi-region Kubernetes platform serving "
                "200+ microservices and 50+ development teams."
            ),
            achievements=[
                "Designed and implemented multi-region K8s platform with 99.99% uptime SLA",
                "Reduced infrastructure costs by 40% through right-sizing and spot instances",
                "Implemented GitOps workflow with ArgoCD reducing deployment errors by 80%",
                "Built self-service platform enabling teams to deploy without DevOps involvement",
            ],
            sort_order=0,
        ),
        ExperienceCreate(
            title="DevOps Engineer",
            company="ScaleUp Technologies",
            start_date="2019-06",
            end_date="2021-12",
            description=(
                "Built and maintained CI/CD infrastructure and cloud platform for "
                "rapidly growing SaaS company."
            ),
            achievements=[
                "Migrated on-premise infrastructure to AWS, reducing ops burden by 60%",
                "Implemented infrastructure-as-code with Terraform for all environments",
                "Built automated security scanning into CI pipeline catching 95% of vulnerabilities",
                "Reduced deployment time from 45 minutes to 5 minutes",
            ],
            sort_order=1,
        ),
    ],
    education=[
        EducationCreate(
            institution="University of Washington",
            degree="B.S.",
            field="Information Systems",
            start_date="2015-09",
            end_date="2019-06",
            gpa="3.6",
            achievements=["Capstone: Automated Cloud Deployment System"],
            sort_order=0,
        ),
    ],
    certifications=[
        CertificationCreate(
            name="AWS Solutions Architect - Professional",
            issuer="Amazon Web Services",
            date_obtained="2022-08",
            expiry_date="2025-08",
            sort_order=0,
        ),
        CertificationCreate(
            name="Certified Kubernetes Administrator (CKA)",
            issuer="Cloud Native Computing Foundation",
            date_obtained="2021-03",
            expiry_date="2024-03",
            sort_order=1,
        ),
        CertificationCreate(
            name="HashiCorp Certified: Terraform Associate",
            issuer="HashiCorp",
            date_obtained="2021-09",
            expiry_date="2024-09",
            sort_order=2,
        ),
    ],
    languages=[
        LanguageCreate(language="English", proficiency=LanguageProficiency.NATIVE, sort_order=0),
        LanguageCreate(language="Mandarin", proficiency=LanguageProficiency.CONVERSATIONAL, sort_order=1),
    ],
)

# List of all demo profiles for iteration
DEMO_PROFILES: list[ProfileCreate] = [
    BACKEND_FOCUS_PROFILE,
    FULLSTACK_FOCUS_PROFILE,
    DEVOPS_FOCUS_PROFILE,
]

# The first profile should be active by default
DEFAULT_ACTIVE_PROFILE_SLUG = "backend-focus"
```

---

## Part 2: Migrations (`migrations.py`)

**Update file:** `src/services/database/migrations.py`

### Requirements

1. Import `SCHEMA_SQL` and `SCHEMA_VERSION` from `schemas.py`
2. Update `initialize_database()` to use the new schema
3. Add migration logic from v1 to v2 (drop old tables, create new)
4. Keep the migration framework extensible for future versions

### Implementation

```python
"""Database migrations and schema setup."""

import logging
import sqlite3
from pathlib import Path

from src.services.database.exceptions import MigrationError
from src.services.database.schemas import SCHEMA_SQL, SCHEMA_VERSION, get_drop_tables_sql

logger = logging.getLogger(__name__)


def initialize_database(db_path: Path) -> sqlite3.Connection:
    """
    Initialize database with schema.

    Args:
        db_path: Path to SQLite database file.

    Returns:
        Database connection.

    Raises:
        MigrationError: If schema creation fails.
    """
    try:
        # Ensure directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect with row factory for dict-like access
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row

        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")

        # Check if this is a fresh database or needs migration
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='settings'"
        )
        settings_exists = cursor.fetchone() is not None

        if not settings_exists:
            # Fresh database - create schema
            logger.info("Creating fresh database schema")
            conn.executescript(SCHEMA_SQL)
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?)",
                ("schema_version", str(SCHEMA_VERSION))
            )
            conn.commit()
        else:
            # Existing database - check version and migrate if needed
            run_migrations(conn)

        logger.info(f"Database initialized: {db_path}")
        return conn

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise MigrationError(f"Failed to initialize database: {e}") from e


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Get current schema version from database."""
    try:
        cursor = conn.execute(
            "SELECT value FROM settings WHERE key = 'schema_version'"
        )
        row = cursor.fetchone()
        return int(row["value"]) if row else 0
    except sqlite3.OperationalError:
        # Settings table doesn't exist
        return 0


def run_migrations(conn: sqlite3.Connection) -> None:
    """
    Run any pending migrations.

    Migrations are run sequentially from current version to target version.
    """
    current_version = get_schema_version(conn)

    if current_version == SCHEMA_VERSION:
        logger.debug(f"Database already at version {SCHEMA_VERSION}")
        return

    if current_version > SCHEMA_VERSION:
        raise MigrationError(
            f"Database version {current_version} is newer than code version {SCHEMA_VERSION}"
        )

    logger.info(f"Migrating database from v{current_version} to v{SCHEMA_VERSION}")

    try:
        # Run each migration step
        if current_version < 2:
            _migrate_v1_to_v2(conn)

        # Update version
        conn.execute(
            "UPDATE settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = 'schema_version'",
            (str(SCHEMA_VERSION),)
        )
        conn.commit()
        logger.info(f"Migration complete - now at v{SCHEMA_VERSION}")

    except Exception as e:
        conn.rollback()
        raise MigrationError(f"Migration failed: {e}") from e


def _migrate_v1_to_v2(conn: sqlite3.Connection) -> None:
    """
    Migrate from v1 (flat profiles) to v2 (normalized user/profile).

    This is a destructive migration that drops old data.
    In production, you would want to preserve and transform data.
    For the PoC, we simply recreate the schema.
    """
    logger.warning("Migrating v1 to v2 - this will reset all profile data")

    # Drop all old tables
    drop_sql = get_drop_tables_sql()
    conn.executescript(drop_sql)

    # Create new schema
    conn.executescript(SCHEMA_SQL)

    # Reset demo_data_loaded so it will be re-seeded
    conn.execute(
        """
        INSERT OR REPLACE INTO settings (key, value, updated_at)
        VALUES ('demo_data_loaded', 'false', CURRENT_TIMESTAMP)
        """
    )

    logger.info("v1 to v2 migration complete - schema recreated")


def reset_database(conn: sqlite3.Connection) -> None:
    """
    Reset database to fresh state.

    WARNING: This deletes all data!
    Used for testing and development.
    """
    logger.warning("Resetting database - all data will be lost")

    drop_sql = get_drop_tables_sql()
    conn.executescript(drop_sql)
    conn.executescript(SCHEMA_SQL)

    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
        ("schema_version", str(SCHEMA_VERSION))
    )
    conn.commit()

    logger.info("Database reset complete")
```

---

## Part 3: Database Service (`service.py`)

**Rewrite file:** `src/services/database/service.py`

This is the largest file. Implement in sections.

### Section 1: Imports and Helpers

```python
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
    NoActiveProfileError,
    ProfileNotFoundError,
    ProfileSlugExistsError,
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


def _parse_json_list(value: str | None) -> list[str]:
    """Parse JSON string to list, returning empty list if None or invalid."""
    if not value:
        return []
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []
```

### Section 2: DatabaseService Class - Init and Lifecycle

```python
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
```

### Section 3: Settings Operations

```python
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
            (key, str_value, str_value)
        )
        conn.commit()
```

### Section 4: User Operations

```python
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
            (data.username, data.email, data.display_name)
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
```

### Section 5: Profile CRUD Operations

```python
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
                (SELECT COUNT(*) FROM profile_skills WHERE profile_id = p.id) as skill_count,
                (SELECT COUNT(*) FROM profile_experiences WHERE profile_id = p.id) as experience_count,
                (SELECT COUNT(*) FROM profile_education WHERE profile_id = p.id) as education_count,
                (SELECT COUNT(*) FROM profile_certifications WHERE profile_id = p.id) as certification_count,
                (SELECT COUNT(*) FROM profile_languages WHERE profile_id = p.id) as language_count,
                (SELECT COUNT(*) FROM applications WHERE profile_id = p.id) as application_count,
                (SELECT COUNT(*) FROM applications WHERE profile_id = p.id AND status = 'completed') as completed_application_count,
                (SELECT AVG(compatibility_score) FROM applications WHERE profile_id = p.id AND compatibility_score IS NOT NULL) as avg_compatibility_score
            FROM profiles p
            WHERE p.user_id = ?
            ORDER BY p.is_active DESC, p.updated_at DESC
            """,
            (user_id,)
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
            (user_id,)
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
            INSERT INTO profiles (user_id, slug, name, title, email, phone, location, summary, is_active, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
            """,
            (user_id, slug, data.name, data.title, data.email, data.phone, data.location, data.summary)
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
                f"UPDATE profiles SET {', '.join(updates)} WHERE id = ?",
                params
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
            "UPDATE profiles SET is_active = 0 WHERE user_id = ?",
            (profile.user_id,)
        )

        # Activate this one
        conn.execute(
            "UPDATE profiles SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (profile.id,)
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
```

### Section 6: Profile Related Data Operations

```python
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
            avg_compatibility_score=round(row["avg_compatibility_score"], 1) if row["avg_compatibility_score"] else None,
        )

    # --- Skills ---

    async def _load_profile_skills(self, profile_id: int) -> list[Skill]:
        """Load skills for a profile."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM profile_skills WHERE profile_id = ? ORDER BY sort_order",
            (profile_id,)
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

    async def _save_profile_skills(self, profile_id: int, skills: list[SkillCreate]) -> None:
        """Save skills for a profile."""
        conn = self._get_conn()
        for skill in skills:
            conn.execute(
                """
                INSERT INTO profile_skills (profile_id, name, level, years, category, sort_order)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (profile_id, skill.name, skill.level.value if skill.level else None, 
                 skill.years, skill.category, skill.sort_order)
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
            (profile_id,)
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

    async def _save_profile_experiences(self, profile_id: int, experiences: list[ExperienceCreate]) -> None:
        """Save experiences for a profile."""
        conn = self._get_conn()
        for exp in experiences:
            conn.execute(
                """
                INSERT INTO profile_experiences (profile_id, title, company, start_date, end_date, description, achievements, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (profile_id, exp.title, exp.company, exp.start_date, exp.end_date,
                 exp.description, json.dumps(exp.achievements), exp.sort_order)
            )
        conn.commit()

    async def _delete_profile_experiences(self, profile_id: int) -> None:
        """Delete all experiences for a profile."""
        conn = self._get_conn()
        conn.execute("DELETE FROM profile_experiences WHERE profile_id = ?", (profile_id,))
        conn.commit()

    # --- Education ---

    async def _load_profile_education(self, profile_id: int) -> list[Education]:
        """Load education for a profile."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM profile_education WHERE profile_id = ? ORDER BY sort_order",
            (profile_id,)
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

    async def _save_profile_education(self, profile_id: int, education: list[EducationCreate]) -> None:
        """Save education for a profile."""
        conn = self._get_conn()
        for edu in education:
            conn.execute(
                """
                INSERT INTO profile_education (profile_id, institution, degree, field, start_date, end_date, gpa, achievements, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (profile_id, edu.institution, edu.degree, edu.field, edu.start_date,
                 edu.end_date, edu.gpa, json.dumps(edu.achievements), edu.sort_order)
            )
        conn.commit()

    async def _delete_profile_education(self, profile_id: int) -> None:
        """Delete all education for a profile."""
        conn = self._get_conn()
        conn.execute("DELETE FROM profile_education WHERE profile_id = ?", (profile_id,))
        conn.commit()

    # --- Certifications ---

    async def _load_profile_certifications(self, profile_id: int) -> list[Certification]:
        """Load certifications for a profile."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM profile_certifications WHERE profile_id = ? ORDER BY sort_order",
            (profile_id,)
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

    async def _save_profile_certifications(self, profile_id: int, certifications: list[CertificationCreate]) -> None:
        """Save certifications for a profile."""
        conn = self._get_conn()
        for cert in certifications:
            conn.execute(
                """
                INSERT INTO profile_certifications (profile_id, name, issuer, date_obtained, expiry_date, credential_url, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (profile_id, cert.name, cert.issuer, cert.date_obtained,
                 cert.expiry_date, cert.credential_url, cert.sort_order)
            )
        conn.commit()

    async def _delete_profile_certifications(self, profile_id: int) -> None:
        """Delete all certifications for a profile."""
        conn = self._get_conn()
        conn.execute("DELETE FROM profile_certifications WHERE profile_id = ?", (profile_id,))
        conn.commit()

    # --- Languages ---

    async def _load_profile_languages(self, profile_id: int) -> list[Language]:
        """Load languages for a profile."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM profile_languages WHERE profile_id = ? ORDER BY sort_order",
            (profile_id,)
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

    async def _save_profile_languages(self, profile_id: int, languages: list[LanguageCreate]) -> None:
        """Save languages for a profile."""
        conn = self._get_conn()
        for lang in languages:
            conn.execute(
                """
                INSERT INTO profile_languages (profile_id, language, proficiency, sort_order)
                VALUES (?, ?, ?, ?)
                """,
                (profile_id, lang.language, lang.proficiency.value if lang.proficiency else None, lang.sort_order)
            )
        conn.commit()

    async def _delete_profile_languages(self, profile_id: int) -> None:
        """Delete all languages for a profile."""
        conn = self._get_conn()
        conn.execute("DELETE FROM profile_languages WHERE profile_id = ?", (profile_id,))
        conn.commit()
```

### Section 7: Application Operations

```python
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
            f"SELECT COUNT(*) FROM applications a WHERE {where_sql}",
            params
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
            query_params
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
            (job_id,)
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
            (app_id,)
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
            INSERT INTO applications (job_id, user_id, profile_id, job_title, company_name, job_text, status)
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
            )
        )
        conn.commit()

        return await self.get_application_by_id(cursor.lastrowid)  # type: ignore

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
            return await self.get_application(job_id)

        params.append(job_id)

        conn.execute(
            f"UPDATE applications SET {', '.join(updates)} WHERE job_id = ?",
            params
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
            analysis_data=json.loads(row["analysis_data"]) if row["analysis_data"] else None,
            pipeline_data=json.loads(row["pipeline_data"]) if row["pipeline_data"] else None,
            error_message=row["error_message"],
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            profile_name=row["profile_name"] if "profile_name" in row.keys() else None,
            profile_slug=row["profile_slug"] if "profile_slug" in row.keys() else None,
        )
```

### Section 8: Demo Data Seeding and Singleton

```python
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
            logger.warning(f"Could not activate default profile: {DEFAULT_ACTIVE_PROFILE_SLUG}")

        # Mark as done
        await self.set_setting("demo_data_loaded", True)
        logger.info("Demo data seeding complete")

    async def _create_demo_profile(self, user_id: int, data: ProfileCreate) -> Profile:
        """Create a demo profile (sets is_demo=True)."""
        conn = self._get_conn()

        slug = data.slug or _slugify(data.name)

        cursor = conn.execute(
            """
            INSERT INTO profiles (user_id, slug, name, title, email, phone, location, summary, is_active, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 1)
            """,
            (user_id, slug, data.name, data.title, data.email, data.phone, data.location, data.summary)
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
```

---

## Part 4: Update `__init__.py`

Add the new imports from `demo_data.py`:

```python
# Add to __init__.py
from .demo_data import (
    TEST_USER,
    DEMO_PROFILES,
    BACKEND_FOCUS_PROFILE,
    FULLSTACK_FOCUS_PROFILE,
    DEVOPS_FOCUS_PROFILE,
    DEFAULT_ACTIVE_PROFILE_SLUG,
)

# Add to __all__
"TEST_USER",
"DEMO_PROFILES", 
"BACKEND_FOCUS_PROFILE",
"FULLSTACK_FOCUS_PROFILE",
"DEVOPS_FOCUS_PROFILE",
"DEFAULT_ACTIVE_PROFILE_SLUG",
```

---

## Validation Steps

### 1. Delete Old Database and Test Fresh Init

```bash
# Remove old database
rm -f data/scout.db

# Test initialization
python -c "
import asyncio
from src.services.database import get_database_service

async def test():
    db = await get_database_service()
    
    # Check user created
    user = await db.get_current_user()
    print(f'User: {user.username} ({user.display_name})')
    
    # Check profiles created
    profiles = await db.list_profiles()
    print(f'Profiles: {len(profiles)}')
    for p in profiles:
        print(f'  - {p.name} ({p.slug}) [active={p.is_active}]')
        print(f'    Skills: {p.skill_count}, Exp: {p.experience_count}')
    
    # Check active profile
    active = await db.get_active_profile()
    print(f'Active: {active.name if active else None}')
    
    # Check completeness
    from src.services.database import calculate_completeness
    if active:
        comp = calculate_completeness(active)
        print(f'Completeness: {comp.overall_score}% ({comp.level})')

asyncio.run(test())
"
```

### 2. Test Profile CRUD

```bash
python -c "
import asyncio
from src.services.database import (
    get_database_service,
    ProfileCreate,
    ProfileUpdate,
    SkillCreate,
    SkillLevel,
)

async def test():
    db = await get_database_service()
    user = await db.get_current_user()
    
    # Create new profile
    new_profile = await db.create_profile(user.id, ProfileCreate(
        name='Test Profile',
        title='Test Engineer',
        summary='A test profile',
        skills=[
            SkillCreate(name='Testing', level=SkillLevel.EXPERT, years=5),
        ],
    ))
    print(f'Created: {new_profile.name} ({new_profile.slug})')
    print(f'  Skills: {len(new_profile.skills)}')
    
    # Update profile
    updated = await db.update_profile(new_profile.slug, ProfileUpdate(
        title='Senior Test Engineer',
        skills=[
            SkillCreate(name='Testing', level=SkillLevel.EXPERT, years=6),
            SkillCreate(name='Automation', level=SkillLevel.ADVANCED, years=3),
        ],
    ))
    print(f'Updated: {updated.title}')
    print(f'  Skills: {len(updated.skills)}')
    
    # Delete profile
    await db.delete_profile(new_profile.slug)
    print('Deleted')
    
    # Verify deletion
    profiles = await db.list_profiles()
    slugs = [p.slug for p in profiles]
    assert new_profile.slug not in slugs
    print('Verified deletion')

asyncio.run(test())
"
```

### 3. Test Application Operations

```bash
python -c "
import asyncio
from src.services.database import (
    get_database_service,
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationStatus,
)

async def test():
    db = await get_database_service()
    user = await db.get_current_user()
    active = await db.get_active_profile()
    
    # Create application
    app = await db.create_application(ApplicationCreate(
        job_id='test-job-001',
        user_id=user.id,
        profile_id=active.id,
        job_title='Test Position',
        company_name='Test Corp',
        job_text='This is a test job posting...',
    ))
    print(f'Created application: {app.job_id}')
    
    # Update application
    updated = await db.update_application('test-job-001', ApplicationUpdate(
        status=ApplicationStatus.COMPLETED,
        compatibility_score=85.5,
    ))
    print(f'Updated: status={updated.status.value}, score={updated.compatibility_score}')
    
    # List applications
    apps, total = await db.list_applications(user_id=user.id)
    print(f'Total applications: {total}')
    
    # Cleanup
    await db.delete_application('test-job-001')
    print('Cleaned up')

asyncio.run(test())
"
```

### 4. Run Existing Tests (Expect Some Failures)

```bash
# These may fail due to model changes - that's expected
# They will be fixed in WP3
pytest tests/test_database_service.py -v --tb=short 2>&1 | head -50
```

---

## Completion Checklist

- [ ] `demo_data.py` rewritten with Test User + 3 profiles
- [ ] `migrations.py` updated with v1→v2 migration
- [ ] `service.py` completely rewritten with all operations
- [ ] `__init__.py` updated with demo data exports
- [ ] Fresh database initialization works
- [ ] Demo data seeds correctly
- [ ] Profile CRUD operations work
- [ ] Application operations work
- [ ] Code committed

```bash
git add src/services/database/
git commit -m "WP2: Implement DatabaseService with User/Profile architecture

- Full CRUD operations for users, profiles, and applications
- Normalized profile data (skills, experiences, education, etc.)
- Demo data: Test User with 3 profile personas
- Migration from v1 to v2 schema
- Profile completeness scoring integration"
```

---

## Notes for Work Package 3

WP3 will cover:
1. Update `src/modules/collector/models.py` - rename `UserProfile` → `Profile` 
2. Update Collector to load from new database schema
3. Update API routes for new profile structure
4. Update all tests
5. Integration testing

**Key change:** The Collector's `UserProfile` model will be replaced by importing `Profile` from the database module, or we create a separate `CVProfile` model that can be constructed from the database `Profile`.
