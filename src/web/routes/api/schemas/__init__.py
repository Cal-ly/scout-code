"""API Schema exports."""

from src.web.routes.api.schemas.common import (
    ErrorResponse,
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
)
from src.web.routes.api.schemas.jobs import (
    ApplyRequest,
    ApplyResponse,
    JobListResponse,
    JobSummary,
    QuickScoreRequest,
    QuickScoreResponse,
    StatusResponse,
    StepInfo,
)
from src.web.routes.api.schemas.metrics import (
    MetricsEntriesResponse,
    MetricsEntryResponse,
    MetricsStatusResponse,
    MetricsSummaryResponse,
    ModelComparisonResponse,
    ModelStatsResponse,
    SystemMetricsHistoryResponse,
    SystemMetricsPointResponse,
)
from src.web.routes.api.schemas.profile import (
    ProfileAssessmentResponse,
    ProfileCreateRequest,
    ProfileCreateResponse,
    ProfileStatusResponse,
    ProfileSummaryResponse,
    SectionScoreResponse,
)

__all__ = [
    # Common
    "ErrorResponse",
    "SuccessResponse",
    "PaginationParams",
    "PaginatedResponse",
    # Jobs
    "ApplyRequest",
    "ApplyResponse",
    "QuickScoreRequest",
    "QuickScoreResponse",
    "StatusResponse",
    "StepInfo",
    "JobSummary",
    "JobListResponse",
    # Profile
    "ProfileStatusResponse",
    "ProfileCreateRequest",
    "ProfileCreateResponse",
    "ProfileAssessmentResponse",
    "ProfileSummaryResponse",
    "SectionScoreResponse",
    # Metrics
    "MetricsStatusResponse",
    "MetricsSummaryResponse",
    "MetricsEntryResponse",
    "MetricsEntriesResponse",
    "ModelStatsResponse",
    "ModelComparisonResponse",
    "SystemMetricsPointResponse",
    "SystemMetricsHistoryResponse",
]
