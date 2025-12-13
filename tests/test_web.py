"""
Unit tests for API Routes.

Run with: pytest tests/test_web.py -v
"""

from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from src.services.pipeline import (
    PipelineInput,
    PipelineResult,
    PipelineStatus,
    PipelineStep,
    StepResult,
    StepStatus,
)
from src.web.dependencies import (
    JobStore,
    get_job_store,
    get_store,
    reset_job_store,
)
from src.web.schemas import (
    ApplyRequest,
    ApplyResponse,
    ErrorResponse,
    HealthResponse,
    JobListResponse,
    JobSummary,
    StatusResponse,
    StepInfo,
)

# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def mock_pipeline_result() -> PipelineResult:
    """Create a mock pipeline result."""
    return PipelineResult(
        pipeline_id="test-123",
        status=PipelineStatus.COMPLETED,
        started_at=datetime(2025, 1, 15, 10, 0, 0),
        completed_at=datetime(2025, 1, 15, 10, 0, 30),
        total_duration_ms=30000,
        job_id="job-abc",
        job_title="Senior Python Developer",
        company_name="TechCorp",
        compatibility_score=85.5,
        cv_path="/output/cv_test.pdf",
        cover_letter_path="/output/cover_letter_test.pdf",
        steps=[
            StepResult(
                step=PipelineStep.RINSER,
                status=StepStatus.COMPLETED,
                duration_ms=5000,
            ),
            StepResult(
                step=PipelineStep.ANALYZER,
                status=StepStatus.COMPLETED,
                duration_ms=10000,
            ),
            StepResult(
                step=PipelineStep.CREATOR,
                status=StepStatus.COMPLETED,
                duration_ms=10000,
            ),
            StepResult(
                step=PipelineStep.FORMATTER,
                status=StepStatus.COMPLETED,
                duration_ms=5000,
            ),
        ],
    )


@pytest.fixture
def mock_failed_result() -> PipelineResult:
    """Create a mock failed pipeline result."""
    return PipelineResult(
        pipeline_id="fail-456",
        status=PipelineStatus.FAILED,
        started_at=datetime(2025, 1, 15, 10, 0, 0),
        job_id="fail-job",
        job_title="Failed Job",
        company_name="FailCorp",
        error="LLM service error",
        failed_step=PipelineStep.ANALYZER,
        steps=[
            StepResult(
                step=PipelineStep.RINSER,
                status=StepStatus.COMPLETED,
                duration_ms=5000,
            ),
            StepResult(
                step=PipelineStep.ANALYZER,
                status=StepStatus.FAILED,
                duration_ms=2000,
                error="LLM service error",
            ),
        ],
    )


@pytest.fixture
def mock_running_result() -> PipelineResult:
    """Create a mock running pipeline result."""
    return PipelineResult(
        pipeline_id="run-789",
        status=PipelineStatus.RUNNING,
        started_at=datetime(2025, 1, 15, 10, 0, 0),
        current_step=PipelineStep.CREATOR,
        job_id="run-job",
        job_title="Running Job",
        company_name="RunCorp",
        steps=[
            StepResult(
                step=PipelineStep.RINSER,
                status=StepStatus.COMPLETED,
                duration_ms=5000,
            ),
            StepResult(
                step=PipelineStep.ANALYZER,
                status=StepStatus.COMPLETED,
                duration_ms=10000,
            ),
            StepResult(
                step=PipelineStep.CREATOR,
                status=StepStatus.RUNNING,
            ),
        ],
    )


@pytest.fixture
def sample_job_text() -> str:
    """Sample job posting text."""
    return """
    Senior Python Developer - TechCorp

    We are looking for an experienced Python developer to join our team.

    Requirements:
    - 5+ years Python experience
    - Experience with FastAPI or Django
    - Strong understanding of async programming
    - Experience with PostgreSQL and Redis
    - Good communication skills

    Responsibilities:
    - Design and implement REST APIs
    - Write clean, maintainable code
    - Participate in code reviews
    - Mentor junior developers

    Benefits:
    - Competitive salary
    - Remote work options
    - Health insurance
    - Stock options
    """ * 3  # Make it longer than 100 chars


