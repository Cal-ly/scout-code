"""
Unit tests for LLM Service.

Run with: pytest tests/test_llm_service.py -v
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.services.llm_service import (
    LLMConfig,
    LLMError,
    LLMHealth,
    LLMInitializationError,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMResponseError,
    LLMService,
    LLMTimeoutError,
    MessageRole,
    PromptMessage,
    TokenUsage,
    reset_llm_service,
)
from src.services.cost_tracker.exceptions import BudgetExceededError


# =============================================================================
# MODEL TESTS
# =============================================================================


class TestPromptMessage:
    """Tests for PromptMessage model."""

    def test_create_user_message(self) -> None:
        """Should create a user message."""
        msg = PromptMessage(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"

    def test_create_assistant_message(self) -> None:
        """Should create an assistant message."""
        msg = PromptMessage(role=MessageRole.ASSISTANT, content="Hi there!")
        assert msg.role == MessageRole.ASSISTANT
        assert msg.content == "Hi there!"

    def test_to_api_format(self) -> None:
        """Should convert to Anthropic API format."""
        msg = PromptMessage(role=MessageRole.USER, content="Test")
        api_format = msg.to_api_format()
        assert api_format == {"role": "user", "content": "Test"}


class TestLLMRequest:
    """Tests for LLMRequest model."""

    def test_create_request_defaults(self) -> None:
        """Should create request with defaults."""
        messages = [PromptMessage(role=MessageRole.USER, content="Hello")]
        request = LLMRequest(messages=messages)

        assert len(request.messages) == 1
        assert request.system is None
        assert request.temperature == 0.3
        assert request.max_tokens == 2000
        assert request.use_cache is True
        assert request.cache_ttl == 3600

    def test_create_request_custom_values(self) -> None:
        """Should create request with custom values."""
        messages = [PromptMessage(role=MessageRole.USER, content="Hello")]
        request = LLMRequest(
            messages=messages,
            system="Be helpful",
            temperature=0.7,
            max_tokens=1000,
            module="test",
            use_cache=False,
        )

        assert request.system == "Be helpful"
        assert request.temperature == 0.7
        assert request.max_tokens == 1000
        assert request.module == "test"
        assert request.use_cache is False

    def test_generate_cache_key_consistent(self) -> None:
        """Should generate consistent cache keys."""
        messages = [PromptMessage(role=MessageRole.USER, content="Hello")]
        request1 = LLMRequest(messages=messages, temperature=0.3)
        request2 = LLMRequest(messages=messages, temperature=0.3)

        assert request1.generate_cache_key() == request2.generate_cache_key()

    def test_generate_cache_key_different(self) -> None:
        """Should generate different keys for different requests."""
        messages1 = [PromptMessage(role=MessageRole.USER, content="Hello")]
        messages2 = [PromptMessage(role=MessageRole.USER, content="Hi")]
        request1 = LLMRequest(messages=messages1)
        request2 = LLMRequest(messages=messages2)

        assert request1.generate_cache_key() != request2.generate_cache_key()

    def test_temperature_range_valid(self) -> None:
        """Should accept temperature in valid range."""
        messages = [PromptMessage(role=MessageRole.USER, content="Test")]
        request = LLMRequest(messages=messages, temperature=0.5)
        assert request.temperature == 0.5

    def test_temperature_range_invalid(self) -> None:
        """Should reject temperature outside range."""
        messages = [PromptMessage(role=MessageRole.USER, content="Test")]
        with pytest.raises(ValueError):
            LLMRequest(messages=messages, temperature=1.5)


class TestTokenUsage:
    """Tests for TokenUsage model."""

    def test_create_usage(self) -> None:
        """Should create token usage."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50

    def test_total_tokens(self) -> None:
        """Should calculate total tokens."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.total_tokens == 150


class TestLLMResponse:
    """Tests for LLMResponse model."""

    def test_create_response(self) -> None:
        """Should create a response."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        response = LLMResponse(
            content="Hello there!",
            usage=usage,
            cost=0.001,
            model="claude-3-5-haiku-20241022",
        )

        assert response.content == "Hello there!"
        assert response.usage.total_tokens == 150
        assert response.cost == 0.001
        assert response.cached is False
        assert response.retry_count == 0


