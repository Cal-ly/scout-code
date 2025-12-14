"""
Memory Log Handler for Web Interface

Captures recent log entries in a ring buffer for display in the web UI.
"""

import logging
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime


@dataclass
class LogEntry:
    """Single log entry."""
    timestamp: str
    level: str
    logger: str
    message: str


class MemoryLogHandler(logging.Handler):
    """
    In-memory log handler that keeps recent entries in a ring buffer.

    Thread-safe implementation using deque with maxlen.
    """

    _instance: "MemoryLogHandler | None" = None
    _lock = threading.Lock()

    def __init__(self, max_entries: int = 500):
        """
        Initialize memory log handler.

        Args:
            max_entries: Maximum number of log entries to keep.
        """
        super().__init__()
        self._entries: deque[LogEntry] = deque(maxlen=max_entries)
        self._max_entries = max_entries

        # Set format
        self.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))

    def emit(self, record: logging.LogRecord) -> None:
        """
        Handle a log record.

        Args:
            record: Log record to process.
        """
        try:
            entry = LogEntry(
                timestamp=datetime.fromtimestamp(record.created).isoformat(),
                level=record.levelname,
                logger=record.name,
                message=self.format(record),
            )
            self._entries.append(entry)
        except Exception:
            self.handleError(record)

    def get_entries(
        self,
        limit: int = 100,
        level: str | None = None,
        logger_filter: str | None = None,
    ) -> list[LogEntry]:
        """
        Get recent log entries.

        Args:
            limit: Maximum number of entries to return.
            level: Filter by log level (INFO, WARNING, ERROR, etc.).
            logger_filter: Filter by logger name (partial match).

        Returns:
            List of log entries, oldest first (chronological order).
        """
        entries = list(self._entries)

        # Apply filters
        if level:
            entries = [e for e in entries if e.level == level.upper()]

        if logger_filter:
            entries = [e for e in entries if logger_filter in e.logger]

        # Return oldest first (chronological), newest at end for terminal-style display
        # Limit from the end to keep most recent entries
        if len(entries) > limit:
            entries = entries[-limit:]
        return entries

    def clear(self) -> None:
        """Clear all log entries."""
        self._entries.clear()

    @classmethod
    def get_instance(cls, max_entries: int = 500) -> "MemoryLogHandler":
        """
        Get singleton instance.

        Args:
            max_entries: Maximum entries (only used on first call).

        Returns:
            Singleton MemoryLogHandler instance.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(max_entries)
        return cls._instance


def setup_memory_logging(max_entries: int = 500) -> MemoryLogHandler:
    """
    Set up memory logging for the application.

    Adds a MemoryLogHandler to the root logger.

    Args:
        max_entries: Maximum log entries to keep.

    Returns:
        The configured MemoryLogHandler instance.
    """
    handler = MemoryLogHandler.get_instance(max_entries)
    handler.setLevel(logging.DEBUG)

    # Add to root logger
    root_logger = logging.getLogger()

    # Avoid duplicate handlers
    for h in root_logger.handlers:
        if isinstance(h, MemoryLogHandler):
            return handler

    root_logger.addHandler(handler)
    return handler


def get_memory_log_handler() -> MemoryLogHandler:
    """Get the memory log handler instance."""
    return MemoryLogHandler.get_instance()
