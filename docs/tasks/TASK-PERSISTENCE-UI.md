# Task: Persistence & UI Consolidation

## Overview

**Task ID:** SCOUT-PERSISTENCE-UI  
**Priority:** High  
**Total Estimated Effort:** 6-9 hours (3 phases)  
**Dependencies:** API Hardening (complete), Refactoring (complete)

Implement SQLite-based persistence for profiles and applications, support multiple profiles, and consolidate the web UI for a coherent user experience suitable for thesis demonstration.

---

## Objectives

1. **Persist profiles** in SQLite with multi-profile support
2. **Persist applications** including generated PDFs, surviving restarts
3. **Synchronize** active profile with ChromaDB (clear & re-index on switch)
4. **Consolidate UI** into fewer, more consistent pages
5. **Pre-load synthetic demo profiles** for demonstration purposes

---

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database | SQLite | Single file, production-like, easy backup |
| Vector Store | ChromaDB (keep) | Already working, clear on profile switch |
| Profile Storage | DB + JSON blob | Structured queries + flexible profile data |
| Application Storage | Full persistence | Job text, analysis, PDFs - enables analytics |
| Re-indexing | Clear & rebuild | Simpler than multi-collection |
| Demo Profiles | Pre-load on first run | Always available for demonstration |

---

## Database Schema

**File:** `data/scout.db`

### Tables

```sql
-- Application settings (singleton-ish)
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User profiles
CREATE TABLE profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- Display name: "Senior Developer Profile"
    slug TEXT UNIQUE NOT NULL,             -- URL-safe: "senior-developer-profile"
    full_name TEXT NOT NULL,               -- Resume name: "Emma Chen"
    email TEXT,
    title TEXT,                            -- "Full-Stack Developer"
    profile_data TEXT NOT NULL,            -- JSON blob (full UserProfile)
    is_active INTEGER DEFAULT 0,           -- Only one active at a time
    is_indexed INTEGER DEFAULT 0,          -- Has ChromaDB embeddings
    is_demo INTEGER DEFAULT 0,             -- Is a demo/example profile
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Job applications
CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT UNIQUE NOT NULL,           -- 8-char ID: "abc12345"
    profile_id INTEGER NOT NULL,           -- FK to profiles
    job_title TEXT,
    company_name TEXT,
    job_text TEXT,                         -- Original posting
    status TEXT DEFAULT 'pending',         -- pending, running, completed, failed
    compatibility_score INTEGER,
    cv_path TEXT,                          -- "/data/outputs/cv_abc12345.pdf"
    cover_letter_path TEXT,
    analysis_data TEXT,                    -- JSON blob (full AnalysisResult)
    pipeline_data TEXT,                    -- JSON blob (step timings, etc.)
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id)
);

-- Indexes for common queries
CREATE INDEX idx_profiles_active ON profiles(is_active);
CREATE INDEX idx_profiles_slug ON profiles(slug);
CREATE INDEX idx_applications_profile ON applications(profile_id);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_created ON applications(created_at DESC);
```

### Settings Keys

| Key | Value | Description |
|-----|-------|-------------|
| `active_profile_id` | `1` | Currently active profile ID |
| `schema_version` | `1` | For future migrations |
| `demo_data_loaded` | `true` | Whether demo profiles were loaded |

---

## File Structure Changes

### New Files to Create

```
src/
├── services/
│   └── database/                    # NEW: Database service
│       ├── __init__.py
│       ├── models.py                # SQLAlchemy/Pydantic models
│       ├── service.py               # Database operations
│       ├── migrations.py            # Schema setup & migrations
│       └── exceptions.py
│
├── web/
│   └── routes/
│       └── api/
│           └── v1/
│               └── profiles.py      # NEW: Multi-profile CRUD endpoints
│               └── applications.py  # ENHANCED: Persistent applications

data/
├── scout.db                         # NEW: SQLite database
├── outputs/                         # NEW: Persistent PDF storage
│   ├── cv_abc12345.pdf
│   └── cl_abc12345.pdf
└── chroma/                          # EXISTING: Vector store
```

### Files to Modify

```
src/web/routes/api/v1/jobs.py        # Use DB for job storage
src/web/routes/api/v1/profile.py     # Integrate with DB service
src/web/dependencies.py              # Remove in-memory JobStore
src/modules/collector/collector.py   # Load profile from DB
src/services/pipeline/pipeline.py    # Save results to DB
src/web/templates/profile_edit.html  # Change "Your Name" → "Test User"
src/web/templates/profiles_list.html # Consolidate UI
src/web/templates/index.html         # Show active profile info
src/web/templates/partials/navbar.html # Dynamic profile name
src/web/static/js/common.js          # Profile switching logic
```

### Files to Delete

```
src/web/templates/profile.html       # Redundant
src/web/templates/profile_editor.html # Merge into profile_edit.html
src/web/templates/profile_detail.html # Merge into profiles list
```

---

## Pre-Flight Checklist

```bash
# SSH to Pi
ssh cally@192.168.1.21

# Navigate to project
cd /home/cally/projects/scout-code
source venv/bin/activate

# Verify current state
pytest tests/ -q --tb=no
# Expected: 680+ passed

# Check disk space for new DB
df -h /home/cally/projects/scout-code/data

# Backup current profile if exists
cp data/profile.yaml data/profile.yaml.backup 2>/dev/null || echo "No existing profile"

# Commit current state
git add -A
git commit -m "chore: pre-persistence checkpoint"
```

---

# Phase P1: Data Layer

**Estimated Time:** 2-3 hours  
**Goal:** SQLite database service with models and migrations

## P1.1: Create Database Service Package

### File: `src/services/database/__init__.py`

```python
"""
Database Service

SQLite-based persistence for profiles and applications.

Usage:
    from src.services.database import get_database_service, Profile, Application

    db = await get_database_service()
    profiles = await db.list_profiles()
    await db.create_profile(profile_data)
"""

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
from src.services.database.service import (
    DatabaseService,
    get_database_service,
    reset_database_service,
)

__all__ = [
    # Service
    "DatabaseService",
    "get_database_service",
    "reset_database_service",
    # Models
    "Profile",
    "ProfileCreate",
    "ProfileUpdate",
    "Application",
    "ApplicationCreate",
    "ApplicationUpdate",
    "ApplicationStatus",
    "Settings",
]
```

### File: `src/services/database/exceptions.py`

```python
"""Database service exceptions."""


class DatabaseError(Exception):
    """Base database error."""
    pass


class ProfileNotFoundError(DatabaseError):
    """Profile not found."""
    pass


class ProfileExistsError(DatabaseError):
    """Profile with this slug already exists."""
    pass


class ApplicationNotFoundError(DatabaseError):
    """Application not found."""
    pass


class MigrationError(DatabaseError):
    """Database migration failed."""
    pass
```

### File: `src/services/database/models.py`