class TestLLMHealth:
    """Tests for LLMHealth model."""

    def test_default_healthy(self) -> None:
        """Should default to healthy status."""
        health = LLMHealth()
        assert health.status == "healthy"
        assert health.api_connected is True

    def test_unhealthy_state(self) -> None:
        """Should represent unhealthy state."""
        health = LLMHealth(
            status="unavailable",
            api_connected=False,
            last_error="Connection failed",
        )
        assert health.status == "unavailable"
        assert health.api_connected is False
        assert health.last_error == "Connection failed"


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_cost_tracker() -> Mock:
    """Create mock Cost Tracker."""
    tracker = AsyncMock()
    tracker.can_proceed.return_value = True
    tracker.record_cost.return_value = Mock()
    tracker.get_budget_status.return_value = Mock(
        daily_spent=1.0,
        daily_limit=10.0,
        monthly_spent=5.0,
        monthly_limit=50.0,
    )
    return tracker


@pytest.fixture
def mock_cache() -> AsyncMock:
    """Create mock Cache Service."""
    cache = AsyncMock()
    cache.get.return_value = None  # Cache miss by default
    cache.set.return_value = None
    return cache


@pytest.fixture
def mock_anthropic_response() -> Mock:
    """Create mock Anthropic API response."""
    response = Mock()
    response.content = [Mock(text="Test response")]
    response.usage = Mock(input_tokens=100, output_tokens=50)
    return response


@pytest.fixture
async def llm_service(mock_cost_tracker: Mock, mock_cache: AsyncMock) -> LLMService:
    """Create LLM Service for testing."""
    reset_llm_service()

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("src.services.llm_service.service.anthropic.AsyncAnthropic") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            service = LLMService(mock_cost_tracker, mock_cache)
            await service.initialize()

            yield service

            await service.shutdown()


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


class TestInitialization:
    """Tests for service initialization."""

    @pytest.mark.asyncio
    async def test_initialize_success(
        self, mock_cost_tracker: Mock, mock_cache: AsyncMock
    ) -> None:
        """Should initialize successfully with API key."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("src.services.llm_service.service.anthropic.AsyncAnthropic") as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

                service = LLMService(mock_cost_tracker, mock_cache)
                await service.initialize()

                assert service._initialized is True
                await service.shutdown()

    @pytest.mark.asyncio
    async def test_initialize_missing_api_key(
        self, mock_cost_tracker: Mock, mock_cache: AsyncMock
    ) -> None:
        """Should raise error if API key missing."""
        with patch.dict("os.environ", {}, clear=True):
            # Remove ANTHROPIC_API_KEY if it exists
            import os
            original = os.environ.pop("ANTHROPIC_API_KEY", None)

            try:
                service = LLMService(mock_cost_tracker, mock_cache)
                with pytest.raises(LLMInitializationError, match="ANTHROPIC_API_KEY"):
                    await service.initialize()
            finally:
                if original:
                    os.environ["ANTHROPIC_API_KEY"] = original

    @pytest.mark.asyncio
    async def test_double_initialize_warning(
        self, llm_service: LLMService, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Should warn on double initialization."""
        await llm_service.initialize()
        assert "already initialized" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_operation_before_init_raises(
        self, mock_cost_tracker: Mock, mock_cache: AsyncMock
    ) -> None:
        """Should raise error if not initialized."""
        service = LLMService(mock_cost_tracker, mock_cache)

        with pytest.raises(LLMError, match="not initialized"):
            await service.generate(
                messages=[PromptMessage(role=MessageRole.USER, content="test")]
            )


