# S1 LLM Service - Claude Code Instructions

**Version:** 2.0 (PoC Aligned)  
**Updated:** November 26, 2025  
**Status:** Ready for Implementation  
**Priority:** Phase 1 - Foundation Service (Build Fourth - after S2, S3, S4)

---

## PoC Scope Summary

| Feature | Status | Notes |
|---------|--------|-------|
| Anthropic Claude API | ✅ In Scope | Primary and only provider |
| Claude 3.5 Haiku model | ✅ In Scope | Single model, hardcoded |
| Basic retry logic | ✅ In Scope | 3 attempts, fixed delays (1s, 2s, 4s) |
| Cost tracking integration | ✅ In Scope | Check budget before, record after |
| Cache integration | ✅ In Scope | Check cache before, store after |
| JSON response parsing | ✅ In Scope | For structured extraction |
| Request timeout | ✅ In Scope | 30 second timeout |
| OpenAI fallback | ❌ Deferred | Single provider sufficient |
| Model selection | ❌ Deferred | Haiku only for cost control |
| Streaming responses | ❌ Deferred | Not needed for PoC |
| Function calling | ❌ Deferred | Not needed for PoC |
| Rate limit handling | ❌ Deferred | Low volume won't hit limits |
| Provider health tracking | ❌ Deferred | Single provider, simple retry |

---

## Context & Objective

Build the **LLM Service** for Scout - a simple wrapper around Anthropic's Claude API that integrates with Cost Tracker and Cache services. This service is the sole interface for all LLM operations in the application.

### Why This Service Exists

All Scout modules need LLM capabilities for:
- Rinser: Extract structured job data from raw text
- Analyzer: Generate strategy recommendations
- Creator: Generate tailored CVs and cover letters

The LLM Service centralizes:
- API authentication and calls
- Cost tracking and budget enforcement
- Response caching
- Error handling and retries

### Dependencies

This service **requires** these services to be implemented first:
- **S2 Cost Tracker**: For budget checks and cost recording
- **S3 Cache Service**: For response caching

---

## Technical Requirements

### Dependencies

```toml
[tool.poetry.dependencies]
anthropic = "^0.39.0"  # Anthropic Python SDK
```

### File Structure

```
scout/
├── app/
│   ├── models/
│   │   └── llm.py               # LLM data models
│   ├── services/
│   │   └── llm.py               # LLM Service
│   ├── config/
│   │   └── settings.py          # Add LLM settings
│   └── utils/
│       └── exceptions.py        # Add LLM exceptions
├── prompts/                     # Prompt templates (future)
└── tests/
    └── unit/
        └── services/
            └── test_llm.py
```

---

## Data Models

Create `app/models/llm.py`:

```python
"""
LLM Service Data Models

Simple models for Anthropic Claude API integration.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
import hashlib
import json


class MessageRole(str, Enum):
    """Valid message roles for Claude API."""
    USER = "user"
    ASSISTANT = "assistant"


class PromptMessage(BaseModel):
    """
    A single message in the conversation.
    
    Note: Claude API handles system prompts separately,
    so role is only 'user' or 'assistant'.
    """
    role: MessageRole
    content: str
    
    def to_api_format(self) -> Dict[str, str]:
        """Convert to Anthropic API format."""
        return {
            "role": self.role.value,
            "content": self.content
        }


class LLMRequest(BaseModel):
    """
    Request to the LLM Service.
    
    Simplified for PoC - no model selection, no provider selection.
    """
    # Messages (required)
    messages: List[PromptMessage]
    system: Optional[str] = None  # System prompt
    
    # Generation parameters
    temperature: float = Field(default=0.3, ge=0, le=1)
    max_tokens: int = Field(default=2000, ge=1, le=4096)
    
    # Context for cost tracking
    module: Optional[str] = None  # e.g., "rinser", "analyzer", "creator"
    purpose: Optional[str] = None  # e.g., "extract_job_structure"
    
    # Caching control
    use_cache: bool = True
    cache_ttl: int = 3600  # 1 hour default
    
    def generate_cache_key(self) -> str:
        """
        Generate cache key from request parameters.
        
        Includes all parameters that affect the response.
        """
        key_data = {
            "messages": [m.model_dump() for m in self.messages],
            "system": self.system,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()


class TokenUsage(BaseModel):
    """
    Token usage from an LLM call.
    
    Used for cost calculation.
    """
    input_tokens: int
    output_tokens: int
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class LLMResponse(BaseModel):
    """
    Response from the LLM Service.
    
    Contains the generated content and metadata.
    """
    # Content
    content: str
    
    # Usage
    usage: TokenUsage
    
    # Cost (calculated)
    cost: float
    
    # Metadata
    model: str = "claude-3-5-haiku-20241022"
    cached: bool = False
    latency_ms: int = 0
    
    # Request tracking
    request_id: Optional[str] = None
    
    # Retry info
    retry_count: int = 0


class LLMHealth(BaseModel):
    """
    Health status for the LLM Service.
    """
    status: str = "healthy"  # "healthy", "degraded", "unavailable"
    api_connected: bool = True
    last_request_time: Optional[datetime] = None
    last_error: Optional[str] = None
    total_requests: int = 0
    total_cost: float = 0.0
```

