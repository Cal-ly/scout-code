# Module 5: Formatter - Claude Code Instructions

**Version:** 2.0 (PoC Aligned)  
**Updated:** November 26, 2025  
**Status:** Ready for Implementation  
**Priority:** Phase 2 - Core Module (Build Fifth in Phase 2)

---

## PoC Scope Summary

| Feature | Status | Notes |
|---------|--------|-------|
| PDF generation | ✅ In Scope | WeasyPrint for HTML→PDF |
| CV template (HTML/CSS) | ✅ In Scope | Single modern template |
| Cover letter template | ✅ In Scope | Single professional template |
| Jinja2 templating | ✅ In Scope | For dynamic content |
| DOCX generation | ❌ Deferred | PDF only for PoC |
| Multiple templates | ❌ Deferred | Single template each |
| Template customization UI | ❌ Deferred | Hardcoded templates |
| ATS optimization | ❌ Deferred | Basic formatting only |

---

## Context & Objective

Build the **Formatter Module** for Scout - takes generated content from Creator and produces downloadable PDF files for CV and cover letter.

### Why This Module Exists

The Formatter is the final output stage:
- Takes structured content from Creator
- Renders via HTML/CSS templates using Jinja2
- Converts to PDF using WeasyPrint
- Produces ready-to-download application materials

This creates the actual files the user will submit.

### Dependencies

This module **requires**:
- **M4 Creator**: ApplicationPackage with content

---

## Technical Requirements

### Dependencies

```toml
[tool.poetry.dependencies]
weasyprint = "^60.0"  # HTML to PDF
jinja2 = "^3.1"       # Templating
```

### File Structure

```
scout/
├── app/
│   ├── models/
│   │   └── output.py            # Output models
│   ├── core/
│   │   └── formatter.py         # Formatter module
│   └── templates/
│       ├── cv_modern.html       # CV template
│       ├── cover_letter.html    # Cover letter template
│       └── styles/
│           └── common.css       # Shared styles
├── output/                      # Generated files
│   └── [job_id]/
│       ├── cv.pdf
│       └── cover_letter.pdf
└── tests/
    └── unit/
        └── core/
            └── test_formatter.py
```

---

## Data Models

Create `app/models/output.py`:

```python
"""
Output Data Models

Models for formatted output files.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict
from pathlib import Path
from datetime import datetime


class FormattedDocument(BaseModel):
    """
    A single formatted document.
    """
    document_type: str  # "cv" or "cover_letter"
    file_path: Path
    file_size_bytes: int
    format: str = "pdf"
    generated_at: datetime = Field(default_factory=datetime.now)


class FormattedApplication(BaseModel):
    """
    Complete formatted application output.
    """
    job_id: str
    job_title: str
    company_name: str
    
    # Output files
    cv: FormattedDocument
    cover_letter: FormattedDocument
    
    # Output directory
    output_dir: Path
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    
    def get_all_files(self) -> Dict[str, Path]:
        """Get all output files as dict."""
        return {
            "cv": self.cv.file_path,
            "cover_letter": self.cover_letter.file_path
        }
```

---

## Templates

### CV Template

