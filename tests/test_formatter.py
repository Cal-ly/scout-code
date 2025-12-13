"""
Unit tests for M5 Formatter Module.

Run with: pytest tests/test_formatter.py -v
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.modules.creator.models import (
    CreatedContent,
    CVSection,
    GeneratedCoverLetter,
    GeneratedCV,
)
from src.modules.formatter import (
    FormattedApplication,
    FormattedDocument,
    Formatter,
    FormatterError,
    OutputDirectoryError,
    PDFGenerationError,
    RenderError,
    TemplateNotFoundError,
    reset_formatter,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_templates(tmp_path: Path) -> Path:
    """Create temporary template files."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    # Minimal CV template
    cv_template = templates_dir / "cv_modern.html"
    cv_template.write_text(
        """
<!DOCTYPE html>
<html>
<head><title>CV</title></head>
<body>
    <h1>{{ cv.full_name }}</h1>
    <p>{{ cv.email }}</p>
    <p>{{ cv.professional_summary }}</p>
    {% for section in cv.sections %}
    <div>{{ section.title }}</div>
    {% endfor %}
    {% for skill in cv.technical_skills %}
    <span>{{ skill }}</span>
    {% endfor %}
</body>
</html>
"""
    )

    # Minimal cover letter template
    letter_template = templates_dir / "cover_letter.html"
    letter_template.write_text(
        """
<!DOCTYPE html>
<html>
<head><title>Cover Letter</title></head>
<body>
    <p>{{ sender.full_name }}</p>
    <p>{{ date }}</p>
    <p>{{ letter.opening }}</p>
    {% for paragraph in letter.body_paragraphs %}
    <p>{{ paragraph }}</p>
    {% endfor %}
    <p>{{ letter.closing }}</p>
</body>
</html>
"""
    )

    return templates_dir


