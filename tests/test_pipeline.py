"""
Unit tests for S6 Pipeline Orchestrator.

Run with: pytest tests/test_pipeline.py -v
"""

from datetime import datetime
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest

from src.modules.analyzer.models import (
    AnalysisResult,
    ApplicationStrategy,
    CompatibilityScore,
    MatchLevel,
)
from src.modules.creator.models import (
    CreatedContent,
    CVSection,
    GeneratedCoverLetter,
    GeneratedCV,
)
from src.modules.formatter.models import FormattedApplication, FormattedDocument
from src.modules.rinser.models import (
    CompanyInfo,
    ProcessedJob,
    Requirement,
    RequirementPriority,
)
from src.services.pipeline.exceptions import (
    InvalidInputError,
    PipelineError,
    PipelineNotInitializedError,
    StepError,
)
from src.services.pipeline.models import (
    PipelineInput,
    PipelineProgress,
    PipelineResult,
    PipelineStatus,
    PipelineStep,
    StepResult,
    StepStatus,
)
from src.services.pipeline.pipeline import (
    PipelineOrchestrator,
    reset_pipeline_orchestrator,
)

# =============================================================================
# TEST DATA FIXTURES
# =============================================================================


@pytest.fixture
def mock_processed_job() -> ProcessedJob:
    """Create mock processed job."""
    return ProcessedJob(
        id="job-123",
        title="Software Engineer",
        company=CompanyInfo(name="TestCorp", industry="Technology"),
        location="Remote",
        requirements=[
            Requirement(
                text="Python experience",
                priority=RequirementPriority.MUST_HAVE,
            ),
            Requirement(
                text="Git experience",
                priority=RequirementPriority.NICE_TO_HAVE,
            ),
        ],
        responsibilities=[],
        raw_text="Test job " * 50,  # At least 100 chars
    )


@pytest.fixture
def mock_analysis() -> AnalysisResult:
    """Create mock analysis result."""
    return AnalysisResult(
        job_id="job-123",
        job_title="Software Engineer",
        company_name="TestCorp",
        compatibility=CompatibilityScore(
            overall=75.0,
            level=MatchLevel.STRONG,
            technical_skills=80,
            experience_relevance=70,
            requirements_met=75,
            must_haves_met=2,
            must_haves_total=3,
        ),
        skill_matches=[],
        experience_matches=[],
        gaps=[],
        strategy=ApplicationStrategy(
            positioning="Strong Python developer",
            key_strengths=["Python", "Problem-solving"],
            address_gaps=[],
            tone="professional",
        ),
    )


@pytest.fixture
def mock_content() -> CreatedContent:
    """Create mock created content."""
    return CreatedContent(
        job_id="job-123",
        job_title="Software Engineer",
        company_name="TestCorp",
        cv=GeneratedCV(
            full_name="Test User",
            email="test@example.com",
            location="Test City",
            professional_summary="Experienced developer",
            sections=[
                CVSection(
                    section_type="experience",
                    title="Work Experience",
                    content="Developer at TechCorp",
                    bullet_points=["Built APIs", "Led team"],
                ),
            ],
            technical_skills=["Python", "JavaScript"],
            soft_skills=["Leadership"],
            target_job_title="Software Engineer",
            target_company="TestCorp",
        ),
        cover_letter=GeneratedCoverLetter(
            company_name="TestCorp",
            job_title="Software Engineer",
            opening="I am excited to apply...",
            body_paragraphs=["My experience includes..."],
            closing="I look forward to...",
            word_count=150,
        ),
        compatibility_score=75.0,
    )


@pytest.fixture
def mock_formatted(tmp_path: Path) -> FormattedApplication:
    """Create mock formatted application."""
    cv_path = tmp_path / "cv.pdf"
    cv_path.write_bytes(b"PDF content CV")
    letter_path = tmp_path / "cover_letter.pdf"
    letter_path.write_bytes(b"PDF content Letter")

    return FormattedApplication(
        job_id="job-123",
        job_title="Software Engineer",
        company_name="TestCorp",
        cv=FormattedDocument(
            document_type="cv",
            file_path=cv_path,
            file_size_bytes=100,
        ),
        cover_letter=FormattedDocument(
            document_type="cover_letter",
            file_path=letter_path,
            file_size_bytes=100,
        ),
        output_dir=tmp_path,
    )


