"""
LLM Service

Wrapper around Anthropic Claude API with cost tracking and caching.

Usage:
    llm = LLMService(cost_tracker, cache)
    await llm.initialize()

    # Simple text generation
    response = await llm.generate(
        messages=[PromptMessage(role=MessageRole.USER, content="Hello!")],
        module="test"
    )
    print(response.content)

    # JSON extraction
    data = await llm.generate_json(
        prompt="Extract name and age from: John is 30 years old",
        module="rinser"
    )
    print(data)  # {"name": "John", "age": 30}
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any

import anthropic
from anthropic import APIError, APITimeoutError, RateLimitError

from src.services.cache_service import CacheService
from src.services.cost_tracker import CostTrackerService
from src.services.cost_tracker.exceptions import BudgetExceededError
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

logger = logging.getLogger(__name__)

# Default model for PoC
DEFAULT_MODEL = "claude-3-5-haiku-20241022"


class LLMService:
    """
    LLM Service for Scout.

    Provides a simple interface to Claude API with:
    - Automatic budget checking via Cost Tracker
    - Response caching via Cache Service
    - Retry logic with exponential backoff
    - Cost calculation and recording

    Attributes:
        cost_tracker: Cost Tracker Service instance.
        cache: Cache Service instance.

    Example:
        >>> llm = LLMService(cost_tracker, cache)
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
        cost_tracker: CostTrackerService,
        cache: CacheService,
        config: LLMConfig | None = None,
    ):
        """
        Initialize LLM Service.

        Args:
            cost_tracker: Cost Tracker Service for budget management.
            cache: Cache Service for response caching.
            config: Optional configuration overrides.
        """
        self._cost_tracker = cost_tracker
        self._cache = cache
        self._client: anthropic.AsyncAnthropic | None = None
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
        self._total_cost = 0.0
        self._last_request_time: datetime | None = None
        self._last_error: str | None = None

    async def initialize(self) -> None:
        """
        Initialize the LLM Service.

        Creates Anthropic client using ANTHROPIC_API_KEY environment variable.

        Raises:
            LLMInitializationError: If API key is missing or client creation fails.
        """
        if self._initialized:
            logger.warning("LLM Service already initialized")
            return

        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMInitializationError(
                "ANTHROPIC_API_KEY environment variable not set"
            )

        try:
            # Create async client
            self._client = anthropic.AsyncAnthropic(
                api_key=api_key,
                timeout=float(self._timeout),
            )

            self._initialized = True
            logger.info(f"LLM Service initialized with model: {self._model}")

        except Exception as e:
            raise LLMInitializationError(
                f"Failed to initialize Anthropic client: {e}"
            ) from e

    async def shutdown(self) -> None:
        """Gracefully shutdown the LLM Service."""
        if not self._initialized:
            return

        if self._client:
            await self._client.close()
            self._client = None

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
    # BUDGET CHECK
    # =========================================================================

    async def _check_budget(self) -> None:
        """
        Check if budget allows proceeding with request.

        Raises:
            BudgetExceededError: If daily or monthly budget exceeded.
        """
        can_proceed = await self._cost_tracker.can_proceed()
        if not can_proceed:
            status = await self._cost_tracker.get_budget_status()
            raise BudgetExceededError(
                f"Budget exceeded. Daily: ${status.daily_spent:.2f}/${status.daily_limit:.2f}, "
                f"Monthly: ${status.monthly_spent:.2f}/${status.monthly_limit:.2f}"
            )

    # =========================================================================
    # API CALL
    # =========================================================================

    async def _call_api(
        self,
        request: LLMRequest,
        request_id: str,
    ) -> LLMResponse:
        """
        Make actual API call to Anthropic.

        Args:
            request: The LLM request.
            request_id: Unique request identifier.

        Returns:
            LLMResponse with content and usage.

        Raises:
            LLMProviderError: On API errors.
            LLMTimeoutError: On timeout.
        """
        if self._client is None:
            raise LLMError("Anthropic client not initialized")

        start_time = time.time()

        # Build messages for API (cast to Any for Anthropic SDK compatibility)
        messages: Any = [m.to_api_format() for m in request.messages]

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=request.system or "",
                messages=messages,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Extract content from response (handle different block types)
            content = ""
            if response.content:
                first_block = response.content[0]
                if hasattr(first_block, "text"):
                    content = str(first_block.text)

            # Build usage
            usage = TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            # Calculate cost
            cost = self._calculate_cost(usage.input_tokens, usage.output_tokens)

            return LLMResponse(
                content=content,
                usage=usage,
                cost=cost,
                model=self._model,
                cached=False,
                latency_ms=latency_ms,
                request_id=request_id,
            )

        except APITimeoutError:
            raise LLMTimeoutError(f"Request timed out after {self._timeout}s")
        except RateLimitError as e:
            raise LLMProviderError(f"Rate limit exceeded: {e}", status_code=429)
        except APIError as e:
            status_code = getattr(e, "status_code", None)
            raise LLMProviderError(f"Anthropic API error: {e}", status_code=status_code)

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
        Generate text using Claude.

        This is the main method for LLM interactions.

        Args:
            messages: Conversation messages.
            system: Optional system prompt.
            temperature: Sampling temperature (0-1).
            max_tokens: Maximum tokens to generate.
            module: Module making the request (for cost tracking).
            purpose: Purpose of request (for logging).
            use_cache: Whether to use caching.
            cache_ttl: Cache time-to-live in seconds.

        Returns:
            LLMResponse with generated content.

        Raises:
            BudgetExceededError: If budget limit reached.
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

        # Check budget before making request
        await self._check_budget()

        # Make API call with retry
        response = await self._call_with_retry(request, request_id)

        # Record cost in cost tracker
        cost = self._calculate_cost(
            response.usage.input_tokens, response.usage.output_tokens
        )
        await self._cost_tracker.record_cost(
            service_name="anthropic",
            model=self._model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost=cost,
            module=module,
        )

        # Update stats
        self._total_requests += 1
        self._total_cost += response.cost
        self._last_request_time = datetime.now()
        self._last_error = None  # Clear on success

        # Cache response
        if use_cache:
            await self._store_in_cache(cache_key, response, cache_ttl)

        logger.info(
            f"LLM response [{request_id}]: "
            f"{response.usage.total_tokens} tokens, "
            f"${response.cost:.6f}, "
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
        api_connected = True

        if not self._initialized:
            status = "unavailable"
            api_connected = False
        elif self._last_error:
            status = "degraded"

        return LLMHealth(
            status=status,
            api_connected=api_connected,
            last_request_time=self._last_request_time,
            last_error=self._last_error,
            total_requests=self._total_requests,
            total_cost=self._total_cost,
        )


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

_llm_instance: LLMService | None = None


async def get_llm_service() -> LLMService:
    """
    Get the LLM Service instance.

    Creates and initializes singleton on first call.
    Requires Cost Tracker and Cache services.

    Returns:
        Initialized LLMService.
    """
    global _llm_instance

    if _llm_instance is None:
        from src.services.cache_service import get_cache_service
        from src.services.cost_tracker import get_cost_tracker

        cost_tracker = await get_cost_tracker()
        cache = await get_cache_service()

        _llm_instance = LLMService(cost_tracker, cache)
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