```python
"""Database models using Pydantic."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, computed_field


class ApplicationStatus(str, Enum):
    """Application processing status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# PROFILE MODELS
# =============================================================================


class ProfileBase(BaseModel):
    """Base profile fields."""
    name: str = Field(..., min_length=1, max_length=200)
    full_name: str = Field(..., min_length=1, max_length=200)
    email: str | None = None
    title: str | None = None


class ProfileCreate(ProfileBase):
    """Profile creation request."""
    profile_data: dict[str, Any]  # Full UserProfile as dict
    is_active: bool = False
    is_demo: bool = False


class ProfileUpdate(BaseModel):
    """Profile update request (all fields optional)."""
    name: str | None = None
    full_name: str | None = None
    email: str | None = None
    title: str | None = None
    profile_data: dict[str, Any] | None = None
    is_active: bool | None = None


class Profile(ProfileBase):
    """Profile database record."""
    id: int
    slug: str
    profile_data: dict[str, Any]
    is_active: bool = False
    is_indexed: bool = False
    is_demo: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def display_name(self) -> str:
        """Display name for UI."""
        return self.name or self.full_name


# =============================================================================
# APPLICATION MODELS
# =============================================================================


class ApplicationBase(BaseModel):
    """Base application fields."""
    job_title: str | None = None
    company_name: str | None = None


class ApplicationCreate(ApplicationBase):
    """Application creation request."""
    job_id: str
    profile_id: int
    job_text: str


class ApplicationUpdate(BaseModel):
    """Application update request."""
    job_title: str | None = None
    company_name: str | None = None
    status: ApplicationStatus | None = None
    compatibility_score: int | None = None
    cv_path: str | None = None
    cover_letter_path: str | None = None
    analysis_data: dict[str, Any] | None = None
    pipeline_data: dict[str, Any] | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class Application(ApplicationBase):
    """Application database record."""
    id: int
    job_id: str
    profile_id: int
    job_text: str
    status: ApplicationStatus = ApplicationStatus.PENDING
    compatibility_score: int | None = None
    cv_path: str | None = None
    cover_letter_path: str | None = None
    analysis_data: dict[str, Any] | None = None
    pipeline_data: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Joined data
    profile_name: str | None = None

    model_config = {"from_attributes": True}


# =============================================================================
# SETTINGS MODEL
# =============================================================================


class Settings(BaseModel):
    """Application settings."""
    active_profile_id: int | None = None
    schema_version: int = 1
    demo_data_loaded: bool = False
```

### File: `src/services/database/migrations.py`

```python
"""Database migrations and schema setup."""

import json
import logging
import sqlite3
from pathlib import Path

from src.services.database.exceptions import MigrationError

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

SCHEMA_SQL = """
-- Application settings
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User profiles
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT,
    title TEXT,
    profile_data TEXT NOT NULL,
    is_active INTEGER DEFAULT 0,
    is_indexed INTEGER DEFAULT 0,
    is_demo INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Job applications
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT UNIQUE NOT NULL,
    profile_id INTEGER NOT NULL,
    job_title TEXT,
    company_name TEXT,
    job_text TEXT,
    status TEXT DEFAULT 'pending',
    compatibility_score INTEGER,
    cv_path TEXT,
    cover_letter_path TEXT,
    analysis_data TEXT,
    pipeline_data TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_profiles_active ON profiles(is_active);
CREATE INDEX IF NOT EXISTS idx_profiles_slug ON profiles(slug);
CREATE INDEX IF NOT EXISTS idx_applications_profile ON applications(profile_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_created ON applications(created_at DESC);
"""


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
        
        # Create schema
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        
        # Set schema version if not exists
        cursor = conn.execute(
            "SELECT value FROM settings WHERE key = 'schema_version'"
        )
        if cursor.fetchone() is None:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?)",
                ("schema_version", str(SCHEMA_VERSION))
            )
            conn.commit()
        
        logger.info(f"Database initialized: {db_path}")
        return conn
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise MigrationError(f"Failed to initialize database: {e}") from e


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Get current schema version."""
    cursor = conn.execute(
        "SELECT value FROM settings WHERE key = 'schema_version'"
    )
    row = cursor.fetchone()
    return int(row["value"]) if row else 0


def run_migrations(conn: sqlite3.Connection) -> None:
    """
    Run any pending migrations.
    
    Currently a placeholder for future schema updates.
    """
    current_version = get_schema_version(conn)
    
    if current_version < SCHEMA_VERSION:
        logger.info(f"Migrating from v{current_version} to v{SCHEMA_VERSION}")
        # Add migration logic here as needed
        
        conn.execute(
            "UPDATE settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = 'schema_version'",
            (str(SCHEMA_VERSION),)
        )
        conn.commit()
        logger.info("Migration complete")
```

### File: `src/services/database/service.py`

```python
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
```

## P1.2: Create Demo Data Loader

### File: `src/services/database/demo_data.py`

