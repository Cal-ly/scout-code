"""
Pipeline Orchestrator Service

Coordinates execution of all modules for job application processing.

Usage:
    from src.services.pipeline import PipelineOrchestrator, get_pipeline_orchestrator

    # Singleton access (for FastAPI)
    orchestrator = await get_pipeline_orchestrator()
    result = await orchestrator.execute(input_data)

    # Manual instantiation (for testing)
    orchestrator = PipelineOrchestrator(
        collector=collector,
        rinser=rinser,
        analyzer=analyzer,
        creator=creator,
        formatter=formatter
    )
    await orchestrator.initialize()
    result = await orchestrator.execute(input_data)
"""

import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime

from src.modules.analyzer import AnalysisResult, Analyzer
from src.modules.collector import Collector
from src.modules.creator import CreatedContent, Creator
from src.modules.formatter import FormattedApplication, Formatter
from src.modules.rinser import ProcessedJob, Rinser
from src.services.pipeline.exceptions import StepError
from src.services.pipeline.models import (
    PipelineInput,
    PipelineProgress,
    PipelineResult,
    PipelineStatus,
    PipelineStep,
    StepResult,
    StepStatus,
)

logger = logging.getLogger(__name__)

# Type for progress callback
ProgressCallback = Callable[[PipelineProgress], Awaitable[None]]