# =============================================================================
# MODULE MOCK FIXTURES
# =============================================================================


@pytest.fixture
def mock_collector() -> Mock:
    """Create mock Collector."""
    collector = Mock()
    collector.get_profile = Mock(return_value=None)
    return collector


@pytest.fixture
def mock_rinser(mock_processed_job: ProcessedJob) -> Mock:
    """Create mock Rinser."""
    rinser = Mock()
    rinser.process_job = AsyncMock(return_value=mock_processed_job)
    return rinser


@pytest.fixture
def mock_analyzer(mock_analysis: AnalysisResult) -> Mock:
    """Create mock Analyzer."""
    analyzer = Mock()
    analyzer.analyze = AsyncMock(return_value=mock_analysis)
    return analyzer


@pytest.fixture
def mock_creator(mock_content: CreatedContent) -> Mock:
    """Create mock Creator."""
    creator = Mock()
    creator.create_content = AsyncMock(return_value=mock_content)
    return creator


@pytest.fixture
def mock_formatter(mock_formatted: FormattedApplication) -> Mock:
    """Create mock Formatter."""
    formatter = Mock()
    formatter.format_application = AsyncMock(return_value=mock_formatted)
    return formatter


@pytest.fixture
def orchestrator(
    mock_collector: Mock,
    mock_rinser: Mock,
    mock_analyzer: Mock,
    mock_creator: Mock,
    mock_formatter: Mock,
) -> PipelineOrchestrator:
    """Create Pipeline Orchestrator for testing."""
    return PipelineOrchestrator(
        collector=mock_collector,
        rinser=mock_rinser,
        analyzer=mock_analyzer,
        creator=mock_creator,
        formatter=mock_formatter,
    )


@pytest.fixture
def sample_job_text() -> str:
    """Sample job text of sufficient length."""
    return "Software Engineer Position " * 10


# =============================================================================
# MODEL TESTS
# =============================================================================


class TestPipelineModels:
    """Tests for pipeline data models."""

    def test_pipeline_step_values(self) -> None:
        """Should have all pipeline steps."""
        assert PipelineStep.RINSER == "rinser"
        assert PipelineStep.ANALYZER == "analyzer"
        assert PipelineStep.CREATOR == "creator"
        assert PipelineStep.FORMATTER == "formatter"

    def test_step_status_values(self) -> None:
        """Should have all step statuses."""
        assert StepStatus.PENDING == "pending"
        assert StepStatus.RUNNING == "running"
        assert StepStatus.COMPLETED == "completed"
        assert StepStatus.FAILED == "failed"
        assert StepStatus.SKIPPED == "skipped"

    def test_pipeline_status_values(self) -> None:
        """Should have all pipeline statuses."""
        assert PipelineStatus.PENDING == "pending"
        assert PipelineStatus.RUNNING == "running"
        assert PipelineStatus.COMPLETED == "completed"
        assert PipelineStatus.FAILED == "failed"

    def test_step_result_creation(self) -> None:
        """Should create step result."""
        result = StepResult(
            step=PipelineStep.RINSER,
            status=StepStatus.COMPLETED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            duration_ms=100,
        )
        assert result.step == PipelineStep.RINSER
        assert result.status == StepStatus.COMPLETED
        assert result.duration_ms == 100

    def test_step_result_with_error(self) -> None:
        """Should create step result with error."""
        result = StepResult(
            step=PipelineStep.ANALYZER,
            status=StepStatus.FAILED,
            error="Analysis failed",
        )
        assert result.status == StepStatus.FAILED
        assert result.error == "Analysis failed"

    def test_step_result_with_output(self) -> None:
        """Should create step result with output."""
        result = StepResult(
            step=PipelineStep.RINSER,
            status=StepStatus.COMPLETED,
            output={"job_id": "123", "title": "Test"},
        )
        assert result.output is not None
        assert result.output["job_id"] == "123"

    def test_pipeline_input_creation(self) -> None:
        """Should create pipeline input."""
        input_data = PipelineInput(raw_job_text="A" * 200)
        assert len(input_data.raw_job_text) == 200
        assert input_data.source is None
        assert input_data.skip_formatting is False

    def test_pipeline_input_with_source(self) -> None:
        """Should create pipeline input with source."""
        input_data = PipelineInput(
            raw_job_text="A" * 200,
            source="linkedin",
            skip_formatting=True,
        )
        assert input_data.source == "linkedin"
        assert input_data.skip_formatting is True

    def test_pipeline_input_min_length_validation(self) -> None:
        """Should require minimum text length."""
        with pytest.raises(ValueError):
            PipelineInput(raw_job_text="Too short")

    def test_pipeline_result_creation(self) -> None:
        """Should create pipeline result."""
        result = PipelineResult(
            pipeline_id="abc123",
            status=PipelineStatus.RUNNING,
            started_at=datetime.now(),
        )
        assert result.pipeline_id == "abc123"
        assert result.status == PipelineStatus.RUNNING
        assert result.steps == []

    def test_pipeline_result_is_success(self) -> None:
        """Should check success status."""
        result = PipelineResult(
            pipeline_id="abc123",
            status=PipelineStatus.COMPLETED,
            started_at=datetime.now(),
        )
        assert result.is_success is True

        result.status = PipelineStatus.FAILED
        assert result.is_success is False

    def test_pipeline_result_get_step_result(self) -> None:
        """Should get step result by step type."""
        result = PipelineResult(
            pipeline_id="abc123",
            status=PipelineStatus.COMPLETED,
            started_at=datetime.now(),
            steps=[
                StepResult(step=PipelineStep.RINSER, status=StepStatus.COMPLETED),
                StepResult(step=PipelineStep.ANALYZER, status=StepStatus.COMPLETED),
            ],
        )
        rinser_result = result.get_step_result(PipelineStep.RINSER)
        assert rinser_result is not None
        assert rinser_result.step == PipelineStep.RINSER

        formatter_result = result.get_step_result(PipelineStep.FORMATTER)
        assert formatter_result is None

    def test_pipeline_progress_creation(self) -> None:
        """Should create pipeline progress."""
        progress = PipelineProgress(
            pipeline_id="abc123",
            status=PipelineStatus.RUNNING,
            current_step=PipelineStep.ANALYZER,
            steps_completed=1,
            steps_total=4,
            progress_percent=25.0,
            message="Analyzing job...",
        )
        assert progress.progress_percent == 25.0
        assert progress.current_step == PipelineStep.ANALYZER