---

## Configuration

Add to `app/config/settings.py`:

```python
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # ... existing settings ...
    
    # LLM Settings
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    llm_model: str = "claude-3-5-haiku-20241022"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2000
    llm_timeout: int = 30  # seconds
    llm_max_retries: int = 3
    
    # Haiku pricing (per 1M tokens) - November 2024
    # Input: $1.00 per 1M tokens = $0.001 per 1K tokens
    # Output: $5.00 per 1M tokens = $0.005 per 1K tokens
    llm_input_cost_per_1k: float = 0.001
    llm_output_cost_per_1k: float = 0.005
    
    class Config:
        env_prefix = ""
        env_file = ".env"
```

Create `.env.example`:
```bash
# Anthropic API Key (required)
ANTHROPIC_API_KEY=sk-ant-api03-...

# Optional overrides
# LLM_TEMPERATURE=0.3
# LLM_MAX_TOKENS=2000
# LLM_TIMEOUT=30
```

---

## Exceptions

Add to `app/utils/exceptions.py`:

```python
class LLMError(ScoutError):
    """Base error for LLM operations."""
    pass


class LLMProviderError(LLMError):
    """Error from the LLM provider (Anthropic)."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)


class LLMTimeoutError(LLMError):
    """LLM request timed out."""
    pass


class LLMResponseError(LLMError):
    """Error parsing or validating LLM response."""
    pass
```

---

## Service Implementation

Create `app/services/llm.py`:

