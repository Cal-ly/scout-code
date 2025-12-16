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
            "UPDATE settings SET value = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE key = 'schema_version'",
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