# =============================================================================
# EXCEPTION TESTS
# =============================================================================


class TestPipelineExceptions:
    """Tests for pipeline exceptions."""

    def test_pipeline_error(self) -> None:
        """Should create pipeline error."""
        error = PipelineError("Test error")
        assert str(error) == "Test error"

    def test_step_error(self) -> None:
        """Should create step error with step name."""
        error = StepError("rinser", "Failed to process")
        assert error.step == "rinser"
        assert "Rinser" in str(error)
        assert "Failed to process" in str(error)

    def test_pipeline_not_initialized_error(self) -> None:
        """Should create not initialized error."""
        error = PipelineNotInitializedError("Not ready")
        assert isinstance(error, PipelineError)

    def test_invalid_input_error(self) -> None:
        """Should create invalid input error."""
        error = InvalidInputError("Bad input")
        assert isinstance(error, PipelineError)


# =============================================================================
# ORCHESTRATOR INITIALIZATION TESTS
# =============================================================================


class TestOrchestratorInitialization:
    """Tests for orchestrator initialization."""

    @pytest.mark.asyncio
    async def test_initialize(self, orchestrator: PipelineOrchestrator) -> None:
        """Should initialize orchestrator."""
        assert orchestrator._initialized is False
        await orchestrator.initialize()
        assert orchestrator._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_idempotent(
        self, orchestrator: PipelineOrchestrator
    ) -> None:
        """Should handle multiple initialize calls."""
        await orchestrator.initialize()
        await orchestrator.initialize()  # Should not error
        assert orchestrator._initialized is True

    @pytest.mark.asyncio
    async def test_shutdown(self, orchestrator: PipelineOrchestrator) -> None:
        """Should shutdown orchestrator."""
        await orchestrator.initialize()
        await orchestrator.shutdown()
        assert orchestrator._initialized is False

    @pytest.mark.asyncio
    async def test_shutdown_not_initialized(
        self, orchestrator: PipelineOrchestrator
    ) -> None:
        """Should handle shutdown when not initialized."""
        await orchestrator.shutdown()  # Should not error
        assert orchestrator._initialized is False

    def test_steps_class_attribute(self) -> None:
        """Should have correct steps order."""
        assert PipelineOrchestrator.STEPS == [
            PipelineStep.RINSER,
            PipelineStep.ANALYZER,
            PipelineStep.CREATOR,
            PipelineStep.FORMATTER,
        ]


