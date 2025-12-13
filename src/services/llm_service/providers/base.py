"""
Base LLM Provider Interface.

Defines the abstract interface that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Any

from src.services.llm_service.models import LLMRequest, LLMResponse


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM providers (Ollama, Anthropic, OpenAI, etc.) must implement
    this interface to work with the LLM Service.

    Example:
        >>> class MyProvider(LLMProvider):
        ...     async def initialize(self) -> None:
        ...         # Setup connection
        ...         pass
        ...
        ...     async def generate(self, request, request_id) -> LLMResponse:
        ...         # Make inference call
        ...         pass
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the provider connection.

        Should establish connections, verify availability,
        and load any required resources.

        Raises:
            LLMInitializationError: If initialization fails.
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Shutdown the provider connection.

        Should clean up resources and close connections gracefully.
        """
        pass

    @abstractmethod
    async def generate(
        self,
        request: LLMRequest,
        request_id: str,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            request: The LLM request containing messages and parameters.
            request_id: Unique identifier for this request.

        Returns:
            LLMResponse with generated content and usage metrics.

        Raises:
            LLMProviderError: On provider-specific errors.
            LLMTimeoutError: If request times out.
        """
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """
        Check provider health status.

        Returns:
            Dictionary with health information including:
            - status: "healthy", "degraded", or "unavailable"
            - provider: Provider name
            - Additional provider-specific info
        """
        pass
