"""
Cost Tracker Service - Main Implementation

Simplified PoC service for tracking costs and enforcing budget limits.
Uses file-based persistence (JSON) instead of Redis/SQLAlchemy.
"""

import json
import logging
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from src.services.cost_tracker.exceptions import (
    BudgetExceededError,
    CostTrackerInitializationError,
)
from src.services.cost_tracker.models import (
    BudgetStatus,
    CostEntry,
    CostSummary,
)

logger = logging.getLogger(__name__)


class CostTrackerService:
    """
    Cost Tracker Service for monitoring and controlling LLM API costs.

    This is a simplified PoC implementation that:
    - Tracks costs per API call
    - Enforces daily and monthly budget limits
    - Persists data to JSON file
    - Provides budget status and reporting

    Attributes:
        daily_limit: Maximum daily spending in USD.
        monthly_limit: Maximum monthly spending in USD.
        data_file: Path to JSON file for persistence.

    Example:
        >>> tracker = CostTrackerService()
        >>> await tracker.initialize()
        >>> can_proceed = await tracker.can_proceed()
        >>> if can_proceed:
        >>>     await tracker.record_cost(...)
    """

    def __init__(
        self,
        daily_limit: float = 10.0,
        monthly_limit: float = 50.0,
        data_file: Path | None = None,
    ):
        """
        Initialize Cost Tracker Service.

        Args:
            daily_limit: Maximum daily spending in USD.
            monthly_limit: Maximum monthly spending in USD.
            data_file: Path to data file (defaults to data/cost_tracker.json).
        """
        self.daily_limit = Decimal(str(daily_limit))
        self.monthly_limit = Decimal(str(monthly_limit))
        self.data_file = data_file or Path("data/cost_tracker.json")

        self._initialized = False
        self._entries: list[CostEntry] = []
        self._current_day: date | None = None
        self._current_month: tuple | None = None  # (year, month)

    async def initialize(self) -> None:
        """
        Initialize the service.

        Creates data directory if needed and loads persisted state.
        Resets daily/monthly counters if needed.

        Raises:
            CostTrackerInitializationError: If initialization fails.
        """
        if self._initialized:
            logger.warning("Cost Tracker already initialized")
            return

        try:
            # Create data directory
            self.data_file.parent.mkdir(parents=True, exist_ok=True)

            # Load persisted data
            await self._load_from_file()

            # Check if we need to reset counters
            today = date.today()
            current_month = (today.year, today.month)

            if self._current_day != today:
                logger.info("New day detected, resetting daily counter")
                self._current_day = today

            if self._current_month != current_month:
                logger.info("New month detected, resetting monthly counter")
                self._current_month = current_month
                # Keep only current month's entries
                self._entries = [
                    e for e in self._entries
                    if (e.timestamp.year, e.timestamp.month) == current_month
                ]

            self._initialized = True
            logger.info("Cost Tracker initialized successfully")

        except Exception as e:
            error_msg = f"Failed to initialize Cost Tracker: {e}"
            logger.error(error_msg)
            raise CostTrackerInitializationError(error_msg) from e

    async def shutdown(self) -> None:
        """Gracefully shutdown the service and persist state."""
        if not self._initialized:
            return

        try:
            await self._save_to_file()
            self._initialized = False
            logger.info("Cost Tracker shut down successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def can_proceed(self) -> bool:
        """
        Check if a new operation can proceed within budget limits.

        Returns:
            True if within budget limits, False otherwise.
        """
        self._ensure_initialized()
        status = await self.get_budget_status()
        return status.can_proceed

    async def record_cost(
        self,
        service_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        module: str | None = None,
        job_id: str | None = None,
    ) -> CostEntry:
        """
        Record a cost entry.

        Args:
            service_name: Name of the service (e.g., "anthropic").
            model: Model identifier.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.
            cost: Cost in USD.
            module: Optional module name.
            job_id: Optional job identifier.

        Returns:
            The created cost entry.

        Raises:
            BudgetExceededError: If recording would exceed budget.
        """
        self._ensure_initialized()

        # Create entry
        entry = CostEntry(
            service_name=service_name,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=Decimal(str(cost)),
            module=module,
            job_id=job_id,
        )

        # Check if this would exceed budget
        status = await self.get_budget_status()
        daily_after = status.daily_spent + entry.cost
        monthly_after = status.monthly_spent + entry.cost

        if daily_after > self.daily_limit:
            raise BudgetExceededError(
                f"Daily budget exceeded: ${daily_after:.4f} > ${self.daily_limit:.2f}"
            )

        if monthly_after > self.monthly_limit:
            raise BudgetExceededError(
                f"Monthly budget exceeded: ${monthly_after:.4f} > ${self.monthly_limit:.2f}"
            )

        # Record entry
        self._entries.append(entry)

        # Persist
        await self._save_to_file()

        logger.info(
            f"Recorded cost: ${entry.cost:.4f} "
            f"({input_tokens} in + {output_tokens} out tokens) "
            f"from {service_name}/{model}"
        )

        return entry

    async def get_budget_status(self) -> BudgetStatus:
        """
        Get current budget status.

        Returns:
            Current budget usage and limits.
        """
        self._ensure_initialized()

        today = date.today()
        current_month = (today.year, today.month)

        # Calculate daily spent
        daily_spent = sum(
            (e.cost for e in self._entries if e.timestamp.date() == today),
            start=Decimal("0"),
        )

        # Calculate monthly spent
        monthly_spent = sum(
            (
                e.cost
                for e in self._entries
                if (e.timestamp.year, e.timestamp.month) == current_month
            ),
            start=Decimal("0"),
        )

        # Calculate remaining
        daily_remaining = max(Decimal("0"), self.daily_limit - daily_spent)
        monthly_remaining = max(Decimal("0"), self.monthly_limit - monthly_spent)

        # Determine if can proceed
        can_proceed = (daily_spent < self.daily_limit and
                       monthly_spent < self.monthly_limit)

        # Generate warning message
        warning_message = None
        daily_pct = (
            float(daily_spent / self.daily_limit * 100) if self.daily_limit > 0 else 0
        )
        monthly_pct = (
            float(monthly_spent / self.monthly_limit * 100)
            if self.monthly_limit > 0
            else 0
        )

        if daily_pct >= 80 or monthly_pct >= 80:
            warning_message = (
                f"Approaching budget limit: "
                f"{daily_pct:.1f}% daily, {monthly_pct:.1f}% monthly"
            )

        return BudgetStatus(
            daily_spent=daily_spent,
            daily_limit=self.daily_limit,
            daily_remaining=daily_remaining,
            monthly_spent=monthly_spent,
            monthly_limit=self.monthly_limit,
            monthly_remaining=monthly_remaining,
            can_proceed=can_proceed,
            warning_message=warning_message,
        )

    async def get_summary(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> CostSummary:
        """
        Get cost summary for a period.

        Args:
            start: Start of period (defaults to beginning of current month).
            end: End of period (defaults to now).

        Returns:
            Cost summary for the period.
        """
        self._ensure_initialized()

        # Default to current month
        if start is None:
            today = date.today()
            start = datetime(today.year, today.month, 1)

        if end is None:
            end = datetime.now()

        # Filter entries in period
        period_entries = [
            e for e in self._entries
            if start <= e.timestamp <= end
        ]

        # Calculate totals
        total_cost = sum((e.cost for e in period_entries), start=Decimal("0"))
        total_tokens = sum(
            (e.input_tokens + e.output_tokens for e in period_entries), start=0
        )

        return CostSummary(
            period_start=start,
            period_end=end,
            total_cost=total_cost,
            total_tokens=total_tokens,
            entry_count=len(period_entries),
        )

    async def _load_from_file(self) -> None:
        """Load state from JSON file."""
        if not self.data_file.exists():
            logger.info(f"No existing data file at {self.data_file}")
            return

        try:
            with open(self.data_file) as f:
                data = json.load(f)

            # Load entries
            self._entries = [
                CostEntry(
                    timestamp=datetime.fromisoformat(e['timestamp']),
                    service_name=e['service_name'],
                    model=e['model'],
                    input_tokens=e['input_tokens'],
                    output_tokens=e['output_tokens'],
                    cost=Decimal(e['cost']),
                    module=e.get('module'),
                    job_id=e.get('job_id'),
                )
                for e in data.get('entries', [])
            ]

            # Load state
            if data.get('current_day'):
                self._current_day = date.fromisoformat(data['current_day'])

            if data.get('current_month'):
                year, month = data['current_month']
                self._current_month = (year, month)

            logger.info(f"Loaded {len(self._entries)} entries from {self.data_file}")

        except Exception as e:
            logger.error(f"Error loading data file: {e}")
            # Continue with empty state rather than failing

    async def _save_to_file(self) -> None:
        """Save state to JSON file."""
        try:
            data = {
                'current_day': self._current_day.isoformat() if self._current_day else None,
                'current_month': list(self._current_month) if self._current_month else None,
                'entries': [
                    {
                        'timestamp': e.timestamp.isoformat(),
                        'service_name': e.service_name,
                        'model': e.model,
                        'input_tokens': e.input_tokens,
                        'output_tokens': e.output_tokens,
                        'cost': str(e.cost),
                        'module': e.module,
                        'job_id': e.job_id,
                    }
                    for e in self._entries
                ],
            }

            # Write atomically
            temp_file = self.data_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)

            temp_file.replace(self.data_file)

            logger.debug(f"Saved {len(self._entries)} entries to {self.data_file}")

        except Exception as e:
            logger.error(f"Error saving data file: {e}")
            raise

    def _ensure_initialized(self) -> None:
        """Ensure service is initialized."""
        if not self._initialized:
            raise RuntimeError(
                "Cost Tracker not initialized. Call initialize() first."
            )


# Global singleton instance
_cost_tracker_instance: CostTrackerService | None = None


async def get_cost_tracker() -> CostTrackerService:
    """
    Get or create the global Cost Tracker instance.

    Returns:
        Initialized Cost Tracker service.
    """
    global _cost_tracker_instance

    if _cost_tracker_instance is None:
        _cost_tracker_instance = CostTrackerService()
        await _cost_tracker_instance.initialize()

    return _cost_tracker_instance
