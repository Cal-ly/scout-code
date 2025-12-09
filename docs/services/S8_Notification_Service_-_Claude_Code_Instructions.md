# S8 Notification Service - Claude Code Instructions

**Version:** 2.0 (PoC Aligned)  
**Updated:** November 26, 2025  
**Status:** Ready for Implementation  
**Priority:** Phase 3 - Integration (Build Second in Phase 3)

---

## PoC Scope Summary

| Feature | Status | Notes |
|---------|--------|-------|
| In-app toast notifications | ✅ In Scope | Simple message queue |
| Success/error/warning types | ✅ In Scope | Basic notification types |
| Notification history | ✅ In Scope | Last N notifications |
| Mark as read | ✅ In Scope | Simple flag |
| Email notifications | ❌ Deferred | Not needed for single-user |
| SMS notifications | ❌ Deferred | Not needed for PoC |
| Push notifications | ❌ Deferred | Desktop app feature |
| Webhooks | ❌ Deferred | Not needed for PoC |

---

## Context & Objective

Build the **Notification Service** for Scout - provides in-app toast notifications to inform users of pipeline progress, success, and errors.

### Why This Service Exists

The Notification Service:
- Provides feedback during long-running operations
- Alerts users to success/failure of operations
- Maintains notification history for review
- Simple polling-based delivery (no WebSocket for PoC)

---

## Technical Requirements

### File Structure

```
scout/
├── app/
│   ├── models/
│   │   └── notification.py      # Notification models
│   ├── services/
│   │   └── notification.py      # Notification Service
│   └── api/
│       └── routes/
│           └── notifications.py # API endpoints
└── tests/
    └── unit/
        └── services/
            └── test_notification.py
```

---

## Data Models

Create `app/models/notification.py`:

```python
"""
Notification Data Models

Simple models for in-app notifications.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid


class NotificationType(str, Enum):
    """Types of notifications."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class Notification(BaseModel):
    """
    A single notification.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: NotificationType
    title: str
    message: str
    created_at: datetime = Field(default_factory=datetime.now)
    read: bool = False
    
    # Optional context
    pipeline_id: Optional[str] = None
    job_id: Optional[str] = None
    
    # Auto-dismiss settings
    auto_dismiss: bool = True
    dismiss_after_seconds: int = 5


class NotificationList(BaseModel):
    """List of notifications with metadata."""
    notifications: List[Notification]
    total: int
    unread_count: int
```

---

## Service Implementation

Create `app/services/notification.py`:

