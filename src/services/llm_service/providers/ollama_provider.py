"""
Ollama LLM Provider Implementation.

Provides local LLM inference using Ollama with Qwen 2.5 3B and Gemma 2 2B models.
"""

import logging
import time
from typing import Any, Literal

import ollama
from ollama import ResponseError

from src.services.llm_service.exceptions import (
    LLMError,
    LLMInitializationError,
    LLMProviderError,
    LLMTimeoutError,
)
from src.services.llm_service.models import (
    LLMRequest,
    LLMResponse,
    TokenUsage,
)
from src.services.llm_service.providers.base import LLMProvider

logger = logging.getLogger(__name__)

# Default models for local inference
DEFAULT_MODEL = "qwen2.5:3b"
FALLBACK_MODEL = "gemma2:2b"


class OllamaProvider(LLMProvider):
    """
    Ollama-based LLM provider for local inference.

    Uses Qwen 2.5 3B as primary model with Gemma 2 2B fallback.
    Supports structured JSON output via Ollama's format parameter.

    Attributes:
        model: Primary model name (default: qwen2.5:3b).
        fallback_model: Fallback model name (default: gemma2:2b).
        host: Ollama server URL.
        timeout: Request timeout in seconds.

    Example:
        >>> provider = OllamaProvider()
        >>> await provider.initialize()
        >>> response = await provider.generate(request, "req-123")
        >>> print(response.content)
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        fallback_model: str = FALLBACK_MODEL,
        host: str = "http://localhost:11434",
        timeout: float = 120.0,
    ):
        """
        Initialize Ollama provider.

        Args:
            model: Primary model name (default: qwen2.5:3b).
            fallback_model: Fallback model name (default: gemma2:2b).
            host: Ollama server URL.
            timeout: Request timeout in seconds.
        """
        self._model = model
        self._fallback_model = fallback_model
        self._host = host
        self._timeout = timeout
        self._client: ollama.AsyncClient | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize Ollama client and verify model availability.

        Raises:
            LLMInitializationError: If Ollama not running or model not found.
        """
        if self._initialized:
            logger.warning("Ollama provider already initialized")
            return

        try:
            self._client = ollama.AsyncClient(host=self._host)

            # Verify Ollama is running by listing models
            models_response = await self._client.list()
            models = models_response.get("models", [])
            model_names = [m.get("name", "") for m in models]

            # Check if primary model is available
            primary_available = any(self._model in name for name in model_names)
            if not primary_available:
                raise LLMInitializationError(
                    f"Model {self._model} not found. "
                    f"Available models: {model_names}. "
                    f"Run: ollama pull {self._model}"
                )

            self._initialized = True
            logger.info(f"Ollama provider initialized with model: {self._model}")

        except ResponseError as e:
            raise LLMInitializationError(
                f"Failed to connect to Ollama at {self._host}: {e}. "
                "Ensure Ollama is running: ollama serve"
            ) from e
        except Exception as e:
            if isinstance(e, LLMInitializationError):
                raise
            raise LLMInitializationError(
                f"Failed to initialize Ollama provider: {e}"
            ) from e

    async def shutdown(self) -> None:
        """Shutdown Ollama client."""
        self._client = None
        self._initialized = False
        logger.info("Ollama provider shutdown complete")

    async def generate(
        self,
        request: LLMRequest,
        request_id: str,
    ) -> LLMResponse:
        """
        Generate response using Ollama.

        Args:
            request: LLM request with messages and parameters.
            request_id: Unique request identifier.

        Returns:
            LLMResponse with content and usage metrics.

        Raises:
            LLMError: If provider not initialized.
            LLMProviderError: On Ollama errors.
            LLMTimeoutError: If request times out.
        """
        if not self._initialized or self._client is None:
            raise LLMError("Ollama provider not initialized")

        start_time = time.time()

        # Build messages for Ollama
        messages: list[dict[str, str]] = []

        # Add system message if provided
        if request.system:
            messages.append({"role": "system", "content": request.system})

        # Add conversation messages
        for msg in request.messages:
            messages.append(msg.to_api_format())

        try:
            # Determine format based on request purpose
            # Ollama accepts Literal['', 'json'] for format param
            format_param: Literal["", "json"] | None = None
            if request.purpose == "json_extraction":
                format_param = "json"

            response = await self._client.chat(
                model=self._model,
                messages=messages,
                format=format_param,
                options={
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens,
                },
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Extract content from response
            content = response.get("message", {}).get("content", "")

            # Ollama provides token counts in response
            prompt_tokens = response.get("prompt_eval_count", 0) or 0
            completion_tokens = response.get("eval_count", 0) or 0

            usage = TokenUsage(
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
            )

            # Local inference has no API cost
            cost = 0.0

            return LLMResponse(
                content=content,
                usage=usage,
                cost=cost,
                model=self._model,
                cached=False,
                latency_ms=latency_ms,
                request_id=request_id,
            )

        except ResponseError as e:
            error_str = str(e).lower()
            if "timeout" in error_str:
                raise LLMTimeoutError(
                    f"Request timed out after {self._timeout}s"
                ) from e
            raise LLMProviderError(f"Ollama error: {e}") from e
        except Exception as e:
            if isinstance(e, (LLMTimeoutError, LLMProviderError)):
                raise
            raise LLMProviderError(f"Unexpected Ollama error: {e}") from e

    async def generate_with_fallback(
        self,
        request: LLMRequest,
        request_id: str,
    ) -> LLMResponse:
        """
        Generate with automatic fallback to secondary model.

        Tries primary model first, falls back to secondary on failure.

        Args:
            request: LLM request with messages and parameters.
            request_id: Unique request identifier.

        Returns:
            LLMResponse from primary or fallback model.
        """
        try:
            return await self.generate(request, request_id)
        except LLMProviderError as e:
            logger.warning(
                f"Primary model {self._model} failed: {e}, "
                f"trying fallback {self._fallback_model}"
            )
            # Temporarily switch to fallback model
            original_model = self._model
            self._model = self._fallback_model
            try:
                return await self.generate(request, request_id)
            finally:
                self._model = original_model

    async def health_check(self) -> dict[str, Any]:
        """
        Check Ollama server and model health.

        Returns:
            Dictionary with health status and available models.
        """
        if not self._initialized or self._client is None:
            return {
                "status": "unavailable",
                "provider": "ollama",
                "error": "Not initialized",
            }

        try:
            models_response = await self._client.list()
            models = models_response.get("models", [])
            return {
                "status": "healthy",
                "provider": "ollama",
                "host": self._host,
                "model": self._model,
                "fallback_model": self._fallback_model,
                "available_models": len(models),
            }
        except Exception as e:
            return {
                "status": "degraded",
                "provider": "ollama",
                "host": self._host,
                "error": str(e),
            }