# =============================================================================
# COST CALCULATION TESTS
# =============================================================================


class TestCostCalculation:
    """Tests for cost calculation."""

    @pytest.mark.asyncio
    async def test_calculate_cost(self, llm_service: LLMService) -> None:
        """Should calculate cost correctly."""
        # 1000 input + 1000 output tokens
        # = $0.001 + $0.005 = $0.006
        cost = llm_service._calculate_cost(1000, 1000)
        assert cost == pytest.approx(0.006, rel=1e-6)

    @pytest.mark.asyncio
    async def test_calculate_cost_zero(self, llm_service: LLMService) -> None:
        """Should handle zero tokens."""
        cost = llm_service._calculate_cost(0, 0)
        assert cost == 0.0

    @pytest.mark.asyncio
    async def test_calculate_cost_small_request(self, llm_service: LLMService) -> None:
        """Should calculate cost for small request."""
        # 100 input + 50 output
        # = $0.0001 + $0.00025 = $0.00035
        cost = llm_service._calculate_cost(100, 50)
        assert cost == pytest.approx(0.00035, rel=1e-6)


# =============================================================================
# CACHE TESTS
# =============================================================================


class TestCaching:
    """Tests for cache integration."""

    @pytest.mark.asyncio
    async def test_cache_hit(
        self,
        llm_service: LLMService,
        mock_cache: AsyncMock,
        mock_anthropic_response: Mock,
    ) -> None:
        """Should return cached response."""
        # Set up cache hit
        cached_data = {
            "content": "Cached response",
            "usage": {"input_tokens": 50, "output_tokens": 25},
            "cost": 0.003,
            "model": "claude-3-5-haiku-20241022",
            "cached": False,
            "latency_ms": 100,
            "request_id": "test-123",
            "retry_count": 0,
        }
        mock_cache.get.return_value = cached_data

        response = await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="test")],
            module="test",
        )

        assert response.content == "Cached response"
        assert response.cached is True
        # API should not have been called
        llm_service._client.messages.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_stores_response(
        self,
        llm_service: LLMService,
        mock_cache: AsyncMock,
        mock_anthropic_response: Mock,
    ) -> None:
        """Should store response in cache on miss."""
        mock_cache.get.return_value = None  # Cache miss
        llm_service._client.messages.create.return_value = mock_anthropic_response

        await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="test")],
            module="test",
        )

        # Verify cache.set was called
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_disabled(
        self,
        llm_service: LLMService,
        mock_cache: AsyncMock,
        mock_anthropic_response: Mock,
    ) -> None:
        """Should skip cache when disabled."""
        llm_service._client.messages.create.return_value = mock_anthropic_response

        await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="test")],
            module="test",
            use_cache=False,
        )

        # Verify cache was not checked or stored
        mock_cache.get.assert_not_called()
        mock_cache.set.assert_not_called()


# =============================================================================
# BUDGET TESTS
# =============================================================================


class TestBudgetEnforcement:
    """Tests for budget enforcement."""

    @pytest.mark.asyncio
    async def test_budget_check_before_request(
        self,
        llm_service: LLMService,
        mock_cost_tracker: Mock,
        mock_anthropic_response: Mock,
    ) -> None:
        """Should check budget before making request."""
        llm_service._client.messages.create.return_value = mock_anthropic_response

        await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="test")],
            module="test",
        )

        mock_cost_tracker.can_proceed.assert_called_once()

    @pytest.mark.asyncio
    async def test_budget_exceeded_raises(
        self, llm_service: LLMService, mock_cost_tracker: Mock
    ) -> None:
        """Should raise when budget exceeded."""
        mock_cost_tracker.can_proceed.return_value = False

        with pytest.raises(BudgetExceededError):
            await llm_service.generate(
                messages=[PromptMessage(role=MessageRole.USER, content="test")],
                module="test",
            )

    @pytest.mark.asyncio
    async def test_cost_recorded_after_success(
        self,
        llm_service: LLMService,
        mock_cost_tracker: Mock,
        mock_anthropic_response: Mock,
    ) -> None:
        """Should record cost after successful request."""
        llm_service._client.messages.create.return_value = mock_anthropic_response

        await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="test")],
            module="test",
        )

        mock_cost_tracker.record_cost.assert_called_once()
        call_kwargs = mock_cost_tracker.record_cost.call_args[1]
        assert call_kwargs["input_tokens"] == 100
        assert call_kwargs["output_tokens"] == 50
        assert call_kwargs["module"] == "test"
        assert call_kwargs["service_name"] == "anthropic"