```python
"""
LLM Service

Wrapper around Anthropic Claude API with cost tracking and caching.

Usage:
    llm = LLMService(cost_tracker, cache)
    await llm.initialize()
    
    # Simple text generation
    response = await llm.generate(
        messages=[PromptMessage(role="user", content="Hello!")],
        module="test"
    )
    print(response.content)
    
    # JSON extraction
    data = await llm.generate_json(
        prompt="Extract name and age from: John is 30 years old",
        schema={"name": "string", "age": "integer"},
        module="rinser"
    )
    print(data)  # {"name": "John", "age": 30}
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

import anthropic
from anthropic import APIError, APITimeoutError, RateLimitError

from app.models.llm import (
    LLMRequest, LLMResponse, PromptMessage, MessageRole,
    TokenUsage, LLMHealth
)
from app.services.cost_tracker import CostTrackerService
from app.services.cache import CacheService
from app.config.settings import settings
from app.utils.exceptions import (
    LLMError, LLMProviderError, LLMTimeoutError, 
    LLMResponseError, BudgetExceededError
)

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM Service for Scout.
    
    Provides a simple interface to Claude API with:
    - Automatic budget checking via Cost Tracker
    - Response caching via Cache Service
    - Retry logic with exponential backoff
    - Cost calculation and recording
    
    Attributes:
        cost_tracker: Cost Tracker Service instance
        cache: Cache Service instance
        
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
        cache: CacheService
    ):
        """
        Initialize LLM Service.
        
        Args:
            cost_tracker: Cost Tracker Service for budget management
            cache: Cache Service for response caching
        """
        self._cost_tracker = cost_tracker
        self._cache = cache
        self._client: Optional[anthropic.AsyncAnthropic] = None
        self._initialized = False
        
        # Configuration
        self._model = settings.llm_model
        self._timeout = settings.llm_timeout
        self._max_retries = settings.llm_max_retries
        self._input_cost_per_1k = settings.llm_input_cost_per_1k
        self._output_cost_per_1k = settings.llm_output_cost_per_1k
        
        # Stats
        self._total_requests = 0
        self._total_cost = 0.0
        self._last_request_time: Optional[datetime] = None
        self._last_error: Optional[str] = None
    
    async def initialize(self) -> None:
        """
        Initialize the LLM Service.
        
        Creates Anthropic client and verifies API key.
        
        Raises:
            LLMProviderError: If API key is invalid or API unreachable
        """
        if self._initialized:
            logger.warning("LLM Service already initialized")
            return
        
        # Create client
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=self._timeout
        )
        
        # Verify connection with minimal request
        try:
            # Just verify the client can be created - don't make a test call
            # to save costs. Real verification happens on first request.
            logger.info(f"LLM Service initialized with model: {self._model}")
            self._initialized = True
        except Exception as e:
            raise LLMProviderError(f"Failed to initialize Anthropic client: {e}")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the LLM Service."""
        if self._client:
            await self._client.close()
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
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost in USD
        """
        input_cost = (input_tokens / 1000) * self._input_cost_per_1k
        output_cost = (output_tokens / 1000) * self._output_cost_per_1k
        return input_cost + output_cost
    
    # =========================================================================
    # CACHE OPERATIONS
    # =========================================================================
    
    async def _check_cache(self, cache_key: str) -> Optional[LLMResponse]:
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
        ttl: int
    ) -> None:
        """Store response in cache."""
        try:
            await self._cache.set(
                cache_key,
                response.model_dump(mode='json'),
                ttl=ttl
            )
            logger.debug(f"Cached LLM response: {cache_key[:16]}...")
        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")
    
    # =========================================================================
    # API CALL
    # =========================================================================
    
    async def _call_api(
        self,
        request: LLMRequest,
        request_id: str
    ) -> LLMResponse:
        """
        Make actual API call to Anthropic.
        
        Args:
            request: The LLM request
            request_id: Unique request identifier
            
        Returns:
            LLMResponse with content and usage
            
        Raises:
            LLMProviderError: On API errors
            LLMTimeoutError: On timeout
        """
        start_time = time.time()
        
        # Build messages for API
        messages = [m.to_api_format() for m in request.messages]
        
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=request.system or "",
                messages=messages
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Extract content
            content = response.content[0].text if response.content else ""
            
            # Build usage
            usage = TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens
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
                request_id=request_id
            )
            
        except APITimeoutError as e:
            raise LLMTimeoutError(f"Request timed out after {self._timeout}s")
        except RateLimitError as e:
            raise LLMProviderError(f"Rate limit exceeded: {e}", status_code=429)
        except APIError as e:
            raise LLMProviderError(f"Anthropic API error: {e}", status_code=e.status_code)
    
    async def _call_with_retry(
        self,
        request: LLMRequest,
        request_id: str
    ) -> LLMResponse:
        """
        Call API with retry logic.
        
        Retries on transient errors with exponential backoff.
        
        Args:
            request: The LLM request
            request_id: Unique request identifier
            
        Returns:
            LLMResponse on success
            
        Raises:
            LLMError: After all retries exhausted
        """
        last_error: Optional[Exception] = None
        
        for attempt in range(self._max_retries):
            try:
                response = await self._call_api(request, request_id)
                response.retry_count = attempt
                return response
                
            except LLMTimeoutError as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1}/{self._max_retries} timed out")
                
            except LLMProviderError as e:
                last_error = e
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
        messages: List[PromptMessage],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        module: Optional[str] = None,
        purpose: Optional[str] = None,
        use_cache: bool = True,
        cache_ttl: int = 3600
    ) -> LLMResponse:
        """
        Generate text using Claude.
        
        This is the main method for LLM interactions.
        
        Args:
            messages: Conversation messages
            system: Optional system prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            module: Module making the request (for cost tracking)
            purpose: Purpose of request (for logging)
            use_cache: Whether to use caching
            cache_ttl: Cache time-to-live in seconds
            
        Returns:
            LLMResponse with generated content
            
        Raises:
            BudgetExceededError: If budget limit reached
            LLMError: On generation failure
            
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
            temperature=temperature or settings.llm_temperature,
            max_tokens=max_tokens or settings.llm_max_tokens,
            module=module,
            purpose=purpose,
            use_cache=use_cache,
            cache_ttl=cache_ttl
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
        self._cost_tracker.check_budget_or_raise()
        
        # Make API call with retry
        response = await self._call_with_retry(request, request_id)
        
        # Record cost
        self._cost_tracker.record_cost(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self._model,
            module=module,
            request_id=request_id
        )
        
        # Update stats
        self._total_requests += 1
        self._total_cost += response.cost
        self._last_request_time = datetime.now()
        
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
        system: Optional[str] = None,
        module: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Simple text generation from a single prompt.
        
        Convenience method for simple use cases.
        
        Args:
            prompt: User prompt
            system: Optional system prompt
            module: Module name for tracking
            **kwargs: Additional arguments for generate()
            
        Returns:
            Generated text content
            
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
            **kwargs
        )
        return response.content
    
    async def generate_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        module: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate and parse JSON response.
        
        Instructs Claude to respond in JSON and parses the result.
        
        Args:
            prompt: User prompt (should request JSON output)
            system: Optional system prompt (will add JSON instruction)
            module: Module name for tracking
            **kwargs: Additional arguments for generate()
            
        Returns:
            Parsed JSON as dictionary
            
        Raises:
            LLMResponseError: If response is not valid JSON
            
        Example:
            >>> data = await llm.generate_json(
            ...     prompt="Extract: John is 30 years old. Return {name, age}",
            ...     module="rinser"
            ... )
            >>> print(data)
            {"name": "John", "age": 30}
        """
        import json
        
        # Add JSON instruction to system prompt
        json_instruction = "You must respond with valid JSON only. No other text."
        if system:
            system = f"{system}\n\n{json_instruction}"
        else:
            system = json_instruction
        
        response = await self.generate(
            messages=[PromptMessage(role=MessageRole.USER, content=prompt)],
            system=system,
            module=module,
            temperature=0.1,  # Lower temperature for structured output
            **kwargs
        )
        
        # Parse JSON from response
        content = response.content.strip()
        
        # Handle markdown code blocks
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first and last lines (```json and ```)
            content = "\n".join(lines[1:-1])
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMResponseError(
                f"Failed to parse JSON response: {e}\nContent: {content[:200]}..."
            )
    
    # =========================================================================
    # HEALTH & STATS
    # =========================================================================
    
    async def health_check(self) -> LLMHealth:
        """
        Check health of LLM Service.
        
        Returns:
            LLMHealth with status and metrics
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
            total_cost=self._total_cost
        )


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

_llm_instance: Optional[LLMService] = None


async def get_llm_service() -> LLMService:
    """
    Get the LLM Service instance.
    
    Creates and initializes singleton on first call.
    Requires Cost Tracker and Cache services.
    
    Returns:
        Initialized LLMService
    """
    global _llm_instance
    
    if _llm_instance is None:
        from app.services.cost_tracker import get_cost_tracker
        from app.services.cache import get_cache_service
        
        cost_tracker = get_cost_tracker()
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
```

