"""
LLM Service

Wrapper around Ollama for local LLM inference with caching.

Usage:
    llm = LLMService(metrics_service, cache)
    await llm.initialize()

    # Simple text generation
    response = await llm.generate(
        messages=[PromptMessage(role=MessageRole.USER, content="Hello!")],
        module="test"
    )
    print(response.content)

    # JSON extraction (uses Ollama's JSON mode)
    data = await llm.generate_json(
        prompt="Extract name and age from: John is 30 years old",
        module="rinser"
    )
    print(data)  # {"name": "John", "age": 30}
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any

from src.services.cache_service import CacheService
from src.services.metrics_service import MetricsService
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
)
from src.services.llm_service.providers import LLMProvider, OllamaProvider

logger = logging.getLogger(__name__)

# Default model for PoC (local Ollama)
DEFAULT_MODEL = "qwen2.5:3b"


class LLMService:
    """
    LLM Service for Scout.

    Provides a simple interface to local LLMs via Ollama with:
    - Provider abstraction for flexibility
    - Response caching via Cache Service
    - Retry logic with exponential backoff
    - Performance metrics tracking

    Attributes:
        metrics: Metrics Service instance (for performance tracking).
        cache: Cache Service instance.

    Example:
        >>> llm = LLMService(metrics_service, cache)
        >>> await llm.initialize()
        >>>
        >>> # Generate text
        >>> response = await llm.generate(
        ...     messages=[PromptMessage(role=MessageRole.USER, content="Hello")],
        ...     module="test"
        ... )
        >>> print(response.content)
        "Hello! How can I help you today?"
    """

    # Retry delays in seconds (exponential backoff)
    RETRY_DELAYS = [1, 2, 4]

    def __init__(
        self,
        metrics_service: MetricsService,
        cache: CacheService,
        config: LLMConfig | None = None,
    ):
        """
        Initialize LLM Service.

        Args:
            metrics_service: Metrics Service for performance tracking.
            cache: Cache Service for response caching.
            config: Optional configuration overrides.
        """
        self._metrics = metrics_service
        self._cache = cache
        self._provider: LLMProvider | None = None
        self._initialized = False

        # Configuration
        self._config = config or LLMConfig()
        self._model = self._config.model
        self._timeout = self._config.timeout
        self._max_retries = self._config.max_retries
        self._input_cost_per_1k = self._config.input_cost_per_1k
        self._output_cost_per_1k = self._config.output_cost_per_1k

        # Stats
        self._total_requests = 0
        self._total_tokens = 0
        self._last_request_time: datetime | None = None
        self._last_error: str | None = None

    async def initialize(self) -> None:
        """
        Initialize the LLM Service.

        Creates Ollama provider and verifies model availability.

        Raises:
            LLMInitializationError: If Ollama not running or model not found.
        """
        if self._initialized:
            logger.warning("LLM Service already initialized")
            return

        try:
            # Create Ollama provider
            self._provider = OllamaProvider(
                model=self._config.model,
                fallback_model=self._config.fallback_model,
                host=self._config.ollama_host,
                timeout=float(self._timeout),
            )
            await self._provider.initialize()

            self._initialized = True
            logger.info(f"LLM Service initialized with Ollama: {self._model}")

        except Exception as e:
            if isinstance(e, LLMInitializationError):
                raise
            raise LLMInitializationError(
                f"Failed to initialize Ollama provider: {e}"
            ) from e

    async def shutdown(self) -> None:
        """Gracefully shutdown the LLM Service."""
        if not self._initialized:
            return

        if self._provider:
            await self._provider.shutdown()
            self._provider = None

        self._initialized = False
        logger.info("LLM Service shutdown complete")

    def _ensure_initialized(self) -> None:
        """Raise error if service not initialized."""
        if not self._initialized:
            raise LLMError("LLM Service not initialized. Call initialize() first.")

    # =========================================================================
    # COST CALCULATION
    # =========================================================================

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for a request.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Cost in USD.
        """
        input_cost = (input_tokens / 1000) * self._input_cost_per_1k
        output_cost = (output_tokens / 1000) * self._output_cost_per_1k
        return input_cost + output_cost

    # =========================================================================
    # CACHE OPERATIONS
    # =========================================================================

    async def _check_cache(self, cache_key: str) -> LLMResponse | None:
        """Check cache for existing response."""
        try:
            cached_data = await self._cache.get(cache_key)
            if cached_data is not None:
                # Reconstruct LLMResponse from cached data
                response = LLMResponse(**cached_data)
                response.cached = True
                logger.debug(f"Cache HIT for LLM request: {cache_key[:16]}...")
                return response
        except Exception as e:
            logger.warning(f"Cache lookup failed: {e}")
        return None

    async def _store_in_cache(
        self,
        cache_key: str,
        response: LLMResponse,
        ttl: int,
    ) -> None:
        """Store response in cache."""
        try:
            await self._cache.set(
                cache_key,
                response.model_dump(mode="json"),
                ttl=ttl,
            )
            logger.debug(f"Cached LLM response: {cache_key[:16]}...")
        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")

    # =========================================================================
    # PROVIDER CALL
    # =========================================================================

    async def _call_api(
        self,
        request: LLMRequest,
        request_id: str,
    ) -> LLMResponse:
        """
        Make actual call to LLM provider (Ollama).

        Args:
            request: The LLM request.
            request_id: Unique request identifier.

        Returns:
            LLMResponse with content and usage.

        Raises:
            LLMProviderError: On provider errors.
            LLMTimeoutError: On timeout.
        """
        if self._provider is None:
            raise LLMError("LLM provider not initialized")

        return await self._provider.generate(request, request_id)

    async def _call_with_retry(
        self,
        request: LLMRequest,
        request_id: str,
    ) -> LLMResponse:
        """
        Call API with retry logic.

        Retries on transient errors with exponential backoff.

        Args:
            request: The LLM request.
            request_id: Unique request identifier.

        Returns:
            LLMResponse on success.

        Raises:
            LLMError: After all retries exhausted.
        """
        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                response = await self._call_api(request, request_id)
                response.retry_count = attempt
                return response

            except LLMTimeoutError as e:
                last_error = e
                self._last_error = str(e)
                logger.warning(f"Attempt {attempt + 1}/{self._max_retries} timed out")

            except LLMProviderError as e:
                last_error = e
                self._last_error = str(e)
                # Don't retry on client errors (4xx except 429)
                if e.status_code and 400 <= e.status_code < 500 and e.status_code != 429:
                    raise
                logger.warning(f"Attempt {attempt + 1}/{self._max_retries} failed: {e}")

            # Wait before retry (if not last attempt)
            if attempt < self._max_retries - 1:
                delay = self.RETRY_DELAYS[min(attempt, len(self.RETRY_DELAYS) - 1)]
                logger.debug(f"Waiting {delay}s before retry...")
                await asyncio.sleep(delay)

        # All retries exhausted
        raise LLMError(f"All {self._max_retries} attempts failed. Last error: {last_error}")

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    async def generate(
        self,
        messages: list[PromptMessage],
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        module: str | None = None,
        purpose: str | None = None,
        use_cache: bool = True,
        cache_ttl: int = 3600,
    ) -> LLMResponse:
        """
        Generate text using local LLM via Ollama.

        This is the main method for LLM interactions.

        Args:
            messages: Conversation messages.
            system: Optional system prompt.
            temperature: Sampling temperature (0-1).
            max_tokens: Maximum tokens to generate.
            module: Module making the request (for metrics tracking).
            purpose: Purpose of request (for logging).
            use_cache: Whether to use caching.
            cache_ttl: Cache time-to-live in seconds.

        Returns:
            LLMResponse with generated content.

        Raises:
            LLMError: On generation failure.

        Example:
            >>> response = await llm.generate(
            ...     messages=[
            ...         PromptMessage(role=MessageRole.USER, content="What is 2+2?")
            ...     ],
            ...     module="test"
            ... )
            >>> print(response.content)
            "2 + 2 equals 4."
        """
        self._ensure_initialized()

        # Build request
        request = LLMRequest(
            messages=messages,
            system=system,
            temperature=temperature or self._config.temperature,
            max_tokens=max_tokens or self._config.max_tokens,
            module=module,
            purpose=purpose,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
        )

        request_id = str(uuid.uuid4())[:8]
        cache_key = request.generate_cache_key()

        logger.debug(
            f"LLM request [{request_id}]: "
            f"module={module}, purpose={purpose}, "
            f"messages={len(messages)}, max_tokens={request.max_tokens}"
        )

        # Check cache first
        if use_cache:
            cached = await self._check_cache(cache_key)
            if cached is not None:
                return cached

        # Make API call with retry
        response = await self._call_with_retry(request, request_id)

        # Record performance metrics
        await self._metrics.record_metrics(
            model=response.model,
            duration_seconds=response.latency_ms / 1000.0,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            success=True,
            module=module,
            retry_count=response.retry_count,
            fallback_used=response.model != self._model,
        )

        # Update stats
        self._total_requests += 1
        self._total_tokens += response.usage.total_tokens
        self._last_request_time = datetime.now()
        self._last_error = None  # Clear on success

        # Cache response
        if use_cache:
            await self._store_in_cache(cache_key, response, cache_ttl)

        tps = response.usage.output_tokens / (response.latency_ms / 1000.0) if response.latency_ms > 0 else 0
        logger.info(
            f"LLM response [{request_id}]: "
            f"{response.usage.total_tokens} tokens, "
            f"{tps:.1f} tok/s, "
            f"{response.latency_ms}ms"
        )

        return response

    async def generate_text(
        self,
        prompt: str,
        system: str | None = None,
        module: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Simple text generation from a single prompt.

        Convenience method for simple use cases.

        Args:
            prompt: User prompt.
            system: Optional system prompt.
            module: Module name for tracking.
            **kwargs: Additional arguments for generate().

        Returns:
            Generated text content.

        Example:
            >>> text = await llm.generate_text(
            ...     "Explain Python in one sentence",
            ...     module="test"
            ... )
            >>> print(text)
            "Python is a high-level, interpreted programming language..."
        """
        response = await self.generate(
            messages=[PromptMessage(role=MessageRole.USER, content=prompt)],
            system=system,
            module=module,
            **kwargs,
        )
        return response.content

    async def generate_json(
        self,
        prompt: str,
        system: str | None = None,
        module: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate and parse JSON response.

        Instructs Claude to respond in JSON and parses the result.

        Args:
            prompt: User prompt (should request JSON output).
            system: Optional system prompt (will add JSON instruction).
            module: Module name for tracking.
            **kwargs: Additional arguments for generate().

        Returns:
            Parsed JSON as dictionary.

        Raises:
            LLMResponseError: If response is not valid JSON.

        Example:
            >>> data = await llm.generate_json(
            ...     prompt="Extract: John is 30 years old. Return {name, age}",
            ...     module="rinser"
            ... )
            >>> print(data)
            {"name": "John", "age": 30}
        """
        # Add JSON instruction to system prompt
        json_instruction = "You must respond with valid JSON only. No other text."
        if system:
            full_system = f"{system}\n\n{json_instruction}"
        else:
            full_system = json_instruction

        response = await self.generate(
            messages=[PromptMessage(role=MessageRole.USER, content=prompt)],
            system=full_system,
            module=module,
            temperature=0.1,  # Lower temperature for structured output
            **kwargs,
        )

        # Parse JSON from response
        content = response.content.strip()

        # Handle markdown code blocks
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first and last lines (```json and ```)
            content = "\n".join(lines[1:-1])

        try:
            result: dict[str, Any] = json.loads(content)
            return result
        except json.JSONDecodeError as e:
            raise LLMResponseError(
                f"Failed to parse JSON response: {e}\nContent: {content[:200]}..."
            ) from e

    # =========================================================================
    # HEALTH & STATS
    # =========================================================================

    async def health_check(self) -> LLMHealth:
        """
        Check health of LLM Service.

        Returns:
            LLMHealth with status and metrics.
        """
        status = "healthy"
        ollama_connected = True
        model_loaded: str | None = self._model

        if not self._initialized:
            status = "unavailable"
            ollama_connected = False
            model_loaded = None
        elif self._last_error:
            status = "degraded"

        # Check provider health if available
        if self._provider:
            provider_health = await self._provider.health_check()
            if provider_health.get("status") != "healthy":
                status = provider_health.get("status", "degraded")

        return LLMHealth(
            status=status,
            ollama_connected=ollama_connected,
            model_loaded=model_loaded,
            last_request_time=self._last_request_time,
            last_error=self._last_error,
            total_requests=self._total_requests,
            total_tokens=self._total_tokens,
        )


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

_llm_instance: LLMService | None = None


async def get_llm_service() -> LLMService:
    """
    Get the LLM Service instance.

    Creates and initializes singleton on first call.
    Requires Metrics Service and Cache Service.

    Returns:
        Initialized LLMService.
    """
    global _llm_instance

    if _llm_instance is None:
        from src.services.cache_service import get_cache_service
        from src.services.metrics_service import get_metrics_service

        metrics = await get_metrics_service()
        cache = await get_cache_service()

        _llm_instance = LLMService(metrics, cache)
        await _llm_instance.initialize()

    return _llm_instance


async def shutdown_llm_service() -> None:
    """Shutdown the global LLM Service instance."""
    global _llm_instance

    if _llm_instance is not None:
        await _llm_instance.shutdown()
        _llm_instance = None


def reset_llm_service() -> None:
    """Reset the global instance (for testing)."""
    global _llm_instance
    _llm_instance = None