```python
"""Demo data for initial database population."""

import logging
from datetime import datetime

from src.services.database.models import ProfileCreate
from src.services.database.service import DatabaseService

logger = logging.getLogger(__name__)


# =============================================================================
# DEMO PROFILES
# =============================================================================

DEMO_PROFILES = [
    {
        "name": "Emma Chen - Full-Stack Developer",
        "full_name": "Emma Chen",
        "email": "emma.chen@example.com",
        "title": "Full-Stack Developer",
        "profile_data": {
            "full_name": "Emma Chen",
            "email": "emma.chen@example.com",
            "phone": "+45 12 34 56 78",
            "location": "Copenhagen, Denmark",
            "linkedin_url": "https://linkedin.com/in/emmachen",
            "github_url": "https://github.com/emmachen",
            "title": "Full-Stack Developer",
            "years_experience": 4.0,
            "summary": "Passionate full-stack developer with 4 years of experience building scalable web applications. Strong background in Python and React, with a focus on clean architecture and user experience. Previously worked at a Danish fintech startup where I led the development of their customer-facing platform. I thrive in collaborative environments and enjoy mentoring junior developers.",
            "skills": [
                {"name": "Python", "level": "advanced", "years": 4, "keywords": ["FastAPI", "Django", "Flask"]},
                {"name": "JavaScript", "level": "advanced", "years": 4, "keywords": ["ES6+", "Node.js"]},
                {"name": "TypeScript", "level": "intermediate", "years": 2, "keywords": []},
                {"name": "React", "level": "advanced", "years": 3, "keywords": ["Redux", "Next.js", "Hooks"]},
                {"name": "PostgreSQL", "level": "intermediate", "years": 3, "keywords": ["SQL", "Database Design"]},
                {"name": "Docker", "level": "intermediate", "years": 2, "keywords": ["Docker Compose", "Containerization"]},
                {"name": "AWS", "level": "intermediate", "years": 2, "keywords": ["EC2", "S3", "Lambda", "RDS"]},
                {"name": "Git", "level": "advanced", "years": 4, "keywords": ["GitHub", "GitLab", "CI/CD"]},
                {"name": "REST APIs", "level": "advanced", "years": 4, "keywords": ["OpenAPI", "API Design"]},
                {"name": "Agile", "level": "intermediate", "years": 3, "keywords": ["Scrum", "Kanban"]}
            ],
            "experiences": [
                {
                    "company": "PayFlow ApS",
                    "role": "Full-Stack Developer",
                    "start_date": "2022-03-01T00:00:00",
                    "end_date": None,
                    "current": True,
                    "description": "Lead developer for customer-facing payment platform serving 50,000+ users. Architected and implemented new features using Python/FastAPI backend and React frontend.",
                    "achievements": [
                        "Reduced page load time by 40% through code optimization and caching strategies",
                        "Implemented real-time transaction monitoring dashboard used by operations team",
                        "Mentored 2 junior developers, conducting code reviews and pair programming sessions",
                        "Led migration from monolith to microservices architecture"
                    ],
                    "technologies": ["Python", "FastAPI", "React", "PostgreSQL", "Redis", "AWS"]
                },
                {
                    "company": "TechStart Copenhagen",
                    "role": "Junior Developer",
                    "start_date": "2020-08-01T00:00:00",
                    "end_date": "2022-02-28T00:00:00",
                    "current": False,
                    "description": "Full-stack development for various client projects in an agency setting. Gained experience across multiple tech stacks and industries.",
                    "achievements": [
                        "Delivered 8 client projects on time and within budget",
                        "Built e-commerce platform that processed €2M in first year",
                        "Introduced automated testing practices to the team"
                    ],
                    "technologies": ["Python", "Django", "JavaScript", "React", "MySQL"]
                }
            ],
            "education": [
                {
                    "institution": "IT University of Copenhagen",
                    "degree": "Bachelor of Science",
                    "field": "Software Development",
                    "start_date": "2017-09-01T00:00:00",
                    "end_date": "2020-06-30T00:00:00",
                    "gpa": 10.2,
                    "relevant_courses": ["Web Development", "Database Systems", "Software Architecture", "Algorithms"]
                }
            ],
            "certifications": [
                {
                    "name": "AWS Certified Developer - Associate",
                    "issuer": "Amazon Web Services",
                    "date_obtained": "2023-05-15T00:00:00",
                    "expiry_date": "2026-05-15T00:00:00",
                    "credential_id": "AWS-DEV-12345"
                }
            ],
            "last_updated": datetime.now().isoformat()
        }
    },
    {
        "name": "Marcus Andersen - Senior Backend Engineer",
        "full_name": "Marcus Andersen",
        "email": "marcus.andersen@example.com",
        "title": "Senior Backend Engineer",
        "profile_data": {
            "full_name": "Marcus Andersen",
            "email": "marcus.andersen@example.com",
            "phone": "+45 87 65 43 21",
            "location": "Aarhus, Denmark",
            "linkedin_url": "https://linkedin.com/in/marcusandersen",
            "github_url": "https://github.com/marcusandersen",
            "title": "Senior Backend Engineer",
            "years_experience": 8.0,
            "summary": "Senior backend engineer with 8 years of experience designing and building high-performance distributed systems. Expert in Python and Go, with deep knowledge of cloud infrastructure and DevOps practices. Passionate about system design, performance optimization, and building reliable software at scale. Currently focused on event-driven architectures and real-time data processing.",
            "skills": [
                {"name": "Python", "level": "expert", "years": 8, "keywords": ["FastAPI", "asyncio", "Celery"]},
                {"name": "Go", "level": "advanced", "years": 4, "keywords": ["Gin", "gRPC", "Concurrency"]},
                {"name": "PostgreSQL", "level": "expert", "years": 7, "keywords": ["Performance Tuning", "Replication"]},
                {"name": "Redis", "level": "advanced", "years": 5, "keywords": ["Caching", "Pub/Sub", "Streams"]},
                {"name": "Kubernetes", "level": "advanced", "years": 4, "keywords": ["Helm", "Operators", "Service Mesh"]},
                {"name": "AWS", "level": "expert", "years": 6, "keywords": ["EKS", "RDS", "SQS", "Lambda", "DynamoDB"]},
                {"name": "Kafka", "level": "advanced", "years": 3, "keywords": ["Event Streaming", "KSQL"]},
                {"name": "System Design", "level": "expert", "years": 6, "keywords": ["Microservices", "DDD", "CQRS"]},
                {"name": "CI/CD", "level": "advanced", "years": 5, "keywords": ["GitHub Actions", "ArgoCD", "Terraform"]},
                {"name": "Monitoring", "level": "advanced", "years": 5, "keywords": ["Prometheus", "Grafana", "Datadog"]}
            ],
            "experiences": [
                {
                    "company": "Danske Bank",
                    "role": "Senior Backend Engineer",
                    "start_date": "2021-01-01T00:00:00",
                    "end_date": None,
                    "current": True,
                    "description": "Tech lead for core banking platform modernization initiative. Leading a team of 5 engineers building next-generation transaction processing system.",
                    "achievements": [
                        "Designed event-driven architecture handling 1M+ transactions daily",
                        "Reduced system latency by 60% through optimization and caching",
                        "Led successful migration from on-premise to AWS with zero downtime",
                        "Established engineering best practices and code review standards"
                    ],
                    "technologies": ["Python", "Go", "Kafka", "PostgreSQL", "Kubernetes", "AWS"]
                },
                {
                    "company": "Netcompany",
                    "role": "Backend Developer",
                    "start_date": "2018-03-01T00:00:00",
                    "end_date": "2020-12-31T00:00:00",
                    "current": False,
                    "description": "Backend development for enterprise clients in healthcare and public sector. Built scalable APIs and data pipelines.",
                    "achievements": [
                        "Developed national health registry integration serving 5M+ citizens",
                        "Built real-time analytics platform for public transportation",
                        "Promoted from mid-level to senior developer within 2 years"
                    ],
                    "technologies": ["Python", "Java", "PostgreSQL", "RabbitMQ", "Docker"]
                },
                {
                    "company": "Startup Hub Aarhus",
                    "role": "Software Developer",
                    "start_date": "2016-06-01T00:00:00",
                    "end_date": "2018-02-28T00:00:00",
                    "current": False,
                    "description": "Early-stage startup building IoT platform for smart buildings. Full ownership of backend services.",
                    "achievements": [
                        "Built RESTful API serving 10,000+ IoT devices",
                        "Implemented real-time alerting system for building managers",
                        "Reduced cloud costs by 35% through architecture optimization"
                    ],
                    "technologies": ["Python", "Node.js", "MongoDB", "MQTT", "AWS"]
                }
            ],
            "education": [
                {
                    "institution": "Aarhus University",
                    "degree": "Master of Science",
                    "field": "Computer Science",
                    "start_date": "2014-09-01T00:00:00",
                    "end_date": "2016-06-30T00:00:00",
                    "gpa": 11.0,
                    "relevant_courses": ["Distributed Systems", "Advanced Algorithms", "Database Implementation"]
                },
                {
                    "institution": "Aarhus University",
                    "degree": "Bachelor of Science",
                    "field": "Computer Science",
                    "start_date": "2011-09-01T00:00:00",
                    "end_date": "2014-06-30T00:00:00",
                    "gpa": 10.5,
                    "relevant_courses": []
                }
            ],
            "certifications": [
                {
                    "name": "AWS Solutions Architect - Professional",
                    "issuer": "Amazon Web Services",
                    "date_obtained": "2022-08-20T00:00:00",
                    "expiry_date": "2025-08-20T00:00:00",
                    "credential_id": "AWS-SAP-67890"
                },
                {
                    "name": "Certified Kubernetes Administrator",
                    "issuer": "CNCF",
                    "date_obtained": "2023-02-10T00:00:00",
                    "expiry_date": "2026-02-10T00:00:00",
                    "credential_id": "CKA-2023-12345"
                }
            ],
            "last_updated": datetime.now().isoformat()
        }
    },
    {
        "name": "Sofia Martinez - Data Engineer",
        "full_name": "Sofia Martinez",
        "email": "sofia.martinez@example.com",
        "title": "Data Engineer",
        "profile_data": {
            "full_name": "Sofia Martinez",
            "email": "sofia.martinez@example.com",
            "phone": "+45 55 66 77 88",
            "location": "Copenhagen, Denmark",
            "linkedin_url": "https://linkedin.com/in/sofiamartinez",
            "github_url": "https://github.com/sofiamartinez",
            "title": "Data Engineer",
            "years_experience": 5.0,
            "summary": "Data engineer with 5 years of experience building data pipelines and analytics platforms. Transitioning towards machine learning engineering with recent focus on MLOps and model deployment. Strong Python skills combined with cloud infrastructure expertise. Bilingual in Spanish and English, with professional proficiency in Danish.",
            "skills": [
                {"name": "Python", "level": "expert", "years": 5, "keywords": ["Pandas", "PySpark", "Airflow"]},
                {"name": "SQL", "level": "expert", "years": 5, "keywords": ["PostgreSQL", "BigQuery", "Snowflake"]},
                {"name": "Apache Spark", "level": "advanced", "years": 3, "keywords": ["PySpark", "Spark SQL"]},
                {"name": "Airflow", "level": "advanced", "years": 3, "keywords": ["DAGs", "Operators", "Scheduling"]},
                {"name": "AWS", "level": "intermediate", "years": 3, "keywords": ["S3", "Glue", "Athena", "SageMaker"]},
                {"name": "Machine Learning", "level": "intermediate", "years": 2, "keywords": ["scikit-learn", "XGBoost"]},
                {"name": "MLOps", "level": "beginner", "years": 1, "keywords": ["MLflow", "Model Serving"]},
                {"name": "dbt", "level": "intermediate", "years": 2, "keywords": ["Data Modeling", "Testing"]},
                {"name": "Docker", "level": "intermediate", "years": 3, "keywords": ["Containerization"]},
                {"name": "Git", "level": "advanced", "years": 5, "keywords": ["Version Control", "CI/CD"]}
            ],
            "experiences": [
                {
                    "company": "Vestas Wind Systems",
                    "role": "Senior Data Engineer",
                    "start_date": "2022-06-01T00:00:00",
                    "end_date": None,
                    "current": True,
                    "description": "Building data infrastructure for wind turbine analytics. Processing terabytes of sensor data daily to enable predictive maintenance and performance optimization.",
                    "achievements": [
                        "Designed data lake architecture processing 5TB+ daily sensor data",
                        "Built ML feature store enabling data scientists to deploy models 3x faster",
                        "Reduced data pipeline failures by 80% through improved monitoring",
                        "Led initiative to implement data quality framework across organization"
                    ],
                    "technologies": ["Python", "Spark", "Airflow", "AWS", "dbt", "Snowflake"]
                },
                {
                    "company": "Maersk",
                    "role": "Data Engineer",
                    "start_date": "2020-01-01T00:00:00",
                    "end_date": "2022-05-31T00:00:00",
                    "current": False,
                    "description": "Developed ETL pipelines and analytics solutions for global shipping operations. Worked with large-scale logistics data.",
                    "achievements": [
                        "Built real-time container tracking data pipeline",
                        "Automated reporting saving 20 hours per week of manual work",
                        "Migrated legacy data warehouse to cloud-native solution"
                    ],
                    "technologies": ["Python", "SQL", "Azure", "Databricks", "Power BI"]
                },
                {
                    "company": "Analytics Startup (Madrid)",
                    "role": "Junior Data Analyst",
                    "start_date": "2019-02-01T00:00:00",
                    "end_date": "2019-12-31T00:00:00",
                    "current": False,
                    "description": "Data analysis and visualization for marketing analytics platform. First role after completing master's degree.",
                    "achievements": [
                        "Developed customer segmentation model improving campaign ROI by 25%",
                        "Created automated dashboards for 15 enterprise clients"
                    ],
                    "technologies": ["Python", "SQL", "Tableau", "Google Analytics"]
                }
            ],
            "education": [
                {
                    "institution": "Technical University of Denmark",
                    "degree": "Master of Science",
                    "field": "Data Science",
                    "start_date": "2017-09-01T00:00:00",
                    "end_date": "2019-01-31T00:00:00",
                    "gpa": 10.8,
                    "relevant_courses": ["Machine Learning", "Big Data Systems", "Statistical Modeling", "Deep Learning"]
                },
                {
                    "institution": "Universidad Politécnica de Madrid",
                    "degree": "Bachelor of Science",
                    "field": "Computer Engineering",
                    "start_date": "2013-09-01T00:00:00",
                    "end_date": "2017-06-30T00:00:00",
                    "gpa": None,
                    "relevant_courses": []
                }
            ],
            "certifications": [
                {
                    "name": "Google Cloud Professional Data Engineer",
                    "issuer": "Google Cloud",
                    "date_obtained": "2023-09-01T00:00:00",
                    "expiry_date": "2025-09-01T00:00:00",
                    "credential_id": "GCP-DE-54321"
                },
                {
                    "name": "Databricks Certified Data Engineer Associate",
                    "issuer": "Databricks",
                    "date_obtained": "2022-11-15T00:00:00",
                    "expiry_date": None,
                    "credential_id": "DBX-DE-98765"
                }
            ],
            "last_updated": datetime.now().isoformat()
        }
    }
]


async def load_demo_profiles(db: DatabaseService) -> list[int]:
    """
    Load demo profiles into database.
    
    Returns:
        List of created profile IDs.
    """
    created_ids = []
    
    for profile_dict in DEMO_PROFILES:
        try:
            profile_create = ProfileCreate(
                name=profile_dict["name"],
                full_name=profile_dict["full_name"],
                email=profile_dict["email"],
                title=profile_dict["title"],
                profile_data=profile_dict["profile_data"],
                is_active=False,
                is_demo=True,
            )
            
            profile = await db.create_profile(profile_create)
            created_ids.append(profile.id)
            logger.info(f"Created demo profile: {profile.name} (ID: {profile.id})")
            
        except Exception as e:
            logger.warning(f"Failed to create demo profile {profile_dict['name']}: {e}")
    
    # Activate the first demo profile if no active profile exists
    if created_ids:
        active = await db.get_active_profile()
        if active is None:
            await db.activate_profile(created_ids[0])
            logger.info(f"Activated demo profile ID: {created_ids[0]}")
    
    # Mark demo data as loaded
    await db.set_setting("demo_data_loaded", True)
    
    return created_ids


async def ensure_demo_data(db: DatabaseService) -> None:
    """
    Ensure demo data is loaded (idempotent).
    
    Called on application startup.
    """
    settings = await db.get_settings()
    
    if not settings.demo_data_loaded:
        logger.info("Loading demo profiles...")
        await load_demo_profiles(db)
        logger.info("Demo profiles loaded")
    else:
        logger.debug("Demo data already loaded")
```

