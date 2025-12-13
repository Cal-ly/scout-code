"""
S8 Notification Service

Simple in-app notification system for toast notifications.

Usage:
    from src.services.notification import get_notification_service

    service = get_notification_service()
    service.notify_success("Application Ready!", "CV and cover letter generated")
    notifications = service.get_unread()
"""

import logging
import threading
from collections import deque

from src.services.notification.models import (
    Notification,
    NotificationList,
    NotificationType,
)

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Notification Service - manages in-app toast notifications.

    Uses an in-memory deque with configurable max size.
    Notifications are polled by the frontend.

    Thread-safe: All operations protected by a lock for concurrent access
    from background tasks and API requests.

    Attributes:
        max_notifications: Maximum notifications to keep in memory.
        _lock: Threading lock for concurrent access safety.

    Example:
        >>> service = NotificationService()
        >>> service.notify_success("Done!", "Application created")
        >>> unread = service.get_unread()
    """

    DEFAULT_MAX_NOTIFICATIONS = 50

    def __init__(self, max_notifications: int = DEFAULT_MAX_NOTIFICATIONS):
        """
        Initialize Notification Service.

        Args:
            max_notifications: Max notifications to keep in memory.
        """
        self._max = max_notifications
        self._notifications: deque[Notification] = deque(maxlen=max_notifications)
        self._lock = threading.Lock()

        logger.debug(f"NotificationService initialized (max: {max_notifications})")

    # =========================================================================
    # NOTIFICATION CREATION
    # =========================================================================

    def _add_notification(self, notification: Notification) -> Notification:
        """Add notification to queue."""
        with self._lock:
            self._notifications.append(notification)
        logger.debug(
            f"Notification added: [{notification.type.value}] {notification.title}"
        )
        return notification

    def notify(
        self,
        notification_type: NotificationType,
        title: str,
        message: str,
        pipeline_id: str | None = None,
        job_id: str | None = None,
        auto_dismiss: bool = True,
        dismiss_after: int = 5,
    ) -> Notification:
        """
        Create a notification.

        Args:
            notification_type: Notification type.
            title: Short title.
            message: Detailed message.
            pipeline_id: Associated pipeline ID.
            job_id: Associated job ID.
            auto_dismiss: Whether to auto-dismiss.
            dismiss_after: Seconds before auto-dismiss.

        Returns:
            Created Notification.
        """
        notification = Notification(
            type=notification_type,
            title=title,
            message=message,
            pipeline_id=pipeline_id,
            job_id=job_id,
            auto_dismiss=auto_dismiss,
            dismiss_after_seconds=dismiss_after,
        )

        return self._add_notification(notification)

    def notify_info(
        self,
        title: str,
        message: str,
        pipeline_id: str | None = None,
        job_id: str | None = None,
        auto_dismiss: bool = True,
        dismiss_after: int = 5,
    ) -> Notification:
        """Create info notification."""
        return self.notify(
            NotificationType.INFO,
            title,
            message,
            pipeline_id=pipeline_id,
            job_id=job_id,
            auto_dismiss=auto_dismiss,
            dismiss_after=dismiss_after,
        )

    def notify_success(
        self,
        title: str,
        message: str,
        pipeline_id: str | None = None,
        job_id: str | None = None,
        auto_dismiss: bool = True,
        dismiss_after: int = 5,
    ) -> Notification:
        """Create success notification."""
        return self.notify(
            NotificationType.SUCCESS,
            title,
            message,
            pipeline_id=pipeline_id,
            job_id=job_id,
            auto_dismiss=auto_dismiss,
            dismiss_after=dismiss_after,
        )

    def notify_warning(
        self,
        title: str,
        message: str,
        pipeline_id: str | None = None,
        job_id: str | None = None,
    ) -> Notification:
        """Create warning notification (no auto-dismiss)."""
        return self.notify(
            NotificationType.WARNING,
            title,
            message,
            pipeline_id=pipeline_id,
            job_id=job_id,
            auto_dismiss=False,  # Warnings stay
            dismiss_after=0,
        )

    def notify_error(
        self,
        title: str,
        message: str,
        pipeline_id: str | None = None,
        job_id: str | None = None,
    ) -> Notification:
        """Create error notification (no auto-dismiss)."""
        return self.notify(
            NotificationType.ERROR,
            title,
            message,
            pipeline_id=pipeline_id,
            job_id=job_id,
            auto_dismiss=False,  # Errors stay
            dismiss_after=0,
        )

    # =========================================================================
    # PIPELINE NOTIFICATIONS
    # =========================================================================

    def notify_pipeline_started(
        self,
        pipeline_id: str,
        job_title: str,
    ) -> Notification:
        """Notify pipeline started."""
        return self.notify_info(
            title="Processing Started",
            message=f"Processing job: {job_title}",
            pipeline_id=pipeline_id,
        )

    def notify_pipeline_completed(
        self,
        pipeline_id: str,
        job_title: str,
        company: str,
        score: float,
    ) -> Notification:
        """Notify pipeline completed successfully."""
        return self.notify_success(
            title="Application Ready!",
            message=f"{job_title} at {company} - {score:.0f}% match",
            pipeline_id=pipeline_id,
            dismiss_after=10,
        )

    def notify_pipeline_failed(
        self,
        pipeline_id: str,
        error: str,
    ) -> Notification:
        """Notify pipeline failed."""
        return self.notify_error(
            title="Processing Failed",
            message=error[:200],  # Truncate long errors
            pipeline_id=pipeline_id,
        )

    # =========================================================================
    # RETRIEVAL
    # =========================================================================

    def get_all(self, limit: int = 20) -> NotificationList:
        """
        Get all notifications.

        Args:
            limit: Maximum to return.

        Returns:
            NotificationList with notifications (newest first).
        """
        with self._lock:
            notifications = list(self._notifications)[-limit:]
            unread = sum(1 for n in self._notifications if not n.read)
            total = len(self._notifications)
        notifications.reverse()  # Newest first

        return NotificationList(
            notifications=notifications,
            total=total,
            unread_count=unread,
        )

    def get_unread(self) -> NotificationList:
        """
        Get unread notifications.

        Returns:
            NotificationList with unread notifications (newest first).
        """
        with self._lock:
            unread = [n for n in self._notifications if not n.read]
        unread.reverse()  # Newest first

        return NotificationList(
            notifications=unread,
            total=len(unread),
            unread_count=len(unread),
        )

    def get_by_id(self, notification_id: str) -> Notification | None:
        """
        Get notification by ID.

        Args:
            notification_id: Notification ID.

        Returns:
            Notification if found, None otherwise.
        """
        with self._lock:
            for n in self._notifications:
                if n.id == notification_id:
                    return n
            return None

    # =========================================================================
    # MANAGEMENT
    # =========================================================================

    def mark_read(self, notification_id: str) -> bool:
        """
        Mark notification as read.

        Args:
            notification_id: Notification ID.

        Returns:
            True if found and marked, False otherwise.
        """
        with self._lock:
            for n in self._notifications:
                if n.id == notification_id:
                    n.read = True
                    return True
            return False

    def mark_all_read(self) -> int:
        """
        Mark all notifications as read.

        Returns:
            Number marked as read.
        """
        count = 0
        with self._lock:
            for n in self._notifications:
                if not n.read:
                    n.read = True
                    count += 1
        return count

    def clear_all(self) -> int:
        """
        Clear all notifications.

        Returns:
            Number cleared.
        """
        with self._lock:
            count = len(self._notifications)
            self._notifications.clear()
        return count

    def count(self) -> int:
        """Get total notification count."""
        with self._lock:
            return len(self._notifications)

    def unread_count(self) -> int:
        """Get unread notification count."""
        with self._lock:
            return sum(1 for n in self._notifications if not n.read)


# =============================================================================
# SINGLETON
# =============================================================================

_notification_service: NotificationService | None = None


def get_notification_service() -> NotificationService:
    """
    Get the Notification Service singleton.

    Returns:
        NotificationService instance.
    """
    global _notification_service

    if _notification_service is None:
        _notification_service = NotificationService()
        logger.info("NotificationService singleton created")

    return _notification_service


def reset_notification_service() -> None:
    """Reset singleton (for testing)."""
    global _notification_service
    _notification_service = None
