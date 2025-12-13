"""
S8 Notification Service Package

In-app toast notification system for Scout.

Usage:
    from src.services.notification import (
        NotificationService,
        get_notification_service,
        Notification,
        NotificationType,
    )

    # Get singleton
    service = get_notification_service()

    # Create notifications
    service.notify_success("Done!", "Application created")
    service.notify_error("Failed", "Something went wrong")

    # Get unread
    unread = service.get_unread()
"""

from src.services.notification.exceptions import (
    NotificationError,
    NotificationNotFoundError,
)
from src.services.notification.models import (
    Notification,
    NotificationList,
    NotificationType,
)
from src.services.notification.notification import (
    NotificationService,
    get_notification_service,
    reset_notification_service,
)

__all__ = [
    # Service
    "NotificationService",
    "get_notification_service",
    "reset_notification_service",
    # Models
    "Notification",
    "NotificationList",
    "NotificationType",
    # Exceptions
    "NotificationError",
    "NotificationNotFoundError",
]
