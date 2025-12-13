"""
M2 Rinser Module

Job posting processing and structured extraction.

Usage:
    from src.modules.rinser import Rinser, get_rinser

    # Singleton access (for FastAPI)
    rinser = await get_rinser()
    job = await rinser.process_job(raw_text)

    # Manual instantiation (for testing)
    rinser = Rinser(llm_service, vector_store)
    await rinser.initialize()
"""

from src.modules.rinser.exceptions import (
    ExtractionError,
    IndexingError,
    RinserError,
    SanitizationError,
    ValidationError,
)
from src.modules.rinser.models import (
    CompanyInfo,
    JobInput,
    ProcessedJob,
    ProcessingResult,
    Requirement,
    RequirementCategory,
    RequirementPriority,
    Responsibility,
)
from src.modules.rinser.rinser import (
    Rinser,
    get_rinser,
    reset_rinser,
    shutdown_rinser,
)

__all__ = [
    # Module
    "Rinser",
    "get_rinser",
    "shutdown_rinser",
    "reset_rinser",
    # Models
    "ProcessedJob",
    "Requirement",
    "RequirementPriority",
    "RequirementCategory",
    "Responsibility",
    "CompanyInfo",
    "JobInput",
    "ProcessingResult",
    # Exceptions
    "RinserError",
    "ExtractionError",
    "SanitizationError",
    "IndexingError",
    "ValidationError",
]