@pytest.fixture
def temp_output(tmp_path: Path) -> Path:
    """Create temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def sample_cv() -> GeneratedCV:
    """Create sample CV."""
    return GeneratedCV(
        full_name="Jane Developer",
        email="jane@example.com",
        phone="+1-555-1234",
        location="San Francisco, CA",
        linkedin_url="https://linkedin.com/in/janedev",
        github_url="https://github.com/janedev",
        professional_summary="Experienced software developer with 6+ years of Python expertise.",
        sections=[
            CVSection(
                section_type="experience",
                title="Senior Developer | TechCorp",
                content="4 years",
                bullet_points=[
                    "Led development of REST APIs",
                    "Improved system performance by 40%",
                    "Mentored team of 5 developers",
                ],
            ),
            CVSection(
                section_type="experience",
                title="Python Developer | StartupInc",
                content="2 years",
                bullet_points=[
                    "Built microservices architecture",
                    "Implemented CI/CD pipeline",
                ],
            ),
            CVSection(
                section_type="education",
                title="Bachelor's in Computer Science",
                content="UC Berkeley",
                bullet_points=["Data Structures", "Algorithms"],
            ),
        ],
        technical_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        soft_skills=["Leadership", "Communication"],
        target_job_title="Senior Python Developer",
        target_company="TargetCorp",
    )


@pytest.fixture
def sample_cover_letter() -> GeneratedCoverLetter:
    """Create sample cover letter."""
    return GeneratedCoverLetter(
        company_name="TargetCorp",
        job_title="Senior Python Developer",
        recipient_name="Hiring Manager",
        opening="I am excited to apply for the Senior Python Developer position at TargetCorp.",
        body_paragraphs=[
            "With 6 years of Python experience, I have built scalable backend systems.",
            "At TechCorp, I led initiatives that improved performance by 40%.",
        ],
        closing="I look forward to the opportunity to discuss how I can contribute to your team.",
        tone="professional",
        word_count=100,
    )


@pytest.fixture
def sample_content(
    sample_cv: GeneratedCV, sample_cover_letter: GeneratedCoverLetter
) -> CreatedContent:
    """Create sample created content."""
    return CreatedContent(
        job_id="test-job-123",
        job_title="Senior Python Developer",
        company_name="TargetCorp",
        cv=sample_cv,
        cover_letter=sample_cover_letter,
        compatibility_score=78.0,
    )


@pytest.fixture
def formatter(temp_templates: Path, temp_output: Path) -> Formatter:
    """Create Formatter for testing."""
    return Formatter(templates_dir=temp_templates, output_dir=temp_output)


@pytest.fixture
async def initialized_formatter(formatter: Formatter) -> Formatter:
    """Create initialized Formatter instance."""
    await formatter.initialize()
    return formatter


# =============================================================================
# MODEL TESTS
# =============================================================================


class TestFormattedDocumentModel:
    """Tests for FormattedDocument model."""

    def test_create_formatted_document(self, tmp_path: Path) -> None:
        """Should create FormattedDocument with all fields."""
        file_path = tmp_path / "test.pdf"
        file_path.write_bytes(b"PDF content")

        doc = FormattedDocument(
            document_type="cv",
            file_path=file_path,
            file_size_bytes=100,
            format="pdf",
        )

        assert doc.document_type == "cv"
        assert doc.file_path == file_path
        assert doc.file_size_bytes == 100
        assert doc.format == "pdf"

    def test_default_values(self, tmp_path: Path) -> None:
        """Should have sensible defaults."""
        file_path = tmp_path / "test.pdf"

        doc = FormattedDocument(
            document_type="cover_letter",
            file_path=file_path,
        )

        assert doc.format == "pdf"
        assert doc.file_size_bytes == 0
        assert doc.generated_at is not None


class TestFormattedApplicationModel:
    """Tests for FormattedApplication model."""

    def test_create_formatted_application(self, tmp_path: Path) -> None:
        """Should create FormattedApplication with all fields."""
        cv_doc = FormattedDocument(
            document_type="cv",
            file_path=tmp_path / "cv.pdf",
        )
        letter_doc = FormattedDocument(
            document_type="cover_letter",
            file_path=tmp_path / "letter.pdf",
        )

        app = FormattedApplication(
            job_id="job-123",
            job_title="Developer",
            company_name="TestCorp",
            cv=cv_doc,
            cover_letter=letter_doc,
            output_dir=tmp_path,
        )

        assert app.job_id == "job-123"
        assert app.cv == cv_doc
        assert app.cover_letter == letter_doc

    def test_get_all_files(self, tmp_path: Path) -> None:
        """Should return dict of all file paths."""
        cv_path = tmp_path / "cv.pdf"
        letter_path = tmp_path / "letter.pdf"

        cv_doc = FormattedDocument(document_type="cv", file_path=cv_path)
        letter_doc = FormattedDocument(
            document_type="cover_letter", file_path=letter_path
        )

        app = FormattedApplication(
            job_id="job-123",
            job_title="Developer",
            company_name="TestCorp",
            cv=cv_doc,
            cover_letter=letter_doc,
            output_dir=tmp_path,
        )

        files = app.get_all_files()

        assert files["cv"] == cv_path
        assert files["cover_letter"] == letter_path

    def test_total_size_bytes(self, tmp_path: Path) -> None:
        """Should calculate total size correctly."""
        cv_doc = FormattedDocument(
            document_type="cv",
            file_path=tmp_path / "cv.pdf",
            file_size_bytes=1000,
        )
        letter_doc = FormattedDocument(
            document_type="cover_letter",
            file_path=tmp_path / "letter.pdf",
            file_size_bytes=500,
        )

        app = FormattedApplication(
            job_id="job-123",
            job_title="Developer",
            company_name="TestCorp",
            cv=cv_doc,
            cover_letter=letter_doc,
            output_dir=tmp_path,
        )

        assert app.total_size_bytes == 1500


# =============================================================================
# FORMATTER INITIALIZATION TESTS
# =============================================================================


class TestFormatterInitialization:
    """Tests for Formatter initialization."""

    def test_create_formatter(
        self, temp_templates: Path, temp_output: Path
    ) -> None:
        """Should create Formatter instance."""
        formatter = Formatter(
            templates_dir=temp_templates, output_dir=temp_output
        )

        assert formatter._templates_dir == temp_templates
        assert formatter._output_dir == temp_output
        assert not formatter._initialized

    def test_create_formatter_default_paths(self) -> None:
        """Should use absolute default paths when not specified."""
        formatter = Formatter()

        # Paths should be absolute (using __file__ to determine project root)
        assert formatter._templates_dir.is_absolute()
        assert formatter._output_dir.is_absolute()
        # Should end with the expected path segments
        assert formatter._templates_dir.parts[-2:] == ("src", "templates")
        assert formatter._output_dir.parts[-1] == "output"

    @pytest.mark.asyncio
    async def test_initialize(self, formatter: Formatter) -> None:
        """Should initialize Formatter module."""
        await formatter.initialize()

        assert formatter._initialized
        assert formatter._jinja_env is not None

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(
        self, initialized_formatter: Formatter
    ) -> None:
        """Should handle double initialization gracefully."""
        await initialized_formatter.initialize()  # Second call
        assert initialized_formatter._initialized

    @pytest.mark.asyncio
    async def test_initialize_missing_templates_dir(
        self, temp_output: Path
    ) -> None:
        """Should raise error if templates directory missing."""
        formatter = Formatter(
            templates_dir=Path("/nonexistent/templates"),
            output_dir=temp_output,
        )

        with pytest.raises(FormatterError, match="Templates directory not found"):
            await formatter.initialize()

    @pytest.mark.asyncio
    async def test_shutdown(
        self, initialized_formatter: Formatter
    ) -> None:
        """Should shutdown Formatter module."""
        await initialized_formatter.shutdown()

        assert not initialized_formatter._initialized
        assert initialized_formatter._jinja_env is None

    @pytest.mark.asyncio
    async def test_shutdown_not_initialized(
        self, formatter: Formatter
    ) -> None:
        """Should handle shutdown when not initialized."""
        await formatter.shutdown()  # Should not raise


# =============================================================================
# TEMPLATE RENDERING TESTS
# =============================================================================


class TestTemplateRendering:
    """Tests for template rendering."""

    @pytest.mark.asyncio
    async def test_render_cv_html(
        self, initialized_formatter: Formatter, sample_cv: GeneratedCV
    ) -> None:
        """Should render CV to HTML."""
        html = initialized_formatter._render_cv_html(sample_cv)

        assert "Jane Developer" in html
        assert "jane@example.com" in html
        assert "Experienced software developer" in html

    @pytest.mark.asyncio
    async def test_render_cv_html_includes_experience(
        self, initialized_formatter: Formatter, sample_cv: GeneratedCV
    ) -> None:
        """Should include experience sections in HTML."""
        html = initialized_formatter._render_cv_html(sample_cv)

        assert "Senior Developer | TechCorp" in html
        assert "Python Developer | StartupInc" in html

    @pytest.mark.asyncio
    async def test_render_cv_html_includes_skills(
        self, initialized_formatter: Formatter, sample_cv: GeneratedCV
    ) -> None:
        """Should include skills in HTML."""
        html = initialized_formatter._render_cv_html(sample_cv)

        assert "Python" in html
        assert "FastAPI" in html

    @pytest.mark.asyncio
    async def test_render_cover_letter_html(
        self,
        initialized_formatter: Formatter,
        sample_cover_letter: GeneratedCoverLetter,
    ) -> None:
        """Should render cover letter to HTML."""
        sender = {
            "full_name": "Jane Developer",
            "email": "jane@example.com",
            "phone": None,
            "location": "San Francisco, CA",
        }

        html = initialized_formatter._render_cover_letter_html(
            sample_cover_letter, sender
        )

        assert "Jane Developer" in html
        assert "I am excited to apply" in html
        assert "I look forward to" in html

    @pytest.mark.asyncio
    async def test_render_cv_not_initialized(
        self, formatter: Formatter, sample_cv: GeneratedCV
    ) -> None:
        """Should raise error if not initialized."""
        with pytest.raises(FormatterError, match="not initialized"):
            formatter._render_cv_html(sample_cv)

    @pytest.mark.asyncio
    async def test_render_cv_template_not_found(
        self, temp_output: Path, sample_cv: GeneratedCV, tmp_path: Path
    ) -> None:
        """Should raise TemplateNotFoundError for missing template."""
        # Create templates dir without CV template
        templates_dir = tmp_path / "templates_missing"
        templates_dir.mkdir()
        # Only create cover letter template
        (templates_dir / "cover_letter.html").write_text("<html></html>")

        formatter = Formatter(templates_dir=templates_dir, output_dir=temp_output)
        await formatter.initialize()

        with pytest.raises(TemplateNotFoundError):
            formatter._render_cv_html(sample_cv)


# =============================================================================
# PDF GENERATION TESTS
# =============================================================================


class TestPDFGeneration:
    """Tests for PDF generation."""

    @pytest.mark.asyncio
    async def test_format_cv(
        self,
        initialized_formatter: Formatter,
        sample_cv: GeneratedCV,
        temp_output: Path,
    ) -> None:
        """Should generate CV PDF."""
        output_path = temp_output / "cv.pdf"

        doc = await initialized_formatter.format_cv(sample_cv, output_path)

        assert doc.document_type == "cv"
        assert doc.file_path.exists()
        assert doc.file_size_bytes > 0
        assert doc.format == "pdf"

    @pytest.mark.asyncio
    async def test_format_cv_creates_directory(
        self,
        initialized_formatter: Formatter,
        sample_cv: GeneratedCV,
        temp_output: Path,
    ) -> None:
        """Should create parent directory if it doesn't exist."""
        output_path = temp_output / "subdir" / "cv.pdf"

        doc = await initialized_formatter.format_cv(sample_cv, output_path)

        assert doc.file_path.exists()
        assert output_path.parent.exists()

    @pytest.mark.asyncio
    async def test_format_cover_letter(
        self,
        initialized_formatter: Formatter,
        sample_cover_letter: GeneratedCoverLetter,
        temp_output: Path,
    ) -> None:
        """Should generate cover letter PDF."""
        output_path = temp_output / "cover_letter.pdf"
        sender = {
            "full_name": "Jane Developer",
            "email": "jane@example.com",
            "phone": None,
            "location": "San Francisco, CA",
        }

        doc = await initialized_formatter.format_cover_letter(
            sample_cover_letter, sender, output_path
        )

        assert doc.document_type == "cover_letter"
        assert doc.file_path.exists()
        assert doc.file_size_bytes > 0

    @pytest.mark.asyncio
    async def test_format_cv_not_initialized(
        self, formatter: Formatter, sample_cv: GeneratedCV, temp_output: Path
    ) -> None:
        """Should raise error if not initialized."""
        with pytest.raises(FormatterError, match="not initialized"):
            await formatter.format_cv(sample_cv, temp_output / "cv.pdf")


