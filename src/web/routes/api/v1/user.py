"""
User API Routes

Current user information for the UI.
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.services.database import DatabaseService, get_database_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["user"])


class UserResponse(BaseModel):
    """Current user info."""

    id: int
    username: str
    display_name: str | None
    email: str | None


@router.get("", response_model=UserResponse)
async def get_current_user(
    db: DatabaseService = Depends(get_database_service),
) -> UserResponse:
    """Get current user information."""
    user = await db.get_current_user()
    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
    )
