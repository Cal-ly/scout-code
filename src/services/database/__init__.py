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
