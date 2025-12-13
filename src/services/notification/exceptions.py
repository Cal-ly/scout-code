"""
S8 Notification Service Exceptions

Custom exceptions for notification operations.
"""


class NotificationError(Exception):
    """Base exception for notification operations."""

    pass


class NotificationNotFoundError(NotificationError):
    """Notification not found."""

    def __init__(self, notification_id: str):
        self.notification_id = notification_id
        super().__init__(f"Notification not found: {notification_id}")