# =============================================================================
# APPLICATION FORMATTING TESTS
# =============================================================================


class TestApplicationFormatting:
    """Tests for complete application formatting."""

    @pytest.mark.asyncio
    async def test_format_application(
        self, initialized_formatter: Formatter, sample_content: CreatedContent
    ) -> None:
        """Should format complete application."""
        output = await initialized_formatter.format_application(sample_content)

        assert isinstance(output, FormattedApplication)
        assert output.job_id == "test-job-123"
        assert output.cv.file_path.exists()
        assert output.cover_letter.file_path.exists()
        assert output.output_dir.exists()

    @pytest.mark.asyncio
    async def test_format_application_creates_job_directory(
        self,
        initialized_formatter: Formatter,
        sample_content: CreatedContent,
        temp_output: Path,
    ) -> None:
        """Should create job-specific output directory."""
        output = await initialized_formatter.format_application(sample_content)

        expected_dir = temp_output / sample_content.job_id
        assert expected_dir.exists()
        assert output.output_dir == expected_dir

    @pytest.mark.asyncio
    async def test_format_application_file_names(
        self,
        initialized_formatter: Formatter,
        sample_content: CreatedContent,
    ) -> None:
        """Should use correct file names."""
        output = await initialized_formatter.format_application(sample_content)

        assert output.cv.file_path.name == "cv.pdf"
        assert output.cover_letter.file_path.name == "cover_letter.pdf"

    @pytest.mark.asyncio
    async def test_format_application_get_all_files(
        self, initialized_formatter: Formatter, sample_content: CreatedContent
    ) -> None:
        """Should return all file paths."""
        output = await initialized_formatter.format_application(sample_content)

        files = output.get_all_files()

        assert "cv" in files
        assert "cover_letter" in files
        assert all(p.exists() for p in files.values())

    @pytest.mark.asyncio
    async def test_format_application_not_initialized(
        self, formatter: Formatter, sample_content: CreatedContent
    ) -> None:
        """Should raise error if not initialized."""
        with pytest.raises(FormatterError, match="not initialized"):
            await formatter.format_application(sample_content)


