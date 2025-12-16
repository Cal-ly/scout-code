"""
Metrics API Routes

Performance metrics endpoints.

Endpoints:
    GET /api/v1/metrics/status - Current status
    GET /api/v1/metrics/summary - Summary for period
    GET /api/v1/metrics/entries - Paginated entries
    GET /api/v1/metrics/comparison - Model comparison
    GET /api/v1/metrics/system-history - System metrics history
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException

from src.web.routes.api.schemas import (
    MetricsEntriesResponse,
    MetricsEntryResponse,
    MetricsStatusResponse,
    MetricsSummaryResponse,
    ModelComparisonResponse,
    ModelStatsResponse,
    SystemMetricsHistoryResponse,
    SystemMetricsPointResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/status", response_model=MetricsStatusResponse)
async def get_status() -> MetricsStatusResponse:
    """Get current metrics status."""
    from src.services.metrics_service import get_metrics_service

    try:
        metrics = await get_metrics_service()
        status = await metrics.get_status()
        return MetricsStatusResponse(
            calls_today=status.calls_today,
            success_rate_today=status.success_rate_today,
            avg_tokens_per_second=status.avg_tokens_per_second,
            avg_duration_seconds=status.avg_duration_seconds,
            primary_model_success_rate=status.primary_model_success_rate,
            fallback_usage_rate=status.fallback_usage_rate,
            current_cpu_percent=status.current_cpu_percent,
            current_memory_percent=status.current_memory_percent,
            current_temperature=status.current_temperature,
            throttling_warning=status.throttling_warning,
            performance_trend=status.performance_trend,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", response_model=MetricsSummaryResponse)
async def get_summary(days: int = 7) -> MetricsSummaryResponse:
    """Get metrics summary for period."""
    from src.services.metrics_service import get_metrics_service

    try:
        metrics = await get_metrics_service()
        end = datetime.now()
        start = end - timedelta(days=min(days, 90))
        summary = await metrics.get_summary(start=start, end=end)

        return MetricsSummaryResponse(
            period_start=summary.period_start.isoformat(),
            period_end=summary.period_end.isoformat(),
            total_calls=summary.total_calls,
            total_tokens=summary.total_tokens,
            successful_calls=summary.successful_calls,
            avg_tokens_per_second=summary.avg_tokens_per_second,
            median_duration_seconds=summary.median_duration_seconds,
            p95_duration_seconds=summary.p95_duration_seconds,
            success_rate=summary.success_rate,
            error_breakdown=summary.error_breakdown,
            fallback_rate=summary.fallback_rate,
            avg_cpu_percent=summary.avg_cpu_percent,
            avg_memory_mb=summary.avg_memory_mb,
            avg_temperature_c=summary.avg_temperature_c,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entries", response_model=MetricsEntriesResponse)
async def get_entries(
    skip: int = 0,
    limit: int = 50,
    model: str | None = None,
    module: str | None = None,
    success: bool | None = None,
    sort_by: str = "timestamp",
    sort_order: str = "desc",
) -> MetricsEntriesResponse:
    """Get paginated metrics entries."""
    from src.services.metrics_service import get_metrics_service

    try:
        metrics = await get_metrics_service()
        entries = metrics._entries.copy()

        # Filter
        if model:
            entries = [e for e in entries if e.model == model]
        if module:
            entries = [e for e in entries if e.module == module]
        if success is not None:
            entries = [e for e in entries if e.success == success]

        # Sort
        reverse = sort_order == "desc"
        if sort_by == "timestamp":
            entries.sort(key=lambda e: e.timestamp, reverse=reverse)
        elif sort_by == "duration":
            entries.sort(key=lambda e: e.duration_seconds, reverse=reverse)
        elif sort_by == "tokens_per_second":
            entries.sort(key=lambda e: e.tokens_per_second, reverse=reverse)

        # Paginate
        total = len(entries)
        limit = min(limit, 100)
        paginated = entries[skip : skip + limit]

        return MetricsEntriesResponse(
            entries=[
                MetricsEntryResponse(
                    timestamp=e.timestamp.isoformat(),
                    model=e.model,
                    module=e.module,
                    job_id=e.job_id,
                    duration_seconds=e.duration_seconds,
                    prompt_tokens=e.prompt_tokens,
                    completion_tokens=e.completion_tokens,
                    tokens_per_second=e.tokens_per_second,
                    success=e.success,
                    error_type=e.error_type,
                    retry_count=e.retry_count,
                    fallback_used=e.fallback_used,
                    cpu_percent=e.cpu_percent,
                    memory_mb=e.memory_mb,
                    temperature_c=e.temperature_c,
                )
                for e in paginated
            ],
            total=total,
            skip=skip,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comparison", response_model=ModelComparisonResponse)
async def get_comparison() -> ModelComparisonResponse:
    """Get model comparison data."""
    from src.services.metrics_service import get_metrics_service

    try:
        metrics = await get_metrics_service()
        comparison = await metrics.get_model_comparison()

        return ModelComparisonResponse(
            models=[
                ModelStatsResponse(
                    model_name=s.model_name,
                    total_calls=s.total_calls,
                    success_count=s.success_count,
                    success_rate=s.success_rate,
                    total_tokens=s.total_tokens,
                    total_duration_seconds=s.total_duration_seconds,
                    avg_tokens_per_second=s.avg_tokens_per_second,
                    avg_duration_seconds=s.avg_duration_seconds,
                    error_breakdown=s.error_breakdown,
                )
                for s in comparison.values()
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system-history", response_model=SystemMetricsHistoryResponse)
async def get_system_history(minutes: int = 15) -> SystemMetricsHistoryResponse:
    """Get system metrics time-series."""
    from src.services.metrics_service import get_metrics_service

    try:
        metrics = await get_metrics_service()
        points = await metrics.get_system_metrics_history(minutes=minutes)

        return SystemMetricsHistoryResponse(
            points=[
                SystemMetricsPointResponse(
                    timestamp=p.timestamp.isoformat(),
                    cpu_percent=p.cpu_percent,
                    memory_percent=p.memory_percent,
                    memory_mb=p.memory_mb,
                    temperature_c=p.temperature_c,
                )
                for p in points
            ],
            minutes=minutes,
            count=len(points),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
