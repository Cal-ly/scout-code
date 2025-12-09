"""
Cost Tracker Service - Custom Exceptions
"""


class CostTrackerError(Exception):
    """Base exception for Cost Tracker service."""
    pass


class BudgetExceededError(CostTrackerError):
    """Raised when a budget limit has been exceeded."""
    pass


class CostTrackerInitializationError(CostTrackerError):
    """Raised when the service fails to initialize."""
    pass