```python
"""
Notification Service

Simple in-app notification system.

Usage:
    notification_service = NotificationService()
    
    notification_service.notify_success("Application created!")
    
    notifications = notification_service.get_unread()
"""

import logging
from typing import List, Optional
from collections import deque
from datetime import datetime

from app.models.notification import (
    Notification, NotificationList, NotificationType
)

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Notification Service - manages in-app notifications.
    
    Uses an in-memory queue with configurable max size.
    Notifications are polled by the frontend.
    
    Attributes:
        max_notifications: Maximum notifications to keep
        
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
            max_notifications: Max notifications to keep in memory
        """
        self._max = max_notifications
        self._notifications: deque[Notification] = deque(maxlen=max_notifications)
        
        logger.debug(f"Notification Service initialized (max: {max_notifications})")
    
    # =========================================================================
    # NOTIFICATION CREATION
    # =========================================================================
    
    def _add_notification(self, notification: Notification) -> Notification:
        """Add notification to queue."""
        self._notifications.append(notification)
        logger.debug(f"Notification added: [{notification.type.value}] {notification.title}")
        return notification
    
    def notify(
        self,
        type: NotificationType,
        title: str,
        message: str,
        pipeline_id: Optional[str] = None,
        job_id: Optional[str] = None,
        auto_dismiss: bool = True,
        dismiss_after: int = 5
    ) -> Notification:
        """
        Create a notification.
        
        Args:
            type: Notification type
            title: Short title
            message: Detailed message
            pipeline_id: Associated pipeline ID
            job_id: Associated job ID
            auto_dismiss: Whether to auto-dismiss
            dismiss_after: Seconds before auto-dismiss
            
        Returns:
            Created Notification
        """
        notification = Notification(
            type=type,
            title=title,
            message=message,
            pipeline_id=pipeline_id,
            job_id=job_id,
            auto_dismiss=auto_dismiss,
            dismiss_after_seconds=dismiss_after
        )
        
        return self._add_notification(notification)
    
    def notify_info(
        self,
        title: str,
        message: str,
        **kwargs
    ) -> Notification:
        """Create info notification."""
        return self.notify(NotificationType.INFO, title, message, **kwargs)
    
    def notify_success(
        self,
        title: str,
        message: str,
        **kwargs
    ) -> Notification:
        """Create success notification."""
        return self.notify(NotificationType.SUCCESS, title, message, **kwargs)
    
    def notify_warning(
        self,
        title: str,
        message: str,
        **kwargs
    ) -> Notification:
        """Create warning notification."""
        return self.notify(
            NotificationType.WARNING, title, message,
            auto_dismiss=False,  # Warnings stay
            **kwargs
        )
    
    def notify_error(
        self,
        title: str,
        message: str,
        **kwargs
    ) -> Notification:
        """Create error notification."""
        return self.notify(
            NotificationType.ERROR, title, message,
            auto_dismiss=False,  # Errors stay
            **kwargs
        )
    
    # =========================================================================
    # PIPELINE NOTIFICATIONS
    # =========================================================================
    
    def notify_pipeline_started(
        self,
        pipeline_id: str,
        job_title: str
    ) -> Notification:
        """Notify pipeline started."""
        return self.notify_info(
            title="Processing Started",
            message=f"Processing job: {job_title}",
            pipeline_id=pipeline_id
        )
    
    def notify_pipeline_completed(
        self,
        pipeline_id: str,
        job_title: str,
        company: str,
        score: float
    ) -> Notification:
        """Notify pipeline completed successfully."""
        return self.notify_success(
            title="Application Ready!",
            message=f"{job_title} at {company} - {score:.0f}% match",
            pipeline_id=pipeline_id,
            dismiss_after=10
        )
    
    def notify_pipeline_failed(
        self,
        pipeline_id: str,
        error: str
    ) -> Notification:
        """Notify pipeline failed."""
        return self.notify_error(
            title="Processing Failed",
            message=error[:200],  # Truncate long errors
            pipeline_id=pipeline_id
        )
    
    # =========================================================================
    # RETRIEVAL
    # =========================================================================
    
    def get_all(self, limit: int = 20) -> NotificationList:
        """
        Get all notifications.
        
        Args:
            limit: Maximum to return
            
        Returns:
            NotificationList with notifications
        """
        notifications = list(self._notifications)[-limit:]
        notifications.reverse()  # Newest first
        
        unread = sum(1 for n in self._notifications if not n.read)
        
        return NotificationList(
            notifications=notifications,
            total=len(self._notifications),
            unread_count=unread
        )
    
    def get_unread(self) -> NotificationList:
        """
        Get unread notifications.
        
        Returns:
            NotificationList with unread notifications
        """
        unread = [n for n in self._notifications if not n.read]
        unread.reverse()  # Newest first
        
        return NotificationList(
            notifications=unread,
            total=len(unread),
            unread_count=len(unread)
        )
    
    def get_by_id(self, notification_id: str) -> Optional[Notification]:
        """Get notification by ID."""
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
            notification_id: Notification ID
            
        Returns:
            True if found and marked
        """
        notification = self.get_by_id(notification_id)
        if notification:
            notification.read = True
            return True
        return False
    
    def mark_all_read(self) -> int:
        """
        Mark all notifications as read.
        
        Returns:
            Number marked as read
        """
        count = 0
        for n in self._notifications:
            if not n.read:
                n.read = True
                count += 1
        return count
    
    def clear_all(self) -> int:
        """
        Clear all notifications.
        
        Returns:
            Number cleared
        """
        count = len(self._notifications)
        self._notifications.clear()
        return count


# =============================================================================
# SINGLETON
# =============================================================================

_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get the Notification Service singleton."""
    global _notification_service
    
    if _notification_service is None:
        _notification_service = NotificationService()
    
    return _notification_service


def reset_notification_service() -> None:
    """Reset singleton (for testing)."""
    global _notification_service
    _notification_service = None
```

