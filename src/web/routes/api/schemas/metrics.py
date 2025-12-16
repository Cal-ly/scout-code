"""Metrics-related API schemas."""

from pydantic import BaseModel


class MetricsStatusResponse(BaseModel):
    """Current metrics status."""

    calls_today: int
    success_rate_today: float
    avg_tokens_per_second: float
    avg_duration_seconds: float
    primary_model_success_rate: float
    fallback_usage_rate: float
    current_cpu_percent: float | None
    current_memory_percent: float | None
    current_temperature: float | None
    throttling_warning: bool
    performance_trend: str


class MetricsSummaryResponse(BaseModel):
    """Metrics summary for period."""

    period_start: str
    period_end: str
    total_calls: int
    total_tokens: int
    successful_calls: int
    avg_tokens_per_second: float
    median_duration_seconds: float
    p95_duration_seconds: float
    success_rate: float
    error_breakdown: dict[str, int]
    fallback_rate: float
    avg_cpu_percent: float | None
    avg_memory_mb: float | None
    avg_temperature_c: float | None


class MetricsEntryResponse(BaseModel):
    """Single metrics entry."""

    timestamp: str
    model: str
    module: str | None
    job_id: str | None
    duration_seconds: float
    prompt_tokens: int
    completion_tokens: int
    tokens_per_second: float
    success: bool
    error_type: str | None
    retry_count: int
    fallback_used: bool
    cpu_percent: float | None
    memory_mb: float | None
    temperature_c: float | None


class MetricsEntriesResponse(BaseModel):
    """Paginated metrics entries."""

    entries: list[MetricsEntryResponse]
    total: int
    skip: int
    limit: int


class ModelStatsResponse(BaseModel):
    """Model statistics."""

    model_name: str
    total_calls: int
    success_count: int
    success_rate: float
    total_tokens: int
    total_duration_seconds: float
    avg_tokens_per_second: float
    avg_duration_seconds: float
    error_breakdown: dict[str, int]


class ModelComparisonResponse(BaseModel):
    """Model comparison data."""

    models: list[ModelStatsResponse]


class SystemMetricsPointResponse(BaseModel):
    """Single system metrics point."""

    timestamp: str
    cpu_percent: float | None
    memory_percent: float | None
    memory_mb: float | None
    temperature_c: float | None


class SystemMetricsHistoryResponse(BaseModel):
    """System metrics time-series."""

    points: list[SystemMetricsPointResponse]
    minutes: int
    count: int
