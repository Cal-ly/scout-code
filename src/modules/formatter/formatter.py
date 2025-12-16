"""
M5 Formatter Module

Converts generated content to PDF documents using Jinja2 templates and xhtml2pdf.

Usage:
    from src.modules.formatter import Formatter, get_formatter

    # Singleton access (for FastAPI)
    formatter = await get_formatter()
    output = await formatter.format_application(created_content)

    # Manual instantiation (for testing)
    formatter = Formatter(templates_dir, output_dir)
    await formatter.initialize()
    output = await formatter.format_application(created_content)
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape
from xhtml2pdf import pisa

from src.modules.creator.models import (
    CreatedContent,
    GeneratedCoverLetter,
    GeneratedCV,
)
from src.modules.formatter.exceptions import (
    FormatterError,
    OutputDirectoryError,
    PDFGenerationError,
    RenderError,
    TemplateNotFoundError,
)
from src.modules.formatter.models import FormattedApplication, FormattedDocument

logger = logging.getLogger(__name__)

# Default paths (relative to project root via __file__)
_MODULE_DIR = Path(__file__).parent
_PROJECT_ROOT = _MODULE_DIR.parent.parent.parent  # src/modules/formatter -> project root
DEFAULT_TEMPLATES_DIR = _PROJECT_ROOT / "src" / "templates"
DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "data" / "outputs"


class Formatter:
    """
    Formatter Module - generates PDF documents from created content.

    Responsibilities:
    - Load HTML/CSS templates
    - Render content with Jinja2
    - Convert to PDF with xhtml2pdf
    - Manage output directory structure

    Attributes:
        templates_dir: Path to HTML templates directory.
        output_dir: Path for generated output files.

    Example:
        >>> formatter = Formatter()
        >>> await formatter.initialize()
        >>> output = await formatter.format_application(content)
        >>> print(output.cv.file_path)
        Path("output/job-123/cv.pdf")
    """

    def __init__(
        self,
        templates_dir: Path | None = None,
        output_dir: Path | None = None,
    ):
        """
        Initialize Formatter.

        Args:
            templates_dir: Path to templates directory (default: src/templates).
            output_dir: Path for output files (default: output).
        """
        self._templates_dir = templates_dir or DEFAULT_TEMPLATES_DIR
        self._output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self._jinja_env: Environment | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the Formatter module.

        Sets up Jinja2 environment and verifies templates exist.

        Raises:
            FormatterError: If initialization fails.
        """
        if self._initialized:
            logger.warning("Formatter already initialized")
            return

        # Verify templates directory exists
        if not self._templates_dir.exists():
            raise FormatterError(
                f"Templates directory not found: {self._templates_dir}"
            )

        # Initialize Jinja2 environment
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(self._templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Ensure output directory exists
        self._output_dir.mkdir(parents=True, exist_ok=True)

        self._initialized = True
        logger.info(
            f"Formatter initialized with templates: {self._templates_dir}"
        )

    async def shutdown(self) -> None:
        """Gracefully shutdown the Formatter module."""
        if not self._initialized:
            return

        self._jinja_env = None
        self._initialized = False
        logger.info("Formatter module shutdown complete")

    def _ensure_initialized(self) -> None:
        """Raise error if module not initialized."""
        if not self._initialized or self._jinja_env is None:
            raise FormatterError(
                "Formatter not initialized. Call initialize() first."
            )

    # =========================================================================
    # TEMPLATE RENDERING
    # =========================================================================

    def _render_cv_html(self, cv: GeneratedCV) -> str:
        """
        Render CV to HTML.

        Args:
            cv: Generated CV content.

        Returns:
            Rendered HTML string.

        Raises:
            RenderError: If template rendering fails.
        """
        self._ensure_initialized()

        try:
            template = self._jinja_env.get_template("cv_modern.html")  # type: ignore
            return template.render(cv=cv)

        except TemplateNotFound as e:
            raise TemplateNotFoundError(
                f"CV template not found: {e}"
            ) from e
        except Exception as e:
            raise RenderError(f"Failed to render CV template: {e}") from e

    def _render_cover_letter_html(
        self,
        letter: GeneratedCoverLetter,
        sender_info: dict[str, str | None],
    ) -> str:
        """
        Render cover letter to HTML.

        Args:
            letter: Generated cover letter.
            sender_info: Sender contact information.

        Returns:
            Rendered HTML string.

        Raises:
            RenderError: If template rendering fails.
        """
        self._ensure_initialized()

        try:
            template = self._jinja_env.get_template("cover_letter.html")  # type: ignore
            return template.render(
                letter=letter,
                sender=sender_info,
                date=datetime.now().strftime("%B %d, %Y"),
            )

        except TemplateNotFound as e:
            raise TemplateNotFoundError(
                f"Cover letter template not found: {e}"
            ) from e
        except Exception as e:
            raise RenderError(
                f"Failed to render cover letter template: {e}"
            ) from e

    # =========================================================================
    # PDF GENERATION
    # =========================================================================

    def _html_to_pdf(self, html_content: str, output_path: Path) -> int:
        """
        Convert HTML to PDF.

        Args:
            html_content: HTML string to convert.
            output_path: Output file path.

        Returns:
            File size in bytes.

        Raises:
            PDFGenerationError: If PDF generation fails.
        """
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Generate PDF using xhtml2pdf
            with open(output_path, "w+b") as pdf_file:
                pisa_status = pisa.CreatePDF(
                    html_content,
                    dest=pdf_file,
                    encoding="utf-8",
                )

                if pisa_status.err:
                    raise PDFGenerationError(
                        f"xhtml2pdf reported {pisa_status.err} errors"
                    )

            return output_path.stat().st_size

        except PDFGenerationError:
            raise
        except Exception as e:
            raise PDFGenerationError(
                f"Failed to generate PDF: {e}"
            ) from e

    async def format_cv(
        self,
        cv: GeneratedCV,
        output_path: Path,
    ) -> FormattedDocument:
        """
        Format CV to PDF.

        Args:
            cv: Generated CV content.
            output_path: Output file path.

        Returns:
            FormattedDocument with file info.

        Raises:
            FormatterError: If formatting fails.
        """
        self._ensure_initialized()

        logger.info(f"Formatting CV for {cv.full_name}")

        try:
            # Render HTML
            html_content = self._render_cv_html(cv)

            # Convert to PDF
            file_size = self._html_to_pdf(html_content, output_path)

            logger.info(f"CV saved: {output_path} ({file_size} bytes)")

            return FormattedDocument(
                document_type="cv",
                file_path=output_path,
                file_size_bytes=file_size,
                format="pdf",
            )

        except (TemplateNotFoundError, RenderError, PDFGenerationError):
            raise
        except Exception as e:
            raise FormatterError(f"Failed to format CV: {e}") from e

    async def format_cover_letter(
        self,
        letter: GeneratedCoverLetter,
        sender_info: dict[str, str | None],
        output_path: Path,
    ) -> FormattedDocument:
        """
        Format cover letter to PDF.

        Args:
            letter: Generated cover letter.
            sender_info: Sender contact information.
            output_path: Output file path.

        Returns:
            FormattedDocument with file info.

        Raises:
            FormatterError: If formatting fails.
        """
        self._ensure_initialized()

        logger.info(f"Formatting cover letter for {letter.company_name}")

        try:
            # Render HTML
            html_content = self._render_cover_letter_html(letter, sender_info)

            # Convert to PDF
            file_size = self._html_to_pdf(html_content, output_path)

            logger.info(
                f"Cover letter saved: {output_path} ({file_size} bytes)"
            )

            return FormattedDocument(
                document_type="cover_letter",
                file_path=output_path,
                file_size_bytes=file_size,
                format="pdf",
            )

        except (TemplateNotFoundError, RenderError, PDFGenerationError):
            raise
        except Exception as e:
            raise FormatterError(
                f"Failed to format cover letter: {e}"
            ) from e

    # =========================================================================
    # MAIN FORMATTING
    # =========================================================================

    async def format_application(
        self,
        content: CreatedContent,
    ) -> FormattedApplication:
        """
        Format complete application to PDFs.

        Main entry point for the Formatter module.

        Args:
            content: Created content from Creator module.

        Returns:
            FormattedApplication with file paths.

        Raises:
            FormatterError: If formatting fails.

        Example:
            >>> output = await formatter.format_application(content)
            >>> print(output.cv.file_path)
            >>> print(output.cover_letter.file_path)
        """
        self._ensure_initialized()

        logger.info(
            f"Formatting application for {content.job_title} "
            f"at {content.company_name}"
        )

        # Create output directory for this job
        job_output_dir = self._output_dir / content.job_id
        job_output_dir.mkdir(parents=True, exist_ok=True)

        # Extract sender info from CV
        sender_info: dict[str, str | None] = {
            "full_name": content.cv.full_name,
            "email": content.cv.email,
            "phone": content.cv.phone,
            "location": content.cv.location,
        }

        # Format CV
        cv_path = job_output_dir / "cv.pdf"
        cv_doc = await self.format_cv(content.cv, cv_path)

        # Format cover letter
        letter_path = job_output_dir / "cover_letter.pdf"
        letter_doc = await self.format_cover_letter(
            content.cover_letter,
            sender_info,
            letter_path,
        )

        output = FormattedApplication(
            job_id=content.job_id,
            job_title=content.job_title,
            company_name=content.company_name,
            cv=cv_doc,
            cover_letter=letter_doc,
            output_dir=job_output_dir,
        )

        logger.info(
            f"Application formatted: {job_output_dir} "
            f"(CV: {cv_doc.file_size_bytes}B, "
            f"Letter: {letter_doc.file_size_bytes}B)"
        )

        return output

    # =========================================================================
    # CLEANUP
    # =========================================================================

    def cleanup_output(self, job_id: str) -> bool:
        """
        Remove output files for a job.

        Args:
            job_id: Job identifier.

        Returns:
            True if cleaned up, False if not found.
        """
        job_output_dir = self._output_dir / job_id

        if not job_output_dir.exists():
            return False

        try:
            shutil.rmtree(job_output_dir)
            logger.info(f"Cleaned up output for job {job_id}")
            return True

        except Exception as e:
            raise OutputDirectoryError(
                f"Failed to cleanup output: {e}"
            ) from e

    def list_outputs(self) -> list[str]:
        """
        List all job output directories.

        Returns:
            List of job IDs with outputs.
        """
        if not self._output_dir.exists():
            return []

        return [
            d.name
            for d in self._output_dir.iterdir()
            if d.is_dir()
        ]


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

_formatter_instance: Formatter | None = None


async def get_formatter() -> Formatter:
    """
    Get the Formatter instance.

    Creates and initializes singleton on first call.

    Returns:
        Initialized Formatter.
    """
    global _formatter_instance

    if _formatter_instance is None:
        _formatter_instance = Formatter()
        await _formatter_instance.initialize()

    return _formatter_instance


async def shutdown_formatter() -> None:
    """Shutdown the global Formatter instance."""
    global _formatter_instance

    if _formatter_instance is not None:
        await _formatter_instance.shutdown()
        _formatter_instance = None


def reset_formatter() -> None:
    """Reset the global instance (for testing)."""
    global _formatter_instance
    _formatter_instance = None
