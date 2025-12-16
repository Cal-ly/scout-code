"""Database models using Pydantic."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, computed_field


class ApplicationStatus(str, Enum):
    """Application processing status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# PROFILE MODELS
# =============================================================================


class ProfileBase(BaseModel):
    """Base profile fields."""
    name: str = Field(..., min_length=1, max_length=200)
    full_name: str = Field(..., min_length=1, max_length=200)
    email: str | None = None
    title: str | None = None


class ProfileCreate(ProfileBase):
    """Profile creation request."""
    profile_data: dict[str, Any]  # Full UserProfile as dict
    is_active: bool = False
    is_demo: bool = False


class ProfileUpdate(BaseModel):
    """Profile update request (all fields optional)."""
    name: str | None = None
    full_name: str | None = None
    email: str | None = None
    title: str | None = None
    profile_data: dict[str, Any] | None = None
    is_active: bool | None = None


class Profile(ProfileBase):
    """Profile database record."""
    id: int
    slug: str
    profile_data: dict[str, Any]
    is_active: bool = False
    is_indexed: bool = False
    is_demo: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def display_name(self) -> str:
        """Display name for UI."""
        return self.name or self.full_name


# =============================================================================
# APPLICATION MODELS
# =============================================================================


class ApplicationBase(BaseModel):
    """Base application fields."""
    job_title: str | None = None
    company_name: str | None = None


class ApplicationCreate(ApplicationBase):
    """Application creation request."""
    job_id: str
    profile_id: int
    job_text: str


class ApplicationUpdate(BaseModel):
    """Application update request."""
    job_title: str | None = None
    company_name: str | None = None
    status: ApplicationStatus | None = None
    compatibility_score: int | None = None
    cv_path: str | None = None
    cover_letter_path: str | None = None
    analysis_data: dict[str, Any] | None = None
    pipeline_data: dict[str, Any] | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class Application(ApplicationBase):
    """Application database record."""
    id: int
    job_id: str
    profile_id: int
    job_text: str
    status: ApplicationStatus = ApplicationStatus.PENDING
    compatibility_score: int | None = None
    cv_path: str | None = None
    cover_letter_path: str | None = None
    analysis_data: dict[str, Any] | None = None
    pipeline_data: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Joined data
    profile_name: str | None = None

    model_config = {"from_attributes": True}


# =============================================================================
# SETTINGS MODEL
# =============================================================================


class Settings(BaseModel):
    """Application settings."""
    active_profile_id: int | None = None
    schema_version: int = 1
    demo_data_loaded: bool = False