@pytest.fixture
def job_store() -> Generator[JobStore, None, None]:
    """Create a fresh job store for each test."""
    reset_job_store()
    store = get_job_store()
    yield store
    reset_job_store()


# =============================================================================
# SCHEMA TESTS
# =============================================================================


class TestSchemas:
    """Tests for Pydantic schemas."""

    def test_apply_request_valid(self, sample_job_text: str) -> None:
        """Should create valid apply request."""
        request = ApplyRequest(job_text=sample_job_text, source="linkedin")
        assert len(request.job_text) >= 100
        assert request.source == "linkedin"

    def test_apply_request_too_short(self) -> None:
        """Should reject job text less than 100 chars."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ApplyRequest(job_text="Short text", source=None)

    def test_apply_request_optional_source(self, sample_job_text: str) -> None:
        """Should allow missing source."""
        request = ApplyRequest(job_text=sample_job_text, source=None)
        assert request.source is None

    def test_apply_response(self) -> None:
        """Should create valid apply response."""
        response = ApplyResponse(job_id="abc123", status="running")
        assert response.job_id == "abc123"
        assert response.status == "running"

    def test_job_summary(self) -> None:
        """Should create valid job summary."""
        summary = JobSummary(
            job_id="abc123",
            job_title="Python Dev",
            company_name="TechCorp",
            status="completed",
            compatibility_score=85.0,
            submitted_at=datetime.now(),
        )
        assert summary.job_id == "abc123"
        assert summary.compatibility_score == 85.0

    def test_job_list_response(self) -> None:
        """Should create valid job list response."""
        response = JobListResponse(
            jobs=[
                JobSummary(
                    job_id="1",
                    status="completed",
                    submitted_at=datetime.now(),
                ),
            ],
            total=1,
        )
        assert len(response.jobs) == 1
        assert response.total == 1

    def test_step_info(self) -> None:
        """Should create valid step info."""
        info = StepInfo(
            step="rinser",
            status="completed",
            duration_ms=5000,
        )
        assert info.step == "rinser"
        assert info.duration_ms == 5000

    def test_status_response(self) -> None:
        """Should create valid status response."""
        response = StatusResponse(
            job_id="abc123",
            pipeline_id="pipe-123",
            status="completed",
            started_at=datetime.now(),
        )
        assert response.job_id == "abc123"
        assert response.status == "completed"

    def test_error_response(self) -> None:
        """Should create valid error response."""
        response = ErrorResponse(
            error="NotFound",
            message="Job not found",
            detail="Job abc123 does not exist",
        )
        assert response.error == "NotFound"

    def test_health_response(self) -> None:
        """Should create valid health response."""
        response = HealthResponse(
            status="healthy",
            version="0.1.0",
            services={"pipeline": "ok"},
        )
        assert response.status == "healthy"


# =============================================================================
# JOB STORE TESTS
# =============================================================================


class TestJobStore:
    """Tests for JobStore functionality."""

    def test_store_empty_initially(self, job_store: JobStore) -> None:
        """Should start empty."""
        assert job_store.count() == 0
        assert job_store.list_all() == []

    def test_store_result(
        self, job_store: JobStore, mock_pipeline_result: PipelineResult
    ) -> None:
        """Should store pipeline result."""
        job_id = job_store.store(mock_pipeline_result)
        assert job_id == "job-abc"
        assert job_store.count() == 1

    def test_get_stored_result(
        self, job_store: JobStore, mock_pipeline_result: PipelineResult
    ) -> None:
        """Should retrieve stored result."""
        job_id = job_store.store(mock_pipeline_result)
        result = job_store.get(job_id)
        assert result is not None
        assert result.job_id == "job-abc"

    def test_get_nonexistent_result(self, job_store: JobStore) -> None:
        """Should return None for nonexistent job."""
        result = job_store.get("nonexistent")
        assert result is None

    def test_list_all_results(
        self,
        job_store: JobStore,
        mock_pipeline_result: PipelineResult,
        mock_failed_result: PipelineResult,
    ) -> None:
        """Should list all stored results."""
        job_store.store(mock_pipeline_result)
        job_store.store(mock_failed_result)
        results = job_store.list_all()
        assert len(results) == 2

    def test_list_sorted_by_date(self, job_store: JobStore) -> None:
        """Should list results sorted by date descending."""
        result1 = PipelineResult(
            pipeline_id="old",
            status=PipelineStatus.COMPLETED,
            started_at=datetime(2025, 1, 1),
        )
        result2 = PipelineResult(
            pipeline_id="new",
            status=PipelineStatus.COMPLETED,
            started_at=datetime(2025, 1, 15),
        )
        job_store.store(result1)
        job_store.store(result2)

        results = job_store.list_all()
        assert results[0].pipeline_id == "new"
        assert results[1].pipeline_id == "old"

    def test_clear_store(
        self, job_store: JobStore, mock_pipeline_result: PipelineResult
    ) -> None:
        """Should clear all stored results."""
        job_store.store(mock_pipeline_result)
        assert job_store.count() == 1
        job_store.clear()
        assert job_store.count() == 0

    def test_store_uses_pipeline_id_as_fallback(self, job_store: JobStore) -> None:
        """Should use pipeline_id if job_id is None."""
        result = PipelineResult(
            pipeline_id="pipe-123",
            status=PipelineStatus.COMPLETED,
            started_at=datetime.now(),
            job_id=None,
        )
        job_id = job_store.store(result)
        assert job_id == "pipe-123"


# =============================================================================
# DEPENDENCY TESTS
# =============================================================================


class TestDependencies:
    """Tests for FastAPI dependencies."""

    def test_get_job_store_singleton(self) -> None:
        """Should return same instance."""
        reset_job_store()
        store1 = get_job_store()
        store2 = get_job_store()
        assert store1 is store2
        reset_job_store()

    def test_reset_job_store(self) -> None:
        """Should reset singleton."""
        reset_job_store()
        store1 = get_job_store()
        reset_job_store()
        store2 = get_job_store()
        assert store1 is not store2
        reset_job_store()

    def test_get_store_dependency(self) -> None:
        """Should work as FastAPI dependency."""
        reset_job_store()
        store = get_store()
        assert isinstance(store, JobStore)
        reset_job_store()


# =============================================================================
# API ROUTE TESTS
# =============================================================================


class TestAPIRoutes:
    """Tests for API route endpoints."""

    @pytest.fixture
    def mock_orchestrator(self) -> Mock:
        """Create mock orchestrator."""
        orchestrator = Mock()
        orchestrator.execute = AsyncMock()
        return orchestrator

    @pytest.fixture
    def client(self, mock_orchestrator: Mock) -> Generator[TestClient, None, None]:
        """Create test client with mocked dependencies."""
        # Reset job store for each test
        reset_job_store()

        # Override dependencies
        from src.web.dependencies import get_orchestrator
        from src.web.main import app

        async def override_orchestrator() -> Mock:
            return mock_orchestrator

        app.dependency_overrides[get_orchestrator] = override_orchestrator

        yield TestClient(app, raise_server_exceptions=False)

        # Cleanup
        app.dependency_overrides.clear()
        reset_job_store()

    def test_info_endpoint(self, client: TestClient) -> None:
        """Should return app info."""
        response = client.get("/info")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Scout"
        assert data["status"] == "ready"

    def test_health_endpoint(self, client: TestClient) -> None:
        """Should return health status with service checks."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        # Status can be "healthy" or "degraded" depending on service state
        assert data["status"] in ("healthy", "degraded")
        assert "version" in data
        assert "services" in data
        # Verify services are checked (may be "ok" or have error states)
        assert "pipeline" in data["services"]
        assert "job_store" in data["services"]
        assert "notifications" in data["services"]

    def test_apply_endpoint(
        self, client: TestClient, sample_job_text: str
    ) -> None:
        """Should accept apply request."""
        response = client.post(
            "/api/apply",
            json={"job_text": sample_job_text, "source": "linkedin"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "running"

    def test_apply_endpoint_validation_error(self, client: TestClient) -> None:
        """Should reject invalid request."""
        response = client.post(
            "/api/apply",
            json={"job_text": "too short"},
        )
        assert response.status_code == 422

    def test_status_endpoint_not_found(self, client: TestClient) -> None:
        """Should return 404 for nonexistent job."""
        response = client.get("/api/status/nonexistent")
        assert response.status_code == 404

    def test_status_endpoint_success(
        self, client: TestClient, mock_pipeline_result: PipelineResult
    ) -> None:
        """Should return status for existing job."""
        # Store result directly
        store = get_job_store()
        store.store(mock_pipeline_result)

        response = client.get("/api/status/job-abc")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-abc"
        assert data["status"] == "completed"
        assert data["job_title"] == "Senior Python Developer"
        assert data["compatibility_score"] == 85.5

    def test_jobs_endpoint_empty(self, client: TestClient) -> None:
        """Should return empty list."""
        response = client.get("/api/jobs")
        assert response.status_code == 200
        data = response.json()
        assert data["jobs"] == []
        assert data["total"] == 0

    def test_jobs_endpoint_with_results(
        self, client: TestClient, mock_pipeline_result: PipelineResult
    ) -> None:
        """Should return job list."""
        store = get_job_store()
        store.store(mock_pipeline_result)

        response = client.get("/api/jobs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["job_id"] == "job-abc"

    def test_download_endpoint_not_found(self, client: TestClient) -> None:
        """Should return 404 for nonexistent job."""
        response = client.get("/api/download/nonexistent/cv")
        assert response.status_code == 404

    def test_download_endpoint_no_file_path(
        self, client: TestClient, mock_running_result: PipelineResult
    ) -> None:
        """Should return 404 when file not ready."""
        store = get_job_store()
        store.store(mock_running_result)

        response = client.get("/api/download/run-job/cv")
        assert response.status_code == 404
        assert "not available" in response.json()["detail"]

    def test_download_endpoint_file_not_exists(
        self, client: TestClient, mock_pipeline_result: PipelineResult
    ) -> None:
        """Should return 404 when file doesn't exist on disk."""
        store = get_job_store()
        store.store(mock_pipeline_result)

        response = client.get("/api/download/job-abc/cv")
        assert response.status_code == 404
        assert "File not found" in response.json()["detail"]

    def test_download_endpoint_success(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Should return file when exists."""
        # Create temp PDF file
        pdf_path = tmp_path / "test_cv.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake pdf content")

        result = PipelineResult(
            pipeline_id="dl-test",
            status=PipelineStatus.COMPLETED,
            started_at=datetime.now(),
            job_id="dl-job",
            cv_path=str(pdf_path),
        )

        store = get_job_store()
        store.store(result)

        response = client.get("/api/download/dl-job/cv")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    def test_download_cover_letter(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Should download cover letter."""
        pdf_path = tmp_path / "cover_letter.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake pdf content")

        result = PipelineResult(
            pipeline_id="dl-test",
            status=PipelineStatus.COMPLETED,
            started_at=datetime.now(),
            job_id="dl-job",
            cover_letter_path=str(pdf_path),
        )

        store = get_job_store()
        store.store(result)

        response = client.get("/api/download/dl-job/cover_letter")
        assert response.status_code == 200


# =============================================================================
# RESPONSE CONVERSION TESTS
# =============================================================================


class TestResponseConversion:
    """Tests for response conversion functions."""

    def test_result_to_status_response(
        self, mock_pipeline_result: PipelineResult
    ) -> None:
        """Should convert pipeline result to status response."""
        from src.web.routes.api import result_to_status_response

        response = result_to_status_response(mock_pipeline_result)

        assert response.job_id == "job-abc"
        assert response.pipeline_id == "test-123"
        assert response.status == "completed"
        assert response.job_title == "Senior Python Developer"
        assert response.company_name == "TechCorp"
        assert response.compatibility_score == 85.5
        assert len(response.steps) == 4

    def test_result_to_status_response_with_current_step(
        self, mock_running_result: PipelineResult
    ) -> None:
        """Should include current step for running pipeline."""
        from src.web.routes.api import result_to_status_response

        response = result_to_status_response(mock_running_result)

        assert response.status == "running"
        assert response.current_step == "creator"

    def test_result_to_status_response_with_error(
        self, mock_failed_result: PipelineResult
    ) -> None:
        """Should include error info for failed pipeline."""
        from src.web.routes.api import result_to_status_response

        response = result_to_status_response(mock_failed_result)

        assert response.status == "failed"
        assert response.error == "LLM service error"

    def test_result_to_job_summary(
        self, mock_pipeline_result: PipelineResult
    ) -> None:
        """Should convert pipeline result to job summary."""
        from src.web.routes.api import result_to_job_summary

        summary = result_to_job_summary(mock_pipeline_result)

        assert summary.job_id == "job-abc"
        assert summary.job_title == "Senior Python Developer"
        assert summary.company_name == "TechCorp"
        assert summary.status == "completed"
        assert summary.compatibility_score == 85.5

    def test_result_to_job_summary_uses_pipeline_id_fallback(self) -> None:
        """Should use pipeline_id if job_id is None."""
        from src.web.routes.api import result_to_job_summary

        result = PipelineResult(
            pipeline_id="pipe-123",
            status=PipelineStatus.COMPLETED,
            started_at=datetime.now(),
            job_id=None,
        )
        summary = result_to_job_summary(result)
        assert summary.job_id == "pipe-123"


# =============================================================================
# BACKGROUND TASK TESTS
# =============================================================================


class TestBackgroundTasks:
    """Tests for background task execution."""

    @pytest.mark.asyncio
    async def test_execute_pipeline_success(
        self, mock_pipeline_result: PipelineResult
    ) -> None:
        """Should store successful result."""
        from src.web.routes.api import execute_pipeline

        mock_orchestrator = Mock()
        mock_orchestrator.execute = AsyncMock(return_value=mock_pipeline_result)

        store = JobStore()
        input_data = PipelineInput(raw_job_text="x" * 100)

        await execute_pipeline(mock_orchestrator, store, input_data, "test-job")

        assert store.count() == 1
        result = store.get("job-abc")  # Uses job_id from result
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_pipeline_failure(self) -> None:
        """Should store error result on failure."""
        from src.web.routes.api import execute_pipeline

        mock_orchestrator = Mock()
        mock_orchestrator.execute = AsyncMock(
            side_effect=Exception("Pipeline failed")
        )

        store = JobStore()
        input_data = PipelineInput(raw_job_text="x" * 100)

        await execute_pipeline(mock_orchestrator, store, input_data, "fail-job")

        assert store.count() == 1
        result = store.get("fail-job")
        assert result is not None
        assert result.status == PipelineStatus.FAILED
        assert "Pipeline failed" in str(result.error)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestAPIIntegration:
    """Integration tests for full API flow."""

    @pytest.fixture
    def mock_orchestrator_with_result(
        self, mock_pipeline_result: PipelineResult
    ) -> Mock:
        """Create mock orchestrator that returns a result."""
        orchestrator = Mock()
        orchestrator.execute = AsyncMock(return_value=mock_pipeline_result)
        return orchestrator

    @pytest.fixture
    def integration_client(
        self, mock_orchestrator_with_result: Mock
    ) -> Generator[TestClient, None, None]:
        """Create test client for integration tests."""
        reset_job_store()

        from src.web.dependencies import get_orchestrator
        from src.web.main import app

        async def override_orchestrator() -> Mock:
            return mock_orchestrator_with_result

        app.dependency_overrides[get_orchestrator] = override_orchestrator

        yield TestClient(app, raise_server_exceptions=False)

        app.dependency_overrides.clear()
        reset_job_store()

    def test_full_apply_and_status_flow(
        self,
        integration_client: TestClient,
        sample_job_text: str,
        mock_pipeline_result: PipelineResult,
    ) -> None:
        """Should complete full apply -> status flow."""
        # Store a result to simulate background task completion
        store = get_job_store()
        store.store(mock_pipeline_result)

        # Check status
        response = integration_client.get("/api/status/job-abc")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["job_title"] == "Senior Python Developer"

    def test_list_jobs_after_apply(
        self,
        integration_client: TestClient,
        mock_pipeline_result: PipelineResult,
    ) -> None:
        """Should list job after apply."""
        store = get_job_store()
        store.store(mock_pipeline_result)

        response = integration_client.get("/api/jobs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["job_id"] == "job-abc"
