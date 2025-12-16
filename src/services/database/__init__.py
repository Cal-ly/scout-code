"""Database service - SQLite persistence for users, profiles, and applications.

Usage:
    from src.services.database import get_database_service, Profile, Application

    db = await get_database_service()
    profiles = await db.list_profiles()
    await db.create_profile(profile_data)
"""

from .completeness import calculate_completeness
from .exceptions import (
    ApplicationNotFoundError,
    DatabaseError,
    MigrationError,
    NoActiveProfileError,
    ProfileExistsError,
    ProfileNotFoundError,
    ProfileSlugExistsError,
    UserNotFoundError,
)
from .models import (
    # Application models
    Application,
    ApplicationBase,
    ApplicationCreate,
    ApplicationStatus,
    ApplicationUpdate,
    # Certification models
    Certification,
    CertificationBase,
    CertificationCreate,
    # Completeness models
    CompletenessSection,
    # Education models
    Education,
    EducationBase,
    EducationCreate,
    # Experience models
    Experience,
    ExperienceBase,
    ExperienceCreate,
    # Language models
    Language,
    LanguageBase,
    LanguageCreate,
    LanguageProficiency,
    # Profile models
    Profile,
    ProfileBase,
    ProfileCompleteness,
    ProfileCreate,
    ProfileSummary,
    ProfileUpdate,
    # Settings
    Settings,
    # Skill models
    Skill,
    SkillBase,
    SkillCreate,
    SkillLevel,
    # User models
    User,
    UserBase,
    UserCreate,
)
from .schemas import SCHEMA_SQL, SCHEMA_VERSION, get_drop_tables_sql
from .service import (
    DatabaseService,
    get_database_service,
    reset_database_service,
)

__all__ = [
    # Service
    "DatabaseService",
    "get_database_service",
    "reset_database_service",
    # Schema
    "SCHEMA_SQL",
    "SCHEMA_VERSION",
    "get_drop_tables_sql",
    # Enums
    "SkillLevel",
    "LanguageProficiency",
    "ApplicationStatus",
    # User models
    "User",
    "UserBase",
    "UserCreate",
    # Skill models
    "Skill",
    "SkillBase",
    "SkillCreate",
    # Experience models
    "Experience",
    "ExperienceBase",
    "ExperienceCreate",
    # Education models
    "Education",
    "EducationBase",
    "EducationCreate",
    # Certification models
    "Certification",
    "CertificationBase",
    "CertificationCreate",
    # Language models
    "Language",
    "LanguageBase",
    "LanguageCreate",
    # Profile models
    "Profile",
    "ProfileBase",
    "ProfileCreate",
    "ProfileUpdate",
    "ProfileSummary",
    # Completeness
    "ProfileCompleteness",
    "CompletenessSection",
    "calculate_completeness",
    # Application models
    "Application",
    "ApplicationBase",
    "ApplicationCreate",
    "ApplicationUpdate",
    # Settings
    "Settings",
    # Exceptions
    "DatabaseError",
    "MigrationError",
    "UserNotFoundError",
    "ProfileNotFoundError",
    "ProfileSlugExistsError",
    "ProfileExistsError",
    "ApplicationNotFoundError",
    "NoActiveProfileError",
]