Create `app/templates/cv_modern.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ cv.full_name }} - CV</title>
    <style>
        /* Reset and base */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.4;
            color: #333;
            padding: 40px;
            max-width: 800px;
            margin: 0 auto;
        }
        
        /* Header */
        .header {
            text-align: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #2c3e50;
        }
        
        .name {
            font-size: 24pt;
            font-weight: 700;
            color: #2c3e50;
            margin-bottom: 8px;
        }
        
        .contact {
            font-size: 9pt;
            color: #555;
        }
        
        .contact a {
            color: #2980b9;
            text-decoration: none;
        }
        
        /* Sections */
        .section {
            margin-bottom: 18px;
        }
        
        .section-title {
            font-size: 12pt;
            font-weight: 700;
            color: #2c3e50;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
            padding-bottom: 4px;
            border-bottom: 1px solid #bdc3c7;
        }
        
        /* Summary */
        .summary {
            font-size: 10pt;
            color: #444;
            text-align: justify;
        }
        
        /* Experience */
        .experience-item {
            margin-bottom: 14px;
        }
        
        .experience-header {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 4px;
        }
        
        .experience-title {
            font-weight: 700;
            font-size: 11pt;
            color: #2c3e50;
        }
        
        .experience-duration {
            font-size: 9pt;
            color: #777;
        }
        
        .experience-bullets {
            list-style-type: disc;
            margin-left: 20px;
            margin-top: 4px;
        }
        
        .experience-bullets li {
            margin-bottom: 3px;
            font-size: 10pt;
        }
        
        /* Skills */
        .skills-container {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }
        
        .skill-tag {
            background: #ecf0f1;
            padding: 3px 10px;
            border-radius: 3px;
            font-size: 9pt;
            color: #2c3e50;
        }
        
        /* Education */
        .education-item {
            margin-bottom: 8px;
        }
        
        .education-degree {
            font-weight: 700;
            font-size: 10pt;
        }
        
        .education-school {
            font-size: 9pt;
            color: #555;
        }
        
        /* Print optimization */
        @media print {
            body {
                padding: 20px;
            }
            
            .section {
                page-break-inside: avoid;
            }
        }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <div class="name">{{ cv.full_name }}</div>
        <div class="contact">
            {{ cv.email }}
            {% if cv.phone %} • {{ cv.phone }}{% endif %}
            • {{ cv.location }}
            {% if cv.linkedin_url %} • <a href="{{ cv.linkedin_url }}">LinkedIn</a>{% endif %}
            {% if cv.github_url %} • <a href="{{ cv.github_url }}">GitHub</a>{% endif %}
        </div>
    </div>
    
    <!-- Professional Summary -->
    <div class="section">
        <div class="section-title">Professional Summary</div>
        <div class="summary">{{ cv.professional_summary }}</div>
    </div>
    
    <!-- Experience -->
    <div class="section">
        <div class="section-title">Experience</div>
        {% for section in cv.sections if section.section_type == 'experience' %}
        <div class="experience-item">
            <div class="experience-header">
                <span class="experience-title">{{ section.title }}</span>
                <span class="experience-duration">{{ section.content }}</span>
            </div>
            {% if section.bullet_points %}
            <ul class="experience-bullets">
                {% for bullet in section.bullet_points %}
                <li>{{ bullet }}</li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    
    <!-- Technical Skills -->
    <div class="section">
        <div class="section-title">Technical Skills</div>
        <div class="skills-container">
            {% for skill in cv.technical_skills %}
            <span class="skill-tag">{{ skill }}</span>
            {% endfor %}
        </div>
    </div>
    
    <!-- Education -->
    <div class="section">
        <div class="section-title">Education</div>
        {% for section in cv.sections if section.section_type == 'education' %}
        <div class="education-item">
            <div class="education-degree">{{ section.title }}</div>
            <div class="education-school">{{ section.content }}</div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
```

### Cover Letter Template

Create `app/templates/cover_letter.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Cover Letter - {{ letter.job_title }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Georgia', serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
            padding: 60px;
            max-width: 700px;
            margin: 0 auto;
        }
        
        .header {
            margin-bottom: 30px;
        }
        
        .sender-info {
            margin-bottom: 20px;
        }
        
        .sender-name {
            font-weight: 700;
            font-size: 14pt;
        }
        
        .sender-contact {
            font-size: 10pt;
            color: #555;
        }
        
        .date {
            margin-bottom: 20px;
            font-size: 10pt;
            color: #555;
        }
        
        .recipient {
            margin-bottom: 20px;
        }
        
        .salutation {
            margin-bottom: 20px;
        }
        
        .body {
            margin-bottom: 30px;
        }
        
        .body p {
            margin-bottom: 15px;
            text-align: justify;
        }
        
        .closing {
            margin-bottom: 40px;
        }
        
        .signature {
            font-style: italic;
        }
        
        @media print {
            body {
                padding: 40px;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <!-- Sender Info -->
        <div class="sender-info">
            <div class="sender-name">{{ sender.full_name }}</div>
            <div class="sender-contact">
                {{ sender.email }}<br>
                {% if sender.phone %}{{ sender.phone }}<br>{% endif %}
                {{ sender.location }}
            </div>
        </div>
        
        <!-- Date -->
        <div class="date">{{ date }}</div>
        
        <!-- Recipient -->
        <div class="recipient">
            {{ letter.recipient_name or "Hiring Manager" }}<br>
            {{ letter.company_name }}
        </div>
    </div>
    
    <!-- Salutation -->
    <div class="salutation">
        Dear {{ letter.recipient_name or "Hiring Manager" }},
    </div>
    
    <!-- Body -->
    <div class="body">
        <p>{{ letter.opening }}</p>
        {% for paragraph in letter.body_paragraphs %}
        <p>{{ paragraph }}</p>
        {% endfor %}
        <p>{{ letter.closing }}</p>
    </div>
    
    <!-- Signature -->
    <div class="closing">
        Sincerely,
    </div>
    
    <div class="signature">
        {{ sender.full_name }}
    </div>
</body>
</html>
```

