"""Database migrations and schema setup."""

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
