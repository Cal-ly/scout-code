"""
Metrics Service - System Collector

Collects system metrics (CPU, memory, temperature) with Raspberry Pi 5 support.
Gracefully degrades when psutil is not available or on non-Pi systems.
"""

import logging
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)

# Raspberry Pi thermal zone paths (checked in order)
PI_THERMAL_PATHS = [
    Path("/sys/class/thermal/thermal_zone0/temp"),
    Path("/sys/class/hwmon/hwmon0/temp1_input"),
]

# Temperature threshold for throttling warning (Celsius)
THROTTLING_THRESHOLD = 80.0


class SystemSnapshot(NamedTuple):
    """System metrics snapshot."""

    cpu_percent: float | None
    memory_mb: float | None
    temperature_c: float | None


class SystemCollector:
    """
    Collects system metrics with Raspberry Pi 5 optimizations.

    Provides CPU usage, memory usage, and temperature readings.
    Gracefully handles missing psutil or unavailable sensors.

    Attributes:
        psutil_available: Whether psutil is available.
        thermal_path: Path to thermal sensor (Pi-specific).

    Example:
        >>> collector = SystemCollector()
        >>> snapshot = collector.collect_snapshot()
        >>> print(f"CPU: {snapshot.cpu_percent}%")
    """

    def __init__(self) -> None:
        """Initialize the system collector and detect available sensors."""
        self._psutil_available = False
        self._thermal_path: Path | None = None
        self._initialize()

    def _initialize(self) -> None:
        """Detect available metrics sources."""
        # Check for psutil
        try:
            import psutil

            self._psutil_available = True
            # Prime CPU measurement - first call with interval=None returns 0.0
            # because there's no baseline. This call establishes the baseline.
            psutil.cpu_percent(interval=None)
            logger.info(
                f"psutil {psutil.__version__} available for system metrics "
                f"(CPU: yes, Memory: yes)"
            )
        except ImportError:
            logger.warning("psutil not available, CPU/memory metrics disabled")

        # Find thermal sensor path (Pi-specific)
        for path in PI_THERMAL_PATHS:
            if path.exists():
                self._thermal_path = path
                logger.debug(f"Found thermal sensor at {path}")
                break

        if self._thermal_path is None:
            logger.debug("No Pi thermal sensor found, will try psutil sensors")

    @property
    def psutil_available(self) -> bool:
        """Whether psutil is available for CPU/memory metrics."""
        return self._psutil_available

    @property
    def thermal_path(self) -> Path | None:
        """Path to thermal sensor if available."""
        return self._thermal_path

    def get_cpu_percent(self) -> float | None:
        """
        Get current CPU usage percentage.

        Returns:
            CPU usage as percentage (0-100), or None if unavailable.
        """
        if not self._psutil_available:
            return None

        try:
            import psutil

            # interval=None returns cached value (non-blocking)
            return psutil.cpu_percent(interval=None)
        except Exception as e:
            logger.warning(f"Failed to get CPU percent: {e}")
            return None

    def get_memory_mb(self) -> float | None:
        """
        Get current memory usage in megabytes.

        Returns:
            Memory usage in MB, or None if unavailable.
        """
        if not self._psutil_available:
            return None

        try:
            import psutil

            mem = psutil.virtual_memory()
            return mem.used / (1024 * 1024)
        except Exception as e:
            logger.warning(f"Failed to get memory usage: {e}")
            return None

    def get_memory_percent(self) -> float | None:
        """
        Get current memory usage percentage.

        Returns:
            Memory usage as percentage (0-100), or None if unavailable.
        """
        if not self._psutil_available:
            return None

        try:
            import psutil

            mem = psutil.virtual_memory()
            return mem.percent
        except Exception as e:
            logger.warning(f"Failed to get memory percent: {e}")
            return None

    def get_temperature(self) -> float | None:
        """
        Get CPU temperature in Celsius.

        Tries Pi-specific sysfs path first, falls back to psutil sensors.

        Returns:
            Temperature in Celsius, or None if unavailable.
        """
        # Try Pi thermal sensor first
        if self._thermal_path and self._thermal_path.exists():
            try:
                with open(self._thermal_path) as f:
                    # Value is in millidegrees Celsius
                    raw_temp = int(f.read().strip())
                    return raw_temp / 1000.0
            except (OSError, ValueError) as e:
                logger.debug(f"Failed to read thermal sensor: {e}")

        # Fallback to psutil sensors
        if self._psutil_available:
            try:
                import psutil

                temps = psutil.sensors_temperatures()
                if temps:
                    # Try common sensor names
                    for sensor_name in ["coretemp", "cpu_thermal", "k10temp", "acpitz"]:
                        if sensor_name in temps and temps[sensor_name]:
                            return temps[sensor_name][0].current

                    # Use first available sensor
                    for entries in temps.values():
                        if entries:
                            return entries[0].current
            except Exception as e:
                logger.debug(f"Failed to get temperature from psutil: {e}")

        return None

    def is_throttling_risk(self) -> bool:
        """
        Check if temperature indicates throttling risk.

        Returns:
            True if temperature exceeds throttling threshold.
        """
        temp = self.get_temperature()
        if temp is None:
            return False
        return temp >= THROTTLING_THRESHOLD

    def collect_snapshot(self) -> SystemSnapshot:
        """
        Collect all system metrics as a snapshot.

        Returns:
            SystemSnapshot with CPU, memory, and temperature.
        """
        return SystemSnapshot(
            cpu_percent=self.get_cpu_percent(),
            memory_mb=self.get_memory_mb(),
            temperature_c=self.get_temperature(),
        )

    def collect_dict(self) -> dict[str, float | None]:
        """
        Collect all system metrics as a dictionary.

        Returns:
            Dictionary with cpu_percent, memory_mb, temperature_c keys.
        """
        snapshot = self.collect_snapshot()
        return {
            "cpu_percent": snapshot.cpu_percent,
            "memory_mb": snapshot.memory_mb,
            "temperature_c": snapshot.temperature_c,
        }


# Module-level singleton for convenience
_collector_instance: SystemCollector | None = None


def get_system_collector() -> SystemCollector:
    """
    Get or create the global SystemCollector instance.

    Returns:
        SystemCollector singleton.
    """
    global _collector_instance

    if _collector_instance is None:
        _collector_instance = SystemCollector()

    return _collector_instance
