"""
LLM Service

Anthropic Claude API integration for all LLM operations.
PoC scope: Claude 3.5 Haiku only, basic retry logic, cost tracking.

Usage:
    from src.services.llm_service import LLMService, get_llm_service

    # Singleton access (for FastAPI)
    llm = await get_llm_service()

    # Manual instantiation (for testing)
    llm = LLMService(cost_tracker, cache)
    await llm.initialize()
"""

from src.services.llm_service.exceptions import (
    LLMError,
    LLMInitializationError,
    LLMProviderError,
    LLMResponseError,
    LLMTimeoutError,
)
from src.services.llm_service.models import (
    LLMConfig,
    LLMHealth,
    LLMRequest,
    LLMResponse,
    MessageRole,
    PromptMessage,
    TokenUsage,
)
from src.services.llm_service.service import (
    LLMService,
    get_llm_service,
    reset_llm_service,
    shutdown_llm_service,
)

__all__ = [
    # Service
    "LLMService",
    "get_llm_service",
    "shutdown_llm_service",
    "reset_llm_service",
    # Models
    "LLMRequest",
    "LLMResponse",
    "LLMConfig",
    "LLMHealth",
    "PromptMessage",
    "MessageRole",
    "TokenUsage",
    # Exceptions
    "LLMError",
    "LLMProviderError",
    "LLMTimeoutError",
    "LLMResponseError",
    "LLMInitializationError",
]
