"""
Unit tests for LLM Service.

Tests the Ollama-based local LLM integration.

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
    LLMProvider,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMResponseError,
    LLMService,
    LLMTimeoutError,
    MessageRole,
    OllamaProvider,
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
        """Should convert to LLM API format."""
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
            cost=0.0,  # Local inference is free
            model="qwen2.5:3b",
        )

        assert response.content == "Hello there!"
        assert response.usage.total_tokens == 150
        assert response.cost == 0.0
        assert response.cached is False
        assert response.retry_count == 0


class TestLLMHealth:
    """Tests for LLMHealth model."""

    def test_default_healthy(self) -> None:
        """Should default to healthy status."""
        health = LLMHealth()
        assert health.status == "healthy"
        assert health.ollama_connected is True

    def test_unhealthy_state(self) -> None:
        """Should represent unhealthy state."""
        health = LLMHealth(
            status="unavailable",
            ollama_connected=False,
            model_loaded=None,
            last_error="Connection failed",
        )
        assert health.status == "unavailable"
        assert health.ollama_connected is False
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
        daily_spent=0.0,
        daily_limit=10.0,
        monthly_spent=0.0,
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
def mock_ollama_response() -> dict:
    """Create mock Ollama API response."""
    return {
        "message": {"content": "Test response"},
        "prompt_eval_count": 100,
        "eval_count": 50,
    }


@pytest.fixture
def mock_provider() -> AsyncMock:
    """Create mock Ollama provider."""
    provider = AsyncMock(spec=LLMProvider)
    provider.initialize.return_value = None
    provider.shutdown.return_value = None
    provider.health_check.return_value = {"status": "healthy", "provider": "ollama"}
    return provider


@pytest.fixture
async def llm_service(
    mock_cost_tracker: Mock, mock_cache: AsyncMock, mock_provider: AsyncMock
) -> LLMService:
    """Create LLM Service for testing."""
    reset_llm_service()

    with patch(
        "src.services.llm_service.service.OllamaProvider", return_value=mock_provider
    ):
        service = LLMService(mock_cost_tracker, mock_cache)
        await service.initialize()

        # Set up default response for generate
        mock_provider.generate.return_value = LLMResponse(
            content="Test response",
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            cost=0.0,
            model="qwen2.5:3b",
            latency_ms=100,
            request_id="test-123",
        )

        yield service

        await service.shutdown()


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


class TestInitialization:
    """Tests for service initialization."""

    @pytest.mark.asyncio
    async def test_initialize_success(
        self, mock_cost_tracker: Mock, mock_cache: AsyncMock, mock_provider: AsyncMock
    ) -> None:
        """Should initialize successfully with Ollama."""
        with patch(
            "src.services.llm_service.service.OllamaProvider", return_value=mock_provider
        ):
            service = LLMService(mock_cost_tracker, mock_cache)
            await service.initialize()

            assert service._initialized is True
            mock_provider.initialize.assert_called_once()
            await service.shutdown()

    @pytest.mark.asyncio
    async def test_initialize_ollama_not_running(
        self, mock_cost_tracker: Mock, mock_cache: AsyncMock
    ) -> None:
        """Should raise error if Ollama not running."""
        mock_provider = AsyncMock(spec=LLMProvider)
        mock_provider.initialize.side_effect = LLMInitializationError(
            "Failed to connect to Ollama"
        )

        with patch(
            "src.services.llm_service.service.OllamaProvider", return_value=mock_provider
        ):
            service = LLMService(mock_cost_tracker, mock_cache)
            with pytest.raises(LLMInitializationError, match="Ollama"):
                await service.initialize()

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
    """Tests for cost calculation (local = free)."""

    @pytest.mark.asyncio
    async def test_calculate_cost_local_is_free(
        self, llm_service: LLMService
    ) -> None:
        """Should calculate zero cost for local inference."""
        # Default config has 0.0 cost rates for local inference
        cost = llm_service._calculate_cost(1000, 1000)
        assert cost == 0.0

    @pytest.mark.asyncio
    async def test_calculate_cost_zero(self, llm_service: LLMService) -> None:
        """Should handle zero tokens."""
        cost = llm_service._calculate_cost(0, 0)
        assert cost == 0.0


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
    ) -> None:
        """Should return cached response."""
        # Set up cache hit
        cached_data = {
            "content": "Cached response",
            "usage": {"input_tokens": 50, "output_tokens": 25},
            "cost": 0.0,
            "model": "qwen2.5:3b",
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
        # Provider should not have been called
        llm_service._provider.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_stores_response(
        self,
        llm_service: LLMService,
        mock_cache: AsyncMock,
    ) -> None:
        """Should store response in cache on miss."""
        mock_cache.get.return_value = None  # Cache miss

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
    ) -> None:
        """Should skip cache when disabled."""
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
    ) -> None:
        """Should check budget before making request."""
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
    ) -> None:
        """Should record cost after successful request."""
        await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="test")],
            module="test",
        )

        mock_cost_tracker.record_cost.assert_called_once()
        call_kwargs = mock_cost_tracker.record_cost.call_args[1]
        assert call_kwargs["input_tokens"] == 100
        assert call_kwargs["output_tokens"] == 50
        assert call_kwargs["module"] == "test"
        assert call_kwargs["service_name"] == "ollama"


# =============================================================================
# RETRY TESTS
# =============================================================================


class TestRetryLogic:
    """Tests for retry logic."""

    @pytest.mark.asyncio
    async def test_retry_on_timeout(
        self, llm_service: LLMService, mock_provider: AsyncMock
    ) -> None:
        """Should retry on timeout."""
        success_response = LLMResponse(
            content="Test response",
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            cost=0.0,
            model="qwen2.5:3b",
            latency_ms=100,
            request_id="test-123",
        )

        # First call times out, second succeeds
        mock_provider.generate.side_effect = [
            LLMTimeoutError("Request timed out"),
            success_response,
        ]

        response = await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="test")],
            module="test",
        )

        assert response.retry_count == 1
        assert mock_provider.generate.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_provider_error(
        self, llm_service: LLMService, mock_provider: AsyncMock
    ) -> None:
        """Should retry on provider error."""
        success_response = LLMResponse(
            content="Test response",
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            cost=0.0,
            model="qwen2.5:3b",
            latency_ms=100,
            request_id="test-123",
        )

        # First call fails, second succeeds
        mock_provider.generate.side_effect = [
            LLMProviderError("Ollama error"),
            success_response,
        ]

        response = await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="test")],
            module="test",
        )

        assert response.retry_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(
        self, llm_service: LLMService, mock_provider: AsyncMock
    ) -> None:
        """Should not retry on 4xx errors (except 429)."""
        error = LLMProviderError("Bad request", status_code=400)
        mock_provider.generate.side_effect = error

        with pytest.raises(LLMProviderError):
            await llm_service.generate(
                messages=[PromptMessage(role=MessageRole.USER, content="test")],
                module="test",
            )

        # Should only try once
        assert mock_provider.generate.call_count == 1

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(
        self, llm_service: LLMService, mock_provider: AsyncMock
    ) -> None:
        """Should fail after all retries exhausted."""
        # All calls timeout
        mock_provider.generate.side_effect = LLMTimeoutError("Request timed out")

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
    async def test_generate_success(self, llm_service: LLMService) -> None:
        """Should generate response successfully."""
        response = await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="Hello")],
            module="test",
        )

        assert response.content == "Test response"
        assert response.usage.input_tokens == 100
        assert response.usage.output_tokens == 50
        assert response.cost == 0.0  # Local inference is free

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(
        self, llm_service: LLMService, mock_provider: AsyncMock
    ) -> None:
        """Should pass system prompt to provider."""
        await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="Hello")],
            system="Be helpful and concise",
            module="test",
        )

        # Verify system was passed in the request
        call_args = mock_provider.generate.call_args
        request = call_args[0][0]  # First positional argument
        assert request.system == "Be helpful and concise"

    @pytest.mark.asyncio
    async def test_generate_updates_stats(self, llm_service: LLMService) -> None:
        """Should update service statistics."""
        await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="Hello")],
            module="test",
        )

        assert llm_service._total_requests == 1
        assert llm_service._total_tokens == 150  # 100 + 50
        assert llm_service._last_request_time is not None


class TestGenerateText:
    """Tests for generate_text convenience method."""

    @pytest.mark.asyncio
    async def test_generate_text_success(self, llm_service: LLMService) -> None:
        """Should return text content directly."""
        text = await llm_service.generate_text(prompt="Hello", module="test")
        assert text == "Test response"

    @pytest.mark.asyncio
    async def test_generate_text_with_system(
        self, llm_service: LLMService, mock_provider: AsyncMock
    ) -> None:
        """Should pass system prompt."""
        await llm_service.generate_text(
            prompt="Hello",
            system="Be brief",
            module="test",
        )

        call_args = mock_provider.generate.call_args
        request = call_args[0][0]
        assert request.system == "Be brief"


# =============================================================================
# JSON GENERATION TESTS
# =============================================================================


class TestGenerateJson:
    """Tests for JSON generation."""

    @pytest.mark.asyncio
    async def test_generate_json_success(
        self, llm_service: LLMService, mock_provider: AsyncMock
    ) -> None:
        """Should parse JSON response."""
        mock_provider.generate.return_value = LLMResponse(
            content='{"name": "John", "age": 30}',
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            cost=0.0,
            model="qwen2.5:3b",
            latency_ms=100,
            request_id="test-123",
        )

        result = await llm_service.generate_json(
            prompt="Extract: John is 30",
            module="test",
        )

        assert result == {"name": "John", "age": 30}

    @pytest.mark.asyncio
    async def test_generate_json_with_markdown(
        self, llm_service: LLMService, mock_provider: AsyncMock
    ) -> None:
        """Should handle JSON wrapped in markdown code blocks."""
        mock_provider.generate.return_value = LLMResponse(
            content='```json\n{"name": "John"}\n```',
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            cost=0.0,
            model="qwen2.5:3b",
            latency_ms=100,
            request_id="test-123",
        )

        result = await llm_service.generate_json(
            prompt="Extract name",
            module="test",
        )

        assert result == {"name": "John"}

    @pytest.mark.asyncio
    async def test_generate_json_adds_instruction(
        self, llm_service: LLMService, mock_provider: AsyncMock
    ) -> None:
        """Should add JSON instruction to system prompt."""
        mock_provider.generate.return_value = LLMResponse(
            content='{"result": "ok"}',
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            cost=0.0,
            model="qwen2.5:3b",
            latency_ms=100,
            request_id="test-123",
        )

        await llm_service.generate_json(
            prompt="Test",
            system="Be helpful",
            module="test",
        )

        call_args = mock_provider.generate.call_args
        request = call_args[0][0]
        assert "JSON" in request.system
        assert "Be helpful" in request.system

    @pytest.mark.asyncio
    async def test_generate_json_invalid_raises(
        self, llm_service: LLMService, mock_provider: AsyncMock
    ) -> None:
        """Should raise on invalid JSON."""
        mock_provider.generate.return_value = LLMResponse(
            content="not valid json",
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            cost=0.0,
            model="qwen2.5:3b",
            latency_ms=100,
            request_id="test-123",
        )

        with pytest.raises(LLMResponseError, match="Failed to parse JSON"):
            await llm_service.generate_json(
                prompt="Extract something",
                module="test",
            )

    @pytest.mark.asyncio
    async def test_generate_json_uses_low_temperature(
        self, llm_service: LLMService, mock_provider: AsyncMock
    ) -> None:
        """Should use low temperature for structured output."""
        mock_provider.generate.return_value = LLMResponse(
            content='{"result": "ok"}',
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            cost=0.0,
            model="qwen2.5:3b",
            latency_ms=100,
            request_id="test-123",
        )

        await llm_service.generate_json(prompt="Test", module="test")

        call_args = mock_provider.generate.call_args
        request = call_args[0][0]
        assert request.temperature == 0.1


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
        assert health.ollama_connected is True
        assert health.model_loaded == "qwen2.5:3b"

    @pytest.mark.asyncio
    async def test_health_check_unavailable(
        self, mock_cost_tracker: Mock, mock_cache: AsyncMock
    ) -> None:
        """Should report unavailable when not initialized."""
        service = LLMService(mock_cost_tracker, mock_cache)
        # Don't initialize

        health = await service.health_check()

        assert health.status == "unavailable"
        assert health.ollama_connected is False
        assert health.model_loaded is None

    @pytest.mark.asyncio
    async def test_health_check_degraded_after_error(
        self, llm_service: LLMService
    ) -> None:
        """Should report degraded after an error."""
        llm_service._last_error = "Connection failed"

        health = await llm_service.health_check()

        assert health.status == "degraded"

    @pytest.mark.asyncio
    async def test_health_check_tracks_stats(self, llm_service: LLMService) -> None:
        """Should include request stats in health."""
        # Make a request
        await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="test")],
            module="test",
        )

        health = await llm_service.health_check()

        assert health.total_requests == 1
        assert health.total_tokens == 150  # 100 + 50
        assert health.last_request_time is not None


# =============================================================================
# SHUTDOWN TESTS
# =============================================================================


class TestShutdown:
    """Tests for service shutdown."""

    @pytest.mark.asyncio
    async def test_shutdown_closes_provider(
        self, mock_cost_tracker: Mock, mock_cache: AsyncMock, mock_provider: AsyncMock
    ) -> None:
        """Should shutdown provider on shutdown."""
        with patch(
            "src.services.llm_service.service.OllamaProvider", return_value=mock_provider
        ):
            service = LLMService(mock_cost_tracker, mock_cache)
            await service.initialize()
            await service.shutdown()

            mock_provider.shutdown.assert_called_once()
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
        """Should use default Ollama configuration."""
        config = LLMConfig()
        assert config.provider == "ollama"
        assert config.model == "qwen2.5:3b"
        assert config.fallback_model == "gemma2:2b"
        assert config.ollama_host == "http://localhost:11434"
        assert config.temperature == 0.3
        assert config.max_tokens == 2000
        assert config.max_retries == 3
        assert config.timeout == 120

    def test_custom_config(self) -> None:
        """Should accept custom configuration."""
        config = LLMConfig(
            model="llama3.2:3b",
            fallback_model="phi3:mini",
            ollama_host="http://192.168.1.100:11434",
            temperature=0.7,
            max_tokens=4000,
        )
        assert config.model == "llama3.2:3b"
        assert config.fallback_model == "phi3:mini"
        assert config.ollama_host == "http://192.168.1.100:11434"
        assert config.temperature == 0.7
        assert config.max_tokens == 4000

    @pytest.mark.asyncio
    async def test_service_uses_config(
        self, mock_cost_tracker: Mock, mock_cache: AsyncMock, mock_provider: AsyncMock
    ) -> None:
        """Should use provided configuration."""
        config = LLMConfig(timeout=60, max_retries=5)

        with patch(
            "src.services.llm_service.service.OllamaProvider", return_value=mock_provider
        ):
            service = LLMService(mock_cost_tracker, mock_cache, config=config)

            assert service._timeout == 60
            assert service._max_retries == 5


# =============================================================================
# OLLAMA PROVIDER TESTS
# =============================================================================


class TestOllamaProvider:
    """Tests for OllamaProvider."""

    def test_provider_initialization_params(self) -> None:
        """Should accept initialization parameters."""
        provider = OllamaProvider(
            model="qwen2.5:3b",
            fallback_model="gemma2:2b",
            host="http://localhost:11434",
            timeout=120.0,
        )

        assert provider._model == "qwen2.5:3b"
        assert provider._fallback_model == "gemma2:2b"
        assert provider._host == "http://localhost:11434"
        assert provider._timeout == 120.0
        assert provider._initialized is False

    @pytest.mark.asyncio
    async def test_provider_not_initialized_error(self) -> None:
        """Should raise error if generate called before initialize."""
        provider = OllamaProvider()

        with pytest.raises(LLMError, match="not initialized"):
            await provider.generate(
                LLMRequest(
                    messages=[PromptMessage(role=MessageRole.USER, content="test")]
                ),
                "req-123",
            )

    @pytest.mark.asyncio
    async def test_provider_health_not_initialized(self) -> None:
        """Should return unavailable status when not initialized."""
        provider = OllamaProvider()

        health = await provider.health_check()

        assert health["status"] == "unavailable"
        assert health["error"] == "Not initialized"
