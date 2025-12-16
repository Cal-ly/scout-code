"""
Logs API Routes

Application log endpoints.

Endpoints:
    GET /api/v1/logs - Get log entries
    DELETE /api/v1/logs - Clear logs
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["logs"])


class LogEntry(BaseModel):
    """Single log entry."""

    timestamp: str
    level: str
    logger: str
    message: str


class LogsResponse(BaseModel):
    """Logs response."""

    entries: list[LogEntry]
    total: int


@router.get("", response_model=LogsResponse)
async def get_logs(
    limit: int = 100,
    level: str | None = None,
    logger_filter: str | None = None,
) -> LogsResponse:
    """Get application logs."""
    from src.web.log_handler import get_memory_log_handler

    handler = get_memory_log_handler()
    entries = handler.get_entries(
        limit=min(limit, 500),
        level=level,
        logger_filter=logger_filter,
    )

    return LogsResponse(
        entries=[
            LogEntry(
                timestamp=e.timestamp,
                level=e.level,
                logger=e.logger,
                message=e.message,
            )
            for e in entries
        ],
        total=len(entries),
    )


@router.delete("")
async def clear_logs() -> dict:
    """Clear log buffer."""
    from src.web.log_handler import get_memory_log_handler

    handler = get_memory_log_handler()
    handler.clear()
    return {"status": "cleared"}