# =============================================================================
# EXECUTION TESTS
# =============================================================================


class TestPipelineExecution:
    """Tests for pipeline execution."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self, orchestrator: PipelineOrchestrator, sample_job_text: str
    ) -> None:
        """Should execute all steps successfully."""
        input_data = PipelineInput(raw_job_text=sample_job_text)

        result = await orchestrator.execute(input_data)

        assert result.is_success
        assert result.status == PipelineStatus.COMPLETED
        assert len(result.steps) == 4
        assert all(s.status == StepStatus.COMPLETED for s in result.steps)

    @pytest.mark.asyncio
    async def test_execute_captures_job_info(
        self, orchestrator: PipelineOrchestrator, sample_job_text: str
    ) -> None:
        """Should capture job information in result."""
        input_data = PipelineInput(raw_job_text=sample_job_text)

        result = await orchestrator.execute(input_data)

        assert result.job_id == "job-123"
        assert result.job_title == "Software Engineer"
        assert result.company_name == "TestCorp"
        assert result.compatibility_score == 75.0

    @pytest.mark.asyncio
    async def test_execute_captures_file_paths(
        self, orchestrator: PipelineOrchestrator, sample_job_text: str
    ) -> None:
        """Should capture output file paths."""
        input_data = PipelineInput(raw_job_text=sample_job_text)

        result = await orchestrator.execute(input_data)

        assert result.cv_path is not None
        assert result.cover_letter_path is not None
        assert "cv.pdf" in result.cv_path
        assert "cover_letter.pdf" in result.cover_letter_path

    @pytest.mark.asyncio
    async def test_execute_tracks_timing(
        self, orchestrator: PipelineOrchestrator, sample_job_text: str
    ) -> None:
        """Should track execution timing."""
        input_data = PipelineInput(raw_job_text=sample_job_text)

        result = await orchestrator.execute(input_data)

        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.total_duration_ms >= 0
        assert all(s.duration_ms >= 0 for s in result.steps)

    @pytest.mark.asyncio
    async def test_execute_generates_pipeline_id(
        self, orchestrator: PipelineOrchestrator, sample_job_text: str
    ) -> None:
        """Should generate unique pipeline ID."""
        input_data = PipelineInput(raw_job_text=sample_job_text)

        result1 = await orchestrator.execute(input_data)
        result2 = await orchestrator.execute(input_data)

        assert result1.pipeline_id != result2.pipeline_id
        assert len(result1.pipeline_id) == 8


# =============================================================================
# SKIP FORMATTING TESTS
# =============================================================================


class TestSkipFormatting:
    """Tests for skipping formatting."""

    @pytest.mark.asyncio
    async def test_skip_formatting(
        self,
        orchestrator: PipelineOrchestrator,
        mock_formatter: Mock,
        sample_job_text: str,
    ) -> None:
        """Should skip formatter when requested."""
        input_data = PipelineInput(
            raw_job_text=sample_job_text,
            skip_formatting=True,
        )

        result = await orchestrator.execute(input_data)

        assert result.is_success
        mock_formatter.format_application.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_formatting_marks_skipped(
        self, orchestrator: PipelineOrchestrator, sample_job_text: str
    ) -> None:
        """Should mark formatter step as skipped."""
        input_data = PipelineInput(
            raw_job_text=sample_job_text,
            skip_formatting=True,
        )

        result = await orchestrator.execute(input_data)

        formatter_step = result.get_step_result(PipelineStep.FORMATTER)
        assert formatter_step is not None
        assert formatter_step.status == StepStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_skip_formatting_no_file_paths(
        self, orchestrator: PipelineOrchestrator, sample_job_text: str
    ) -> None:
        """Should not have file paths when formatting skipped."""
        input_data = PipelineInput(
            raw_job_text=sample_job_text,
            skip_formatting=True,
        )

        result = await orchestrator.execute(input_data)

        assert result.cv_path is None
        assert result.cover_letter_path is None

    @pytest.mark.asyncio
    async def test_skip_formatting_still_has_other_data(
        self, orchestrator: PipelineOrchestrator, sample_job_text: str
    ) -> None:
        """Should still have job data when formatting skipped."""
        input_data = PipelineInput(
            raw_job_text=sample_job_text,
            skip_formatting=True,
        )

        result = await orchestrator.execute(input_data)

        assert result.job_id is not None
        assert result.job_title is not None
        assert result.compatibility_score is not None


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_rinser_failure(
        self,
        orchestrator: PipelineOrchestrator,
        mock_rinser: Mock,
        sample_job_text: str,
    ) -> None:
        """Should handle Rinser failure."""
        mock_rinser.process_job.side_effect = Exception("Rinser error")

        input_data = PipelineInput(raw_job_text=sample_job_text)
        result = await orchestrator.execute(input_data)

        assert not result.is_success
        assert result.status == PipelineStatus.FAILED
        assert result.failed_step == PipelineStep.RINSER
        assert "Rinser" in str(result.error)

    @pytest.mark.asyncio
    async def test_analyzer_failure(
        self,
        orchestrator: PipelineOrchestrator,
        mock_analyzer: Mock,
        sample_job_text: str,
    ) -> None:
        """Should handle Analyzer failure."""
        mock_analyzer.analyze.side_effect = Exception("Analyzer error")

        input_data = PipelineInput(raw_job_text=sample_job_text)
        result = await orchestrator.execute(input_data)

        assert not result.is_success
        assert result.failed_step == PipelineStep.ANALYZER
        assert "Analyzer" in str(result.error)

    @pytest.mark.asyncio
    async def test_creator_failure(
        self,
        orchestrator: PipelineOrchestrator,
        mock_creator: Mock,
        sample_job_text: str,
    ) -> None:
        """Should handle Creator failure."""
        mock_creator.create_content.side_effect = Exception("Creator error")

        input_data = PipelineInput(raw_job_text=sample_job_text)
        result = await orchestrator.execute(input_data)

        assert not result.is_success
        assert result.failed_step == PipelineStep.CREATOR
        assert "Creator" in str(result.error)

    @pytest.mark.asyncio
    async def test_formatter_failure(
        self,
        orchestrator: PipelineOrchestrator,
        mock_formatter: Mock,
        sample_job_text: str,
    ) -> None:
        """Should handle Formatter failure."""
        mock_formatter.format_application.side_effect = Exception("Formatter error")

        input_data = PipelineInput(raw_job_text=sample_job_text)
        result = await orchestrator.execute(input_data)

        assert not result.is_success
        assert result.failed_step == PipelineStep.FORMATTER
        assert "Formatter" in str(result.error)

    @pytest.mark.asyncio
    async def test_partial_results_on_rinser_failure(
        self,
        orchestrator: PipelineOrchestrator,
        mock_rinser: Mock,
        sample_job_text: str,
    ) -> None:
        """Should have no job info on rinser failure."""
        mock_rinser.process_job.side_effect = Exception("Rinser error")

        input_data = PipelineInput(raw_job_text=sample_job_text)
        result = await orchestrator.execute(input_data)

        assert result.job_id is None
        assert result.job_title is None

    @pytest.mark.asyncio
    async def test_partial_results_on_analyzer_failure(
        self,
        orchestrator: PipelineOrchestrator,
        mock_analyzer: Mock,
        sample_job_text: str,
    ) -> None:
        """Should have job info but no score on analyzer failure."""
        mock_analyzer.analyze.side_effect = Exception("Analyzer error")

        input_data = PipelineInput(raw_job_text=sample_job_text)
        result = await orchestrator.execute(input_data)

        # Should have job info from successful rinser step
        assert result.job_id == "job-123"
        assert result.job_title == "Software Engineer"
        # But no compatibility score
        assert result.compatibility_score is None

    @pytest.mark.asyncio
    async def test_partial_results_on_creator_failure(
        self,
        orchestrator: PipelineOrchestrator,
        mock_creator: Mock,
        sample_job_text: str,
    ) -> None:
        """Should preserve results from successful steps on creator failure."""
        mock_creator.create_content.side_effect = Exception("Creator error")

        input_data = PipelineInput(raw_job_text=sample_job_text)
        result = await orchestrator.execute(input_data)

        # Should have job info and score
        assert result.job_id == "job-123"
        assert result.compatibility_score == 75.0
        # But no file paths
        assert result.cv_path is None

    @pytest.mark.asyncio
    async def test_step_error_captured_in_steps(
        self,
        orchestrator: PipelineOrchestrator,
        mock_analyzer: Mock,
        sample_job_text: str,
    ) -> None:
        """Should capture error message in step result."""
        mock_analyzer.analyze.side_effect = Exception("Specific analyzer error")

        input_data = PipelineInput(raw_job_text=sample_job_text)
        result = await orchestrator.execute(input_data)

        analyzer_step = result.get_step_result(PipelineStep.ANALYZER)
        assert analyzer_step is not None
        assert analyzer_step.status == StepStatus.FAILED
        assert analyzer_step.error is not None
        assert "Specific analyzer error" in analyzer_step.error


# =============================================================================
# PROGRESS CALLBACK TESTS
# =============================================================================


class TestProgressCallback:
    """Tests for progress reporting."""

    @pytest.mark.asyncio
    async def test_progress_callback_called(
        self, orchestrator: PipelineOrchestrator, sample_job_text: str
    ) -> None:
        """Should call progress callback."""
        progress_updates: list[PipelineProgress] = []

        async def callback(progress: PipelineProgress) -> None:
            progress_updates.append(progress)

        input_data = PipelineInput(raw_job_text=sample_job_text)
        await orchestrator.execute(input_data, progress_callback=callback)

        assert len(progress_updates) > 0

    @pytest.mark.asyncio
    async def test_progress_callback_start_message(
        self, orchestrator: PipelineOrchestrator, sample_job_text: str
    ) -> None:
        """Should have start progress message."""
        progress_updates: list[PipelineProgress] = []

        async def callback(progress: PipelineProgress) -> None:
            progress_updates.append(progress)

        input_data = PipelineInput(raw_job_text=sample_job_text)
        await orchestrator.execute(input_data, progress_callback=callback)

        assert progress_updates[0].steps_completed == 0
        assert "Starting" in progress_updates[0].message

    @pytest.mark.asyncio
    async def test_progress_callback_completion_message(
        self, orchestrator: PipelineOrchestrator, sample_job_text: str
    ) -> None:
        """Should have completion progress message."""
        progress_updates: list[PipelineProgress] = []

        async def callback(progress: PipelineProgress) -> None:
            progress_updates.append(progress)

        input_data = PipelineInput(raw_job_text=sample_job_text)
        await orchestrator.execute(input_data, progress_callback=callback)

        assert progress_updates[-1].status == PipelineStatus.COMPLETED
        assert "completed" in progress_updates[-1].message

    @pytest.mark.asyncio
    async def test_progress_callback_step_updates(
        self, orchestrator: PipelineOrchestrator, sample_job_text: str
    ) -> None:
        """Should report progress for each step."""
        progress_updates: list[PipelineProgress] = []

        async def callback(progress: PipelineProgress) -> None:
            progress_updates.append(progress)

        input_data = PipelineInput(raw_job_text=sample_job_text)
        await orchestrator.execute(input_data, progress_callback=callback)

        # Should have updates for: start, each step (4), completion
        assert len(progress_updates) >= 6

    @pytest.mark.asyncio
    async def test_progress_callback_percent(
        self, orchestrator: PipelineOrchestrator, sample_job_text: str
    ) -> None:
        """Should calculate progress percentage."""
        progress_updates: list[PipelineProgress] = []

        async def callback(progress: PipelineProgress) -> None:
            progress_updates.append(progress)

        input_data = PipelineInput(raw_job_text=sample_job_text)
        await orchestrator.execute(input_data, progress_callback=callback)

        # First should be 0%
        assert progress_updates[0].progress_percent == 0.0
        # Last should be 100%
        assert progress_updates[-1].progress_percent == 100.0

    @pytest.mark.asyncio
    async def test_progress_callback_on_failure(
        self,
        orchestrator: PipelineOrchestrator,
        mock_analyzer: Mock,
        sample_job_text: str,
    ) -> None:
        """Should report failure in progress."""
        mock_analyzer.analyze.side_effect = Exception("Error")
        progress_updates: list[PipelineProgress] = []

        async def callback(progress: PipelineProgress) -> None:
            progress_updates.append(progress)

        input_data = PipelineInput(raw_job_text=sample_job_text)
        await orchestrator.execute(input_data, progress_callback=callback)

        assert progress_updates[-1].status == PipelineStatus.FAILED
        assert "failed" in progress_updates[-1].message


# =============================================================================
# SIMPLE EXECUTION TESTS
# =============================================================================


class TestSimpleExecution:
    """Tests for simple execution method."""

    @pytest.mark.asyncio
    async def test_execute_simple(
        self, orchestrator: PipelineOrchestrator, sample_job_text: str
    ) -> None:
        """Should execute with just text input."""
        result = await orchestrator.execute_simple(sample_job_text)

        assert result.is_success
        assert result.status == PipelineStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_simple_calls_execute(
        self, orchestrator: PipelineOrchestrator, sample_job_text: str
    ) -> None:
        """Should call full execute method."""
        result = await orchestrator.execute_simple(sample_job_text)

        assert len(result.steps) == 4
        assert result.job_id is not None


# =============================================================================
# SOURCE PARAMETER TESTS
# =============================================================================


class TestSourceParameter:
    """Tests for source parameter handling."""

    @pytest.mark.asyncio
    async def test_source_passed_to_rinser(
        self, orchestrator: PipelineOrchestrator, mock_rinser: Mock
    ) -> None:
        """Should pass source to rinser."""
        input_data = PipelineInput(
            raw_job_text="A" * 150,
            source="linkedin",
        )

        await orchestrator.execute(input_data)

        mock_rinser.process_job.assert_called_once()
        call_args = mock_rinser.process_job.call_args
        assert call_args.kwargs.get("source") == "linkedin"

    @pytest.mark.asyncio
    async def test_none_source(
        self, orchestrator: PipelineOrchestrator, mock_rinser: Mock
    ) -> None:
        """Should handle None source."""
        input_data = PipelineInput(raw_job_text="A" * 150)

        await orchestrator.execute(input_data)

        call_args = mock_rinser.process_job.call_args
        assert call_args.kwargs.get("source") is None


# =============================================================================
# SINGLETON TESTS
# =============================================================================


class TestSingleton:
    """Tests for singleton pattern."""

    def test_reset_singleton(self) -> None:
        """Should reset singleton instance."""
        reset_pipeline_orchestrator()
        # Should not raise - just resets the instance


# =============================================================================
# STEP EXECUTION ORDER TESTS
# =============================================================================


class TestStepExecutionOrder:
    """Tests for correct step execution order."""

    @pytest.mark.asyncio
    async def test_steps_execute_in_order(
        self,
        orchestrator: PipelineOrchestrator,
        mock_rinser: Mock,
        mock_analyzer: Mock,
        mock_creator: Mock,
        mock_formatter: Mock,
        sample_job_text: str,
    ) -> None:
        """Should execute steps in correct order."""
        call_order: list[str] = []

        async def track_rinser(*args: object, **kwargs: object) -> ProcessedJob:
            call_order.append("rinser")
            return cast(ProcessedJob, mock_rinser.process_job.return_value)

        async def track_analyzer(*args: object, **kwargs: object) -> AnalysisResult:
            call_order.append("analyzer")
            return cast(AnalysisResult, mock_analyzer.analyze.return_value)

        async def track_creator(*args: object, **kwargs: object) -> CreatedContent:
            call_order.append("creator")
            return cast(CreatedContent, mock_creator.create_content.return_value)

        async def track_formatter(
            *args: object, **kwargs: object
        ) -> FormattedApplication:
            call_order.append("formatter")
            return cast(
                FormattedApplication, mock_formatter.format_application.return_value
            )

        mock_rinser.process_job.side_effect = track_rinser
        mock_analyzer.analyze.side_effect = track_analyzer
        mock_creator.create_content.side_effect = track_creator
        mock_formatter.format_application.side_effect = track_formatter

        input_data = PipelineInput(raw_job_text=sample_job_text)
        await orchestrator.execute(input_data)

        assert call_order == ["rinser", "analyzer", "creator", "formatter"]

    @pytest.mark.asyncio
    async def test_steps_results_in_order(
        self, orchestrator: PipelineOrchestrator, sample_job_text: str
    ) -> None:
        """Should have step results in order."""
        input_data = PipelineInput(raw_job_text=sample_job_text)
        result = await orchestrator.execute(input_data)

        step_order = [s.step for s in result.steps]
        assert step_order == [
            PipelineStep.RINSER,
            PipelineStep.ANALYZER,
            PipelineStep.CREATOR,
            PipelineStep.FORMATTER,
        ]
