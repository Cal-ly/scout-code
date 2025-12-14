"""
Metrics Service

Performance and reliability tracking for local LLM inference on Raspberry Pi 5.

Tracks:
- Inference performance (duration, tokens/second, time-to-first-token)
- Reliability metrics (success rate, errors, retries, fallbacks)
- System metrics (CPU, memory, temperature)

Example:
    >>> from src.services.metrics_service import get_metrics_service
    >>>
    >>> metrics = await get_metrics_service()
    >>> entry = await metrics.record_metrics(
    ...     model="qwen2.5:3b",
    ...     duration_seconds=5.2,
    ...     prompt_tokens=100,
    ...     completion_tokens=50,
    ...     success=True,
    ...     module="analyzer",
    ... )
    >>> status = await metrics.get_status()
    >>> print(f"Today: {status.calls_today} calls, {status.success_rate_today:.1f}% success")
"""

from src.services.metrics_service.exceptions import (
    MetricsCollectionError,
    MetricsInitializationError,
    MetricsServiceError,
)
from src.services.metrics_service.models import (
    MetricsEntry,
    ModelStats,
    ModuleStats,
    PerformanceStatus,
    PerformanceSummary,
    SystemMetricsPoint,
)
from src.services.metrics_service.service import (
    MetricsService,
    get_metrics_service,
    reset_metrics_service,
)
from src.services.metrics_service.system_collector import (
    SystemCollector,
    SystemSnapshot,
    get_system_collector,
)

__all__ = [
    # Service
    "MetricsService",
    "get_metrics_service",
    "reset_metrics_service",
    # Models
    "MetricsEntry",
    "ModelStats",
    "ModuleStats",
    "PerformanceStatus",
    "PerformanceSummary",
    "SystemMetricsPoint",
    # System Collector
    "SystemCollector",
    "SystemSnapshot",
    "get_system_collector",
    # Exceptions
    "MetricsServiceError",
    "MetricsInitializationError",
    "MetricsCollectionError",
]