---

## Configuration

Add to `app/config/settings.py`:

```python
from pathlib import Path


class Settings(BaseSettings):
    # ... existing settings ...
    
    # Formatter Settings
    templates_dir: Path = Path("app/templates")
    output_dir: Path = Path("output")
```

---

## Module Implementation

Create `app/core/formatter.py`:

```python
"""
Formatter Module

Converts generated content to PDF documents.

Usage:
    formatter = Formatter()
    
    output = await formatter.format_application(package)
    print(f"CV saved to: {output.cv.file_path}")
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML, CSS

from app.models.content import ApplicationPackage, GeneratedCV, GeneratedCoverLetter
from app.models.output import FormattedDocument, FormattedApplication
from app.config.settings import settings
from app.utils.exceptions import ScoutError

logger = logging.getLogger(__name__)


class FormatterError(ScoutError):
    """Error in Formatter operations."""
    pass


class Formatter:
    """
    Formatter Module - generates PDF documents.
    
    Responsibilities:
    - Load HTML/CSS templates
    - Render content with Jinja2
    - Convert to PDF with WeasyPrint
    
    Example:
        >>> formatter = Formatter()
        >>> output = await formatter.format_application(package)
        >>> print(output.cv.file_path)
        Path("output/abc123/cv.pdf")
    """
    
    def __init__(
        self,
        templates_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None
    ):
        """
        Initialize Formatter.
        
        Args:
            templates_dir: Path to templates directory
            output_dir: Path for output files
        """
        self._templates_dir = templates_dir or Path(settings.templates_dir)
        self._output_dir = output_dir or Path(settings.output_dir)
        
        # Initialize Jinja2 environment
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(self._templates_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        logger.debug(f"Formatter initialized with templates: {self._templates_dir}")
    
    # =========================================================================
    # TEMPLATE RENDERING
    # =========================================================================
    
    def _render_cv_html(self, cv: GeneratedCV) -> str:
        """
        Render CV to HTML.
        
        Args:
            cv: Generated CV content
            
        Returns:
            HTML string
        """
        template = self._jinja_env.get_template("cv_modern.html")
        return template.render(cv=cv)
    
    def _render_cover_letter_html(
        self,
        letter: GeneratedCoverLetter,
        sender_info: dict
    ) -> str:
        """
        Render cover letter to HTML.
        
        Args:
            letter: Generated cover letter
            sender_info: Sender contact info
            
        Returns:
            HTML string
        """
        template = self._jinja_env.get_template("cover_letter.html")
        return template.render(
            letter=letter,
            sender=sender_info,
            date=datetime.now().strftime("%B %d, %Y")
        )
    
    # =========================================================================
    # PDF GENERATION
    # =========================================================================
    
    def _html_to_pdf(self, html_content: str, output_path: Path) -> int:
        """
        Convert HTML to PDF.
        
        Args:
            html_content: HTML string
            output_path: Output file path
            
        Returns:
            File size in bytes
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate PDF
        html = HTML(string=html_content)
        html.write_pdf(str(output_path))
        
        return output_path.stat().st_size
    
    async def format_cv(
        self,
        cv: GeneratedCV,
        output_path: Path
    ) -> FormattedDocument:
        """
        Format CV to PDF.
        
        Args:
            cv: Generated CV content
            output_path: Output file path
            
        Returns:
            FormattedDocument with file info
        """
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
                format="pdf"
            )
            
        except Exception as e:
            raise FormatterError(f"Failed to format CV: {e}")
    
    async def format_cover_letter(
        self,
        letter: GeneratedCoverLetter,
        sender_info: dict,
        output_path: Path
    ) -> FormattedDocument:
        """
        Format cover letter to PDF.
        
        Args:
            letter: Generated cover letter
            sender_info: Sender contact information
            output_path: Output file path
            
        Returns:
            FormattedDocument with file info
        """
        logger.info(f"Formatting cover letter for {letter.company_name}")
        
        try:
            # Render HTML
            html_content = self._render_cover_letter_html(letter, sender_info)
            
            # Convert to PDF
            file_size = self._html_to_pdf(html_content, output_path)
            
            logger.info(f"Cover letter saved: {output_path} ({file_size} bytes)")
            
            return FormattedDocument(
                document_type="cover_letter",
                file_path=output_path,
                file_size_bytes=file_size,
                format="pdf"
            )
            
        except Exception as e:
            raise FormatterError(f"Failed to format cover letter: {e}")
    
    # =========================================================================
    # MAIN FORMATTING
    # =========================================================================
    
    async def format_application(
        self,
        package: ApplicationPackage
    ) -> FormattedApplication:
        """
        Format complete application to PDFs.
        
        Main entry point for the Formatter module.
        
        Args:
            package: Application package from Creator
            
        Returns:
            FormattedApplication with file paths
            
        Example:
            >>> output = await formatter.format_application(package)
            >>> print(output.cv.file_path)
            >>> print(output.cover_letter.file_path)
        """
        logger.info(
            f"Formatting application for {package.job_title} "
            f"at {package.company_name}"
        )
        
        # Create output directory for this job
        job_output_dir = self._output_dir / package.job_id
        job_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract sender info from CV
        sender_info = {
            "full_name": package.cv.full_name,
            "email": package.cv.email,
            "phone": package.cv.phone,
            "location": package.cv.location
        }
        
        # Format CV
        cv_path = job_output_dir / "cv.pdf"
        cv_doc = await self.format_cv(package.cv, cv_path)
        
        # Format cover letter
        letter_path = job_output_dir / "cover_letter.pdf"
        letter_doc = await self.format_cover_letter(
            package.cover_letter,
            sender_info,
            letter_path
        )
        
        output = FormattedApplication(
            job_id=package.job_id,
            job_title=package.job_title,
            company_name=package.company_name,
            cv=cv_doc,
            cover_letter=letter_doc,
            output_dir=job_output_dir
        )
        
        logger.info(
            f"Application formatted: {job_output_dir} "
            f"(CV: {cv_doc.file_size_bytes}B, Letter: {letter_doc.file_size_bytes}B)"
        )
        
        return output
    
    def cleanup_output(self, job_id: str) -> bool:
        """
        Remove output files for a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if cleaned up, False if not found
        """
        job_output_dir = self._output_dir / job_id
        
        if not job_output_dir.exists():
            return False
        
        import shutil
        shutil.rmtree(job_output_dir)
        logger.info(f"Cleaned up output for job {job_id}")
        
        return True
```