---

## Test Implementation

Create `tests/unit/services/test_llm.py`:

```python
"""
Unit tests for LLM Service.

Run with: pytest tests/unit/services/test_llm.py -v
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from app.services.llm import LLMService, get_llm_service, reset_llm_service
from app.models.llm import (
    LLMRequest, LLMResponse, PromptMessage, MessageRole,
    TokenUsage, LLMHealth
)
from app.utils.exceptions import (
    LLMError, LLMProviderError, LLMTimeoutError,
    LLMResponseError, BudgetExceededError
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_cost_tracker():
    """Create mock Cost Tracker."""
    tracker = Mock()
    tracker.can_proceed.return_value = True
    tracker.check_budget_or_raise.return_value = None
    tracker.record_cost.return_value = Mock()
    return tracker


@pytest.fixture
def mock_cache():
    """Create mock Cache Service."""
    cache = AsyncMock()
    cache.get.return_value = None  # Cache miss by default
    cache.set.return_value = None
    return cache


@pytest.fixture
def mock_settings():
    """Mock settings."""
    with patch("app.services.llm.settings") as mock:
        mock.anthropic_api_key = "test-key"
        mock.llm_model = "claude-3-5-haiku-20241022"
        mock.llm_temperature = 0.3
        mock.llm_max_tokens = 2000
        mock.llm_timeout = 30
        mock.llm_max_retries = 3
        mock.llm_input_cost_per_1k = 0.001
        mock.llm_output_cost_per_1k = 0.005
        yield mock


@pytest.fixture
def mock_anthropic_response():
    """Create mock Anthropic API response."""
    response = Mock()
    response.content = [Mock(text="Test response")]
    response.usage = Mock(input_tokens=100, output_tokens=50)
    return response


@pytest.fixture
async def llm_service(mock_cost_tracker, mock_cache, mock_settings):
    """Create LLM Service for testing."""
    reset_llm_service()
    service = LLMService(mock_cost_tracker, mock_cache)
    
    # Mock the Anthropic client
    with patch("app.services.llm.anthropic.AsyncAnthropic") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        await service.initialize()
        service._client = mock_client
        
        yield service
        
    await service.shutdown()


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================

class TestInitialization:
    """Tests for service initialization."""
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_cost_tracker, mock_cache, mock_settings):
        """Should initialize successfully."""
        with patch("app.services.llm.anthropic.AsyncAnthropic"):
            service = LLMService(mock_cost_tracker, mock_cache)
            await service.initialize()
            
            assert service._initialized is True
    
    @pytest.mark.asyncio
    async def test_double_initialize_warning(self, llm_service, caplog):
        """Should warn on double initialization."""
        await llm_service.initialize()
        assert "already initialized" in caplog.text.lower()
    
    @pytest.mark.asyncio
    async def test_operation_before_init_raises(self, mock_cost_tracker, mock_cache, mock_settings):
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
    async def test_calculate_cost(self, llm_service):
        """Should calculate cost correctly."""
        # 1000 input + 1000 output tokens
        # = $0.001 + $0.005 = $0.006
        cost = llm_service._calculate_cost(1000, 1000)
        assert cost == pytest.approx(0.006, rel=1e-6)
    
    @pytest.mark.asyncio
    async def test_calculate_cost_zero(self, llm_service):
        """Should handle zero tokens."""
        cost = llm_service._calculate_cost(0, 0)
        assert cost == 0.0


# =============================================================================
# CACHE TESTS
# =============================================================================

class TestCaching:
    """Tests for cache integration."""
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, llm_service, mock_cache, mock_anthropic_response):
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
            "retry_count": 0
        }
        mock_cache.get.return_value = cached_data
        
        response = await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="test")],
            module="test"
        )
        
        assert response.content == "Cached response"
        assert response.cached is True
        # API should not have been called
        llm_service._client.messages.create.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cache_miss_stores_response(
        self, llm_service, mock_cache, mock_anthropic_response
    ):
        """Should store response in cache on miss."""
        mock_cache.get.return_value = None  # Cache miss
        llm_service._client.messages.create.return_value = mock_anthropic_response
        
        await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="test")],
            module="test"
        )
        
        # Verify cache.set was called
        mock_cache.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_disabled(self, llm_service, mock_cache, mock_anthropic_response):
        """Should skip cache when disabled."""
        llm_service._client.messages.create.return_value = mock_anthropic_response
        
        await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="test")],
            module="test",
            use_cache=False
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
        self, llm_service, mock_cost_tracker, mock_anthropic_response
    ):
        """Should check budget before making request."""
        llm_service._client.messages.create.return_value = mock_anthropic_response
        
        await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="test")],
            module="test"
        )
        
        mock_cost_tracker.check_budget_or_raise.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_budget_exceeded_raises(self, llm_service, mock_cost_tracker):
        """Should raise when budget exceeded."""
        mock_cost_tracker.check_budget_or_raise.side_effect = BudgetExceededError(
            "daily", 10.0, 10.0
        )
        
        with pytest.raises(BudgetExceededError):
            await llm_service.generate(
                messages=[PromptMessage(role=MessageRole.USER, content="test")],
                module="test"
            )
    
    @pytest.mark.asyncio
    async def test_cost_recorded_after_success(
        self, llm_service, mock_cost_tracker, mock_anthropic_response
    ):
        """Should record cost after successful request."""
        llm_service._client.messages.create.return_value = mock_anthropic_response
        
        await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="test")],
            module="test"
        )
        
        mock_cost_tracker.record_cost.assert_called_once()
        call_kwargs = mock_cost_tracker.record_cost.call_args[1]
        assert call_kwargs["input_tokens"] == 100
        assert call_kwargs["output_tokens"] == 50
        assert call_kwargs["module"] == "test"


# =============================================================================
# RETRY TESTS
# =============================================================================

class TestRetryLogic:
    """Tests for retry logic."""
    
    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, llm_service, mock_anthropic_response):
        """Should retry on timeout."""
        from anthropic import APITimeoutError
        
        # First call times out, second succeeds
        llm_service._client.messages.create.side_effect = [
            APITimeoutError(request=Mock()),
            mock_anthropic_response
        ]
        
        response = await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="test")],
            module="test"
        )
        
        assert response.retry_count == 1
        assert llm_service._client.messages.create.call_count == 2
    
    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(self, llm_service):
        """Should not retry on 4xx errors (except 429)."""
        from anthropic import APIError
        
        error = APIError(
            message="Bad request",
            request=Mock(),
            body={}
        )
        error.status_code = 400
        llm_service._client.messages.create.side_effect = error
        
        with pytest.raises(LLMProviderError):
            await llm_service.generate(
                messages=[PromptMessage(role=MessageRole.USER, content="test")],
                module="test"
            )
        
        # Should only try once
        assert llm_service._client.messages.create.call_count == 1
    
    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self, llm_service):
        """Should fail after all retries exhausted."""
        from anthropic import APITimeoutError
        
        # All calls timeout
        llm_service._client.messages.create.side_effect = APITimeoutError(
            request=Mock()
        )
        
        with pytest.raises(LLMError, match="All 3 attempts failed"):
            await llm_service.generate(
                messages=[PromptMessage(role=MessageRole.USER, content="test")],
                module="test"
            )


# =============================================================================
# GENERATE TESTS
# =============================================================================

class TestGenerate:
    """Tests for generate method."""
    
    @pytest.mark.asyncio
    async def test_generate_success(self, llm_service, mock_anthropic_response):
        """Should generate response successfully."""
        llm_service._client.messages.create.return_value = mock_anthropic_response
        
        response = await llm_service.generate(
            messages=[PromptMessage(role=MessageRole.USER, content="Hello")],
            module="test"
        )
        
        assert response.content == "Test response"
        assert response.usage.input_tokens == 100
        assert response.usage.output_tokens == 50
        assert response.cost == pytest.approx(0.00035, rel=1e-4)
    
    @pytest.mark.asyncio
    async def test_generate_text_convenience(self, llm_service, mock_anthropic_response):
        """Should use generate_text convenience method."""
        llm_service._client.messages.create.return_value = mock_anthropic_response
        
        text = await llm_service.generate_text(
            prompt="Hello",
            module="test"
        )
        
        assert text == "Test response"


# =============================================================================
# JSON GENERATION TESTS
# =============================================================================

class TestGenerateJson:
    """Tests for JSON generation."""
    
    @pytest.mark.asyncio
    async def test_generate_json_success(self, llm_service):
        """Should parse JSON response."""
        json_response = Mock()
        json_response.content = [Mock(text='{"name": "John", "age": 30}')]
        json_response.usage = Mock(input_tokens=100, output_tokens=50)
        llm_service._client.messages.create.return_value = json_response
        
        result = await llm_service.generate_json(
            prompt="Extract: John is 30",
            module="test"
        )
        
        assert result == {"name": "John", "age": 30}
    
    @pytest.mark.asyncio
    async def test_generate_json_with_markdown(self, llm_service):
        """Should handle JSON wrapped in markdown code blocks."""
        json_response = Mock()
        json_response.content = [Mock(text='```json\n{"name": "John"}\n```')]
        json_response.usage = Mock(input_tokens=100, output_tokens=50)
        llm_service._client.messages.create.return_value = json_response
        
        result = await llm_service.generate_json(
            prompt="Extract name",
            module="test"
        )
        
        assert result == {"name": "John"}
    
    @pytest.mark.asyncio
    async def test_generate_json_invalid_raises(self, llm_service):
        """Should raise on invalid JSON."""
        json_response = Mock()
        json_response.content = [Mock(text='not valid json')]
        json_response.usage = Mock(input_tokens=100, output_tokens=50)
        llm_service._client.messages.create.return_value = json_response
        
        with pytest.raises(LLMResponseError, match="Failed to parse JSON"):
            await llm_service.generate_json(
                prompt="Extract something",
                module="test"
            )


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================

class TestHealthCheck:
    """Tests for health checks."""
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, llm_service):
        """Should report healthy status."""
        health = await llm_service.health_check()
        
        assert health.status == "healthy"
        assert health.api_connected is True
    
    @pytest.mark.asyncio
    async def test_health_check_unavailable(self, mock_cost_tracker, mock_cache, mock_settings):
        """Should report unavailable when not initialized."""
        service = LLMService(mock_cost_tracker, mock_cache)
        # Don't initialize
        
        health = await service.health_check()
        
        assert health.status == "unavailable"
        assert health.api_connected is False
```

