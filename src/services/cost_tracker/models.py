"""
Cost Tracker Service - Data Models

Simplified PoC models for tracking LLM costs and enforcing budget limits.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class CostEntry(BaseModel):
    """
    Individual cost entry for a single API call.

    Attributes:
        timestamp: When the cost was incurred.
        service_name: Name of the service (e.g., "anthropic").
        model: Model used (e.g., "claude-3-5-haiku-20241022").
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.
        cost: Cost in USD.
        module: Which Scout module made the call.
        job_id: Optional job identifier.
    """

    timestamp: datetime = Field(default_factory=datetime.now)
    service_name: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: Decimal
    module: str | None = None
    job_id: str | None = None

    @field_validator('cost')
    @classmethod
    def validate_cost(cls, v: Decimal) -> Decimal:
        """Ensure cost is non-negative."""
        if v < 0:
            raise ValueError("Cost cannot be negative")
        return v

    @field_validator('input_tokens', 'output_tokens')
    @classmethod
    def validate_tokens(cls, v: int) -> int:
        """Ensure token counts are non-negative."""
        if v < 0:
            raise ValueError("Token count cannot be negative")
        return v


class BudgetStatus(BaseModel):
    """
    Current budget usage status.

    Attributes:
        daily_spent: Amount spent today in USD.
        daily_limit: Daily spending limit in USD.
        daily_remaining: Remaining daily budget.
        monthly_spent: Amount spent this month in USD.
        monthly_limit: Monthly spending limit in USD.
        monthly_remaining: Remaining monthly budget.
        can_proceed: Whether new requests can proceed.
        warning_message: Optional warning if approaching limit.
    """

    daily_spent: Decimal
    daily_limit: Decimal
    daily_remaining: Decimal
    monthly_spent: Decimal
    monthly_limit: Decimal
    monthly_remaining: Decimal
    can_proceed: bool
    warning_message: str | None = None

    @property
    def daily_percentage(self) -> float:
        """Percentage of daily budget used."""
        if self.daily_limit <= 0:
            return 0.0
        return float(self.daily_spent / self.daily_limit * 100)

    @property
    def monthly_percentage(self) -> float:
        """Percentage of monthly budget used."""
        if self.monthly_limit <= 0:
            return 0.0
        return float(self.monthly_spent / self.monthly_limit * 100)


class CostSummary(BaseModel):
    """
    Summary of costs for a time period.

    Attributes:
        period_start: Start of the period.
        period_end: End of the period.
        total_cost: Total cost in USD.
        total_tokens: Total tokens used.
        entry_count: Number of cost entries.
        average_cost_per_call: Average cost per API call.
    """

    period_start: datetime
    period_end: datetime
    total_cost: Decimal
    total_tokens: int
    entry_count: int

    @property
    def average_cost_per_call(self) -> Decimal:
        """Calculate average cost per API call."""
        if self.entry_count == 0:
            return Decimal("0")
        return self.total_cost / Decimal(str(self.entry_count))
