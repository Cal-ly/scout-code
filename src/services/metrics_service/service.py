"""
Metrics Service - Main Implementation

Tracks LLM inference performance, reliability, and system metrics.
Designed for local Ollama inference on Raspberry Pi 5.

Uses file-based persistence (JSON) with 30-day retention and archival.
Includes background collection of system metrics for time-series graphs.
"""

import asyncio
import json
import logging
import statistics
from datetime import date, datetime, timedelta
from pathlib import Path

from src.services.metrics_service.exceptions import (
    MetricsInitializationError,
)
from src.services.metrics_service.models import (
    MetricsEntry,
    ModelStats,
    ModuleStats,
    PerformanceStatus,
    PerformanceSummary,
    SystemMetricsPoint,
)
from src.services.metrics_service.system_collector import (
    THROTTLING_THRESHOLD,
    SystemCollector,
)

logger = logging.getLogger(__name__)

# Default retention period in days
DEFAULT_RETENTION_DAYS = 30

# System metrics collection interval (seconds)
SYSTEM_METRICS_INTERVAL = 10

# Maximum age of system metrics data (hours)
SYSTEM_METRICS_MAX_AGE_HOURS = 24


class MetricsService:
    """
    Metrics Service for tracking local LLM inference performance.

    Tracks:
    - Inference performance (duration, tokens/second)
    - Reliability (success rate, errors, retries, fallbacks)
    - System metrics (CPU, memory, temperature)

    Data is stored in monthly JSON files with automatic archival
    of entries older than the retention period.

    Attributes:
        data_dir: Directory for metrics data files.
        retention_days: Days to keep active data (default: 30).

    Example:
        >>> service = MetricsService()
        >>> await service.initialize()
        >>> entry = await service.record_metrics(
        ...     model="qwen2.5:3b",
        ...     duration_seconds=5.2,
        ...     prompt_tokens=100,
        ...     completion_tokens=50,
        ...     success=True,
        ... )
        >>> status = await service.get_status()
    """

    def __init__(
        self,
        data_dir: Path | None = None,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        enable_system_metrics: bool = True,
        system_metrics_interval: int = SYSTEM_METRICS_INTERVAL,
    ) -> None:
        """
        Initialize Metrics Service.

        Args:
            data_dir: Directory for data files (defaults to data/metrics).
            retention_days: Days to keep active data before archiving.
            enable_system_metrics: Whether to collect system metrics.
            system_metrics_interval: Interval for background collection (seconds).
        """
        self.data_dir = data_dir or Path("data/metrics")
        self.retention_days = retention_days
        self._enable_system_metrics = enable_system_metrics
        self._system_metrics_interval = system_metrics_interval

        self._initialized = False
        self._entries: list[MetricsEntry] = []
        self._current_month: tuple[int, int] | None = None
        self._system_collector: SystemCollector | None = None

        # System metrics time-series
        self._system_metrics_points: list[SystemMetricsPoint] = []
        self._collection_task: asyncio.Task | None = None
        self._stop_collection = False

    async def initialize(self) -> None:
        """
        Initialize the service.

        Creates data directories, loads persisted state, archives old data,
        and starts background system metrics collection.

        Raises:
            MetricsInitializationError: If initialization fails.
        """
        if self._initialized:
            logger.warning("Metrics Service already initialized")
            return

        try:
            # Create data directories
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._archive_dir.mkdir(parents=True, exist_ok=True)

            # Initialize system collector if enabled
            if self._enable_system_metrics:
                self._system_collector = SystemCollector()

            # Set current month
            today = date.today()
            self._current_month = (today.year, today.month)

            # Load current month's data
            await self._load_current_month()

            # Load system metrics time-series
            await self._load_system_metrics()

            # Archive old entries
            await self._archive_old_data()

            self._initialized = True

            # Start background collection task
            if self._enable_system_metrics:
                self._stop_collection = False
                self._collection_task = asyncio.create_task(
                    self._collect_system_metrics_loop()
                )
                logger.info(
                    f"Started system metrics collection "
                    f"(interval: {self._system_metrics_interval}s)"
                )

            logger.info(
                f"Metrics Service initialized with {len(self._entries)} entries, "
                f"{len(self._system_metrics_points)} system metrics points"
            )

        except Exception as e:
            error_msg = f"Failed to initialize Metrics Service: {e}"
            logger.error(error_msg)
            raise MetricsInitializationError(error_msg) from e

    async def shutdown(self) -> None:
        """Gracefully shutdown the service and persist state."""
        if not self._initialized:
            return

        try:
            # Stop background collection task
            if self._collection_task is not None:
                self._stop_collection = True
                self._collection_task.cancel()
                try:
                    await self._collection_task
                except asyncio.CancelledError:
                    pass
                self._collection_task = None
                logger.debug("Stopped system metrics collection task")

            # Save data
            await self._save_current_month()
            await self._save_system_metrics()

            self._initialized = False
            logger.info("Metrics Service shut down successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    @property
    def _archive_dir(self) -> Path:
        """Path to archive directory."""
        return self.data_dir / "archive"

    def _get_month_file(self, year: int, month: int) -> Path:
        """Get path to a month's data file."""
        return self.data_dir / f"metrics_{year}_{month:02d}.json"

    def _get_archive_file(self, year: int, month: int) -> Path:
        """Get path to an archived month's data file."""
        return self._archive_dir / f"metrics_{year}_{month:02d}.json"

    async def record_metrics(
        self,
        model: str,
        duration_seconds: float,
        prompt_tokens: int,
        completion_tokens: int,
        success: bool,
        module: str | None = None,
        job_id: str | None = None,
        error_type: str | None = None,
        retry_count: int = 0,
        fallback_used: bool = False,
    ) -> MetricsEntry:
        """
        Record an inference metrics entry.

        Captures performance, reliability, and optionally system metrics.

        Args:
            model: Model identifier (e.g., "qwen2.5:3b").
            duration_seconds: Total inference time.
            prompt_tokens: Number of input tokens.
            completion_tokens: Number of output tokens.
            success: Whether the inference succeeded.
            module: Optional module name (e.g., "rinser", "analyzer").
            job_id: Optional job identifier for correlation.
            error_type: Type of error if failed.
            retry_count: Number of retries before success/failure.
            fallback_used: Whether fallback model was used.

        Returns:
            The created MetricsEntry.
        """
        self._ensure_initialized()

        # Collect system metrics if enabled
        system_metrics: dict[str, float | None] = {}
        if self._system_collector is not None:
            system_metrics = self._system_collector.collect_dict()

        # Create entry
        entry = MetricsEntry(
            model=model,
            module=module,
            job_id=job_id,
            duration_seconds=duration_seconds,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            success=success,
            error_type=error_type,
            retry_count=retry_count,
            fallback_used=fallback_used,
            cpu_percent=system_metrics.get("cpu_percent"),
            memory_mb=system_metrics.get("memory_mb"),
            temperature_c=system_metrics.get("temperature_c"),
        )

        # Check if we've crossed into a new month
        entry_month = (entry.timestamp.year, entry.timestamp.month)
        if self._current_month != entry_month:
            # Save current month and start new one
            await self._save_current_month()
            self._current_month = entry_month
            self._entries = []

        # Add entry
        self._entries.append(entry)

        # Persist
        await self._save_current_month()

        logger.info(
            f"Recorded metrics: {model} "
            f"({completion_tokens} tokens in {duration_seconds:.2f}s = "
            f"{entry.tokens_per_second:.1f} tok/s) "
            f"{'OK' if success else f'FAIL: {error_type}'}"
        )

        return entry

    async def get_status(self) -> PerformanceStatus:
        """
        Get current performance status.

        Returns today's statistics and health indicators.

        Returns:
            PerformanceStatus with today's metrics.
        """
        self._ensure_initialized()

        today = date.today()
        today_entries = [e for e in self._entries if e.timestamp.date() == today]

        # Calculate today's stats
        calls_today = len(today_entries)
        successful_today = [e for e in today_entries if e.success]
        success_rate_today = (
            (len(successful_today) / calls_today * 100) if calls_today > 0 else 0.0
        )

        # Average tokens per second (successful calls only)
        tps_values = [e.tokens_per_second for e in successful_today if e.duration_seconds > 0]
        avg_tps = statistics.mean(tps_values) if tps_values else 0.0

        # Average duration (successful calls only)
        durations = [e.duration_seconds for e in successful_today]
        avg_duration = statistics.mean(durations) if durations else 0.0

        # Primary model success rate (entries where fallback was NOT used)
        primary_entries = [e for e in today_entries if not e.fallback_used]
        primary_successful = [e for e in primary_entries if e.success]
        primary_success_rate = (
            (len(primary_successful) / len(primary_entries) * 100)
            if primary_entries
            else 0.0
        )

        # Fallback usage rate
        fallback_entries = [e for e in today_entries if e.fallback_used]
        fallback_rate = (
            (len(fallback_entries) / calls_today * 100) if calls_today > 0 else 0.0
        )

        # Current system metrics
        current_cpu: float | None = None
        current_memory: float | None = None
        current_temp: float | None = None
        throttling_warning = False
        if self._system_collector is not None:
            current_cpu = self._system_collector.get_cpu_percent()
            current_memory = self._system_collector.get_memory_percent()
            current_temp = self._system_collector.get_temperature()
            throttling_warning = self._system_collector.is_throttling_risk()

        # Performance trend (compare last hour to previous hour)
        trend = await self._calculate_trend()

        return PerformanceStatus(
            calls_today=calls_today,
            success_rate_today=success_rate_today,
            avg_tokens_per_second=avg_tps,
            avg_duration_seconds=avg_duration,
            primary_model_success_rate=primary_success_rate,
            fallback_usage_rate=fallback_rate,
            current_cpu_percent=current_cpu,
            current_memory_percent=current_memory,
            current_temperature=current_temp,
            throttling_warning=throttling_warning,
            performance_trend=trend,
        )

    async def get_summary(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> PerformanceSummary:
        """
        Get performance summary for a time period.

        Args:
            start: Start of period (defaults to start of current month).
            end: End of period (defaults to now).

        Returns:
            PerformanceSummary with comprehensive statistics.
        """
        self._ensure_initialized()

        # Default to current month
        if start is None:
            today = date.today()
            start = datetime(today.year, today.month, 1)

        if end is None:
            end = datetime.now()

        # Filter entries in period
        period_entries = [e for e in self._entries if start <= e.timestamp <= end]

        if not period_entries:
            return PerformanceSummary(
                period_start=start,
                period_end=end,
            )

        # Basic counts
        total_calls = len(period_entries)
        successful_entries = [e for e in period_entries if e.success]
        successful_calls = len(successful_entries)
        total_tokens = sum(e.total_tokens for e in period_entries)

        # Performance metrics (successful calls only)
        durations = [e.duration_seconds for e in successful_entries]
        tps_values = [e.tokens_per_second for e in successful_entries if e.duration_seconds > 0]

        avg_tps = statistics.mean(tps_values) if tps_values else 0.0
        median_duration = statistics.median(durations) if durations else 0.0

        # P95 duration
        p95_duration = 0.0
        if durations:
            sorted_durations = sorted(durations)
            p95_index = int(len(sorted_durations) * 0.95)
            p95_duration = sorted_durations[min(p95_index, len(sorted_durations) - 1)]

        # Success rate
        success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0.0

        # Error breakdown
        error_breakdown: dict[str, int] = {}
        for entry in period_entries:
            if not entry.success and entry.error_type:
                error_breakdown[entry.error_type] = (
                    error_breakdown.get(entry.error_type, 0) + 1
                )

        # Fallback rate
        fallback_entries = [e for e in period_entries if e.fallback_used]
        fallback_rate = (len(fallback_entries) / total_calls * 100) if total_calls > 0 else 0.0

        # Model stats
        model_stats = await self._calculate_model_stats(period_entries)

        # Module stats
        module_stats = await self._calculate_module_stats(period_entries)

        # System metrics averages
        cpu_values = [e.cpu_percent for e in period_entries if e.cpu_percent is not None]
        mem_values = [e.memory_mb for e in period_entries if e.memory_mb is not None]
        temp_values = [e.temperature_c for e in period_entries if e.temperature_c is not None]

        return PerformanceSummary(
            period_start=start,
            period_end=end,
            total_calls=total_calls,
            total_tokens=total_tokens,
            successful_calls=successful_calls,
            avg_tokens_per_second=avg_tps,
            median_duration_seconds=median_duration,
            p95_duration_seconds=p95_duration,
            success_rate=success_rate,
            error_breakdown=error_breakdown,
            fallback_rate=fallback_rate,
            model_stats={name: stats.model_dump() for name, stats in model_stats.items()},
            module_stats={name: stats.model_dump() for name, stats in module_stats.items()},
            avg_cpu_percent=statistics.mean(cpu_values) if cpu_values else None,
            avg_memory_mb=statistics.mean(mem_values) if mem_values else None,
            avg_temperature_c=statistics.mean(temp_values) if temp_values else None,
        )

    async def get_model_comparison(self) -> dict[str, ModelStats]:
        """
        Compare performance between models.

        Returns per-model statistics for all models in the current period.

        Returns:
            Dictionary mapping model name to ModelStats.
        """
        self._ensure_initialized()
        return await self._calculate_model_stats(self._entries)

    async def _calculate_model_stats(
        self, entries: list[MetricsEntry]
    ) -> dict[str, ModelStats]:
        """Calculate per-model statistics."""
        model_entries: dict[str, list[MetricsEntry]] = {}

        for entry in entries:
            if entry.model not in model_entries:
                model_entries[entry.model] = []
            model_entries[entry.model].append(entry)

        stats: dict[str, ModelStats] = {}
        for model_name, model_list in model_entries.items():
            successful = [e for e in model_list if e.success]
            total_tokens = sum(e.total_tokens for e in model_list)
            total_duration = sum(e.duration_seconds for e in successful)

            # Error breakdown
            error_breakdown: dict[str, int] = {}
            for entry in model_list:
                if not entry.success and entry.error_type:
                    error_breakdown[entry.error_type] = (
                        error_breakdown.get(entry.error_type, 0) + 1
                    )

            # Average TPS
            tps_values = [e.tokens_per_second for e in successful if e.duration_seconds > 0]
            avg_tps = statistics.mean(tps_values) if tps_values else 0.0

            stats[model_name] = ModelStats(
                model_name=model_name,
                total_calls=len(model_list),
                success_count=len(successful),
                total_tokens=total_tokens,
                total_duration_seconds=total_duration,
                avg_tokens_per_second=avg_tps,
                error_breakdown=error_breakdown,
            )

        return stats

    async def _calculate_module_stats(
        self, entries: list[MetricsEntry]
    ) -> dict[str, ModuleStats]:
        """Calculate per-module statistics."""
        module_entries: dict[str, list[MetricsEntry]] = {}

        for entry in entries:
            module_name = entry.module or "unknown"
            if module_name not in module_entries:
                module_entries[module_name] = []
            module_entries[module_name].append(entry)

        stats: dict[str, ModuleStats] = {}
        for module_name, module_list in module_entries.items():
            successful = [e for e in module_list if e.success]
            total_duration = sum(e.duration_seconds for e in successful)

            # Average TPS
            tps_values = [e.tokens_per_second for e in successful if e.duration_seconds > 0]
            avg_tps = statistics.mean(tps_values) if tps_values else 0.0

            stats[module_name] = ModuleStats(
                module_name=module_name,
                total_calls=len(module_list),
                success_count=len(successful),
                total_duration_seconds=total_duration,
                avg_tokens_per_second=avg_tps,
            )

        return stats

    async def _calculate_trend(self) -> str:
        """
        Calculate performance trend based on recent data.

        Compares last hour to previous hour.

        Returns:
            "improving", "stable", or "degrading"
        """
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        two_hours_ago = now - timedelta(hours=2)

        # Last hour
        last_hour = [
            e for e in self._entries
            if one_hour_ago <= e.timestamp <= now and e.success
        ]

        # Previous hour
        prev_hour = [
            e for e in self._entries
            if two_hours_ago <= e.timestamp < one_hour_ago and e.success
        ]

        if not last_hour or not prev_hour:
            return "stable"

        # Compare average TPS
        last_tps = statistics.mean(
            [e.tokens_per_second for e in last_hour if e.duration_seconds > 0]
        ) if last_hour else 0

        prev_tps = statistics.mean(
            [e.tokens_per_second for e in prev_hour if e.duration_seconds > 0]
        ) if prev_hour else 0

        if prev_tps == 0:
            return "stable"

        change_pct = ((last_tps - prev_tps) / prev_tps) * 100

        if change_pct > 10:
            return "improving"
        elif change_pct < -10:
            return "degrading"
        else:
            return "stable"

    async def _load_current_month(self) -> None:
        """Load current month's data from file."""
        if self._current_month is None:
            return

        year, month = self._current_month
        data_file = self._get_month_file(year, month)

        if not data_file.exists():
            logger.debug(f"No existing data file at {data_file}")
            return

        try:
            with open(data_file) as f:
                data = json.load(f)

            self._entries = [
                MetricsEntry(
                    timestamp=datetime.fromisoformat(e["timestamp"]),
                    model=e["model"],
                    module=e.get("module"),
                    job_id=e.get("job_id"),
                    duration_seconds=e["duration_seconds"],
                    prompt_tokens=e["prompt_tokens"],
                    completion_tokens=e["completion_tokens"],
                    success=e["success"],
                    error_type=e.get("error_type"),
                    retry_count=e.get("retry_count", 0),
                    fallback_used=e.get("fallback_used", False),
                    cpu_percent=e.get("cpu_percent"),
                    memory_mb=e.get("memory_mb"),
                    temperature_c=e.get("temperature_c"),
                )
                for e in data.get("entries", [])
            ]

            logger.info(f"Loaded {len(self._entries)} entries from {data_file}")

        except Exception as e:
            logger.error(f"Error loading data file: {e}")
            # Continue with empty state

    async def _save_current_month(self) -> None:
        """Save current month's data to file."""
        if self._current_month is None:
            return

        year, month = self._current_month
        data_file = self._get_month_file(year, month)

        try:
            data = {
                "month": f"{year}-{month:02d}",
                "entries": [
                    {
                        "timestamp": e.timestamp.isoformat(),
                        "model": e.model,
                        "module": e.module,
                        "job_id": e.job_id,
                        "duration_seconds": e.duration_seconds,
                        "prompt_tokens": e.prompt_tokens,
                        "completion_tokens": e.completion_tokens,
                        "success": e.success,
                        "error_type": e.error_type,
                        "retry_count": e.retry_count,
                        "fallback_used": e.fallback_used,
                        "cpu_percent": e.cpu_percent,
                        "memory_mb": e.memory_mb,
                        "temperature_c": e.temperature_c,
                    }
                    for e in self._entries
                ],
            }

            # Atomic write using temp file
            temp_file = data_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)

            temp_file.replace(data_file)
            logger.debug(f"Saved {len(self._entries)} entries to {data_file}")

        except Exception as e:
            logger.error(f"Error saving data file: {e}")
            raise

    async def _archive_old_data(self) -> None:
        """Archive entries older than retention period."""
        if self._current_month is None:
            return

        cutoff = date.today() - timedelta(days=self.retention_days)

        # Find old entries to archive
        old_entries = [
            e for e in self._entries if e.timestamp.date() < cutoff
        ]

        if not old_entries:
            return

        # Group by month
        monthly_archives: dict[tuple[int, int], list[MetricsEntry]] = {}
        for entry in old_entries:
            month_key = (entry.timestamp.year, entry.timestamp.month)
            if month_key not in monthly_archives:
                monthly_archives[month_key] = []
            monthly_archives[month_key].append(entry)

        # Archive each month's data
        for (year, month), entries in monthly_archives.items():
            archive_file = self._get_archive_file(year, month)

            # Load existing archive if present
            existing: list[dict] = []
            if archive_file.exists():
                try:
                    with open(archive_file) as f:
                        existing = json.load(f).get("entries", [])
                except Exception:
                    pass

            # Add new entries
            new_entries = [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "model": e.model,
                    "module": e.module,
                    "job_id": e.job_id,
                    "duration_seconds": e.duration_seconds,
                    "prompt_tokens": e.prompt_tokens,
                    "completion_tokens": e.completion_tokens,
                    "success": e.success,
                    "error_type": e.error_type,
                    "retry_count": e.retry_count,
                    "fallback_used": e.fallback_used,
                    "cpu_percent": e.cpu_percent,
                    "memory_mb": e.memory_mb,
                    "temperature_c": e.temperature_c,
                }
                for e in entries
            ]

            # Merge and save
            all_entries = existing + new_entries
            archive_data = {
                "month": f"{year}-{month:02d}",
                "archived_at": datetime.now().isoformat(),
                "entries": all_entries,
            }

            with open(archive_file, "w") as f:
                json.dump(archive_data, f, indent=2)

            logger.info(f"Archived {len(entries)} entries to {archive_file}")

        # Remove archived entries from active data
        self._entries = [e for e in self._entries if e.timestamp.date() >= cutoff]
        await self._save_current_month()

    # =========================================================================
    # SYSTEM METRICS TIME-SERIES
    # =========================================================================

    @property
    def _system_metrics_file(self) -> Path:
        """Path to system metrics time-series file."""
        return self.data_dir / "system_metrics.json"

    async def _collect_system_metrics_loop(self) -> None:
        """
        Background task that collects system metrics periodically.

        Runs until shutdown() is called or the task is cancelled.
        Saves to disk every 5 minutes to ensure persistence.
        """
        save_counter = 0
        save_interval = 30  # Save every 30 collections (~5 min at 10s interval)

        while not self._stop_collection:
            try:
                # Collect metrics
                if self._system_collector is not None:
                    point = SystemMetricsPoint(
                        timestamp=datetime.now(),
                        cpu_percent=self._system_collector.get_cpu_percent(),
                        memory_percent=self._system_collector.get_memory_percent(),
                        memory_mb=self._system_collector.get_memory_mb(),
                        temperature_c=self._system_collector.get_temperature(),
                    )
                    self._system_metrics_points.append(point)

                    # Prune old data
                    await self._prune_old_system_metrics()

                    # Periodic save
                    save_counter += 1
                    if save_counter >= save_interval:
                        await self._save_system_metrics()
                        save_counter = 0

                # Wait for next collection
                await asyncio.sleep(self._system_metrics_interval)

            except asyncio.CancelledError:
                # Task cancelled, exit gracefully
                break
            except Exception as e:
                logger.warning(f"Error in system metrics collection: {e}")
                await asyncio.sleep(self._system_metrics_interval)

    async def _prune_old_system_metrics(self) -> None:
        """Remove system metrics older than max age."""
        cutoff = datetime.now() - timedelta(hours=SYSTEM_METRICS_MAX_AGE_HOURS)
        self._system_metrics_points = [
            p for p in self._system_metrics_points if p.timestamp >= cutoff
        ]

    async def _load_system_metrics(self) -> None:
        """Load system metrics time-series from file."""
        if not self._system_metrics_file.exists():
            logger.debug("No existing system metrics file")
            return

        try:
            with open(self._system_metrics_file) as f:
                data = json.load(f)

            # Load points
            self._system_metrics_points = [
                SystemMetricsPoint(
                    timestamp=datetime.fromisoformat(p["timestamp"]),
                    cpu_percent=p.get("cpu_percent"),
                    memory_percent=p.get("memory_percent"),
                    memory_mb=p.get("memory_mb"),
                    temperature_c=p.get("temperature_c"),
                )
                for p in data.get("points", [])
            ]

            # Prune old data on load
            await self._prune_old_system_metrics()

            logger.info(
                f"Loaded {len(self._system_metrics_points)} system metrics points"
            )

        except Exception as e:
            logger.error(f"Error loading system metrics file: {e}")
            # Continue with empty state

    async def _save_system_metrics(self) -> None:
        """Save system metrics time-series to file."""
        try:
            data = {
                "updated_at": datetime.now().isoformat(),
                "interval_seconds": self._system_metrics_interval,
                "max_age_hours": SYSTEM_METRICS_MAX_AGE_HOURS,
                "points": [
                    {
                        "timestamp": p.timestamp.isoformat(),
                        "cpu_percent": p.cpu_percent,
                        "memory_percent": p.memory_percent,
                        "memory_mb": p.memory_mb,
                        "temperature_c": p.temperature_c,
                    }
                    for p in self._system_metrics_points
                ],
            }

            # Atomic write using temp file
            temp_file = self._system_metrics_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(data, f)

            temp_file.replace(self._system_metrics_file)
            logger.debug(
                f"Saved {len(self._system_metrics_points)} system metrics points"
            )

        except Exception as e:
            logger.error(f"Error saving system metrics file: {e}")
            raise

    async def get_system_metrics_history(
        self, minutes: int = 15
    ) -> list[SystemMetricsPoint]:
        """
        Get system metrics history for graphing.

        Args:
            minutes: Number of minutes of history to return (default 15, max 1440).

        Returns:
            List of SystemMetricsPoint objects sorted by timestamp ascending.
        """
        self._ensure_initialized()

        # Limit to max 24 hours
        minutes = min(minutes, 1440)
        cutoff = datetime.now() - timedelta(minutes=minutes)

        # Filter and sort
        points = [
            p for p in self._system_metrics_points if p.timestamp >= cutoff
        ]
        points.sort(key=lambda p: p.timestamp)

        return points

    def _ensure_initialized(self) -> None:
        """Ensure service is initialized."""
        if not self._initialized:
            raise RuntimeError(
                "Metrics Service not initialized. Call initialize() first."
            )


# Global singleton instance
_metrics_instance: MetricsService | None = None


async def get_metrics_service() -> MetricsService:
    """
    Get or create the global Metrics Service instance.

    Returns:
        Initialized Metrics Service.
    """
    global _metrics_instance

    if _metrics_instance is None:
        _metrics_instance = MetricsService()
        await _metrics_instance.initialize()

    return _metrics_instance


async def reset_metrics_service() -> None:
    """
    Reset the global Metrics Service instance.

    Useful for testing.
    """
    global _metrics_instance

    if _metrics_instance is not None:
        await _metrics_instance.shutdown()
        _metrics_instance = None
