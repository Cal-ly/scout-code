"""Common API schemas used across multiple domains."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    message: str
    detail: str | None = None


class SuccessResponse(BaseModel):
    """Standard success response."""

    status: str = "success"
    message: str | None = None


class PaginationParams(BaseModel):
    """Pagination parameters."""

    skip: int = 0
    limit: int = 20


class PaginatedResponse(BaseModel):
    """Base paginated response."""

    total: int
    skip: int
    limit: int
