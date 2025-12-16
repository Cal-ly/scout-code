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
from src.web.routes.api.schemas.profiles import (
    CertificationSchema,
    CompletenessSection,
    EducationSchema,
    ExperienceSchema,
    LanguageSchema,
    ProfileActivateResponse,
    ProfileCompletenessSchema,
    ProfileDetailResponse,
    ProfileListResponse,
    ProfileStatsSchema,
    ProfileUpdateRequest,
    SkillSchema,
)
from src.web.routes.api.schemas.profiles import (
    ProfileCreateRequest as ProfilesCreateRequest,
)
from src.web.routes.api.schemas.profiles import (
    ProfileSummaryResponse as ProfilesSummaryResponse,
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
    # Profile (legacy - single profile)
    "ProfileStatusResponse",
    "ProfileCreateRequest",
    "ProfileCreateResponse",
    "ProfileAssessmentResponse",
    "ProfileSummaryResponse",
    "SectionScoreResponse",
    # Profiles (multi-profile CRUD)
    "SkillSchema",
    "ExperienceSchema",
    "EducationSchema",
    "CertificationSchema",
    "LanguageSchema",
    "ProfilesCreateRequest",
    "ProfileUpdateRequest",
    "ProfileStatsSchema",
    "ProfilesSummaryResponse",
    "ProfileDetailResponse",
    "ProfileListResponse",
    "ProfileActivateResponse",
    "CompletenessSection",
    "ProfileCompletenessSchema",
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