---

## API Routes

Create `app/api/routes/notifications.py`:

```python
"""
Notification API Routes

Endpoints for notification retrieval and management.
"""

from fastapi import APIRouter, Depends

from app.services.notification import NotificationService, get_notification_service
from app.models.notification import NotificationList, Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationList)
async def get_notifications(
    unread_only: bool = False,
    limit: int = 20,
    service: NotificationService = Depends(get_notification_service)
) -> NotificationList:
    """
    Get notifications.
    
    Args:
        unread_only: Only return unread notifications
        limit: Maximum notifications to return
    """
    if unread_only:
        return service.get_unread()
    return service.get_all(limit=limit)


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    service: NotificationService = Depends(get_notification_service)
) -> dict:
    """Mark a notification as read."""
    success = service.mark_read(notification_id)
    return {"success": success}


@router.post("/read-all")
async def mark_all_read(
    service: NotificationService = Depends(get_notification_service)
) -> dict:
    """Mark all notifications as read."""
    count = service.mark_all_read()
    return {"marked_read": count}


@router.delete("")
async def clear_notifications(
    service: NotificationService = Depends(get_notification_service)
) -> dict:
    """Clear all notifications."""
    count = service.clear_all()
    return {"cleared": count}
```

---

## Test Implementation

Create `tests/unit/services/test_notification.py`:

