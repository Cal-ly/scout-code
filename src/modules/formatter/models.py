"""
M5 Formatter Data Models

Models for formatted output files (PDF documents).
"""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class FormattedDocument(BaseModel):
    """
    A single formatted document.

    Attributes:
        document_type: Type of document (cv, cover_letter).
        file_path: Path to the generated file.
        file_size_bytes: Size of the file in bytes.
        format: Output format (pdf).
        generated_at: When the document was generated.
    """

    document_type: str  # "cv" or "cover_letter"
    file_path: Path
    file_size_bytes: int = 0
    format: str = "pdf"
    generated_at: datetime = Field(default_factory=datetime.now)

    model_config = {"arbitrary_types_allowed": True}


class FormattedApplication(BaseModel):
    """
    Complete formatted application output.

    Contains both CV and cover letter PDFs.

    Attributes:
        job_id: ID of the job this application is for.
        job_title: Target job title.
        company_name: Target company name.
        cv: Formatted CV document.
        cover_letter: Formatted cover letter document.
        output_dir: Directory containing output files.
        created_at: When the application was formatted.
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

    model_config = {"arbitrary_types_allowed": True}

    def get_all_files(self) -> dict[str, Path]:
        """Get all output files as dict."""
        return {
            "cv": self.cv.file_path,
            "cover_letter": self.cover_letter.file_path,
        }

    @property
    def total_size_bytes(self) -> int:
        """Get total size of all output files."""
        return self.cv.file_size_bytes + self.cover_letter.file_size_bytes
