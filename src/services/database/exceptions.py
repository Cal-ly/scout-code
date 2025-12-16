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
