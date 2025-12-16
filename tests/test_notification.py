"""
Unit tests for S8 Notification Service.

Run with: pytest tests/test_notification.py -v
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from src.services.notification import (
    Notification,
    NotificationList,
    NotificationService,
    NotificationType,
    get_notification_service,
    reset_notification_service,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def service() -> Generator[NotificationService, None, None]:
    """Create fresh Notification Service."""
    reset_notification_service()
    svc = NotificationService()
    yield svc
    reset_notification_service()


@pytest.fixture
def service_with_notifications() -> Generator[NotificationService, None, None]:
    """Create service with some notifications."""
    reset_notification_service()
    svc = NotificationService()
    svc.notify_info("Info 1", "First info message")
    svc.notify_success("Success 1", "First success message")
    svc.notify_warning("Warning 1", "First warning message")
    yield svc
    reset_notification_service()


# =============================================================================
# MODEL TESTS
# =============================================================================


class TestNotificationModels:
    """Tests for notification data models."""

    def test_notification_type_values(self) -> None:
        """Should have correct type values."""
        assert NotificationType.INFO.value == "info"
        assert NotificationType.SUCCESS.value == "success"
        assert NotificationType.WARNING.value == "warning"
        assert NotificationType.ERROR.value == "error"

    def test_notification_creation(self) -> None:
        """Should create notification with defaults."""
        n = Notification(
            type=NotificationType.INFO,
            title="Test",
            message="Test message",
        )
        assert n.id is not None
        assert len(n.id) == 36  # Full UUID format (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
        assert n.type == NotificationType.INFO
        assert n.title == "Test"
        assert n.message == "Test message"
        assert n.read is False
        assert n.auto_dismiss is True
        assert n.dismiss_after_seconds == 5
        assert n.pipeline_id is None
        assert n.job_id is None

    def test_notification_with_context(self) -> None:
        """Should create notification with context."""
        n = Notification(
            type=NotificationType.SUCCESS,
            title="Done",
            message="Complete",
            pipeline_id="pipe-123",
            job_id="job-456",
        )
        assert n.pipeline_id == "pipe-123"
        assert n.job_id == "job-456"

    def test_notification_list(self) -> None:
        """Should create notification list."""
        n1 = Notification(
            type=NotificationType.INFO,
            title="N1",
            message="M1",
        )
        n2 = Notification(
            type=NotificationType.SUCCESS,
            title="N2",
            message="M2",
        )
        n2.read = True

        nl = NotificationList(
            notifications=[n1, n2],
            total=2,
            unread_count=1,
        )
        assert len(nl.notifications) == 2
        assert nl.total == 2
        assert nl.unread_count == 1


# =============================================================================
# CREATION TESTS
# =============================================================================


class TestNotificationCreation:
    """Tests for notification creation methods."""

    def test_notify_info(self, service: NotificationService) -> None:
        """Should create info notification."""
        n = service.notify_info("Title", "Message")

        assert n.type == NotificationType.INFO
        assert n.title == "Title"
        assert n.message == "Message"
        assert n.read is False
        assert n.auto_dismiss is True

    def test_notify_success(self, service: NotificationService) -> None:
        """Should create success notification."""
        n = service.notify_success("Done", "Completed successfully")

        assert n.type == NotificationType.SUCCESS
        assert n.title == "Done"

    def test_notify_warning_no_auto_dismiss(
        self, service: NotificationService
    ) -> None:
        """Warning should not auto-dismiss."""
        n = service.notify_warning("Warning", "Check this")

        assert n.type == NotificationType.WARNING
        assert n.auto_dismiss is False

    def test_notify_error_no_auto_dismiss(self, service: NotificationService) -> None:
        """Error should not auto-dismiss."""
        n = service.notify_error("Error", "Something failed")

        assert n.type == NotificationType.ERROR
        assert n.auto_dismiss is False

    def test_notification_with_context_ids(
        self, service: NotificationService
    ) -> None:
        """Should store pipeline/job IDs."""
        n = service.notify_info(
            "Test",
            "Message",
            pipeline_id="pipe-123",
            job_id="job-456",
        )

        assert n.pipeline_id == "pipe-123"
        assert n.job_id == "job-456"

    def test_notify_with_custom_dismiss(self, service: NotificationService) -> None:
        """Should respect custom dismiss settings."""
        n = service.notify_success(
            "Done",
            "Complete",
            auto_dismiss=True,
            dismiss_after=15,
        )

        assert n.auto_dismiss is True
        assert n.dismiss_after_seconds == 15


# =============================================================================
# PIPELINE NOTIFICATION TESTS
# =============================================================================


class TestPipelineNotifications:
    """Tests for pipeline-specific notifications."""

    def test_pipeline_started(self, service: NotificationService) -> None:
        """Should create started notification."""
        n = service.notify_pipeline_started("pipe-123", "Software Engineer")

        assert n.type == NotificationType.INFO
        assert "Software Engineer" in n.message
        assert n.pipeline_id == "pipe-123"
        assert "Processing Started" in n.title

    def test_pipeline_completed(self, service: NotificationService) -> None:
        """Should create completion notification."""
        n = service.notify_pipeline_completed(
            "pipe-123", "Software Engineer", "TechCorp", 85.0
        )

        assert n.type == NotificationType.SUCCESS
        assert "TechCorp" in n.message
        assert "85%" in n.message
        assert n.pipeline_id == "pipe-123"
        assert "Application Ready" in n.title

    def test_pipeline_failed(self, service: NotificationService) -> None:
        """Should create failure notification."""
        n = service.notify_pipeline_failed("pipe-123", "Error message")

        assert n.type == NotificationType.ERROR
        assert n.pipeline_id == "pipe-123"
        assert "Processing Failed" in n.title

    def test_pipeline_failed_truncates_long_error(
        self, service: NotificationService
    ) -> None:
        """Should truncate long error messages."""
        long_error = "x" * 500
        n = service.notify_pipeline_failed("pipe-123", long_error)

        assert len(n.message) == 200


# =============================================================================
# RETRIEVAL TESTS
# =============================================================================


class TestRetrieval:
    """Tests for notification retrieval methods."""

    def test_get_all_empty(self, service: NotificationService) -> None:
        """Should return empty list when no notifications."""
        result = service.get_all()

        assert result.total == 0
        assert len(result.notifications) == 0
        assert result.unread_count == 0

    def test_get_all(
        self, service_with_notifications: NotificationService
    ) -> None:
        """Should get all notifications."""
        result = service_with_notifications.get_all()

        assert result.total == 3
        assert len(result.notifications) == 3
        # Newest first
        assert result.notifications[0].title == "Warning 1"

    def test_get_all_with_limit(
        self, service_with_notifications: NotificationService
    ) -> None:
        """Should respect limit parameter."""
        result = service_with_notifications.get_all(limit=2)

        assert len(result.notifications) == 2
        assert result.total == 3

    def test_get_unread(
        self, service_with_notifications: NotificationService
    ) -> None:
        """Should get only unread notifications."""
        # Mark one as read
        notifications = service_with_notifications.get_all().notifications
        service_with_notifications.mark_read(notifications[0].id)

        result = service_with_notifications.get_unread()

        assert result.unread_count == 2
        assert len(result.notifications) == 2

    def test_get_by_id(self, service: NotificationService) -> None:
        """Should find notification by ID."""
        n = service.notify_info("Test", "Message")

        found = service.get_by_id(n.id)

        assert found is not None
        assert found.id == n.id
        assert found.title == "Test"

    def test_get_by_id_not_found(self, service: NotificationService) -> None:
        """Should return None for nonexistent ID."""
        found = service.get_by_id("nonexistent")

        assert found is None

    def test_max_notifications(self) -> None:
        """Should respect max limit with deque."""
        service = NotificationService(max_notifications=5)

        for i in range(10):
            service.notify_info(f"N{i}", "Message")

        result = service.get_all(limit=100)

        assert result.total == 5
        # Should have the last 5 notifications
        assert result.notifications[0].title == "N9"


# =============================================================================
# MANAGEMENT TESTS
# =============================================================================


class TestManagement:
    """Tests for notification management methods."""

    def test_mark_read(self, service: NotificationService) -> None:
        """Should mark notification as read."""
        n = service.notify_info("Test", "Message")
        assert n.read is False

        result = service.mark_read(n.id)

        assert result is True
        assert n.read is True

    def test_mark_read_not_found(self, service: NotificationService) -> None:
        """Should return False for missing ID."""
        result = service.mark_read("nonexistent")

        assert result is False

    def test_mark_all_read(
        self, service_with_notifications: NotificationService
    ) -> None:
        """Should mark all as read."""
        assert service_with_notifications.unread_count() == 3

        count = service_with_notifications.mark_all_read()

        assert count == 3
        assert service_with_notifications.unread_count() == 0

    def test_mark_all_read_already_read(self, service: NotificationService) -> None:
        """Should not count already read notifications."""
        n = service.notify_info("Test", "Message")
        service.mark_read(n.id)

        count = service.mark_all_read()

        assert count == 0

    def test_clear_all(
        self, service_with_notifications: NotificationService
    ) -> None:
        """Should clear all notifications."""
        assert service_with_notifications.count() == 3

        count = service_with_notifications.clear_all()

        assert count == 3
        assert service_with_notifications.count() == 0

    def test_clear_all_empty(self, service: NotificationService) -> None:
        """Should return 0 when clearing empty store."""
        count = service.clear_all()

        assert count == 0

    def test_count(self, service_with_notifications: NotificationService) -> None:
        """Should return total count."""
        assert service_with_notifications.count() == 3

    def test_unread_count(
        self, service_with_notifications: NotificationService
    ) -> None:
        """Should return unread count."""
        assert service_with_notifications.unread_count() == 3

        service_with_notifications.mark_all_read()
        assert service_with_notifications.unread_count() == 0


# =============================================================================
# SINGLETON TESTS
# =============================================================================


class TestSingleton:
    """Tests for singleton pattern."""

    def test_singleton_returns_same_instance(self) -> None:
        """Should return same instance."""
        reset_notification_service()

        s1 = get_notification_service()
        s2 = get_notification_service()

        assert s1 is s2
        reset_notification_service()

    def test_reset_singleton(self) -> None:
        """Should reset singleton."""
        reset_notification_service()

        s1 = get_notification_service()
        reset_notification_service()
        s2 = get_notification_service()

        assert s1 is not s2
        reset_notification_service()

    def test_singleton_persists_notifications(self) -> None:
        """Singleton should persist notifications."""
        reset_notification_service()

        s1 = get_notification_service()
        s1.notify_info("Test", "Message")

        s2 = get_notification_service()
        result = s2.get_all()

        assert result.total == 1
        reset_notification_service()


# =============================================================================
# API ROUTE TESTS
# =============================================================================


class TestNotificationRoutes:
    """Tests for notification API routes."""

    @pytest.fixture
    def client(self) -> Generator[TestClient, None, None]:
        """Create test client."""
        reset_notification_service()

        from src.web.main import app

        yield TestClient(app, raise_server_exceptions=False)

        reset_notification_service()

    def test_get_notifications_empty(self, client: TestClient) -> None:
        """Should return empty list."""
        response = client.get("/api/v1/notifications")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["notifications"] == []

    def test_get_notifications(self, client: TestClient) -> None:
        """Should return notifications."""
        # Add a notification
        service = get_notification_service()
        service.notify_info("Test", "Message")

        response = client.get("/api/v1/notifications")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["notifications"][0]["title"] == "Test"

    def test_get_notifications_unread_only(self, client: TestClient) -> None:
        """Should filter unread only."""
        service = get_notification_service()
        n1 = service.notify_info("Read", "Read message")
        service.notify_info("Unread", "Unread message")
        service.mark_read(n1.id)

        response = client.get("/api/v1/notifications?unread_only=true")

        assert response.status_code == 200
        data = response.json()
        assert data["unread_count"] == 1
        assert data["notifications"][0]["title"] == "Unread"

    def test_get_notifications_with_limit(self, client: TestClient) -> None:
        """Should respect limit parameter."""
        service = get_notification_service()
        for i in range(5):
            service.notify_info(f"N{i}", "Message")

        response = client.get("/api/v1/notifications?limit=3")

        assert response.status_code == 200
        data = response.json()
        assert len(data["notifications"]) == 3
        assert data["total"] == 5

    def test_mark_notification_read(self, client: TestClient) -> None:
        """Should mark notification as read."""
        service = get_notification_service()
        n = service.notify_info("Test", "Message")

        response = client.post(f"/api/v1/notifications/{n.id}/read")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert n.read is True

    def test_mark_notification_read_not_found(self, client: TestClient) -> None:
        """Should return false for nonexistent notification."""
        response = client.post("/api/v1/notifications/nonexistent/read")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_mark_all_read(self, client: TestClient) -> None:
        """Should mark all as read."""
        service = get_notification_service()
        service.notify_info("N1", "Message")
        service.notify_info("N2", "Message")

        response = client.post("/api/v1/notifications/read-all")

        assert response.status_code == 200
        data = response.json()
        assert data["marked_read"] == 2
        assert service.unread_count() == 0

    def test_clear_notifications(self, client: TestClient) -> None:
        """Should clear all notifications."""
        service = get_notification_service()
        service.notify_info("N1", "Message")
        service.notify_info("N2", "Message")

        response = client.delete("/api/v1/notifications")

        assert response.status_code == 200
        data = response.json()
        assert data["cleared"] == 2
        assert service.count() == 0