## P1.3: Add Tests for Database Service

### File: `tests/test_database_service.py`

```python
"""Tests for database service."""

import pytest
import tempfile
from pathlib import Path

from src.services.database import (
    DatabaseService,
    Profile,
    ProfileCreate,
    ProfileUpdate,
    Application,
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationStatus,
)
from src.services.database.exceptions import (
    ProfileNotFoundError,
    ApplicationNotFoundError,
)


@pytest.fixture
async def db_service():
    """Create temporary database service."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        service = DatabaseService(db_path)
        await service.initialize()
        yield service
        await service.close()


# =============================================================================
# PROFILE TESTS
# =============================================================================


class TestProfileCRUD:
    """Profile CRUD tests."""
    
    async def test_create_profile(self, db_service):
        """Test creating a profile."""
        data = ProfileCreate(
            name="Test Profile",
            full_name="Test User",
            email="test@example.com",
            title="Developer",
            profile_data={"skills": ["Python"]},
        )
        
        profile = await db_service.create_profile(data)
        
        assert profile.id is not None
        assert profile.name == "Test Profile"
        assert profile.slug == "test-profile"
        assert profile.full_name == "Test User"
        assert profile.profile_data == {"skills": ["Python"]}
    
    async def test_create_profile_generates_unique_slug(self, db_service):
        """Test slug uniqueness."""
        data1 = ProfileCreate(name="Test", full_name="User 1", profile_data={})
        data2 = ProfileCreate(name="Test", full_name="User 2", profile_data={})
        
        p1 = await db_service.create_profile(data1)
        p2 = await db_service.create_profile(data2)
        
        assert p1.slug == "test"
        assert p2.slug == "test-2"
    
    async def test_get_profile(self, db_service):
        """Test getting profile by ID."""
        data = ProfileCreate(name="Test", full_name="User", profile_data={})
        created = await db_service.create_profile(data)
        
        profile = await db_service.get_profile(created.id)
        
        assert profile.id == created.id
        assert profile.name == "Test"
    
    async def test_get_profile_not_found(self, db_service):
        """Test getting non-existent profile."""
        with pytest.raises(ProfileNotFoundError):
            await db_service.get_profile(999)
    
    async def test_list_profiles(self, db_service):
        """Test listing profiles."""
        await db_service.create_profile(ProfileCreate(name="A", full_name="A", profile_data={}))
        await db_service.create_profile(ProfileCreate(name="B", full_name="B", profile_data={}))
        
        profiles = await db_service.list_profiles()
        
        assert len(profiles) == 2
    
    async def test_update_profile(self, db_service):
        """Test updating a profile."""
        data = ProfileCreate(name="Old Name", full_name="User", profile_data={})
        profile = await db_service.create_profile(data)
        
        updated = await db_service.update_profile(
            profile.id,
            ProfileUpdate(name="New Name", title="Senior Dev")
        )
        
        assert updated.name == "New Name"
        assert updated.slug == "new-name"
        assert updated.title == "Senior Dev"
    
    async def test_delete_profile(self, db_service):
        """Test deleting a profile."""
        data = ProfileCreate(name="Test", full_name="User", profile_data={})
        profile = await db_service.create_profile(data)
        
        await db_service.delete_profile(profile.id)
        
        with pytest.raises(ProfileNotFoundError):
            await db_service.get_profile(profile.id)
    
    async def test_activate_profile(self, db_service):
        """Test activating a profile."""
        p1 = await db_service.create_profile(
            ProfileCreate(name="P1", full_name="U1", profile_data={}, is_active=True)
        )
        p2 = await db_service.create_profile(
            ProfileCreate(name="P2", full_name="U2", profile_data={})
        )
        
        assert p1.is_active is True
        assert p2.is_active is False
        
        await db_service.activate_profile(p2.id)
        
        p1_refreshed = await db_service.get_profile(p1.id)
        p2_refreshed = await db_service.get_profile(p2.id)
        
        assert p1_refreshed.is_active is False
        assert p2_refreshed.is_active is True


# =============================================================================
# APPLICATION TESTS
# =============================================================================


class TestApplicationCRUD:
    """Application CRUD tests."""
    
    async def test_create_application(self, db_service):
        """Test creating an application."""
        profile = await db_service.create_profile(
            ProfileCreate(name="Test", full_name="User", profile_data={})
        )
        
        data = ApplicationCreate(
            job_id="abc12345",
            profile_id=profile.id,
            job_text="Software Engineer at Company...",
        )
        
        app = await db_service.create_application(data)
        
        assert app.job_id == "abc12345"
        assert app.profile_id == profile.id
        assert app.status == ApplicationStatus.PENDING
    
    async def test_get_application_by_job_id(self, db_service):
        """Test getting application by job_id."""
        profile = await db_service.create_profile(
            ProfileCreate(name="Test", full_name="User", profile_data={})
        )
        
        await db_service.create_application(
            ApplicationCreate(job_id="xyz789", profile_id=profile.id, job_text="Job...")
        )
        
        app = await db_service.get_application_by_job_id("xyz789")
        
        assert app is not None
        assert app.job_id == "xyz789"
    
    async def test_update_application(self, db_service):
        """Test updating an application."""
        profile = await db_service.create_profile(
            ProfileCreate(name="Test", full_name="User", profile_data={})
        )
        
        await db_service.create_application(
            ApplicationCreate(job_id="upd123", profile_id=profile.id, job_text="Job...")
        )
        
        updated = await db_service.update_application(
            "upd123",
            ApplicationUpdate(
                status=ApplicationStatus.COMPLETED,
                compatibility_score=85,
                job_title="Software Engineer",
            )
        )
        
        assert updated.status == ApplicationStatus.COMPLETED
        assert updated.compatibility_score == 85
        assert updated.job_title == "Software Engineer"
    
    async def test_list_applications_with_filter(self, db_service):
        """Test listing applications with filters."""
        profile = await db_service.create_profile(
            ProfileCreate(name="Test", full_name="User", profile_data={})
        )
        
        await db_service.create_application(
            ApplicationCreate(job_id="a1", profile_id=profile.id, job_text="Job 1")
        )
        await db_service.create_application(
            ApplicationCreate(job_id="a2", profile_id=profile.id, job_text="Job 2")
        )
        
        # Update one to completed
        await db_service.update_application("a1", ApplicationUpdate(status=ApplicationStatus.COMPLETED))
        
        # Filter by status
        completed, total = await db_service.list_applications(status=ApplicationStatus.COMPLETED)
        
        assert len(completed) == 1
        assert completed[0].job_id == "a1"
    
    async def test_get_profile_stats(self, db_service):
        """Test getting profile statistics."""
        profile = await db_service.create_profile(
            ProfileCreate(name="Test", full_name="User", profile_data={})
        )
        
        await db_service.create_application(
            ApplicationCreate(job_id="s1", profile_id=profile.id, job_text="Job")
        )
        await db_service.create_application(
            ApplicationCreate(job_id="s2", profile_id=profile.id, job_text="Job")
        )
        
        await db_service.update_application("s1", ApplicationUpdate(
            status=ApplicationStatus.COMPLETED, compatibility_score=80
        ))
        await db_service.update_application("s2", ApplicationUpdate(
            status=ApplicationStatus.COMPLETED, compatibility_score=90
        ))
        
        stats = await db_service.get_profile_stats(profile.id)
        
        assert stats["total_applications"] == 2
        assert stats["completed_applications"] == 2
        assert stats["avg_compatibility_score"] == 85.0
```