# =============================================================================
# RETRY TESTS
# =============================================================================


class TestRetryLogic:
    """Tests for retry logic."""

    @pytest.mark.asyncio
    async def test_retry_on_timeout(
        self, llm_service: LLMService, mock_anthropic_response: Mock
    ) -> None:
        """Should retry on timeout."""
        from anthropic import APITimeoutError

        # First call times out, second succeeds
        llm_service._client.messages.create.side_effect = [
            APITimeoutError(request=Mock()),
            mock_anthropic_response,
        ]

        response = await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="test")],
            module="test",
        )

        assert response.retry_count == 1
        assert llm_service._client.messages.create.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(
        self, llm_service: LLMService, mock_anthropic_response: Mock
    ) -> None:
        """Should retry on rate limit (429)."""
        from anthropic import RateLimitError

        # First call rate limited, second succeeds
        llm_service._client.messages.create.side_effect = [
            RateLimitError(
                message="Rate limited",
                response=Mock(status_code=429),
                body={},
            ),
            mock_anthropic_response,
        ]

        response = await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="test")],
            module="test",
        )

        assert response.retry_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(self, llm_service: LLMService) -> None:
        """Should not retry on 4xx errors (except 429)."""
        from anthropic import APIError

        error = APIError(
            message="Bad request",
            request=Mock(),
            body={},
        )
        error.status_code = 400
        llm_service._client.messages.create.side_effect = error

        with pytest.raises(LLMProviderError):
            await llm_service.generate(
                messages=[PromptMessage(role=MessageRole.USER, content="test")],
                module="test",
            )

        # Should only try once
        assert llm_service._client.messages.create.call_count == 1

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self, llm_service: LLMService) -> None:
        """Should fail after all retries exhausted."""
        from anthropic import APITimeoutError

        # All calls timeout
        llm_service._client.messages.create.side_effect = APITimeoutError(
            request=Mock()
        )

        with pytest.raises(LLMError, match="All 3 attempts failed"):
            await llm_service.generate(
                messages=[PromptMessage(role=MessageRole.USER, content="test")],
                module="test",
            )


# =============================================================================
# GENERATE TESTS
# =============================================================================


class TestGenerate:
    """Tests for generate method."""

    @pytest.mark.asyncio
    async def test_generate_success(
        self, llm_service: LLMService, mock_anthropic_response: Mock
    ) -> None:
        """Should generate response successfully."""
        llm_service._client.messages.create.return_value = mock_anthropic_response

        response = await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="Hello")],
            module="test",
        )

        assert response.content == "Test response"
        assert response.usage.input_tokens == 100
        assert response.usage.output_tokens == 50
        assert response.cost == pytest.approx(0.00035, rel=1e-4)

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(
        self, llm_service: LLMService, mock_anthropic_response: Mock
    ) -> None:
        """Should pass system prompt to API."""
        llm_service._client.messages.create.return_value = mock_anthropic_response

        await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="Hello")],
            system="Be helpful and concise",
            module="test",
        )

        # Verify system was passed
        call_kwargs = llm_service._client.messages.create.call_args[1]
        assert call_kwargs["system"] == "Be helpful and concise"

    @pytest.mark.asyncio
    async def test_generate_updates_stats(
        self, llm_service: LLMService, mock_anthropic_response: Mock
    ) -> None:
        """Should update service statistics."""
        llm_service._client.messages.create.return_value = mock_anthropic_response

        await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="Hello")],
            module="test",
        )

        assert llm_service._total_requests == 1
        assert llm_service._total_cost > 0
        assert llm_service._last_request_time is not None