---

## Test Implementation

Create `tests/unit/core/test_formatter.py`:

```python
"""
Unit tests for Formatter Module.

Run with: pytest tests/unit/core/test_formatter.py -v
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

from app.core.formatter import Formatter, FormatterError
from app.models.content import (
    ApplicationPackage, GeneratedCV, GeneratedCoverLetter, CVSection
)
from app.models.output import FormattedDocument, FormattedApplication


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_templates(tmp_path):
    """Create temporary template files."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    
    # Minimal CV template
    cv_template = templates_dir / "cv_modern.html"
    cv_template.write_text("""
    <html>
    <body>
        <h1>{{ cv.full_name }}</h1>
        <p>{{ cv.professional_summary }}</p>
    </body>
    </html>
    """)
    
    # Minimal cover letter template
    letter_template = templates_dir / "cover_letter.html"
    letter_template.write_text("""
    <html>
    <body>
        <p>{{ letter.opening }}</p>
        <p>{{ sender.full_name }}</p>
    </body>
    </html>
    """)
    
    return templates_dir


@pytest.fixture
def temp_output(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def sample_cv():
    """Create sample CV."""
    return GeneratedCV(
        full_name="Jane Developer",
        email="jane@example.com",
        phone="+1-555-1234",
        location="San Francisco, CA",
        professional_summary="Experienced developer...",
        sections=[
            CVSection(
                section_type="experience",
                title="Senior Dev | TechCorp",
                content="4 years",
                bullet_points=["Achievement 1", "Achievement 2"]
            )
        ],
        technical_skills=["Python", "FastAPI"],
        soft_skills=["Leadership"],
        target_job_title="Software Engineer",
        target_company="TargetCorp"
    )


@pytest.fixture
def sample_cover_letter():
    """Create sample cover letter."""
    return GeneratedCoverLetter(
        company_name="TargetCorp",
        job_title="Software Engineer",
        opening="I am excited to apply...",
        body_paragraphs=["With experience...", "I have achieved..."],
        closing="I look forward to...",
        word_count=100
    )


@pytest.fixture
def sample_package(sample_cv, sample_cover_letter):
    """Create sample application package."""
    return ApplicationPackage(
        job_id="test-job-123",
        job_title="Software Engineer",
        company_name="TargetCorp",
        cv=sample_cv,
        cover_letter=sample_cover_letter,
        compatibility_score=75.0
    )


@pytest.fixture
def formatter(temp_templates, temp_output):
    """Create Formatter for testing."""
    return Formatter(
        templates_dir=temp_templates,
        output_dir=temp_output
    )


# =============================================================================
# TEMPLATE RENDERING TESTS
# =============================================================================

class TestTemplateRendering:
    """Tests for template rendering."""
    
    def test_render_cv_html(self, formatter, sample_cv):
        """Should render CV to HTML."""
        html = formatter._render_cv_html(sample_cv)
        
        assert "Jane Developer" in html
        assert "Experienced developer" in html
    
    def test_render_cover_letter_html(self, formatter, sample_cover_letter):
        """Should render cover letter to HTML."""
        sender = {"full_name": "Jane Developer", "email": "jane@example.com"}
        html = formatter._render_cover_letter_html(sample_cover_letter, sender)
        
        assert "I am excited" in html
        assert "Jane Developer" in html


# =============================================================================
# PDF GENERATION TESTS
# =============================================================================

class TestPDFGeneration:
    """Tests for PDF generation."""
    
    @pytest.mark.asyncio
    async def test_format_cv(self, formatter, sample_cv, temp_output):
        """Should generate CV PDF."""
        output_path = temp_output / "cv.pdf"
        
        doc = await formatter.format_cv(sample_cv, output_path)
        
        assert doc.document_type == "cv"
        assert doc.file_path.exists()
        assert doc.file_size_bytes > 0
        assert doc.format == "pdf"
    
    @pytest.mark.asyncio
    async def test_format_cover_letter(self, formatter, sample_cover_letter, temp_output):
        """Should generate cover letter PDF."""
        output_path = temp_output / "cover_letter.pdf"
        sender = {"full_name": "Jane Developer", "email": "jane@example.com"}
        
        doc = await formatter.format_cover_letter(
            sample_cover_letter,
            sender,
            output_path
        )
        
        assert doc.document_type == "cover_letter"
        assert doc.file_path.exists()
        assert doc.file_size_bytes > 0


# =============================================================================
# APPLICATION FORMATTING TESTS
# =============================================================================

class TestApplicationFormatting:
    """Tests for complete application formatting."""
    
    @pytest.mark.asyncio
    async def test_format_application(self, formatter, sample_package):
        """Should format complete application."""
        output = await formatter.format_application(sample_package)
        
        assert isinstance(output, FormattedApplication)
        assert output.job_id == "test-job-123"
        assert output.cv.file_path.exists()
        assert output.cover_letter.file_path.exists()
        assert output.output_dir.exists()
    
    @pytest.mark.asyncio
    async def test_format_application_creates_directory(
        self, formatter, sample_package, temp_output
    ):
        """Should create job-specific output directory."""
        output = await formatter.format_application(sample_package)
        
        expected_dir = temp_output / sample_package.job_id
        assert expected_dir.exists()
        assert output.output_dir == expected_dir
    
    @pytest.mark.asyncio
    async def test_get_all_files(self, formatter, sample_package):
        """Should return all file paths."""
        output = await formatter.format_application(sample_package)
        
        files = output.get_all_files()
        
        assert "cv" in files
        assert "cover_letter" in files
        assert all(p.exists() for p in files.values())


# =============================================================================
# CLEANUP TESTS
# =============================================================================

class TestCleanup:
    """Tests for output cleanup."""
    
    @pytest.mark.asyncio
    async def test_cleanup_output(self, formatter, sample_package):
        """Should remove output directory."""
        output = await formatter.format_application(sample_package)
        assert output.output_dir.exists()
        
        result = formatter.cleanup_output(sample_package.job_id)
        
        assert result is True
        assert not output.output_dir.exists()
    
    def test_cleanup_nonexistent(self, formatter):
        """Should return False for nonexistent job."""
        result = formatter.cleanup_output("nonexistent-job")
        assert result is False


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_format_cv_invalid_template(self, sample_cv, temp_output):
        """Should raise error for missing template."""
        formatter = Formatter(
            templates_dir=Path("/nonexistent"),
            output_dir=temp_output
        )
        
        with pytest.raises(Exception):  # Jinja2 error
            await formatter.format_cv(sample_cv, temp_output / "cv.pdf")
```

