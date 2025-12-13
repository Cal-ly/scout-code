"""
S8 Notification Service Data Models

Models for in-app toast notifications.
"""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    """Types of notifications."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class Notification(BaseModel):
    """
    A single notification.

    Attributes:
        id: Unique notification identifier.
        type: Notification type (info, success, warning, error).
        title: Short notification title.
        message: Detailed notification message.
        created_at: When the notification was created.
        read: Whether the notification has been read.
        pipeline_id: Associated pipeline ID (optional).
        job_id: Associated job ID (optional).
        auto_dismiss: Whether to auto-dismiss the notification.
        dismiss_after_seconds: Seconds before auto-dismiss.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: NotificationType
    title: str
    message: str
    created_at: datetime = Field(default_factory=datetime.now)
    read: bool = False

    # Optional context
    pipeline_id: str | None = None
    job_id: str | None = None

    # Auto-dismiss settings
    auto_dismiss: bool = True
    dismiss_after_seconds: int = 5


class NotificationList(BaseModel):
    """
    List of notifications with metadata.

    Attributes:
        notifications: List of notification objects.
        total: Total number of notifications in store.
        unread_count: Number of unread notifications.
    """

    notifications: list[Notification]
    total: int
    unread_count: int