class TestGenerateText:
    """Tests for generate_text convenience method."""

    @pytest.mark.asyncio
    async def test_generate_text_success(
        self, llm_service: LLMService, mock_anthropic_response: Mock
    ) -> None:
        """Should return text content directly."""
        llm_service._client.messages.create.return_value = mock_anthropic_response

        text = await llm_service.generate_text(prompt="Hello", module="test")

        assert text == "Test response"

    @pytest.mark.asyncio
    async def test_generate_text_with_system(
        self, llm_service: LLMService, mock_anthropic_response: Mock
    ) -> None:
        """Should pass system prompt."""
        llm_service._client.messages.create.return_value = mock_anthropic_response

        await llm_service.generate_text(
            prompt="Hello",
            system="Be brief",
            module="test",
        )

        call_kwargs = llm_service._client.messages.create.call_args[1]
        assert call_kwargs["system"] == "Be brief"


# =============================================================================
# JSON GENERATION TESTS
# =============================================================================


class TestGenerateJson:
    """Tests for JSON generation."""

    @pytest.mark.asyncio
    async def test_generate_json_success(self, llm_service: LLMService) -> None:
        """Should parse JSON response."""
        json_response = Mock()
        json_response.content = [Mock(text='{"name": "John", "age": 30}')]
        json_response.usage = Mock(input_tokens=100, output_tokens=50)
        llm_service._client.messages.create.return_value = json_response

        result = await llm_service.generate_json(
            prompt="Extract: John is 30",
            module="test",
        )

        assert result == {"name": "John", "age": 30}

    @pytest.mark.asyncio
    async def test_generate_json_with_markdown(self, llm_service: LLMService) -> None:
        """Should handle JSON wrapped in markdown code blocks."""
        json_response = Mock()
        json_response.content = [Mock(text='```json\n{"name": "John"}\n```')]
        json_response.usage = Mock(input_tokens=100, output_tokens=50)
        llm_service._client.messages.create.return_value = json_response

        result = await llm_service.generate_json(
            prompt="Extract name",
            module="test",
        )

        assert result == {"name": "John"}

    @pytest.mark.asyncio
    async def test_generate_json_adds_instruction(
        self, llm_service: LLMService
    ) -> None:
        """Should add JSON instruction to system prompt."""
        json_response = Mock()
        json_response.content = [Mock(text='{"result": "ok"}')]
        json_response.usage = Mock(input_tokens=100, output_tokens=50)
        llm_service._client.messages.create.return_value = json_response

        await llm_service.generate_json(
            prompt="Test",
            system="Be helpful",
            module="test",
        )

        call_kwargs = llm_service._client.messages.create.call_args[1]
        assert "JSON" in call_kwargs["system"]
        assert "Be helpful" in call_kwargs["system"]

    @pytest.mark.asyncio
    async def test_generate_json_invalid_raises(self, llm_service: LLMService) -> None:
        """Should raise on invalid JSON."""
        json_response = Mock()
        json_response.content = [Mock(text="not valid json")]
        json_response.usage = Mock(input_tokens=100, output_tokens=50)
        llm_service._client.messages.create.return_value = json_response

        with pytest.raises(LLMResponseError, match="Failed to parse JSON"):
            await llm_service.generate_json(
                prompt="Extract something",
                module="test",
            )

    @pytest.mark.asyncio
    async def test_generate_json_uses_low_temperature(
        self, llm_service: LLMService
    ) -> None:
        """Should use low temperature for structured output."""
        json_response = Mock()
        json_response.content = [Mock(text='{"result": "ok"}')]
        json_response.usage = Mock(input_tokens=100, output_tokens=50)
        llm_service._client.messages.create.return_value = json_response

        await llm_service.generate_json(prompt="Test", module="test")

        call_kwargs = llm_service._client.messages.create.call_args[1]
        assert call_kwargs["temperature"] == 0.1


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================