## P1 Verification

```bash
# Run database tests
pytest tests/test_database_service.py -v

# Verify imports work
python -c "from src.services.database import get_database_service, Profile, Application; print('OK')"

# Test database creation
python -c "
import asyncio
from src.services.database import get_database_service
async def test():
    db = await get_database_service()
    print(f'DB initialized: {db._db_path}')
asyncio.run(test())
"
```

## P1 Commit

```bash
git add -A
git commit -m "feat(database): add SQLite persistence layer

- Create DatabaseService with profile and application CRUD
- Add Pydantic models for type-safe operations
- Implement schema migrations framework
- Add demo profile data (Emma, Marcus, Sofia)
- Include comprehensive tests for database operations

Phase P1 of persistence implementation."
```

---

# Phase P2: Profile & Application Persistence

**Estimated Time:** 2-3 hours  
**Goal:** Integrate database with existing modules and API

## P2.1: Update Application Startup

### File: `src/web/main.py`

Add database initialization to lifespan:

```python
# Add import
from src.services.database import get_database_service
from src.services.database.demo_data import ensure_demo_data

# In lifespan function, add after existing initializations:
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ... existing startup code ...
    
    # Initialize database and load demo data
    try:
        db = await get_database_service()
        await ensure_demo_data(db)
        logger.info("Database initialized with demo data")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    # ... rest of startup ...
```

## P2.2: Create Profiles API Routes

### File: `src/web/routes/api/v1/profiles.py`