---

## Implementation Steps

### Step M5.1: Data Models
```bash
# Create app/models/output.py
# Verify:
python -c "from app.models.output import FormattedApplication; print('OK')"
```

### Step M5.2: Templates
```bash
# Create app/templates/cv_modern.html
# Create app/templates/cover_letter.html
# Verify:
ls app/templates/
```

### Step M5.3: Configuration
```bash
# Add template/output paths to settings
# Verify:
python -c "from app.config.settings import settings; print(settings.templates_dir)"
```

### Step M5.4: Module Implementation
```bash
# Create app/core/formatter.py
# Verify:
python -c "from app.core.formatter import Formatter; print('OK')"
```

### Step M5.5: Unit Tests
```bash
# Create tests/unit/core/test_formatter.py
# Verify:
pytest tests/unit/core/test_formatter.py -v
```

### Step M5.6: Integration Test
```bash
# Verify PDF generation:
python -c "
import asyncio
from pathlib import Path
from app.core.formatter import Formatter
from app.models.content import GeneratedCV, GeneratedCoverLetter, ApplicationPackage

# Create test data
cv = GeneratedCV(
    full_name='Test User',
    email='test@example.com',
    location='Test City',
    professional_summary='Test summary',
    sections=[],
    technical_skills=['Python'],
    soft_skills=[],
    target_job_title='Developer',
    target_company='TestCorp'
)

letter = GeneratedCoverLetter(
    company_name='TestCorp',
    job_title='Developer',
    opening='Hello',
    body_paragraphs=['Body'],
    closing='Goodbye',
    word_count=10
)

package = ApplicationPackage(
    job_id='test-123',
    job_title='Developer',
    company_name='TestCorp',
    cv=cv,
    cover_letter=letter,
    compatibility_score=80
)

async def test():
    formatter = Formatter()
    output = await formatter.format_application(package)
    print(f'CV: {output.cv.file_path}')
    print(f'Cover Letter: {output.cover_letter.file_path}')

asyncio.run(test())
"
```

---

## Success Criteria

| Metric | Target | Verification |
|--------|--------|--------------|
| PDF generation | Valid PDF files | Open generated PDFs |
| Template rendering | Content appears | Check PDF content |
| File organization | Correct structure | Check output directory |
| Error handling | Graceful errors | Test with bad templates |
| Test coverage | >90% | `pytest --cov=app/core/formatter` |

---

*This specification is aligned with Scout PoC Scope Document v1.0*
