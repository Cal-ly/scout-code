"""
Notifications API Routes

Notification management endpoints.

Endpoints:
    GET /api/v1/notifications - Get notifications
    POST /api/v1/notifications/{id}/read - Mark as read
    POST /api/v1/notifications/read-all - Mark all as read
    DELETE /api/v1/notifications - Clear all
"""

import logging

from fastapi import APIRouter, Depends

from src.services.notification import (
    NotificationList,
    NotificationService,
    get_notification_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_service() -> NotificationService:
    """Get notification service."""
    return get_notification_service()


@router.get("", response_model=NotificationList)
async def get_notifications(
    unread_only: bool = False,
    limit: int = 20,
    service: NotificationService = Depends(get_service),
) -> NotificationList:
    """Get notifications."""
    return service.get_unread() if unread_only else service.get_all(limit=limit)


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    service: NotificationService = Depends(get_service),
) -> dict:
    """Mark notification as read."""
    return {"success": service.mark_read(notification_id)}


@router.post("/read-all")
async def mark_all_read(service: NotificationService = Depends(get_service)) -> dict:
    """Mark all as read."""
    return {"marked_read": service.mark_all_read()}


@router.delete("")
async def clear_all(service: NotificationService = Depends(get_service)) -> dict:
    """Clear all notifications."""
    return {"cleared": service.clear_all()}