```python
"""
Multi-Profile API Routes

CRUD operations for user profiles.

Endpoints:
    GET /api/v1/profiles - List all profiles
    POST /api/v1/profiles - Create new profile
    GET /api/v1/profiles/{slug} - Get profile by slug
    PUT /api/v1/profiles/{slug} - Update profile
    DELETE /api/v1/profiles/{slug} - Delete profile
    POST /api/v1/profiles/{slug}/activate - Set as active profile
    GET /api/v1/profiles/active - Get currently active profile
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.services.database import (
    DatabaseService,
    Profile,
    ProfileCreate,
    ProfileUpdate,
    get_database_service,
)
from src.services.database.exceptions import ProfileNotFoundError, ProfileExistsError
from src.modules.collector import get_collector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profiles", tags=["profiles"])


# =============================================================================
# SCHEMAS
# =============================================================================


class ProfileCreateRequest(BaseModel):
    """Request to create a profile."""
    name: str = Field(..., min_length=1, max_length=200)
    full_name: str = Field(..., min_length=1, max_length=200)
    email: str | None = None
    title: str | None = None
    profile_data: dict[str, Any]
    set_active: bool = False


class ProfileUpdateRequest(BaseModel):
    """Request to update a profile."""
    name: str | None = None
    full_name: str | None = None
    email: str | None = None
    title: str | None = None
    profile_data: dict[str, Any] | None = None


class ProfileResponse(BaseModel):
    """Profile response with stats."""
    id: int
    name: str
    slug: str
    full_name: str
    email: str | None
    title: str | None
    is_active: bool
    is_indexed: bool
    is_demo: bool
    created_at: str
    updated_at: str
    stats: dict[str, Any] | None = None


class ProfileListResponse(BaseModel):
    """List of profiles."""
    profiles: list[ProfileResponse]
    total: int
    active_profile_slug: str | None


# =============================================================================
# DEPENDENCIES
# =============================================================================


async def get_db() -> DatabaseService:
    """Get database service."""
    return await get_database_service()


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("", response_model=ProfileListResponse)
async def list_profiles(
    include_demo: bool = True,
    db: DatabaseService = Depends(get_db),
) -> ProfileListResponse:
    """List all profiles."""
    profiles = await db.list_profiles(include_demo=include_demo)
    
    # Get active profile
    active = await db.get_active_profile()
    active_slug = active.slug if active else None
    
    # Build response with stats
    profile_responses = []
    for p in profiles:
        stats = await db.get_profile_stats(p.id)
        profile_responses.append(ProfileResponse(
            id=p.id,
            name=p.name,
            slug=p.slug,
            full_name=p.full_name,
            email=p.email,
            title=p.title,
            is_active=p.is_active,
            is_indexed=p.is_indexed,
            is_demo=p.is_demo,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
            stats=stats,
        ))
    
    return ProfileListResponse(
        profiles=profile_responses,
        total=len(profiles),
        active_profile_slug=active_slug,
    )


@router.post("", response_model=ProfileResponse)
async def create_profile(
    request: ProfileCreateRequest,
    db: DatabaseService = Depends(get_db),
) -> ProfileResponse:
    """Create a new profile."""
    try:
        profile = await db.create_profile(ProfileCreate(
            name=request.name,
            full_name=request.full_name,
            email=request.email,
            title=request.title,
            profile_data=request.profile_data,
            is_active=request.set_active,
            is_demo=False,
        ))
        
        # If set as active, re-index
        if request.set_active:
            await _reindex_profile(profile, db)
        
        stats = await db.get_profile_stats(profile.id)
        
        return ProfileResponse(
            id=profile.id,
            name=profile.name,
            slug=profile.slug,
            full_name=profile.full_name,
            email=profile.email,
            title=profile.title,
            is_active=profile.is_active,
            is_indexed=profile.is_indexed,
            is_demo=profile.is_demo,
            created_at=profile.created_at.isoformat(),
            updated_at=profile.updated_at.isoformat(),
            stats=stats,
        )
        
    except ProfileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/active", response_model=ProfileResponse | None)
async def get_active_profile(db: DatabaseService = Depends(get_db)):
    """Get the currently active profile."""
    profile = await db.get_active_profile()
    if profile is None:
        return None
    
    stats = await db.get_profile_stats(profile.id)
    
    return ProfileResponse(
        id=profile.id,
        name=profile.name,
        slug=profile.slug,
        full_name=profile.full_name,
        email=profile.email,
        title=profile.title,
        is_active=profile.is_active,
        is_indexed=profile.is_indexed,
        is_demo=profile.is_demo,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat(),
        stats=stats,
    )


@router.get("/{slug}", response_model=ProfileResponse)
async def get_profile(slug: str, db: DatabaseService = Depends(get_db)) -> ProfileResponse:
    """Get profile by slug."""
    try:
        profile = await db.get_profile_by_slug(slug)
        stats = await db.get_profile_stats(profile.id)
        
        return ProfileResponse(
            id=profile.id,
            name=profile.name,
            slug=profile.slug,
            full_name=profile.full_name,
            email=profile.email,
            title=profile.title,
            is_active=profile.is_active,
            is_indexed=profile.is_indexed,
            is_demo=profile.is_demo,
            created_at=profile.created_at.isoformat(),
            updated_at=profile.updated_at.isoformat(),
            stats=stats,
        )
        
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found")


@router.get("/{slug}/data")
async def get_profile_data(slug: str, db: DatabaseService = Depends(get_db)) -> dict:
    """Get full profile data (for editing)."""
    try:
        profile = await db.get_profile_by_slug(slug)
        return profile.profile_data
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found")


@router.put("/{slug}", response_model=ProfileResponse)
async def update_profile(
    slug: str,
    request: ProfileUpdateRequest,
    db: DatabaseService = Depends(get_db),
) -> ProfileResponse:
    """Update a profile."""
    try:
        profile = await db.get_profile_by_slug(slug)
        
        updated = await db.update_profile(profile.id, ProfileUpdate(
            name=request.name,
            full_name=request.full_name,
            email=request.email,
            title=request.title,
            profile_data=request.profile_data,
        ))
        
        # If active profile was updated, re-index
        if updated.is_active and request.profile_data is not None:
            await _reindex_profile(updated, db)
        
        stats = await db.get_profile_stats(updated.id)
        
        return ProfileResponse(
            id=updated.id,
            name=updated.name,
            slug=updated.slug,
            full_name=updated.full_name,
            email=updated.email,
            title=updated.title,
            is_active=updated.is_active,
            is_indexed=updated.is_indexed,
            is_demo=updated.is_demo,
            created_at=updated.created_at.isoformat(),
            updated_at=updated.updated_at.isoformat(),
            stats=stats,
        )
        
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found")


@router.delete("/{slug}")
async def delete_profile(slug: str, db: DatabaseService = Depends(get_db)) -> dict:
    """Delete a profile."""
    try:
        profile = await db.get_profile_by_slug(slug)
        
        if profile.is_active:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete active profile. Activate another profile first."
            )
        
        await db.delete_profile(profile.id)
        return {"status": "deleted", "slug": slug}
        
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found")


@router.post("/{slug}/activate", response_model=ProfileResponse)
async def activate_profile(slug: str, db: DatabaseService = Depends(get_db)) -> ProfileResponse:
    """Set a profile as active and re-index for matching."""
    try:
        profile = await db.get_profile_by_slug(slug)
        
        # Activate in database
        activated = await db.activate_profile(profile.id)
        
        # Re-index in vector store
        await _reindex_profile(activated, db)
        
        stats = await db.get_profile_stats(activated.id)
        
        return ProfileResponse(
            id=activated.id,
            name=activated.name,
            slug=activated.slug,
            full_name=activated.full_name,
            email=activated.email,
            title=activated.title,
            is_active=activated.is_active,
            is_indexed=activated.is_indexed,
            is_demo=activated.is_demo,
            created_at=activated.created_at.isoformat(),
            updated_at=activated.updated_at.isoformat(),
            stats=stats,
        )
        
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{slug}' not found")


async def _reindex_profile(profile: Profile, db: DatabaseService) -> None:
    """Re-index profile in vector store."""
    try:
        from src.modules.collector.models import UserProfile
        
        collector = await get_collector()
        
        # Parse profile data to UserProfile
        user_profile = UserProfile(**profile.profile_data)
        
        # Set in collector (this clears and re-indexes)
        collector._profile = user_profile
        collector._profile_loaded = True
        
        # Clear and re-index
        await collector.clear_index()
        chunk_count = await collector.index_profile()
        
        # Mark as indexed in database
        await db.set_profile_indexed(profile.id, True)
        
        logger.info(f"Re-indexed profile {profile.slug}: {chunk_count} chunks")
        
    except Exception as e:
        logger.error(f"Failed to re-index profile {profile.slug}: {e}")
        await db.set_profile_indexed(profile.id, False)
        raise
```

