"""
M5 Formatter Module

Converts generated content to PDF documents.

Usage:
    from src.modules.formatter import Formatter, get_formatter

    # Singleton access (for FastAPI)
    formatter = await get_formatter()
    output = await formatter.format_application(content)

    # Manual instantiation (for testing)
    formatter = Formatter(templates_dir, output_dir)
    await formatter.initialize()
"""

from src.modules.formatter.exceptions import (
    FormatterError,
    OutputDirectoryError,
    PDFGenerationError,
    RenderError,
    TemplateNotFoundError,
)
from src.modules.formatter.formatter import (
    Formatter,
    get_formatter,
    reset_formatter,
    shutdown_formatter,
)
from src.modules.formatter.models import (
    FormattedApplication,
    FormattedDocument,
)

__all__ = [
    # Module
    "Formatter",
    "get_formatter",
    "shutdown_formatter",
    "reset_formatter",
    # Models
    "FormattedApplication",
    "FormattedDocument",
    # Exceptions
    "FormatterError",
    "RenderError",
    "PDFGenerationError",
    "TemplateNotFoundError",
    "OutputDirectoryError",
]
