"""Tests for database service."""

import pytest
import tempfile
from pathlib import Path

from src.services.database import (
    DatabaseService,
    Profile,
    ProfileCreate,
    ProfileUpdate,
    Application,
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationStatus,
)
from src.services.database.exceptions import (
    ProfileNotFoundError,
    ApplicationNotFoundError,
)


@pytest.fixture
async def db_service():
    """Create temporary database service."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        service = DatabaseService(db_path)
        await service.initialize()
        yield service
        await service.close()


# =============================================================================
# PROFILE TESTS
# =============================================================================


class TestProfileCRUD:
    """Profile CRUD tests."""

    @pytest.mark.asyncio
    async def test_create_profile(self, db_service):
        """Test creating a profile."""
        data = ProfileCreate(
            name="Test Profile",
            full_name="Test User",
            email="test@example.com",
            title="Developer",
            profile_data={"skills": ["Python"]},
        )

        profile = await db_service.create_profile(data)

        assert profile.id is not None
        assert profile.name == "Test Profile"
        assert profile.slug == "test-profile"
        assert profile.full_name == "Test User"
        assert profile.profile_data == {"skills": ["Python"]}

    @pytest.mark.asyncio
    async def test_create_profile_generates_unique_slug(self, db_service):
        """Test slug uniqueness."""
        data1 = ProfileCreate(name="Test", full_name="User 1", profile_data={})
        data2 = ProfileCreate(name="Test", full_name="User 2", profile_data={})

        p1 = await db_service.create_profile(data1)
        p2 = await db_service.create_profile(data2)

        assert p1.slug == "test"
        assert p2.slug == "test-2"

    @pytest.mark.asyncio
    async def test_get_profile(self, db_service):
        """Test getting profile by ID."""
        data = ProfileCreate(name="Test", full_name="User", profile_data={})
        created = await db_service.create_profile(data)

        profile = await db_service.get_profile(created.id)

        assert profile.id == created.id
        assert profile.name == "Test"

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, db_service):
        """Test getting non-existent profile."""
        with pytest.raises(ProfileNotFoundError):
            await db_service.get_profile(999)

    @pytest.mark.asyncio
    async def test_get_profile_by_slug(self, db_service):
        """Test getting profile by slug."""
        data = ProfileCreate(name="My Profile", full_name="User", profile_data={})
        created = await db_service.create_profile(data)

        profile = await db_service.get_profile_by_slug("my-profile")

        assert profile.id == created.id
        assert profile.name == "My Profile"

    @pytest.mark.asyncio
    async def test_list_profiles(self, db_service):
        """Test listing profiles."""
        await db_service.create_profile(ProfileCreate(name="A", full_name="A", profile_data={}))
        await db_service.create_profile(ProfileCreate(name="B", full_name="B", profile_data={}))

        profiles = await db_service.list_profiles()

        assert len(profiles) == 2

    @pytest.mark.asyncio
    async def test_list_profiles_exclude_demo(self, db_service):
        """Test listing profiles excluding demo."""
        await db_service.create_profile(
            ProfileCreate(name="User", full_name="User", profile_data={}, is_demo=False)
        )
        await db_service.create_profile(
            ProfileCreate(name="Demo", full_name="Demo", profile_data={}, is_demo=True)
        )

        all_profiles = await db_service.list_profiles(include_demo=True)
        user_profiles = await db_service.list_profiles(include_demo=False)

        assert len(all_profiles) == 2
        assert len(user_profiles) == 1
        assert user_profiles[0].name == "User"

    @pytest.mark.asyncio
    async def test_update_profile(self, db_service):
        """Test updating a profile."""
        data = ProfileCreate(name="Old Name", full_name="User", profile_data={})
        profile = await db_service.create_profile(data)

        updated = await db_service.update_profile(
            profile.id,
            ProfileUpdate(name="New Name", title="Senior Dev")
        )

        assert updated.name == "New Name"
        assert updated.slug == "new-name"
        assert updated.title == "Senior Dev"

    @pytest.mark.asyncio
    async def test_update_profile_data_marks_unindexed(self, db_service):
        """Test that updating profile_data marks profile as not indexed."""
        data = ProfileCreate(name="Test", full_name="User", profile_data={"old": True})
        profile = await db_service.create_profile(data)

        # Mark as indexed
        await db_service.set_profile_indexed(profile.id, True)
        indexed = await db_service.get_profile(profile.id)
        assert indexed.is_indexed is True

        # Update profile_data
        updated = await db_service.update_profile(
            profile.id,
            ProfileUpdate(profile_data={"new": True})
        )

        assert updated.is_indexed is False

    @pytest.mark.asyncio
    async def test_delete_profile(self, db_service):
        """Test deleting a profile."""
        data = ProfileCreate(name="Test", full_name="User", profile_data={})
        profile = await db_service.create_profile(data)

        await db_service.delete_profile(profile.id)

        with pytest.raises(ProfileNotFoundError):
            await db_service.get_profile(profile.id)

    @pytest.mark.asyncio
    async def test_delete_profile_cascades_applications(self, db_service):
        """Test that deleting profile also deletes its applications."""
        profile = await db_service.create_profile(
            ProfileCreate(name="Test", full_name="User", profile_data={})
        )
        await db_service.create_application(
            ApplicationCreate(job_id="job1", profile_id=profile.id, job_text="Test job")
        )

        await db_service.delete_profile(profile.id)

        app = await db_service.get_application_by_job_id("job1")
        assert app is None

    @pytest.mark.asyncio
    async def test_activate_profile(self, db_service):
        """Test activating a profile."""
        p1 = await db_service.create_profile(
            ProfileCreate(name="P1", full_name="U1", profile_data={}, is_active=True)
        )
        p2 = await db_service.create_profile(
            ProfileCreate(name="P2", full_name="U2", profile_data={})
        )

        assert p1.is_active is True
        assert p2.is_active is False

        await db_service.activate_profile(p2.id)

        p1_refreshed = await db_service.get_profile(p1.id)
        p2_refreshed = await db_service.get_profile(p2.id)

        assert p1_refreshed.is_active is False
        assert p2_refreshed.is_active is True

    @pytest.mark.asyncio
    async def test_get_active_profile(self, db_service):
        """Test getting active profile."""
        await db_service.create_profile(
            ProfileCreate(name="Inactive", full_name="U1", profile_data={})
        )
        await db_service.create_profile(
            ProfileCreate(name="Active", full_name="U2", profile_data={}, is_active=True)
        )

        active = await db_service.get_active_profile()

        assert active is not None
        assert active.name == "Active"

    @pytest.mark.asyncio
    async def test_get_active_profile_none(self, db_service):
        """Test getting active profile when none exists."""
        await db_service.create_profile(
            ProfileCreate(name="Test", full_name="User", profile_data={})
        )

        active = await db_service.get_active_profile()

        assert active is None


# =============================================================================
# APPLICATION TESTS
# =============================================================================


class TestApplicationCRUD:
    """Application CRUD tests."""

    @pytest.mark.asyncio
    async def test_create_application(self, db_service):
        """Test creating an application."""
        profile = await db_service.create_profile(
            ProfileCreate(name="Test", full_name="User", profile_data={})
        )

        data = ApplicationCreate(
            job_id="abc12345",
            profile_id=profile.id,
            job_text="Software Engineer at Company...",
        )

        app = await db_service.create_application(data)

        assert app.job_id == "abc12345"
        assert app.profile_id == profile.id
        assert app.status == ApplicationStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_application(self, db_service):
        """Test getting application by ID."""
        profile = await db_service.create_profile(
            ProfileCreate(name="Test", full_name="User", profile_data={})
        )
        created = await db_service.create_application(
            ApplicationCreate(job_id="test123", profile_id=profile.id, job_text="Job...")
        )

        app = await db_service.get_application(created.id)

        assert app.id == created.id
        assert app.job_id == "test123"

    @pytest.mark.asyncio
    async def test_get_application_by_job_id(self, db_service):
        """Test getting application by job_id."""
        profile = await db_service.create_profile(
            ProfileCreate(name="Test", full_name="User", profile_data={})
        )

        await db_service.create_application(
            ApplicationCreate(job_id="xyz789", profile_id=profile.id, job_text="Job...")
        )

        app = await db_service.get_application_by_job_id("xyz789")

        assert app is not None
        assert app.job_id == "xyz789"

    @pytest.mark.asyncio
    async def test_get_application_by_job_id_not_found(self, db_service):
        """Test getting non-existent application returns None."""
        app = await db_service.get_application_by_job_id("nonexistent")
        assert app is None

    @pytest.mark.asyncio
    async def test_update_application(self, db_service):
        """Test updating an application."""
        profile = await db_service.create_profile(
            ProfileCreate(name="Test", full_name="User", profile_data={})
        )

        await db_service.create_application(
            ApplicationCreate(job_id="upd123", profile_id=profile.id, job_text="Job...")
        )

        updated = await db_service.update_application(
            "upd123",
            ApplicationUpdate(
                status=ApplicationStatus.COMPLETED,
                compatibility_score=85,
                job_title="Software Engineer",
            )
        )

        assert updated.status == ApplicationStatus.COMPLETED
        assert updated.compatibility_score == 85
        assert updated.job_title == "Software Engineer"

    @pytest.mark.asyncio
    async def test_update_application_with_analysis_data(self, db_service):
        """Test updating application with JSON analysis data."""
        profile = await db_service.create_profile(
            ProfileCreate(name="Test", full_name="User", profile_data={})
        )

        await db_service.create_application(
            ApplicationCreate(job_id="json123", profile_id=profile.id, job_text="Job...")
        )

        analysis = {"score": 85, "strengths": ["Python", "Django"]}
        updated = await db_service.update_application(
            "json123",
            ApplicationUpdate(analysis_data=analysis)
        )

        assert updated.analysis_data == analysis

    @pytest.mark.asyncio
    async def test_list_applications(self, db_service):
        """Test listing applications."""
        profile = await db_service.create_profile(
            ProfileCreate(name="Test", full_name="User", profile_data={})
        )

        await db_service.create_application(
            ApplicationCreate(job_id="list1", profile_id=profile.id, job_text="Job 1")
        )
        await db_service.create_application(
            ApplicationCreate(job_id="list2", profile_id=profile.id, job_text="Job 2")
        )

        apps, total = await db_service.list_applications()

        assert len(apps) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_list_applications_with_filter(self, db_service):
        """Test listing applications with filters."""
        profile = await db_service.create_profile(
            ProfileCreate(name="Test", full_name="User", profile_data={})
        )

        await db_service.create_application(
            ApplicationCreate(job_id="a1", profile_id=profile.id, job_text="Job 1")
        )
        await db_service.create_application(
            ApplicationCreate(job_id="a2", profile_id=profile.id, job_text="Job 2")
        )

        # Update one to completed
        await db_service.update_application("a1", ApplicationUpdate(status=ApplicationStatus.COMPLETED))

        # Filter by status
        completed, total = await db_service.list_applications(status=ApplicationStatus.COMPLETED)

        assert len(completed) == 1
        assert completed[0].job_id == "a1"

    @pytest.mark.asyncio
    async def test_list_applications_with_pagination(self, db_service):
        """Test listing applications with pagination."""
        profile = await db_service.create_profile(
            ProfileCreate(name="Test", full_name="User", profile_data={})
        )

        for i in range(5):
            await db_service.create_application(
                ApplicationCreate(job_id=f"page{i}", profile_id=profile.id, job_text=f"Job {i}")
            )

        apps, total = await db_service.list_applications(limit=2, offset=0)
        assert len(apps) == 2
        assert total == 5

        apps2, _ = await db_service.list_applications(limit=2, offset=2)
        assert len(apps2) == 2

    @pytest.mark.asyncio
    async def test_list_applications_by_profile(self, db_service):
        """Test listing applications filtered by profile."""
        profile1 = await db_service.create_profile(
            ProfileCreate(name="Profile1", full_name="User1", profile_data={})
        )
        profile2 = await db_service.create_profile(
            ProfileCreate(name="Profile2", full_name="User2", profile_data={})
        )

        await db_service.create_application(
            ApplicationCreate(job_id="p1a1", profile_id=profile1.id, job_text="Job")
        )
        await db_service.create_application(
            ApplicationCreate(job_id="p2a1", profile_id=profile2.id, job_text="Job")
        )

        apps1, total1 = await db_service.list_applications(profile_id=profile1.id)
        apps2, total2 = await db_service.list_applications(profile_id=profile2.id)

        assert len(apps1) == 1
        assert total1 == 1
        assert apps1[0].job_id == "p1a1"
        assert len(apps2) == 1
        assert total2 == 1

    @pytest.mark.asyncio
    async def test_delete_application(self, db_service):
        """Test deleting an application."""
        profile = await db_service.create_profile(
            ProfileCreate(name="Test", full_name="User", profile_data={})
        )
        await db_service.create_application(
            ApplicationCreate(job_id="del123", profile_id=profile.id, job_text="Job...")
        )

        await db_service.delete_application("del123")

        app = await db_service.get_application_by_job_id("del123")
        assert app is None

    @pytest.mark.asyncio
    async def test_get_profile_stats(self, db_service):
        """Test getting profile statistics."""
        profile = await db_service.create_profile(
            ProfileCreate(name="Test", full_name="User", profile_data={})
        )

        await db_service.create_application(
            ApplicationCreate(job_id="s1", profile_id=profile.id, job_text="Job")
        )
        await db_service.create_application(
            ApplicationCreate(job_id="s2", profile_id=profile.id, job_text="Job")
        )

        await db_service.update_application("s1", ApplicationUpdate(
            status=ApplicationStatus.COMPLETED, compatibility_score=80
        ))
        await db_service.update_application("s2", ApplicationUpdate(
            status=ApplicationStatus.COMPLETED, compatibility_score=90
        ))

        stats = await db_service.get_profile_stats(profile.id)

        assert stats["total_applications"] == 2
        assert stats["completed_applications"] == 2
        assert stats["avg_compatibility_score"] == 85.0

    @pytest.mark.asyncio
    async def test_get_profile_stats_empty(self, db_service):
        """Test getting stats for profile with no applications."""
        profile = await db_service.create_profile(
            ProfileCreate(name="Test", full_name="User", profile_data={})
        )

        stats = await db_service.get_profile_stats(profile.id)

        assert stats["total_applications"] == 0
        assert stats["completed_applications"] == 0
        assert stats["avg_compatibility_score"] is None


# =============================================================================
# SETTINGS TESTS
# =============================================================================


class TestSettings:
    """Settings tests."""

    @pytest.mark.asyncio
    async def test_get_settings_default(self, db_service):
        """Test getting default settings."""
        settings = await db_service.get_settings()

        assert settings.schema_version == 1
        assert settings.demo_data_loaded is False

    @pytest.mark.asyncio
    async def test_set_and_get_setting(self, db_service):
        """Test setting and getting a value."""
        await db_service.set_setting("demo_data_loaded", True)

        settings = await db_service.get_settings()

        assert settings.demo_data_loaded is True

    @pytest.mark.asyncio
    async def test_set_setting_overwrite(self, db_service):
        """Test overwriting a setting value."""
        await db_service.set_setting("active_profile_id", 1)
        await db_service.set_setting("active_profile_id", 2)

        settings = await db_service.get_settings()

        assert settings.active_profile_id == 2
