"""
Profile Service Exceptions

Custom exceptions for the Profile Service.
"""


class ProfileError(Exception):
    """Base exception for profile operations."""

    pass


class ProfileNotFoundError(ProfileError):
    """Raised when profile is not found."""

    pass


class ProfileValidationError(ProfileError):
    """Raised when profile validation fails."""

    pass


class ProfileIndexingError(ProfileError):
    """Raised when profile indexing fails."""

    pass


class ProfileDatabaseError(ProfileError):
    """Raised when database operations fail."""

    pass
