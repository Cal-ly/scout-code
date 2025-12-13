"""
M5 Formatter Exceptions

Custom exceptions for the Formatter module.
"""


class FormatterError(Exception):
    """Base exception for Formatter module operations."""

    pass


class RenderError(FormatterError):
    """Error during template rendering."""

    pass


class PDFGenerationError(FormatterError):
    """Error during PDF generation."""

    pass


class TemplateNotFoundError(FormatterError):
    """Template file not found."""

    pass


class OutputDirectoryError(FormatterError):
    """Error with output directory operations."""

    pass
