# S6 Pipeline Orchestrator - Claude Code Instructions

**Version:** 2.0 (PoC Aligned)  
**Updated:** November 26, 2025  
**Status:** Ready for Implementation  
**Priority:** Phase 3 - Integration (Build First in Phase 3)

---

## PoC Scope Summary

| Feature | Status | Notes |
|---------|--------|-------|
| Sequential pipeline execution | ✅ In Scope | Rinser → Analyzer → Creator → Formatter |
| Pipeline state tracking | ✅ In Scope | Current step, status |
| Error handling per step | ✅ In Scope | Capture and report errors |
| Pipeline result aggregation | ✅ In Scope | Combine all outputs |
| Parallel execution | ❌ Deferred | Sequential sufficient |
| DAG-based orchestration | ❌ Deferred | Linear pipeline only |
| Checkpointing/resume | ❌ Deferred | Full re-run acceptable |
| Pipeline versioning | ❌ Deferred | Not needed for PoC |

---

## Context & Objective

Build the **Pipeline Orchestrator** for Scout - coordinates the execution of all modules in sequence to process a job application from raw text to formatted PDFs.

### Why This Service Exists

The Pipeline Orchestrator:
- Provides a single entry point for the entire workflow
- Manages module execution order and dependencies
- Tracks progress and status
- Aggregates results from all steps
- Handles errors gracefully

This is the "glue" that ties all modules together.

### Dependencies

This service **requires** all modules to be implemented:
- **M2 Rinser**: Process raw job text
- **M3 Analyzer**: Analyze compatibility
- **M4 Creator**: Generate content
- **M5 Formatter**: Create PDFs
- **M1 Collector**: Profile data (via Analyzer)

---

## Technical Requirements

### File Structure

```
scout/
├── app/
│   ├── models/
│   │   └── pipeline.py          # Pipeline models
│   ├── services/
│   │   └── pipeline.py          # Pipeline Orchestrator
│   └── api/
│       └── routes/
│           └── pipeline.py      # API endpoints
└── tests/
    └── unit/
        └── services/
            └── test_pipeline.py
```

---

## Data Models

Create `app/models/pipeline.py`:

```python
"""
Pipeline Data Models

Models for pipeline execution and results.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PipelineStep(str, Enum):
    """Pipeline execution steps."""
    RINSER = "rinser"
    ANALYZER = "analyzer"
    CREATOR = "creator"
    FORMATTER = "formatter"


class StepStatus(str, Enum):
    """Status of a pipeline step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStatus(str, Enum):
    """Overall pipeline status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StepResult(BaseModel):
    """Result of a single pipeline step."""
    step: PipelineStep
    status: StepStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: int = 0
    error: Optional[str] = None
    output: Optional[Dict[str, Any]] = None  # Step-specific output


class PipelineInput(BaseModel):
    """Input for pipeline execution."""
    raw_job_text: str = Field(..., min_length=100)
    source: Optional[str] = None  # e.g., "linkedin", "indeed"
    skip_formatting: bool = False  # Skip PDF generation


class PipelineResult(BaseModel):
    """Complete pipeline execution result."""
    # Identification
    pipeline_id: str
    
    # Status
    status: PipelineStatus
    current_step: Optional[PipelineStep] = None
    
    # Timing
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_duration_ms: int = 0
    
    # Step results
    steps: List[StepResult] = Field(default_factory=list)
    
    # Outputs (references to actual data)
    job_id: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    compatibility_score: Optional[float] = None
    
    # Output files
    cv_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    
    # Error info
    error: Optional[str] = None
    failed_step: Optional[PipelineStep] = None
    
    def get_step_result(self, step: PipelineStep) -> Optional[StepResult]:
        """Get result for a specific step."""
        for result in self.steps:
            if result.step == step:
                return result
        return None
    
    @property
    def is_success(self) -> bool:
        """Check if pipeline completed successfully."""
        return self.status == PipelineStatus.COMPLETED


class PipelineProgress(BaseModel):
    """Real-time pipeline progress update."""
    pipeline_id: str
    status: PipelineStatus
    current_step: Optional[PipelineStep]
    steps_completed: int
    steps_total: int
    progress_percent: float
    message: str
```

---

## Service Implementation

Create `app/services/pipeline.py`:

```python
"""
Pipeline Orchestrator Service

Coordinates execution of all modules for job application processing.

Usage:
    orchestrator = PipelineOrchestrator(...)
    result = await orchestrator.execute(raw_job_text)
    
    if result.is_success:
        print(f"Application ready: {result.cv_path}")
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Callable, Awaitable

from app.models.pipeline import (
    PipelineInput, PipelineResult, PipelineProgress,
    PipelineStep, PipelineStatus, StepStatus, StepResult
)
from app.models.job import ProcessedJob
from app.models.analysis import AnalysisResult
from app.models.content import ApplicationPackage
from app.models.output import FormattedApplication
from app.core.collector import Collector
from app.core.rinser import Rinser
from app.core.analyzer import Analyzer
from app.core.creator import Creator
from app.core.formatter import Formatter
from app.utils.exceptions import ScoutError

logger = logging.getLogger(__name__)


class PipelineError(ScoutError):
    """Error in Pipeline execution."""
    pass


# Type for progress callback
ProgressCallback = Callable[[PipelineProgress], Awaitable[None]]


class PipelineOrchestrator:
    """
    Pipeline Orchestrator - coordinates module execution.
    
    Executes: Rinser → Analyzer → Creator → Formatter
    
    Attributes:
        collector: Collector module (pre-loaded)
        rinser: Rinser module
        analyzer: Analyzer module
        creator: Creator module
        formatter: Formatter module
        
    Example:
        >>> orchestrator = PipelineOrchestrator(...)
        >>> result = await orchestrator.execute(job_text)
        >>> if result.is_success:
        ...     print(f"CV: {result.cv_path}")
        ...     print(f"Score: {result.compatibility_score}%")
    """
    
    STEPS = [
        PipelineStep.RINSER,
        PipelineStep.ANALYZER,
        PipelineStep.CREATOR,
        PipelineStep.FORMATTER
    ]
    
    def __init__(
        self,
        collector: Collector,
        rinser: Rinser,
        analyzer: Analyzer,
        creator: Creator,
        formatter: Formatter
    ):
        """
        Initialize Pipeline Orchestrator.
        
        Args:
            collector: Initialized Collector with profile
            rinser: Rinser module
            analyzer: Analyzer module
            creator: Creator module
            formatter: Formatter module
        """
        self._collector = collector
        self._rinser = rinser
        self._analyzer = analyzer
        self._creator = creator
        self._formatter = formatter
        
        # Current execution state
        self._current_pipeline_id: Optional[str] = None
        self._progress_callback: Optional[ProgressCallback] = None
    
    async def _report_progress(
        self,
        pipeline_id: str,
        status: PipelineStatus,
        current_step: Optional[PipelineStep],
        steps_completed: int,
        message: str
    ) -> None:
        """Report progress via callback if set."""
        if self._progress_callback:
            progress = PipelineProgress(
                pipeline_id=pipeline_id,
                status=status,
                current_step=current_step,
                steps_completed=steps_completed,
                steps_total=len(self.STEPS),
                progress_percent=(steps_completed / len(self.STEPS)) * 100,
                message=message
            )
            await self._progress_callback(progress)
    
    def _create_step_result(
        self,
        step: PipelineStep,
        status: StepStatus,
        started_at: datetime,
        error: Optional[str] = None,
        output: Optional[dict] = None
    ) -> StepResult:
        """Create a step result with timing."""
        completed_at = datetime.now()
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        
        return StepResult(
            step=step,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            error=error,
            output=output
        )
    
    # =========================================================================
    # STEP EXECUTION
    # =========================================================================
    
    async def _execute_rinser(
        self,
        raw_text: str,
        source: Optional[str]
    ) -> ProcessedJob:
        """Execute Rinser step."""
        logger.info("Executing Rinser step")
        return await self._rinser.process_job(raw_text, source=source)
    
    async def _execute_analyzer(
        self,
        job: ProcessedJob
    ) -> AnalysisResult:
        """Execute Analyzer step."""
        logger.info("Executing Analyzer step")
        return await self._analyzer.analyze(job)
    
    async def _execute_creator(
        self,
        analysis: AnalysisResult
    ) -> ApplicationPackage:
        """Execute Creator step."""
        logger.info("Executing Creator step")
        return await self._creator.create_application(analysis)
    
    async def _execute_formatter(
        self,
        package: ApplicationPackage
    ) -> FormattedApplication:
        """Execute Formatter step."""
        logger.info("Executing Formatter step")
        return await self._formatter.format_application(package)
    
    # =========================================================================
    # MAIN EXECUTION
    # =========================================================================
    
    async def execute(
        self,
        input_data: PipelineInput,
        progress_callback: Optional[ProgressCallback] = None
    ) -> PipelineResult:
        """
        Execute the complete pipeline.
        
        Main entry point for processing a job application.
        
        Args:
            input_data: Pipeline input with raw job text
            progress_callback: Optional async callback for progress updates
            
        Returns:
            PipelineResult with all outputs
            
        Example:
            >>> input_data = PipelineInput(raw_job_text="...")
            >>> result = await orchestrator.execute(input_data)
            >>> print(f"Status: {result.status}")
        """
        pipeline_id = str(uuid.uuid4())[:8]
        self._current_pipeline_id = pipeline_id
        self._progress_callback = progress_callback
        
        started_at = datetime.now()
        
        result = PipelineResult(
            pipeline_id=pipeline_id,
            status=PipelineStatus.RUNNING,
            started_at=started_at,
            steps=[]
        )
        
        logger.info(f"Starting pipeline {pipeline_id}")
        await self._report_progress(
            pipeline_id, PipelineStatus.RUNNING, None, 0,
            "Starting pipeline execution"
        )
        
        # Track intermediate results
        processed_job: Optional[ProcessedJob] = None
        analysis: Optional[AnalysisResult] = None
        package: Optional[ApplicationPackage] = None
        formatted: Optional[FormattedApplication] = None
        
        steps_completed = 0
        
        try:
            # Step 1: Rinser
            result.current_step = PipelineStep.RINSER
            step_start = datetime.now()
            
            await self._report_progress(
                pipeline_id, PipelineStatus.RUNNING, PipelineStep.RINSER,
                steps_completed, "Processing job posting..."
            )
            
            try:
                processed_job = await self._execute_rinser(
                    input_data.raw_job_text,
                    input_data.source
                )
                result.steps.append(self._create_step_result(
                    PipelineStep.RINSER, StepStatus.COMPLETED, step_start,
                    output={"job_id": processed_job.id, "title": processed_job.title}
                ))
                result.job_id = processed_job.id
                result.job_title = processed_job.title
                result.company_name = processed_job.company.name
                steps_completed += 1
                
            except Exception as e:
                result.steps.append(self._create_step_result(
                    PipelineStep.RINSER, StepStatus.FAILED, step_start,
                    error=str(e)
                ))
                raise PipelineError(f"Rinser failed: {e}")
            
            # Step 2: Analyzer
            result.current_step = PipelineStep.ANALYZER
            step_start = datetime.now()
            
            await self._report_progress(
                pipeline_id, PipelineStatus.RUNNING, PipelineStep.ANALYZER,
                steps_completed, "Analyzing compatibility..."
            )
            
            try:
                analysis = await self._execute_analyzer(processed_job)
                result.steps.append(self._create_step_result(
                    PipelineStep.ANALYZER, StepStatus.COMPLETED, step_start,
                    output={
                        "compatibility": analysis.compatibility.overall,
                        "level": analysis.compatibility.level.value
                    }
                ))
                result.compatibility_score = analysis.compatibility.overall
                steps_completed += 1
                
            except Exception as e:
                result.steps.append(self._create_step_result(
                    PipelineStep.ANALYZER, StepStatus.FAILED, step_start,
                    error=str(e)
                ))
                raise PipelineError(f"Analyzer failed: {e}")
            
            # Step 3: Creator
            result.current_step = PipelineStep.CREATOR
            step_start = datetime.now()
            
            await self._report_progress(
                pipeline_id, PipelineStatus.RUNNING, PipelineStep.CREATOR,
                steps_completed, "Generating application content..."
            )
            
            try:
                package = await self._execute_creator(analysis)
                result.steps.append(self._create_step_result(
                    PipelineStep.CREATOR, StepStatus.COMPLETED, step_start,
                    output={"cv_sections": len(package.cv.sections)}
                ))
                steps_completed += 1
                
            except Exception as e:
                result.steps.append(self._create_step_result(
                    PipelineStep.CREATOR, StepStatus.FAILED, step_start,
                    error=str(e)
                ))
                raise PipelineError(f"Creator failed: {e}")
            
            # Step 4: Formatter (optional)
            if not input_data.skip_formatting:
                result.current_step = PipelineStep.FORMATTER
                step_start = datetime.now()
                
                await self._report_progress(
                    pipeline_id, PipelineStatus.RUNNING, PipelineStep.FORMATTER,
                    steps_completed, "Generating PDF documents..."
                )
                
                try:
                    formatted = await self._execute_formatter(package)
                    result.steps.append(self._create_step_result(
                        PipelineStep.FORMATTER, StepStatus.COMPLETED, step_start,
                        output={
                            "cv_size": formatted.cv.file_size_bytes,
                            "letter_size": formatted.cover_letter.file_size_bytes
                        }
                    ))
                    result.cv_path = str(formatted.cv.file_path)
                    result.cover_letter_path = str(formatted.cover_letter.file_path)
                    steps_completed += 1
                    
                except Exception as e:
                    result.steps.append(self._create_step_result(
                        PipelineStep.FORMATTER, StepStatus.FAILED, step_start,
                        error=str(e)
                    ))
                    raise PipelineError(f"Formatter failed: {e}")
            else:
                result.steps.append(StepResult(
                    step=PipelineStep.FORMATTER,
                    status=StepStatus.SKIPPED
                ))
                steps_completed += 1
            
            # Success
            result.status = PipelineStatus.COMPLETED
            result.current_step = None
            
        except PipelineError as e:
            result.status = PipelineStatus.FAILED
            result.error = str(e)
            result.failed_step = result.current_step
            logger.error(f"Pipeline {pipeline_id} failed: {e}")
        
        except Exception as e:
            result.status = PipelineStatus.FAILED
            result.error = f"Unexpected error: {e}"
            result.failed_step = result.current_step
            logger.exception(f"Pipeline {pipeline_id} unexpected error")
        
        finally:
            result.completed_at = datetime.now()
            result.total_duration_ms = int(
                (result.completed_at - result.started_at).total_seconds() * 1000
            )
            
            await self._report_progress(
                pipeline_id,
                result.status,
                None,
                steps_completed,
                f"Pipeline {'completed' if result.is_success else 'failed'}"
            )
            
            logger.info(
                f"Pipeline {pipeline_id} {result.status.value} "
                f"in {result.total_duration_ms}ms"
            )
        
        return result
    
    async def execute_simple(
        self,
        raw_job_text: str
    ) -> PipelineResult:
        """
        Simple execution with just job text.
        
        Convenience method for basic usage.
        
        Args:
            raw_job_text: Raw job posting text
            
        Returns:
            PipelineResult
        """
        input_data = PipelineInput(raw_job_text=raw_job_text)
        return await self.execute(input_data)


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

async def create_pipeline_orchestrator(
    collector: Collector,
    llm_service,
    vector_store
) -> PipelineOrchestrator:
    """
    Create a fully initialized Pipeline Orchestrator.
    
    Args:
        collector: Initialized Collector
        llm_service: LLM Service instance
        vector_store: Vector Store instance
        
    Returns:
        Configured PipelineOrchestrator
    """
    rinser = Rinser(llm_service, vector_store)
    analyzer = Analyzer(collector, vector_store, llm_service)
    creator = Creator(collector, llm_service)
    formatter = Formatter()
    
    return PipelineOrchestrator(
        collector=collector,
        rinser=rinser,
        analyzer=analyzer,
        creator=creator,
        formatter=formatter
    )
```