# =============================================================================
# CLEANUP TESTS
# =============================================================================


class TestCleanup:
    """Tests for output cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_output(
        self, initialized_formatter: Formatter, sample_content: CreatedContent
    ) -> None:
        """Should remove output directory."""
        output = await initialized_formatter.format_application(sample_content)
        assert output.output_dir.exists()

        result = initialized_formatter.cleanup_output(sample_content.job_id)

        assert result is True
        assert not output.output_dir.exists()

    def test_cleanup_nonexistent(self, initialized_formatter: Formatter) -> None:
        """Should return False for nonexistent job."""
        result = initialized_formatter.cleanup_output("nonexistent-job")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_outputs(
        self, initialized_formatter: Formatter, sample_content: CreatedContent
    ) -> None:
        """Should list job output directories."""
        # Create output
        await initialized_formatter.format_application(sample_content)

        outputs = initialized_formatter.list_outputs()

        assert sample_content.job_id in outputs

    def test_list_outputs_empty(self, initialized_formatter: Formatter) -> None:
        """Should return empty list when no outputs."""
        outputs = initialized_formatter.list_outputs()
        assert outputs == []


# =============================================================================
# DEPENDENCY INJECTION TESTS
# =============================================================================


class TestDependencyInjection:
    """Tests for singleton pattern and dependency injection."""

    def test_reset_formatter(self) -> None:
        """Should reset global instance."""
        reset_formatter()
        # Should not raise

    @pytest.mark.asyncio
    async def test_get_formatter_creates_singleton(
        self, temp_templates: Path, temp_output: Path
    ) -> None:
        """Should create singleton on first call."""
        reset_formatter()

        # Patch the default paths
        with patch(
            "src.modules.formatter.formatter.DEFAULT_TEMPLATES_DIR",
            temp_templates,
        ), patch(
            "src.modules.formatter.formatter.DEFAULT_OUTPUT_DIR",
            temp_output,
        ):
            from src.modules.formatter import get_formatter

            formatter = await get_formatter()

            assert formatter is not None
            assert formatter._initialized

        reset_formatter()


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_cv_minimal_content(
        self, initialized_formatter: Formatter, temp_output: Path
    ) -> None:
        """Should handle CV with minimal content."""
        cv = GeneratedCV(
            full_name="Test User",
            email="test@test.com",
            professional_summary="",
            sections=[],
            technical_skills=[],
            soft_skills=[],
        )

        doc = await initialized_formatter.format_cv(cv, temp_output / "cv.pdf")

        assert doc.file_path.exists()

    @pytest.mark.asyncio
    async def test_cover_letter_no_body(
        self, initialized_formatter: Formatter, temp_output: Path
    ) -> None:
        """Should handle cover letter with no body paragraphs."""
        letter = GeneratedCoverLetter(
            company_name="TestCorp",
            job_title="Developer",
            opening="Opening",
            body_paragraphs=[],
            closing="Closing",
        )
        sender = {"full_name": "Test", "email": "test@test.com", "phone": None, "location": None}

        doc = await initialized_formatter.format_cover_letter(
            letter, sender, temp_output / "letter.pdf"
        )

        assert doc.file_path.exists()

    @pytest.mark.asyncio
    async def test_special_characters_in_content(
        self, initialized_formatter: Formatter, temp_output: Path
    ) -> None:
        """Should handle special characters in content."""
        cv = GeneratedCV(
            full_name="Jean-Pierre O'Connor",
            email="jean@example.com",
            professional_summary="10+ years experience with C++ & Python",
            sections=[
                CVSection(
                    section_type="experience",
                    title="Developer | Tech & Co.",
                    content="2 years",
                    bullet_points=["Used <framework> for development"],
                ),
            ],
            technical_skills=["C++", "Python 3.x"],
        )

        doc = await initialized_formatter.format_cv(cv, temp_output / "cv.pdf")

        assert doc.file_path.exists()

    @pytest.mark.asyncio
    async def test_unicode_content(
        self, initialized_formatter: Formatter, temp_output: Path
    ) -> None:
        """Should handle unicode characters."""
        cv = GeneratedCV(
            full_name="Müller Schmidt",
            email="muller@example.com",
            professional_summary="Experienced developer from München",
            location="München, Germany",
        )

        doc = await initialized_formatter.format_cv(cv, temp_output / "cv.pdf")

        assert doc.file_path.exists()

    @pytest.mark.asyncio
    async def test_format_multiple_jobs(
        self, initialized_formatter: Formatter
    ) -> None:
        """Should handle formatting for multiple jobs."""
        cv = GeneratedCV(full_name="Test", email="test@test.com")
        letter = GeneratedCoverLetter(
            company_name="Co", job_title="Dev", opening="Hi", closing="Bye"
        )

        content1 = CreatedContent(
            job_id="job-001",
            job_title="Dev",
            company_name="Co1",
            cv=cv,
            cover_letter=letter,
        )
        content2 = CreatedContent(
            job_id="job-002",
            job_title="Dev",
            company_name="Co2",
            cv=cv,
            cover_letter=letter,
        )

        output1 = await initialized_formatter.format_application(content1)
        output2 = await initialized_formatter.format_application(content2)

        assert output1.output_dir != output2.output_dir
        assert output1.cv.file_path.exists()
        assert output2.cv.file_path.exists()

        # Cleanup
        initialized_formatter.cleanup_output("job-001")
        initialized_formatter.cleanup_output("job-002")