## P2.3: Update V1 Router to Include Profiles

### File: `src/web/routes/api/v1/__init__.py`

Add profiles router:

```python
# Add import
from src.web.routes.api.v1.profiles import router as profiles_router

# Add to router includes
router.include_router(profiles_router)
```

## P2.4: Update Jobs Route to Use Database

### File: `src/web/routes/api/v1/jobs.py`

Replace in-memory JobStore with database:

```python
# Add imports
from src.services.database import (
    get_database_service,
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationStatus,
)

# Replace the execute_pipeline function to save to database
async def _execute_pipeline(
    orchestrator: PipelineOrchestrator,
    job_id: str,
    job_text: str,
    source: str,
) -> None:
    """Execute pipeline and save results to database."""
    from datetime import datetime
    
    db = await get_database_service()
    
    try:
        # Get active profile
        active_profile = await db.get_active_profile()
        if active_profile is None:
            raise ValueError("No active profile")
        
        # Create application record
        await db.create_application(ApplicationCreate(
            job_id=job_id,
            profile_id=active_profile.id,
            job_text=job_text,
        ))
        
        # Mark as running
        await db.update_application(job_id, ApplicationUpdate(
            status=ApplicationStatus.RUNNING,
            started_at=datetime.now(),
        ))
        
        # Execute pipeline
        input_data = PipelineInput(raw_job_text=job_text, source=source)
        result = await asyncio.wait_for(
            orchestrator.execute(input_data),
            timeout=PIPELINE_TIMEOUT_SECONDS,
        )
        
        # Update with results
        await db.update_application(job_id, ApplicationUpdate(
            status=ApplicationStatus.COMPLETED if result.status.value == "completed" else ApplicationStatus.FAILED,
            job_title=result.job_title,
            company_name=result.company_name,
            compatibility_score=result.compatibility_score,
            cv_path=result.cv_path,
            cover_letter_path=result.cover_letter_path,
            analysis_data=result.analysis.model_dump() if hasattr(result, 'analysis') and result.analysis else None,
            pipeline_data={
                "steps": [{"step": s.step.value, "status": s.status.value, "duration_ms": s.duration_ms} for s in result.steps],
                "total_duration_ms": result.total_duration_ms,
            },
            completed_at=datetime.now(),
            error_message=result.error,
        ))
        
        logger.info(f"Pipeline completed for job {job_id}")
        
    except TimeoutError:
        await db.update_application(job_id, ApplicationUpdate(
            status=ApplicationStatus.FAILED,
            error_message=f"Pipeline timed out after {PIPELINE_TIMEOUT_SECONDS} seconds",
            completed_at=datetime.now(),
        ))
        logger.error(f"Pipeline timed out for job {job_id}")
        
    except Exception as e:
        await db.update_application(job_id, ApplicationUpdate(
            status=ApplicationStatus.FAILED,
            error_message=str(e),
            completed_at=datetime.now(),
        ))
        logger.error(f"Pipeline failed for job {job_id}: {e}")


# Update the apply endpoint
@router.post("/apply", response_model=ApplyResponse)
async def apply(
    request: ApplyRequest,
    background_tasks: BackgroundTasks,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> ApplyResponse:
    """Start a new job application pipeline."""
    job_id = str(uuid.uuid4())[:8]
    
    # Verify active profile exists
    db = await get_database_service()
    active_profile = await db.get_active_profile()
    if active_profile is None:
        raise HTTPException(status_code=400, detail="No active profile. Please activate a profile first.")
    
    logger.info(f"Apply request: job_id={job_id}, profile={active_profile.slug}")
    
    background_tasks.add_task(
        _execute_pipeline,
        orchestrator,
        job_id,
        request.job_text,
        request.source,
    )
    
    return ApplyResponse(job_id=job_id, status="running")


# Update get_status to use database
@router.get("/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str) -> StatusResponse:
    """Get status of a specific job."""
    db = await get_database_service()
    app = await db.get_application_by_job_id(job_id)
    
    if app is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Convert to StatusResponse
    steps = []
    if app.pipeline_data and "steps" in app.pipeline_data:
        steps = [StepInfo(**s) for s in app.pipeline_data["steps"]]
    
    return StatusResponse(
        job_id=app.job_id,
        pipeline_id=app.job_id,
        status=app.status.value,
        current_step=None,
        job_title=app.job_title,
        company_name=app.company_name,
        compatibility_score=app.compatibility_score,
        cv_path=app.cv_path,
        cover_letter_path=app.cover_letter_path,
        steps=steps,
        error=app.error_message,
        started_at=app.started_at,
        completed_at=app.completed_at,
        total_duration_ms=app.pipeline_data.get("total_duration_ms", 0) if app.pipeline_data else 0,
    )


# Update list_jobs to use database
@router.get("", response_model=JobListResponse)
async def list_jobs(
    skip: int = 0,
    limit: int = 20,
    profile_slug: str | None = None,
) -> JobListResponse:
    """Get paginated list of job applications."""
    db = await get_database_service()
    
    profile_id = None
    if profile_slug:
        try:
            profile = await db.get_profile_by_slug(profile_slug)
            profile_id = profile.id
        except:
            pass
    
    applications, total = await db.list_applications(
        profile_id=profile_id,
        limit=limit,
        offset=skip,
    )
    
    summaries = [
        JobSummary(
            job_id=app.job_id,
            job_title=app.job_title,
            company_name=app.company_name,
            status=app.status.value,
            compatibility_score=app.compatibility_score,
            submitted_at=app.created_at,
            completed_at=app.completed_at,
        )
        for app in applications
    ]
    
    return JobListResponse(jobs=summaries, total=total, skip=skip, limit=limit)
```

## P2.5: Update Collector to Load from Database

### File: `src/modules/collector/collector.py`

Add method to load profile from database:

```python
async def load_profile_from_db(self) -> None:
    """
    Load the active profile from database.
    
    Called on startup to initialize with active profile.
    """
    from src.services.database import get_database_service
    
    db = await get_database_service()
    active = await db.get_active_profile()
    
    if active is None:
        logger.warning("No active profile in database")
        return
    
    # Parse profile data
    self._profile = UserProfile(**active.profile_data)
    self._profile_loaded = True
    self._profile_hash = str(active.id)
    
    logger.info(f"Loaded profile from database: {active.name}")
```

## P2.6: Configure Persistent Output Directory

### File: `src/services/pipeline/pipeline.py`

Ensure PDFs are saved to persistent location:

```python
# At the top, define output directory
from pathlib import Path

OUTPUT_DIR = Path("data/outputs")

# In execute method, ensure directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Update formatter call to use this directory
formatted = await self._formatter.format_documents(
    cv_content=created.cv,
    cover_letter=created.cover_letter,
    output_dir=OUTPUT_DIR,
    filename_prefix=f"{pipeline_id}",
)
```

## P2 Verification

```bash
# Run all tests
pytest tests/ -v --tb=short

# Test profile creation via API
curl -X POST http://localhost:8000/api/v1/profiles \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Profile","full_name":"Test User","profile_data":{"skills":[]}}'

# List profiles
curl http://localhost:8000/api/v1/profiles | python -m json.tool

# Get active profile
curl http://localhost:8000/api/v1/profiles/active | python -m json.tool

# Verify database file exists
ls -la data/scout.db

# Verify outputs directory
ls -la data/outputs/
```

## P2 Commit

```bash
git add -A
git commit -m "feat(persistence): integrate database with API and modules

- Add profiles API endpoints (CRUD, activate, list)
- Update jobs API to persist applications in database
- Configure persistent PDF output directory
- Connect Collector to load profile from database
- Integrate demo data loading on startup

Phase P2 of persistence implementation."
```

