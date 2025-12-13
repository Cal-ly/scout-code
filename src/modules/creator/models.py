"""
M4 Creator Data Models

Models for generated CV and cover letter content.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class CVSection(BaseModel):
    """
    A section of the generated CV.

    Content is pre-formatted for the specific job.

    Attributes:
        section_type: Type of section (summary, experience, skills, education).
        title: Section header text.
        content: Formatted content for this section.
        bullet_points: Achievement/responsibility bullets.
    """

    section_type: str  # "summary", "experience", "skills", "education"
    title: str
    content: str = ""
    bullet_points: list[str] = Field(default_factory=list)


class GeneratedCV(BaseModel):
    """
    Complete generated CV content.

    Tailored to specific job based on analysis.

    Attributes:
        full_name: User's full name.
        email: Contact email.
        phone: Contact phone (optional).
        location: City/region.
        linkedin_url: LinkedIn profile URL (optional).
        github_url: GitHub profile URL (optional).
        professional_summary: Generated summary tailored to job.
        sections: List of CV sections (experience, education).
        technical_skills: List of technical skills.
        soft_skills: List of soft skills.
        target_job_title: Job title this CV targets.
        target_company: Company name this CV targets.
        generated_at: When the CV was generated.
    """

    # Header info (from profile)
    full_name: str
    email: str
    phone: str | None = None
    location: str = ""
    linkedin_url: str | None = None
    github_url: str | None = None

    # Generated sections
    professional_summary: str = ""
    sections: list[CVSection] = Field(default_factory=list)

    # Skills (organized)
    technical_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)

    # Metadata
    target_job_title: str = ""
    target_company: str = ""
    generated_at: datetime = Field(default_factory=datetime.now)

    def get_section(self, section_type: str) -> CVSection | None:
        """Get a specific section by type."""
        for section in self.sections:
            if section.section_type == section_type:
                return section
        return None


class GeneratedCoverLetter(BaseModel):
    """
    Complete generated cover letter.

    Tailored to specific job and company.

    Attributes:
        recipient_name: Addressee name ("Hiring Manager" if unknown).
        company_name: Target company.
        job_title: Target job title.
        opening: Opening paragraph with hook.
        body_paragraphs: Main content paragraphs (2-3).
        closing: Closing paragraph with call to action.
        tone: Letter tone (professional, enthusiastic, etc.).
        word_count: Total word count.
        generated_at: When the letter was generated.
    """

    # Header
    recipient_name: str = "Hiring Manager"
    company_name: str
    job_title: str

    # Content paragraphs
    opening: str = ""
    body_paragraphs: list[str] = Field(default_factory=list)
    closing: str = ""

    # Metadata
    tone: str = "professional"
    word_count: int = 0
    generated_at: datetime = Field(default_factory=datetime.now)

    @property
    def full_text(self) -> str:
        """Get complete letter as single text."""
        parts = [self.opening]
        parts.extend(self.body_paragraphs)
        parts.append(self.closing)
        return "\n\n".join(p for p in parts if p)


class CreatedContent(BaseModel):
    """
    Complete created application content.

    Contains all generated content for one application.
    This is the output of the Creator module.

    Attributes:
        job_id: ID of the job this content is for.
        job_title: Target job title.
        company_name: Target company name.
        cv: Generated CV content.
        cover_letter: Generated cover letter.
        compatibility_score: Match score from analysis.
        created_at: When the content was created.
    """

    # Identification
    job_id: str
    job_title: str
    company_name: str

    # Generated content
    cv: GeneratedCV
    cover_letter: GeneratedCoverLetter

    # Analysis reference
    compatibility_score: float = 0.0

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
