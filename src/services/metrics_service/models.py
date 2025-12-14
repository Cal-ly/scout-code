"""
Metrics Service - Data Models

Models for tracking LLM inference performance, reliability, and system metrics.
Designed for local Ollama inference on Raspberry Pi 5.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MetricsEntry(BaseModel):
    """
    Individual inference metrics entry.

    Records performance, reliability, and system state for a single LLM call.

    Attributes:
        timestamp: When the inference occurred.
        model: Model identifier (e.g., "qwen2.5:3b", "gemma2:2b").
        module: Which Scout module made the call.
        job_id: Optional job identifier for correlation.
        duration_seconds: Total inference time.
        prompt_tokens: Number of input tokens.
        completion_tokens: Number of output tokens.
        success: Whether the inference succeeded.
        error_type: Type of error if failed.
        retry_count: Number of retries before success/failure.
        fallback_used: Whether fallback model was used.
        cpu_percent: CPU usage at inference time.
        memory_mb: Memory usage in MB at inference time.
        temperature_c: CPU temperature in Celsius (Pi-specific).
    """

    timestamp: datetime = Field(default_factory=datetime.now)
    model: str
    module: str | None = None
    job_id: str | None = None

    # Performance metrics
    duration_seconds: float
    prompt_tokens: int
    completion_tokens: int

    # Reliability metrics
    success: bool
    error_type: str | None = None
    retry_count: int = 0
    fallback_used: bool = False

    # System metrics (optional, Pi-specific)
    cpu_percent: float | None = None
    memory_mb: float | None = None
    temperature_c: float | None = None

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, v: float) -> float:
        """Ensure duration is non-negative."""
        if v < 0:
            raise ValueError("Duration cannot be negative")
        return v

    @field_validator("prompt_tokens", "completion_tokens")
    @classmethod
    def validate_tokens(cls, v: int) -> int:
        """Ensure token counts are non-negative."""
        if v < 0:
            raise ValueError("Token count cannot be negative")
        return v

    @field_validator("retry_count")
    @classmethod
    def validate_retry_count(cls, v: int) -> int:
        """Ensure retry count is non-negative."""
        if v < 0:
            raise ValueError("Retry count cannot be negative")
        return v

    @property
    def tokens_per_second(self) -> float:
        """Calculate output tokens per second."""
        if self.duration_seconds <= 0:
            return 0.0
        return self.completion_tokens / self.duration_seconds

    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output)."""
        return self.prompt_tokens + self.completion_tokens


class ModelStats(BaseModel):
    """
    Aggregated statistics for a single model.

    Used for comparing performance between models (e.g., Qwen vs Gemma).

    Attributes:
        model_name: Model identifier.
        total_calls: Number of inference calls.
        success_count: Number of successful calls.
        total_tokens: Total tokens processed.
        total_duration_seconds: Total inference time.
        avg_tokens_per_second: Average generation speed.
        error_breakdown: Count of errors by type.
    """

    model_name: str
    total_calls: int = 0
    success_count: int = 0
    total_tokens: int = 0
    total_duration_seconds: float = 0.0
    avg_tokens_per_second: float = 0.0
    error_breakdown: dict[str, int] = Field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.success_count / self.total_calls) * 100.0

    @property
    def avg_duration_seconds(self) -> float:
        """Calculate average inference duration."""
        if self.success_count == 0:
            return 0.0
        return self.total_duration_seconds / self.success_count


class ModuleStats(BaseModel):
    """
    Aggregated statistics for a Scout module.

    Tracks performance per module (Rinser, Analyzer, Creator, etc.).

    Attributes:
        module_name: Module identifier.
        total_calls: Number of inference calls from this module.
        success_count: Number of successful calls.
        total_duration_seconds: Total inference time for this module.
        avg_tokens_per_second: Average generation speed.
    """

    module_name: str
    total_calls: int = 0
    success_count: int = 0
    total_duration_seconds: float = 0.0
    avg_tokens_per_second: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.success_count / self.total_calls) * 100.0

    @property
    def avg_duration_seconds(self) -> float:
        """Calculate average inference duration."""
        if self.success_count == 0:
            return 0.0
        return self.total_duration_seconds / self.success_count


class PerformanceStatus(BaseModel):
    """
    Current performance status snapshot.

    Provides real-time health indicators for dashboard/API.

    Attributes:
        calls_today: Number of inference calls today.
        success_rate_today: Success rate today (0.0-100.0).
        avg_tokens_per_second: Average generation speed today.
        avg_duration_seconds: Average inference duration today.
        primary_model_success_rate: Success rate of primary model.
        fallback_usage_rate: Percentage of calls using fallback model.
        current_temperature: Current CPU temperature in Celsius.
        throttling_warning: True if temperature indicates throttling risk.
        performance_trend: "improving", "stable", or "degrading".
    """

    calls_today: int = 0
    success_rate_today: float = 0.0
    avg_tokens_per_second: float = 0.0
    avg_duration_seconds: float = 0.0
    primary_model_success_rate: float = 0.0
    fallback_usage_rate: float = 0.0
    current_temperature: float | None = None
    throttling_warning: bool = False
    performance_trend: str = "stable"

    @field_validator("performance_trend")
    @classmethod
    def validate_trend(cls, v: str) -> str:
        """Ensure trend is a valid value."""
        valid_trends = {"improving", "stable", "degrading"}
        if v not in valid_trends:
            raise ValueError(f"Trend must be one of: {valid_trends}")
        return v


class PerformanceSummary(BaseModel):
    """
    Performance summary for a time period.

    Comprehensive statistics for reporting and analysis.

    Attributes:
        period_start: Start of the reporting period.
        period_end: End of the reporting period.
        total_calls: Total inference calls in period.
        total_tokens: Total tokens processed.
        successful_calls: Number of successful calls.
        avg_tokens_per_second: Average generation speed.
        median_duration_seconds: Median inference duration.
        p95_duration_seconds: 95th percentile duration.
        success_rate: Overall success rate (0.0-100.0).
        error_breakdown: Count of errors by type.
        fallback_rate: Percentage of calls using fallback.
        model_stats: Per-model statistics.
        module_stats: Per-module statistics.
        avg_cpu_percent: Average CPU usage during inferences.
        avg_memory_mb: Average memory usage during inferences.
        avg_temperature_c: Average temperature during inferences.
    """

    period_start: datetime
    period_end: datetime
    total_calls: int = 0
    total_tokens: int = 0
    successful_calls: int = 0
    avg_tokens_per_second: float = 0.0
    median_duration_seconds: float = 0.0
    p95_duration_seconds: float = 0.0
    success_rate: float = 0.0
    error_breakdown: dict[str, int] = Field(default_factory=dict)
    fallback_rate: float = 0.0
    model_stats: dict[str, Any] = Field(default_factory=dict)
    module_stats: dict[str, Any] = Field(default_factory=dict)

    # System metrics averages
    avg_cpu_percent: float | None = None
    avg_memory_mb: float | None = None
    avg_temperature_c: float | None = None
