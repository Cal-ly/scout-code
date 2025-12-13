"""
Notification API Routes

Endpoints for notification retrieval and management.

Endpoints:
    GET /api/notifications - Get notifications
    POST /api/notifications/{notification_id}/read - Mark notification as read
    POST /api/notifications/read-all - Mark all notifications as read
    DELETE /api/notifications - Clear all notifications
"""

import logging

from fastapi import APIRouter, Depends

from src.services.notification import (
    NotificationList,
    NotificationService,
    get_notification_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# =============================================================================
# DEPENDENCIES
# =============================================================================


def get_service() -> NotificationService:
    """FastAPI dependency for notification service."""
    return get_notification_service()


# =============================================================================
# RESPONSE MODELS
# =============================================================================


class MarkReadResponse:
    """Response for mark read operation."""

    def __init__(self, success: bool):
        self.success = success


class MarkAllReadResponse:
    """Response for mark all read operation."""

    def __init__(self, marked_read: int):
        self.marked_read = marked_read


class ClearResponse:
    """Response for clear operation."""

    def __init__(self, cleared: int):
        self.cleared = cleared


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get(
    "",
    response_model=NotificationList,
    summary="Get notifications",
    description="Get all or unread notifications.",
)
async def get_notifications(
    unread_only: bool = False,
    limit: int = 20,
    service: NotificationService = Depends(get_service),
) -> NotificationList:
    """
    Get notifications.

    Args:
        unread_only: Only return unread notifications.
        limit: Maximum notifications to return.
        service: Notification service.

    Returns:
        NotificationList with notifications.
    """
    if unread_only:
        return service.get_unread()
    return service.get_all(limit=limit)


@router.post(
    "/{notification_id}/read",
    summary="Mark notification as read",
    description="Mark a specific notification as read.",
)
async def mark_notification_read(
    notification_id: str,
    service: NotificationService = Depends(get_service),
) -> dict[str, bool]:
    """
    Mark a notification as read.

    Args:
        notification_id: Notification ID.
        service: Notification service.

    Returns:
        Success status.
    """
    success = service.mark_read(notification_id)
    return {"success": success}


@router.post(
    "/read-all",
    summary="Mark all notifications as read",
    description="Mark all notifications as read.",
)
async def mark_all_read(
    service: NotificationService = Depends(get_service),
) -> dict[str, int]:
    """
    Mark all notifications as read.

    Args:
        service: Notification service.

    Returns:
        Number of notifications marked as read.
    """
    count = service.mark_all_read()
    return {"marked_read": count}


@router.delete(
    "",
    summary="Clear all notifications",
    description="Delete all notifications from the store.",
)
async def clear_notifications(
    service: NotificationService = Depends(get_service),
) -> dict[str, int]:
    """
    Clear all notifications.

    Args:
        service: Notification service.

    Returns:
        Number of notifications cleared.
    """
    count = service.clear_all()
    return {"cleared": count}