```python
"""
Unit tests for Notification Service.

Run with: pytest tests/unit/services/test_notification.py -v
"""

import pytest

from app.services.notification import (
    NotificationService, get_notification_service, reset_notification_service
)
from app.models.notification import NotificationType


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def service():
    """Create fresh Notification Service."""
    reset_notification_service()
    return NotificationService()


# =============================================================================
# CREATION TESTS
# =============================================================================

class TestNotificationCreation:
    """Tests for notification creation."""
    
    def test_notify_info(self, service):
        """Should create info notification."""
        n = service.notify_info("Title", "Message")
        
        assert n.type == NotificationType.INFO
        assert n.title == "Title"
        assert n.message == "Message"
        assert n.read is False
    
    def test_notify_success(self, service):
        """Should create success notification."""
        n = service.notify_success("Done", "Completed successfully")
        
        assert n.type == NotificationType.SUCCESS
    
    def test_notify_warning_no_auto_dismiss(self, service):
        """Warning should not auto-dismiss."""
        n = service.notify_warning("Warning", "Check this")
        
        assert n.auto_dismiss is False
    
    def test_notify_error_no_auto_dismiss(self, service):
        """Error should not auto-dismiss."""
        n = service.notify_error("Error", "Something failed")
        
        assert n.auto_dismiss is False
    
    def test_notification_with_context(self, service):
        """Should store pipeline/job IDs."""
        n = service.notify_info(
            "Test", "Message",
            pipeline_id="pipe-123",
            job_id="job-456"
        )
        
        assert n.pipeline_id == "pipe-123"
        assert n.job_id == "job-456"


# =============================================================================
# PIPELINE NOTIFICATION TESTS
# =============================================================================

class TestPipelineNotifications:
    """Tests for pipeline-specific notifications."""
    
    def test_pipeline_started(self, service):
        """Should create started notification."""
        n = service.notify_pipeline_started("pipe-123", "Software Engineer")
        
        assert n.type == NotificationType.INFO
        assert "Software Engineer" in n.message
        assert n.pipeline_id == "pipe-123"
    
    def test_pipeline_completed(self, service):
        """Should create completion notification."""
        n = service.notify_pipeline_completed(
            "pipe-123", "Software Engineer", "TechCorp", 85.0
        )
        
        assert n.type == NotificationType.SUCCESS
        assert "TechCorp" in n.message
        assert "85%" in n.message
    
    def test_pipeline_failed(self, service):
        """Should create failure notification."""
        n = service.notify_pipeline_failed("pipe-123", "Error message")
        
        assert n.type == NotificationType.ERROR


# =============================================================================
# RETRIEVAL TESTS
# =============================================================================

class TestRetrieval:
    """Tests for notification retrieval."""
    
    def test_get_all(self, service):
        """Should get all notifications."""
        service.notify_info("1", "First")
        service.notify_info("2", "Second")
        
        result = service.get_all()
        
        assert result.total == 2
        assert len(result.notifications) == 2
        # Newest first
        assert result.notifications[0].title == "2"
    
    def test_get_unread(self, service):
        """Should get only unread."""
        n1 = service.notify_info("1", "First")
        service.notify_info("2", "Second")
        
        service.mark_read(n1.id)
        
        result = service.get_unread()
        
        assert result.unread_count == 1
        assert result.notifications[0].title == "2"
    
    def test_get_by_id(self, service):
        """Should find notification by ID."""
        n = service.notify_info("Test", "Message")
        
        found = service.get_by_id(n.id)
        
        assert found is not None
        assert found.title == "Test"
    
    def test_max_notifications(self):
        """Should respect max limit."""
        service = NotificationService(max_notifications=5)
        
        for i in range(10):
            service.notify_info(f"N{i}", "Message")
        
        result = service.get_all(limit=100)
        
        assert result.total == 5


# =============================================================================
# MANAGEMENT TESTS
# =============================================================================

class TestManagement:
    """Tests for notification management."""
    
    def test_mark_read(self, service):
        """Should mark notification as read."""
        n = service.notify_info("Test", "Message")
        assert n.read is False
        
        result = service.mark_read(n.id)
        
        assert result is True
        assert n.read is True
    
    def test_mark_read_not_found(self, service):
        """Should return False for missing ID."""
        result = service.mark_read("nonexistent")
        assert result is False
    
    def test_mark_all_read(self, service):
        """Should mark all as read."""
        service.notify_info("1", "First")
        service.notify_info("2", "Second")
        
        count = service.mark_all_read()
        
        assert count == 2
        assert service.get_unread().unread_count == 0
    
    def test_clear_all(self, service):
        """Should clear all notifications."""
        service.notify_info("1", "First")
        service.notify_info("2", "Second")
        
        count = service.clear_all()
        
        assert count == 2
        assert service.get_all().total == 0


# =============================================================================
# SINGLETON TESTS
# =============================================================================

class TestSingleton:
    """Tests for singleton pattern."""
    
    def test_singleton(self):
        """Should return same instance."""
        reset_notification_service()
        
        s1 = get_notification_service()
        s2 = get_notification_service()
        
        assert s1 is s2
```

---

## Implementation Steps

### Step S8.1: Data Models
```bash
# Create app/models/notification.py
# Verify:
python -c "from app.models.notification import Notification, NotificationType; print('OK')"
```

### Step S8.2: Service Implementation
```bash
# Create app/services/notification.py
# Verify:
python -c "from app.services.notification import NotificationService; print('OK')"
```

### Step S8.3: API Routes
```bash
# Create app/api/routes/notifications.py
# Verify:
python -c "from app.api.routes.notifications import router; print('OK')"
```

### Step S8.4: Unit Tests
```bash
# Create tests/unit/services/test_notification.py
# Verify:
pytest tests/unit/services/test_notification.py -v
```

---

## Success Criteria

| Metric | Target | Verification |
|--------|--------|--------------|
| Notification creation | All types work | Test each type |
| Retrieval | Correct ordering | Test newest-first |
| Read tracking | Accurate counts | Test mark/unmark |
| Max limit | Respected | Test overflow |
| Test coverage | >90% | `pytest --cov=app/services/notification` |

---

*This specification is aligned with Scout PoC Scope Document v1.0*
