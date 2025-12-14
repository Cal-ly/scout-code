"""
Profile Service Models

Pydantic models for profile data and API responses.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ProfileStatus(BaseModel):
    """Profile status response."""

    exists: bool
    is_indexed: bool
    profile_id: int | None = None
    chunk_count: int = 0
    character_count: int = 0
    last_updated: datetime | None = None


class ProfileCreateRequest(BaseModel):
    """Request to create or update a profile."""

    profile_text: str = Field(
        ...,
        min_length=100,
        max_length=10000,
        description="Profile text (100-10,000 characters)",
    )

    @field_validator("profile_text")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace."""
        return v.strip()


class ProfileCreateResponse(BaseModel):
    """Response after creating/updating a profile."""

    profile_id: int
    status: Literal["created", "updated"]
    is_indexed: bool
    chunk_count: int


class ProfileIndexRequest(BaseModel):
    """Request to index a profile."""

    profile_id: int


class ProfileIndexResponse(BaseModel):
    """Response after indexing a profile."""

    success: bool
    chunks_created: int
    profile_id: int


class ProfileData(BaseModel):
    """Full profile data response."""

    profile_id: int
    profile_text: str
    is_indexed: bool
    chunk_count: int
    character_count: int
    created_at: datetime
    updated_at: datetime


class ProfileChunk(BaseModel):
    """A single profile text chunk for embedding."""

    content: str
    chunk_index: int
    chunk_type: Literal["paragraph", "sentence"]
    character_count: int


class ProfileHealth(BaseModel):
    """Profile service health status."""

    status: str
    database_accessible: bool
    profiles_dir_accessible: bool
    profile_count: int
    last_error: str | None = None