---

## Test Implementation

Create `tests/unit/services/test_pipeline.py`:

```python
"""
Unit tests for Pipeline Orchestrator.

Run with: pytest tests/unit/services/test_pipeline.py -v
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock

from app.services.pipeline import (
    PipelineOrchestrator, PipelineError, create_pipeline_orchestrator
)
from app.models.pipeline import (
    PipelineInput, PipelineResult, PipelineStatus, 
    PipelineStep, StepStatus
)
from app.models.job import ProcessedJob, CompanyInfo, Requirement, RequirementPriority
from app.models.analysis import AnalysisResult, CompatibilityScore, MatchLevel
from app.models.content import (
    ApplicationPackage, GeneratedCV, GeneratedCoverLetter
)
from app.models.output import FormattedApplication, FormattedDocument
from pathlib import Path


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_processed_job():
    """Create mock processed job."""
    return ProcessedJob(
        id="job-123",
        title="Software Engineer",
        company=CompanyInfo(name="TestCorp"),
        requirements=[
            Requirement(text="Python", priority=RequirementPriority.MUST_HAVE)
        ],
        responsibilities=[],
        raw_text="Job text"
    )


@pytest.fixture
def mock_analysis():
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
            must_haves_total=3
        ),
        skill_matches=[],
        experience_matches=[],
        gaps=[]
    )


@pytest.fixture
def mock_package():
    """Create mock application package."""
    return ApplicationPackage(
        job_id="job-123",
        job_title="Software Engineer",
        company_name="TestCorp",
        cv=GeneratedCV(
            full_name="Test User",
            email="test@test.com",
            location="Test City",
            professional_summary="Summary",
            sections=[],
            technical_skills=["Python"],
            soft_skills=[],
            target_job_title="Software Engineer",
            target_company="TestCorp"
        ),
        cover_letter=GeneratedCoverLetter(
            company_name="TestCorp",
            job_title="Software Engineer",
            opening="Opening",
            body_paragraphs=["Body"],
            closing="Closing",
            word_count=50
        ),
        compatibility_score=75.0
    )


@pytest.fixture
def mock_formatted(tmp_path):
    """Create mock formatted application."""
    cv_path = tmp_path / "cv.pdf"
    cv_path.write_bytes(b"PDF content")
    letter_path = tmp_path / "cover_letter.pdf"
    letter_path.write_bytes(b"PDF content")
    
    return FormattedApplication(
        job_id="job-123",
        job_title="Software Engineer",
        company_name="TestCorp",
        cv=FormattedDocument(
            document_type="cv",
            file_path=cv_path,
            file_size_bytes=100
        ),
        cover_letter=FormattedDocument(
            document_type="cover_letter",
            file_path=letter_path,
            file_size_bytes=100
        ),
        output_dir=tmp_path
    )


@pytest.fixture
def mock_collector():
    """Create mock Collector."""
    return Mock()


@pytest.fixture
def mock_rinser(mock_processed_job):
    """Create mock Rinser."""
    rinser = Mock()
    rinser.process_job = AsyncMock(return_value=mock_processed_job)
    return rinser


@pytest.fixture
def mock_analyzer(mock_analysis):
    """Create mock Analyzer."""
    analyzer = Mock()
    analyzer.analyze = AsyncMock(return_value=mock_analysis)
    return analyzer


@pytest.fixture
def mock_creator(mock_package):
    """Create mock Creator."""
    creator = Mock()
    creator.create_application = AsyncMock(return_value=mock_package)
    return creator


@pytest.fixture
def mock_formatter(mock_formatted):
    """Create mock Formatter."""
    formatter = Mock()
    formatter.format_application = AsyncMock(return_value=mock_formatted)
    return formatter


@pytest.fixture
def orchestrator(mock_collector, mock_rinser, mock_analyzer, mock_creator, mock_formatter):
    """Create Pipeline Orchestrator for testing."""
    return PipelineOrchestrator(
        collector=mock_collector,
        rinser=mock_rinser,
        analyzer=mock_analyzer,
        creator=mock_creator,
        formatter=mock_formatter
    )


# =============================================================================
# EXECUTION TESTS
# =============================================================================

class TestPipelineExecution:
    """Tests for pipeline execution."""
    
    @pytest.mark.asyncio
    async def test_execute_success(self, orchestrator):
        """Should execute all steps successfully."""
        input_data = PipelineInput(raw_job_text="A" * 200)
        
        result = await orchestrator.execute(input_data)
        
        assert result.is_success
        assert result.status == PipelineStatus.COMPLETED
        assert len(result.steps) == 4
        assert all(s.status == StepStatus.COMPLETED for s in result.steps)
    
    @pytest.mark.asyncio
    async def test_execute_captures_job_info(self, orchestrator):
        """Should capture job information in result."""
        input_data = PipelineInput(raw_job_text="A" * 200)
        
        result = await orchestrator.execute(input_data)
        
        assert result.job_id == "job-123"
        assert result.job_title == "Software Engineer"
        assert result.company_name == "TestCorp"
        assert result.compatibility_score == 75.0
    
    @pytest.mark.asyncio
    async def test_execute_captures_file_paths(self, orchestrator):
        """Should capture output file paths."""
        input_data = PipelineInput(raw_job_text="A" * 200)
        
        result = await orchestrator.execute(input_data)
        
        assert result.cv_path is not None
        assert result.cover_letter_path is not None
    
    @pytest.mark.asyncio
    async def test_execute_tracks_timing(self, orchestrator):
        """Should track execution timing."""
        input_data = PipelineInput(raw_job_text="A" * 200)
        
        result = await orchestrator.execute(input_data)
        
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.total_duration_ms > 0
        assert all(s.duration_ms >= 0 for s in result.steps)


# =============================================================================
# SKIP FORMATTING TESTS
# =============================================================================

class TestSkipFormatting:
    """Tests for skipping formatting."""
    
    @pytest.mark.asyncio
    async def test_skip_formatting(self, orchestrator, mock_formatter):
        """Should skip formatter when requested."""
        input_data = PipelineInput(
            raw_job_text="A" * 200,
            skip_formatting=True
        )
        
        result = await orchestrator.execute(input_data)
        
        assert result.is_success
        mock_formatter.format_application.assert_not_called()
        
        # Formatter step should be skipped
        formatter_step = result.get_step_result(PipelineStep.FORMATTER)
        assert formatter_step.status == StepStatus.SKIPPED


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_rinser_failure(self, orchestrator, mock_rinser):
        """Should handle Rinser failure."""
        mock_rinser.process_job.side_effect = Exception("Rinser error")
        
        input_data = PipelineInput(raw_job_text="A" * 200)
        result = await orchestrator.execute(input_data)
        
        assert not result.is_success
        assert result.status == PipelineStatus.FAILED
        assert result.failed_step == PipelineStep.RINSER
        assert "Rinser" in result.error
    
    @pytest.mark.asyncio
    async def test_analyzer_failure(self, orchestrator, mock_analyzer):
        """Should handle Analyzer failure."""
        mock_analyzer.analyze.side_effect = Exception("Analyzer error")
        
        input_data = PipelineInput(raw_job_text="A" * 200)
        result = await orchestrator.execute(input_data)
        
        assert not result.is_success
        assert result.failed_step == PipelineStep.ANALYZER
    
    @pytest.mark.asyncio
    async def test_partial_results_on_failure(self, orchestrator, mock_creator):
        """Should preserve partial results on failure."""
        mock_creator.create_application.side_effect = Exception("Creator error")
        
        input_data = PipelineInput(raw_job_text="A" * 200)
        result = await orchestrator.execute(input_data)
        
        # Should have job info from successful steps
        assert result.job_id == "job-123"
        assert result.compatibility_score == 75.0
        # But no file paths
        assert result.cv_path is None


# =============================================================================
# PROGRESS CALLBACK TESTS
# =============================================================================

class TestProgressCallback:
    """Tests for progress reporting."""
    
    @pytest.mark.asyncio
    async def test_progress_callback_called(self, orchestrator):
        """Should call progress callback."""
        progress_updates = []
        
        async def callback(progress):
            progress_updates.append(progress)
        
        input_data = PipelineInput(raw_job_text="A" * 200)
        await orchestrator.execute(input_data, progress_callback=callback)
        
        assert len(progress_updates) > 0
        # Should have updates for start, each step, and completion
        assert progress_updates[0].steps_completed == 0
        assert progress_updates[-1].status == PipelineStatus.COMPLETED


# =============================================================================
# SIMPLE EXECUTION TESTS
# =============================================================================

class TestSimpleExecution:
    """Tests for simple execution method."""
    
    @pytest.mark.asyncio
    async def test_execute_simple(self, orchestrator):
        """Should execute with just text input."""
        result = await orchestrator.execute_simple("A" * 200)
        
        assert result.is_success
```

---

## Implementation Steps

### Step S6.1: Data Models
```bash
# Create app/models/pipeline.py
# Verify:
python -c "from app.models.pipeline import PipelineResult, PipelineStatus; print('OK')"
```

### Step S6.2: Service Implementation
```bash
# Create app/services/pipeline.py
# Verify:
python -c "from app.services.pipeline import PipelineOrchestrator; print('OK')"
```

### Step S6.3: Unit Tests
```bash
# Create tests/unit/services/test_pipeline.py
# Verify:
pytest tests/unit/services/test_pipeline.py -v
```

### Step S6.4: Integration Test
```bash
# Full pipeline test (after all modules ready):
python -c "
import asyncio
from app.services.pipeline import create_pipeline_orchestrator
# ... setup and execute full pipeline ...
"
```

---

## Success Criteria

| Metric | Target | Verification |
|--------|--------|--------------|
| Sequential execution | All steps in order | Check step order |
| Error propagation | Failures captured | Test each step failure |
| Result aggregation | All data collected | Check result fields |
| Progress tracking | Updates provided | Test callback |
| Test coverage | >90% | `pytest --cov=app/services/pipeline` |

---

*This specification is aligned with Scout PoC Scope Document v1.0*