class TestHealthCheck:
    """Tests for health checks."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, llm_service: LLMService) -> None:
        """Should report healthy status."""
        health = await llm_service.health_check()

        assert health.status == "healthy"
        assert health.api_connected is True

    @pytest.mark.asyncio
    async def test_health_check_unavailable(
        self, mock_cost_tracker: Mock, mock_cache: AsyncMock
    ) -> None:
        """Should report unavailable when not initialized."""
        service = LLMService(mock_cost_tracker, mock_cache)
        # Don't initialize

        health = await service.health_check()

        assert health.status == "unavailable"
        assert health.api_connected is False

    @pytest.mark.asyncio
    async def test_health_check_degraded_after_error(
        self, llm_service: LLMService
    ) -> None:
        """Should report degraded after an error."""
        llm_service._last_error = "Connection failed"

        health = await llm_service.health_check()

        assert health.status == "degraded"

    @pytest.mark.asyncio
    async def test_health_check_tracks_stats(
        self, llm_service: LLMService, mock_anthropic_response: Mock
    ) -> None:
        """Should include request stats in health."""
        llm_service._client.messages.create.return_value = mock_anthropic_response

        # Make a request
        await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="test")],
            module="test",
        )

        health = await llm_service.health_check()

        assert health.total_requests == 1
        assert health.total_cost > 0
        assert health.last_request_time is not None


# =============================================================================
# SHUTDOWN TESTS
# =============================================================================


class TestShutdown:
    """Tests for service shutdown."""

    @pytest.mark.asyncio
    async def test_shutdown_closes_client(
        self, mock_cost_tracker: Mock, mock_cache: AsyncMock
    ) -> None:
        """Should close Anthropic client on shutdown."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("src.services.llm_service.service.anthropic.AsyncAnthropic") as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

                service = LLMService(mock_cost_tracker, mock_cache)
                await service.initialize()
                await service.shutdown()

                mock_client.close.assert_called_once()
                assert service._initialized is False

    @pytest.mark.asyncio
    async def test_shutdown_idempotent(
        self, mock_cost_tracker: Mock, mock_cache: AsyncMock
    ) -> None:
        """Should handle multiple shutdown calls gracefully."""
        service = LLMService(mock_cost_tracker, mock_cache)
        # Not initialized, shutdown should be safe
        await service.shutdown()
        await service.shutdown()  # Should not raise


# =============================================================================
# CONFIGURATION TESTS
# =============================================================================


class TestConfiguration:
    """Tests for service configuration."""

    def test_default_config(self) -> None:
        """Should use default configuration."""
        config = LLMConfig()
        assert config.model == "claude-3-5-haiku-20241022"
        assert config.temperature == 0.3
        assert config.max_tokens == 2000
        assert config.max_retries == 3

    def test_custom_config(self) -> None:
        """Should accept custom configuration."""
        config = LLMConfig(
            model="claude-3-opus-20240229",
            temperature=0.7,
            max_tokens=4000,
        )
        assert config.model == "claude-3-opus-20240229"
        assert config.temperature == 0.7
        assert config.max_tokens == 4000

    @pytest.mark.asyncio
    async def test_service_uses_config(
        self, mock_cost_tracker: Mock, mock_cache: AsyncMock
    ) -> None:
        """Should use provided configuration."""
        config = LLMConfig(timeout=60, max_retries=5)

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("src.services.llm_service.service.anthropic.AsyncAnthropic"):
                service = LLMService(mock_cost_tracker, mock_cache, config=config)

                assert service._timeout == 60
                assert service._max_retries == 5
