"""
Tests for Cost Tracker Service

Comprehensive test suite for the simplified PoC Cost Tracker.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path

from src.services.cost_tracker import (
    CostTrackerService,
    CostEntry,
    BudgetStatus,
    CostSummary,
    BudgetExceededError,
)


@pytest.fixture
def temp_data_file(tmp_path):
    """Provide a temporary data file path."""
    return tmp_path / "cost_tracker_test.json"


@pytest.fixture
def cost_tracker(temp_data_file):
    """Create an uninitialized cost tracker for testing."""
    return CostTrackerService(
        daily_limit=10.0,
        monthly_limit=50.0,
        data_file=temp_data_file,
    )


@pytest.fixture
async def initialized_tracker(cost_tracker):
    """Create and initialize a cost tracker."""
    await cost_tracker.initialize()
    yield cost_tracker
    await cost_tracker.shutdown()


class TestInitialization:
    """Tests for service initialization."""

    @pytest.mark.asyncio
    async def test_initialize_creates_data_directory(self, cost_tracker):
        """Should create data directory on initialization."""
        # Use a path that doesn't exist yet
        deep_path = Path("/tmp/scout_test/deep/nested/cost_tracker.json")
        tracker = CostTrackerService(data_file=deep_path)

        assert not deep_path.parent.exists()
        await tracker.initialize()
        assert deep_path.parent.exists()
        await tracker.shutdown()

        # Cleanup
        import shutil
        shutil.rmtree("/tmp/scout_test", ignore_errors=True)

    @pytest.mark.asyncio
    async def test_initialize_sets_current_dates(self, cost_tracker):
        """Should set current day and month on initialization."""
        await cost_tracker.initialize()

        today = date.today()
        assert cost_tracker._current_day == today
        assert cost_tracker._current_month == (today.year, today.month)

        await cost_tracker.shutdown()

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, cost_tracker):
        """Should handle multiple initialization calls gracefully."""
        await cost_tracker.initialize()
        await cost_tracker.initialize()  # Should not raise
        assert cost_tracker._initialized
        await cost_tracker.shutdown()

    @pytest.mark.asyncio
    async def test_initialize_loads_existing_data(self, initialized_tracker, temp_data_file):
        """Should load data from existing file."""
        # Record some cost
        await initialized_tracker.record_cost(
            service_name="anthropic",
            model="claude-3-5-haiku",
            input_tokens=100,
            output_tokens=50,
            cost=0.05,
        )
        await initialized_tracker.shutdown()

        # Create new instance and initialize
        new_tracker = CostTrackerService(data_file=temp_data_file)
        await new_tracker.initialize()

        # Should have loaded the entry
        assert len(new_tracker._entries) == 1
        assert new_tracker._entries[0].cost == Decimal("0.05")

        await new_tracker.shutdown()


class TestCostRecording:
    """Tests for recording costs."""

    @pytest.mark.asyncio
    async def test_record_cost_creates_entry(self, initialized_tracker):
        """Should create a cost entry with correct values."""
        entry = await initialized_tracker.record_cost(
            service_name="anthropic",
            model="claude-3-5-haiku",
            input_tokens=100,
            output_tokens=50,
            cost=0.05,
            module="rinser",
            job_id="job123",
        )

        assert entry.service_name == "anthropic"
        assert entry.model == "claude-3-5-haiku"
        assert entry.input_tokens == 100
        assert entry.output_tokens == 50
        assert entry.cost == Decimal("0.05")
        assert entry.module == "rinser"
        assert entry.job_id == "job123"
        assert isinstance(entry.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_record_cost_updates_totals(self, initialized_tracker):
        """Should update daily and monthly totals."""
        status_before = await initialized_tracker.get_budget_status()
        assert status_before.daily_spent == Decimal("0")

        await initialized_tracker.record_cost(
            service_name="anthropic",
            model="claude-3-5-haiku",
            input_tokens=100,
            output_tokens=50,
            cost=2.50,
        )

        status_after = await initialized_tracker.get_budget_status()
        assert status_after.daily_spent == Decimal("2.50")
        assert status_after.monthly_spent == Decimal("2.50")

    @pytest.mark.asyncio
    async def test_record_cost_multiple_entries(self, initialized_tracker):
        """Should handle multiple cost entries."""
        await initialized_tracker.record_cost("anthropic", "haiku", 100, 50, 1.0)
        await initialized_tracker.record_cost("anthropic", "haiku", 200, 100, 2.0)
        await initialized_tracker.record_cost("anthropic", "haiku", 150, 75, 1.5)

        status = await initialized_tracker.get_budget_status()
        assert status.daily_spent == Decimal("4.5")
        assert status.monthly_spent == Decimal("4.5")

    @pytest.mark.asyncio
    async def test_record_cost_persists_to_file(self, initialized_tracker, temp_data_file):
        """Should persist cost entries to file."""
        await initialized_tracker.record_cost("anthropic", "haiku", 100, 50, 0.05)

        assert temp_data_file.exists()

        # Verify file content
        import json
        with open(temp_data_file, 'r') as f:
            data = json.load(f)

        assert len(data['entries']) == 1
        assert data['entries'][0]['cost'] == "0.05"


class TestBudgetEnforcement:
    """Tests for budget limit enforcement."""

    @pytest.mark.asyncio
    async def test_exceeds_daily_limit(self, initialized_tracker):
        """Should raise error when daily limit exceeded."""
        # Daily limit is 10.0
        await initialized_tracker.record_cost("anthropic", "haiku", 1000, 500, 9.0)

        with pytest.raises(BudgetExceededError, match="Daily budget exceeded"):
            await initialized_tracker.record_cost("anthropic", "haiku", 200, 100, 2.0)

    @pytest.mark.asyncio
    async def test_exceeds_monthly_limit(self, temp_data_file):
        """Should raise error when monthly limit exceeded."""
        # Use higher daily limit to test monthly limit independently
        tracker = CostTrackerService(
            daily_limit=100.0,  # High enough to not interfere
            monthly_limit=50.0,
            data_file=temp_data_file,
        )
        await tracker.initialize()

        # Spend 49.0 (under monthly limit)
        for _ in range(5):
            await tracker.record_cost("anthropic", "haiku", 1000, 500, 9.8)

        # This would push us over 50.0 monthly
        with pytest.raises(BudgetExceededError, match="Monthly budget exceeded"):
            await tracker.record_cost("anthropic", "haiku", 200, 100, 2.0)

        await tracker.shutdown()

    @pytest.mark.asyncio
    async def test_can_proceed_within_budget(self, initialized_tracker):
        """Should return True when within budget."""
        assert await initialized_tracker.can_proceed()

        await initialized_tracker.record_cost("anthropic", "haiku", 100, 50, 1.0)
        assert await initialized_tracker.can_proceed()

    @pytest.mark.asyncio
    async def test_cannot_proceed_over_daily_budget(self, initialized_tracker):
        """Should return False when daily budget exceeded."""
        # Spend up to daily limit
        await initialized_tracker.record_cost("anthropic", "haiku", 1000, 500, 9.5)

        # Manually exceed the limit by modifying the entry
        initialized_tracker._entries[0].cost = Decimal("11.0")

        assert not await initialized_tracker.can_proceed()

    @pytest.mark.asyncio
    async def test_cannot_proceed_over_monthly_budget(self, temp_data_file):
        """Should return False when monthly budget exceeded."""
        # Use higher daily limit to test monthly limit independently
        tracker = CostTrackerService(
            daily_limit=100.0,  # High enough to not interfere
            monthly_limit=50.0,
            data_file=temp_data_file,
        )
        await tracker.initialize()

        # Spend up to near monthly limit
        for _ in range(5):
            await tracker.record_cost("anthropic", "haiku", 1000, 500, 9.0)

        # Manually exceed monthly to test
        tracker._entries[0].cost = Decimal("60.0")

        assert not await tracker.can_proceed()

        await tracker.shutdown()


class TestBudgetStatus:
    """Tests for budget status reporting."""

    @pytest.mark.asyncio
    async def test_budget_status_initial_state(self, initialized_tracker):
        """Should show zero usage initially."""
        status = await initialized_tracker.get_budget_status()

        assert status.daily_spent == Decimal("0")
        assert status.daily_limit == Decimal("10")
        assert status.daily_remaining == Decimal("10")
        assert status.monthly_spent == Decimal("0")
        assert status.monthly_limit == Decimal("50")
        assert status.monthly_remaining == Decimal("50")
        assert status.can_proceed is True
        assert status.warning_message is None

    @pytest.mark.asyncio
    async def test_budget_status_after_spending(self, initialized_tracker):
        """Should reflect spending in status."""
        await initialized_tracker.record_cost("anthropic", "haiku", 100, 50, 3.50)

        status = await initialized_tracker.get_budget_status()

        assert status.daily_spent == Decimal("3.50")
        assert status.daily_remaining == Decimal("6.50")
        assert status.monthly_spent == Decimal("3.50")
        assert status.monthly_remaining == Decimal("46.50")

    @pytest.mark.asyncio
    async def test_budget_status_warning_message(self, initialized_tracker):
        """Should show warning when approaching limit."""
        # Spend 85% of daily budget
        await initialized_tracker.record_cost("anthropic", "haiku", 1000, 500, 8.50)

        status = await initialized_tracker.get_budget_status()

        assert status.warning_message is not None
        assert "Approaching budget limit" in status.warning_message

    @pytest.mark.asyncio
    async def test_budget_status_percentage_properties(self, initialized_tracker):
        """Should calculate percentage usage correctly."""
        await initialized_tracker.record_cost("anthropic", "haiku", 1000, 500, 5.0)

        status = await initialized_tracker.get_budget_status()

        assert status.daily_percentage == 50.0
        assert status.monthly_percentage == 10.0


class TestCostSummary:
    """Tests for cost summary reporting."""

    @pytest.mark.asyncio
    async def test_summary_empty(self, initialized_tracker):
        """Should handle empty period."""
        summary = await initialized_tracker.get_summary()

        assert summary.total_cost == Decimal("0")
        assert summary.total_tokens == 0
        assert summary.entry_count == 0
        assert summary.average_cost_per_call == Decimal("0")

    @pytest.mark.asyncio
    async def test_summary_with_entries(self, initialized_tracker):
        """Should calculate summary correctly."""
        await initialized_tracker.record_cost("anthropic", "haiku", 100, 50, 1.0)
        await initialized_tracker.record_cost("anthropic", "haiku", 200, 100, 2.0)
        await initialized_tracker.record_cost("anthropic", "haiku", 150, 75, 1.5)

        summary = await initialized_tracker.get_summary()

        assert summary.total_cost == Decimal("4.5")
        assert summary.total_tokens == 675  # (100+50) + (200+100) + (150+75)
        assert summary.entry_count == 3
        assert summary.average_cost_per_call == Decimal("1.5")

    @pytest.mark.asyncio
    async def test_summary_custom_period(self, initialized_tracker):
        """Should filter by custom date range."""
        # Record entry today
        await initialized_tracker.record_cost("anthropic", "haiku", 100, 50, 1.0)

        # Summary for yesterday (should be empty)
        yesterday = datetime.now() - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0)
        end = yesterday.replace(hour=23, minute=59, second=59)

        summary = await initialized_tracker.get_summary(start=start, end=end)
        assert summary.entry_count == 0

        # Summary including today
        today = datetime.now()
        start = today.replace(hour=0, minute=0, second=0)

        summary = await initialized_tracker.get_summary(start=start)
        assert summary.entry_count == 1


class TestPersistence:
    """Tests for data persistence."""

    @pytest.mark.asyncio
    async def test_persistence_across_restarts(self, temp_data_file):
        """Should persist and restore state across restarts."""
        # First session
        tracker1 = CostTrackerService(data_file=temp_data_file)
        await tracker1.initialize()
        await tracker1.record_cost("anthropic", "haiku", 100, 50, 2.50)
        await tracker1.record_cost("anthropic", "haiku", 200, 100, 3.75)
        await tracker1.shutdown()

        # Second session
        tracker2 = CostTrackerService(data_file=temp_data_file)
        await tracker2.initialize()

        status = await tracker2.get_budget_status()
        assert status.daily_spent == Decimal("6.25")
        assert len(tracker2._entries) == 2

        await tracker2.shutdown()

    @pytest.mark.asyncio
    async def test_atomic_file_writes(self, initialized_tracker, temp_data_file):
        """Should write files atomically to prevent corruption."""
        await initialized_tracker.record_cost("anthropic", "haiku", 100, 50, 1.0)

        # File should exist and be valid JSON
        assert temp_data_file.exists()
        import json
        with open(temp_data_file, 'r') as f:
            data = json.load(f)  # Should not raise

        assert 'entries' in data


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_requires_initialization(self, cost_tracker):
        """Should raise error if not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            await cost_tracker.can_proceed()

    @pytest.mark.asyncio
    async def test_negative_cost_rejected(self):
        """Should reject negative costs."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CostEntry(
                service_name="test",
                model="test",
                input_tokens=100,
                output_tokens=50,
                cost=Decimal("-1.0"),  # Negative!
            )

    @pytest.mark.asyncio
    async def test_negative_tokens_rejected(self):
        """Should reject negative token counts."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CostEntry(
                service_name="test",
                model="test",
                input_tokens=-100,  # Negative!
                output_tokens=50,
                cost=Decimal("1.0"),
            )

    @pytest.mark.asyncio
    async def test_handles_missing_data_file_gracefully(self, initialized_tracker):
        """Should handle missing data file without crashing."""
        # Service initializes even without existing file
        status = await initialized_tracker.get_budget_status()
        assert status.daily_spent == Decimal("0")

    @pytest.mark.asyncio
    async def test_zero_budget_limits(self, temp_data_file):
        """Should handle zero budget limits."""
        tracker = CostTrackerService(
            daily_limit=0.0,
            monthly_limit=0.0,
            data_file=temp_data_file,
        )
        await tracker.initialize()

        status = await tracker.get_budget_status()
        assert status.daily_limit == Decimal("0")
        assert status.can_proceed is False  # Can't proceed with zero budget

        await tracker.shutdown()