class PipelineOrchestrator:
    """
    Pipeline Orchestrator - coordinates module execution.

    Executes: Rinser -> Analyzer -> Creator -> Formatter

    Attributes:
        collector: Collector module (pre-loaded).
        rinser: Rinser module.
        analyzer: Analyzer module.
        creator: Creator module.
        formatter: Formatter module.

    Example:
        >>> orchestrator = PipelineOrchestrator(...)
        >>> await orchestrator.initialize()
        >>> input_data = PipelineInput(raw_job_text="...")
        >>> result = await orchestrator.execute(input_data)
        >>> if result.is_success:
        ...     print(f"CV: {result.cv_path}")
        ...     print(f"Score: {result.compatibility_score}%")
    """

    STEPS = [
        PipelineStep.RINSER,
        PipelineStep.ANALYZER,
        PipelineStep.CREATOR,
        PipelineStep.FORMATTER,
    ]

    def __init__(
        self,
        collector: Collector,
        rinser: Rinser,
        analyzer: Analyzer,
        creator: Creator,
        formatter: Formatter,
    ):
        """
        Initialize Pipeline Orchestrator.

        Args:
            collector: Initialized Collector with profile.
            rinser: Rinser module.
            analyzer: Analyzer module.
            creator: Creator module.
            formatter: Formatter module.
        """
        self._collector = collector
        self._rinser = rinser
        self._analyzer = analyzer
        self._creator = creator
        self._formatter = formatter

        # Initialization state
        self._initialized = False

        # Current execution state
        self._current_pipeline_id: str | None = None
        self._progress_callback: ProgressCallback | None = None

    async def initialize(self) -> None:
        """
        Initialize the pipeline orchestrator.

        Ensures all modules are ready.
        """
        if self._initialized:
            logger.warning("Pipeline orchestrator already initialized")
            return

        logger.info("Initializing pipeline orchestrator")
        self._initialized = True
        logger.info("Pipeline orchestrator initialized")

    async def shutdown(self) -> None:
        """Gracefully shutdown the orchestrator."""
        if not self._initialized:
            return

        logger.info("Shutting down pipeline orchestrator")
        self._initialized = False

    async def _report_progress(
        self,
        pipeline_id: str,
        status: PipelineStatus,
        current_step: PipelineStep | None,
        steps_completed: int,
        message: str,
    ) -> None:
        """Report progress via callback if set.

        Callback errors are logged but not raised to prevent
        callback failures from crashing the pipeline.
        """
        if self._progress_callback:
            progress = PipelineProgress(
                pipeline_id=pipeline_id,
                status=status,
                current_step=current_step,
                steps_completed=steps_completed,
                steps_total=len(self.STEPS),
                progress_percent=(steps_completed / len(self.STEPS)) * 100,
                message=message,
            )
            try:
                await self._progress_callback(progress)
            except Exception as e:
                logger.warning(
                    f"Progress callback failed for pipeline {pipeline_id}: {e}"
                )

    def _create_step_result(
        self,
        step: PipelineStep,
        status: StepStatus,
        started_at: datetime,
        error: str | None = None,
        output: dict | None = None,
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
            output=output,
        )

    # =========================================================================
    # STEP EXECUTION
    # =========================================================================

    async def _execute_rinser(
        self,
        raw_text: str,
        source: str | None,
    ) -> ProcessedJob:
        """Execute Rinser step."""
        logger.info("Executing Rinser step")
        return await self._rinser.process_job(raw_text, source=source)

    async def _execute_analyzer(
        self,
        job: ProcessedJob,
    ) -> AnalysisResult:
        """Execute Analyzer step."""
        logger.info("Executing Analyzer step")
        return await self._analyzer.analyze(job)

    async def _execute_creator(
        self,
        analysis: AnalysisResult,
    ) -> CreatedContent:
        """Execute Creator step."""
        logger.info("Executing Creator step")
        return await self._creator.create_content(analysis)

    async def _execute_formatter(
        self,
        content: CreatedContent,
    ) -> FormattedApplication:
        """Execute Formatter step."""
        logger.info("Executing Formatter step")
        return await self._formatter.format_application(content)

    # =========================================================================
    # MAIN EXECUTION
    # =========================================================================

    async def execute(
        self,
        input_data: PipelineInput,
        progress_callback: ProgressCallback | None = None,
    ) -> PipelineResult:
        """
        Execute the complete pipeline.

        Main entry point for processing a job application.

        Args:
            input_data: Pipeline input with raw job text.
            progress_callback: Optional async callback for progress updates.

        Returns:
            PipelineResult with all outputs.

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
            steps=[],
        )

        logger.info(f"Starting pipeline {pipeline_id}")
        await self._report_progress(
            pipeline_id,
            PipelineStatus.RUNNING,
            None,
            0,
            "Starting pipeline execution",
        )

        # Track intermediate results
        processed_job: ProcessedJob | None = None
        analysis: AnalysisResult | None = None
        content: CreatedContent | None = None
        formatted: FormattedApplication | None = None

        steps_completed = 0

        try:
            # Step 1: Rinser
            result.current_step = PipelineStep.RINSER
            step_start = datetime.now()

            await self._report_progress(
                pipeline_id,
                PipelineStatus.RUNNING,
                PipelineStep.RINSER,
                steps_completed,
                "Processing job posting...",
            )

            try:
                processed_job = await self._execute_rinser(
                    input_data.raw_job_text,
                    input_data.source,
                )
                result.steps.append(
                    self._create_step_result(
                        PipelineStep.RINSER,
                        StepStatus.COMPLETED,
                        step_start,
                        output={
                            "job_id": processed_job.id,
                            "title": processed_job.title,
                        },
                    )
                )
                result.job_id = processed_job.id
                result.job_title = processed_job.title
                result.company_name = processed_job.company.name
                steps_completed += 1

            except Exception as e:
                result.steps.append(
                    self._create_step_result(
                        PipelineStep.RINSER,
                        StepStatus.FAILED,
                        step_start,
                        error=str(e),
                    )
                )
                raise StepError("rinser", str(e)) from e

            # Step 2: Analyzer
            result.current_step = PipelineStep.ANALYZER
            step_start = datetime.now()

            await self._report_progress(
                pipeline_id,
                PipelineStatus.RUNNING,
                PipelineStep.ANALYZER,
                steps_completed,
                "Analyzing compatibility...",
            )

            try:
                analysis = await self._execute_analyzer(processed_job)
                result.steps.append(
                    self._create_step_result(
                        PipelineStep.ANALYZER,
                        StepStatus.COMPLETED,
                        step_start,
                        output={
                            "compatibility": analysis.compatibility.overall,
                            "level": analysis.compatibility.level.value,
                        },
                    )
                )
                result.compatibility_score = analysis.compatibility.overall
                steps_completed += 1

            except Exception as e:
                result.steps.append(
                    self._create_step_result(
                        PipelineStep.ANALYZER,
                        StepStatus.FAILED,
                        step_start,
                        error=str(e),
                    )
                )
                raise StepError("analyzer", str(e)) from e

            # Step 3: Creator
            result.current_step = PipelineStep.CREATOR
            step_start = datetime.now()

            await self._report_progress(
                pipeline_id,
                PipelineStatus.RUNNING,
                PipelineStep.CREATOR,
                steps_completed,
                "Generating application content...",
            )

            try:
                content = await self._execute_creator(analysis)
                result.steps.append(
                    self._create_step_result(
                        PipelineStep.CREATOR,
                        StepStatus.COMPLETED,
                        step_start,
                        output={"cv_sections": len(content.cv.sections)},
                    )
                )
                steps_completed += 1

            except Exception as e:
                result.steps.append(
                    self._create_step_result(
                        PipelineStep.CREATOR,
                        StepStatus.FAILED,
                        step_start,
                        error=str(e),
                    )
                )
                raise StepError("creator", str(e)) from e

            # Step 4: Formatter (optional)
            if not input_data.skip_formatting:
                result.current_step = PipelineStep.FORMATTER
                step_start = datetime.now()

                await self._report_progress(
                    pipeline_id,
                    PipelineStatus.RUNNING,
                    PipelineStep.FORMATTER,
                    steps_completed,
                    "Generating PDF documents...",
                )

                try:
                    formatted = await self._execute_formatter(content)
                    result.steps.append(
                        self._create_step_result(
                            PipelineStep.FORMATTER,
                            StepStatus.COMPLETED,
                            step_start,
                            output={
                                "cv_size": formatted.cv.file_size_bytes,
                                "letter_size": formatted.cover_letter.file_size_bytes,
                            },
                        )
                    )
                    result.cv_path = str(formatted.cv.file_path)
                    result.cover_letter_path = str(formatted.cover_letter.file_path)
                    steps_completed += 1

                except Exception as e:
                    result.steps.append(
                        self._create_step_result(
                            PipelineStep.FORMATTER,
                            StepStatus.FAILED,
                            step_start,
                            error=str(e),
                        )
                    )
                    raise StepError("formatter", str(e)) from e
            else:
                result.steps.append(
                    StepResult(
                        step=PipelineStep.FORMATTER,
                        status=StepStatus.SKIPPED,
                    )
                )
                steps_completed += 1

            # Success
            result.status = PipelineStatus.COMPLETED
            result.current_step = None

        except StepError as e:
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
                f"Pipeline {'completed' if result.is_success else 'failed'}",
            )

            logger.info(
                f"Pipeline {pipeline_id} {result.status.value} "
                f"in {result.total_duration_ms}ms"
            )

        return result

    async def execute_simple(
        self,
        raw_job_text: str,
    ) -> PipelineResult:
        """
        Simple execution with just job text.

        Convenience method for basic usage.

        Args:
            raw_job_text: Raw job posting text.

        Returns:
            PipelineResult
        """
        input_data = PipelineInput(raw_job_text=raw_job_text)
        return await self.execute(input_data)


# =============================================================================
# SINGLETON PATTERN
# =============================================================================

_instance: PipelineOrchestrator | None = None


async def get_pipeline_orchestrator() -> PipelineOrchestrator:
    """
    Get or create the singleton PipelineOrchestrator instance.

    Creates all required modules with their dependencies.

    Returns:
        Initialized PipelineOrchestrator instance.
    """
    global _instance

    if _instance is None:
        # Import and get module instances
        from src.modules.analyzer import get_analyzer
        from src.modules.collector import get_collector
        from src.modules.creator import get_creator
        from src.modules.formatter import get_formatter
        from src.modules.rinser import get_rinser

        collector = await get_collector()
        rinser = await get_rinser()
        analyzer = await get_analyzer()
        creator = await get_creator()
        formatter = await get_formatter()

        _instance = PipelineOrchestrator(
            collector=collector,
            rinser=rinser,
            analyzer=analyzer,
            creator=creator,
            formatter=formatter,
        )
        await _instance.initialize()

    return _instance


async def shutdown_pipeline_orchestrator() -> None:
    """Shutdown the singleton PipelineOrchestrator instance."""
    global _instance

    if _instance is not None:
        await _instance.shutdown()
        _instance = None


def reset_pipeline_orchestrator() -> None:
    """Reset the singleton instance (for testing)."""
    global _instance
    _instance = None