---

# Phase P3: UI Consolidation

**Estimated Time:** 2-3 hours  
**Goal:** Unified, coherent web interface

## P3.1: Update Template Placeholders

### File: `src/web/templates/profile_edit.html`

Replace "Your Name" with "Test User" in all templates and placeholders:

```javascript
// In templates object, change all instances of:
name: "Your Name"
// To:
name: "Test User"

// Also update the placeholder text in yaml-editor:
placeholder="name: &quot;Test User&quot;
email: &quot;test.user@example.com&quot;
...
```

## P3.2: Simplify Profile Templates

Keep only `profile_edit.html` for editing, update `profiles_list.html` for listing.

### Delete redundant templates:

```bash
rm src/web/templates/profile.html
rm src/web/templates/profile_editor.html
rm src/web/templates/profile_detail.html
```

### Update `profiles_list.html` to show profiles with stats and actions

The template should:
- List all profiles with cards
- Show active profile indicator
- Display stats (applications, avg score)
- Provide activate/edit/delete actions
- Link to create new profile

## P3.3: Update Navbar Profile Switcher

### File: `src/web/templates/partials/navbar.html`

Update dropdown links:

```html
<div class="profile-dropdown-footer">
    <a href="/profiles" class="profile-dropdown-link">Manage Profiles</a>
    <a href="/profiles/new" class="profile-dropdown-link">+ Create Profile</a>
</div>
```

## P3.4: Update common.js Profile Functions

### File: `src/web/static/js/common.js`

Update to use new API endpoints:

```javascript
async function loadProfilesList() {
    try {
        const response = await fetch('/api/v1/profiles');
        if (response.ok) {
            const data = await response.json();
            window.Scout.profilesList = data.profiles;
            window.Scout.activeProfileSlug = data.active_profile_slug;
            updateNavbarProfileSwitcher();
        }
    } catch (error) {
        console.error('Error loading profiles:', error);
    }
}

async function switchToProfile(slug) {
    try {
        const response = await fetch(`/api/v1/profiles/${slug}/activate`, {
            method: 'POST'
        });

        if (!response.ok) throw new Error('Failed to switch profile');

        const profile = await response.json();
        window.Scout.activeProfileSlug = profile.slug;
        updateNavbarProfileSwitcher();

        showToast('success', 'Profile Activated', `Now using: ${profile.name}`);
        
        // Reload page to reflect changes
        setTimeout(() => location.reload(), 1000);

    } catch (error) {
        console.error('Error switching profile:', error);
        showToast('error', 'Error', 'Failed to switch profile');
    }
}
```

## P3.5: Update Page Routes

### File: `src/web/routes/pages.py`

Simplify routes:

```python
@router.get("/profiles", response_class=HTMLResponse)
async def profiles_list(request: Request) -> HTMLResponse:
    """Profile management page."""
    return templates.TemplateResponse(request=request, name="profiles_list.html")


@router.get("/profiles/new", response_class=HTMLResponse)
async def profile_create(request: Request) -> HTMLResponse:
    """Create new profile page."""
    return templates.TemplateResponse(request=request, name="profile_edit.html")


@router.get("/profiles/{slug}/edit", response_class=HTMLResponse)
async def profile_edit(request: Request, slug: str) -> HTMLResponse:
    """Edit profile page."""
    return templates.TemplateResponse(request=request, name="profile_edit.html")


# Remove redundant routes:
# - /profile/create (use /profiles/new)
# - /profile/edit (use /profiles/{slug}/edit)
```

## P3.6: Update Applications Page

### File: `src/web/templates/applications.html`

Update to:
- Show which profile generated each application
- Display persistent application history
- Add filtering by profile
- Show application details in modal/expanded view

## P3.7: Update Dashboard

### File: `src/web/templates/index.html`

Update dashboard to:
- Show active profile summary
- Display recent applications
- Show quick stats
- Provide quick actions (analyze job, manage profiles)

## P3 Verification

```bash
# Start server
uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000

# Test pages load
curl -s http://localhost:8000/ | head -20
curl -s http://localhost:8000/profiles | head -20
curl -s http://localhost:8000/profiles/new | head -20
curl -s http://localhost:8000/applications | head -20

# Verify profile switching works in browser
# Navigate to http://192.168.1.21:8000/profiles
# Click "Activate" on a demo profile
# Verify navbar updates
```

## P3 Commit

```bash
git add -A
git commit -m "feat(ui): consolidate web interface

- Remove redundant profile templates
- Update navbar profile switcher
- Simplify page routes
- Update dashboard with profile info
- Add profile filtering to applications
- Change placeholder 'Your Name' to 'Test User'

Phase P3 of persistence implementation."
```

---

# Final Verification

After all three phases:

```bash
cd /home/cally/projects/scout-code
source venv/bin/activate

# 1. Run full test suite
pytest tests/ -v --tb=short
# Expected: All tests passing

# 2. Verify database
sqlite3 data/scout.db "SELECT name, is_active FROM profiles;"
# Should show 3 demo profiles

# 3. Test full flow
uvicorn src.web.main:app --host 0.0.0.0 --port 8000 &
sleep 5

# Check profiles API
curl http://localhost:8000/api/v1/profiles | python -m json.tool

# Check active profile
curl http://localhost:8000/api/v1/profiles/active | python -m json.tool

# Submit a test job
curl -X POST http://localhost:8000/api/v1/jobs/apply \
  -H "Content-Type: application/json" \
  -d '{"job_text":"Software Engineer position at Tech Company. Requirements: Python, JavaScript, 3+ years experience. We are looking for a skilled developer to join our team..."}'

# Check job status
curl http://localhost:8000/api/v1/jobs | python -m json.tool

pkill -f uvicorn

# 4. Verify persistence after restart
uvicorn src.web.main:app --host 0.0.0.0 --port 8000 &
sleep 5
curl http://localhost:8000/api/v1/jobs | python -m json.tool
# Should still show the job from before
pkill -f uvicorn

# 5. Check git status
git log --oneline -10
```

---

# Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| **P1: Data Layer** | 2-3 hours | SQLite service, models, demo data |
| **P2: Integration** | 2-3 hours | Profiles API, jobs persistence, re-indexing |
| **P3: UI Consolidation** | 2-3 hours | Unified pages, profile switcher, demo profiles |

## Database Tables

- `settings` - Application configuration
- `profiles` - User profiles with JSON data
- `applications` - Job applications with results

## API Endpoints Added

```
GET    /api/v1/profiles           - List profiles
POST   /api/v1/profiles           - Create profile
GET    /api/v1/profiles/active    - Get active profile
GET    /api/v1/profiles/{slug}    - Get profile
PUT    /api/v1/profiles/{slug}    - Update profile
DELETE /api/v1/profiles/{slug}    - Delete profile
POST   /api/v1/profiles/{slug}/activate - Activate profile
GET    /api/v1/profiles/{slug}/data - Get profile data for editing
```

## Files Created

```
src/services/database/__init__.py
src/services/database/models.py
src/services/database/service.py
src/services/database/migrations.py
src/services/database/exceptions.py
src/services/database/demo_data.py
src/web/routes/api/v1/profiles.py
tests/test_database_service.py
data/scout.db (created at runtime)
data/outputs/ (created at runtime)
```

## Files Deleted

```
src/web/templates/profile.html
src/web/templates/profile_editor.html
src/web/templates/profile_detail.html
```

---

## Environment

- **SSH:** `ssh cally@192.168.1.21`
- **Project:** `/home/cally/projects/scout-code`
- **Venv:** `source venv/bin/activate`
- **Sudo:** Available for system operations
- **Database:** `data/scout.db` (SQLite)
- **Vector Store:** `data/chroma/` (ChromaDB - unchanged)
