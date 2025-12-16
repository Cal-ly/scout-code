"""Database service exceptions."""


class DatabaseError(Exception):
    """Base exception for database operations."""

    pass


class MigrationError(DatabaseError):
    """Database migration failed."""

    pass


class UserNotFoundError(DatabaseError):
    """User not found in database."""

    def __init__(self, identifier: str | int):
        self.identifier = identifier
        super().__init__(f"User not found: {identifier}")


class ProfileNotFoundError(DatabaseError):
    """Profile not found in database."""

    def __init__(self, identifier: str | int):
        self.identifier = identifier
        super().__init__(f"Profile not found: {identifier}")


class ProfileSlugExistsError(DatabaseError):
    """Profile with this slug already exists."""

    def __init__(self, slug: str):
        self.slug = slug
        super().__init__(f"Profile with slug already exists: {slug}")


# Keep for backward compatibility
ProfileExistsError = ProfileSlugExistsError


class ApplicationNotFoundError(DatabaseError):
    """Application not found in database."""

    def __init__(self, identifier: str | int):
        self.identifier = identifier
        super().__init__(f"Application not found: {identifier}")


class NoActiveProfileError(DatabaseError):
    """No active profile set for user."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"No active profile for user: {user_id}")