---

## Implementation Steps

Follow these steps in order, verifying each before proceeding:

### Step 1.1: Exceptions
```bash
# Add LLM exceptions to app/utils/exceptions.py
# Verify:
python -c "from app.utils.exceptions import LLMError, LLMProviderError; print('OK')"
```

### Step 1.2: Configuration
```bash
# Add LLM settings to app/config/settings.py
# Create .env with ANTHROPIC_API_KEY
# Verify:
python -c "from app.config.settings import settings; print(settings.llm_model)"
```

### Step 1.3: Data Models
```bash
# Create app/models/llm.py
# Verify:
python -c "from app.models.llm import LLMRequest, LLMResponse, PromptMessage; print('OK')"
```

### Step 1.4: Service Implementation
```bash
# Create app/services/llm.py
# Verify:
python -c "from app.services.llm import LLMService; print('OK')"
```

### Step 1.5: Unit Tests
```bash
# Create tests/unit/services/test_llm.py
# Verify:
pytest tests/unit/services/test_llm.py -v
```

### Step 1.6: Integration Verification
```bash
# Verify with real API call (uses actual API key and budget):
python -c "
import asyncio
from app.services.llm import get_llm_service
from app.models.llm import PromptMessage, MessageRole

async def test():
    llm = await get_llm_service()
    response = await llm.generate(
        messages=[
            PromptMessage(role=MessageRole.USER, content='Say hello in exactly 3 words')
        ],
        module='integration_test'
    )
    print(f'Response: {response.content}')
    print(f'Cost: \${response.cost:.6f}')
    print(f'Tokens: {response.usage.total_tokens}')

asyncio.run(test())
"
```

---

## Success Criteria

| Metric | Target | Verification |
|--------|--------|--------------|
| API integration | Working connection | Test with real API key |
| Budget enforcement | 100% blocking when exceeded | Test with exceeded budget |
| Cache integration | Hit returns cached, miss stores | Test with mock cache |
| Retry logic | 3 attempts with backoff | Test with mock failures |
| JSON parsing | Handles plain and markdown | Test various formats |
| Test coverage | >90% | `pytest --cov=app/services/llm` |

---

## Edge Cases Handled

| Edge Case | Handling |
|-----------|----------|
| Invalid API key | LLMProviderError on first request |
| Timeout | Retry up to 3 times |
| Rate limit (429) | Retry with backoff |
| Client error (4xx) | Fail immediately, don't retry |
| Invalid JSON response | LLMResponseError with content preview |
| Budget exceeded | BudgetExceededError before request |
| Empty response | Return empty string |
| Markdown-wrapped JSON | Strip code blocks before parsing |

---

*This specification is aligned with Scout PoC Scope Document v1.0*
