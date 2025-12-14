"""
Profile Service Package

Manages user profiles with database storage, file backup, and vector indexing.

Usage:
    from src.services.profile import get_profile_service

    profile_service = await get_profile_service()
    status = await profile_service.get_status()
"""

from src.services.profile.exceptions import (
    ProfileDatabaseError,
    ProfileError,
    ProfileIndexingError,
    ProfileNotFoundError,
    ProfileValidationError,
)
from src.services.profile.models import (
    ProfileChunk,
    ProfileCreateRequest,
    ProfileCreateResponse,
    ProfileData,
    ProfileHealth,
    ProfileIndexRequest,
    ProfileIndexResponse,
    ProfileStatus,
)
from src.services.profile.service import (
    ProfileService,
    get_profile_service,
    reset_profile_service,
    shutdown_profile_service,
)

__all__ = [
    # Service
    "ProfileService",
    "get_profile_service",
    "shutdown_profile_service",
    "reset_profile_service",
    # Models
    "ProfileStatus",
    "ProfileCreateRequest",
    "ProfileCreateResponse",
    "ProfileIndexRequest",
    "ProfileIndexResponse",
    "ProfileData",
    "ProfileChunk",
    "ProfileHealth",
    # Exceptions
    "ProfileError",
    "ProfileNotFoundError",
    "ProfileValidationError",
    "ProfileIndexingError",
    "ProfileDatabaseError",
]
