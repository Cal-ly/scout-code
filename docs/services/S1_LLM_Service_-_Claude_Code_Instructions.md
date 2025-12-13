# S1 LLM Service - Claude Code Instructions

**Version:** 3.0 (Local LLM - Ollama)
**Updated:** December 13, 2025
**Status:** Implemented
**Priority:** Phase 1 - Foundation Service (Build Fourth - after S2, S3, S4)

---

## PoC Scope Summary

| Feature | Status | Notes |
|---------|--------|-------|
| ~~Anthropic Claude API~~ | ❌ Replaced | Changed to local Ollama |
| **Ollama Local Inference** | ✅ In Scope | Primary provider for edge deployment |
| **Qwen 2.5 3B** | ✅ In Scope | Primary model (Q4 quantized) |
| **Gemma 2 2B** | ✅ In Scope | Fallback model |
| Provider abstraction | ✅ In Scope | LLMProvider interface for flexibility |
| Basic retry logic | ✅ In Scope | 3 attempts, fixed delays (1s, 2s, 4s) |
| Cost tracking integration | ✅ In Scope | Track metrics (no billing for local) |
| Cache integration | ✅ In Scope | Check cache before, store after |
| JSON response parsing | ✅ In Scope | Ollama JSON mode + schema constraints |
| Request timeout | ✅ In Scope | 120 second timeout (local is slower) |
| OpenAI/Anthropic fallback | ❌ Deferred | Local-only for PoC thesis |
| Model selection UI | ❌ Deferred | Config-based selection sufficient |
| Streaming responses | ❌ Deferred | Not needed for PoC |
| Function calling | ❌ Deferred | JSON mode sufficient |

### Architecture Change (December 2025)

**Previous:** Anthropic Claude Haiku 3.5 API
**Current:** Ollama with Qwen 2.5 3B / Gemma 2 2B local models

This change supports the thesis objective of **edge computing on Raspberry Pi 5**.

---

## Context & Objective

Build the **LLM Service** for Scout - a wrapper around **Ollama** for local LLM inference that integrates with Cost Tracker and Cache services. This service is the sole interface for all LLM operations in the application.

### Why This Service Exists

All Scout modules need LLM capabilities for:
- Rinser: Extract structured job data from raw text
- Analyzer: Generate strategy recommendations
- Creator: Generate tailored CVs and cover letters

The LLM Service centralizes:
- Local model management via Ollama
- Provider abstraction (allows future API fallback)
- Cost/usage tracking for metrics
- Response caching
- Error handling and retries

### Dependencies

This service **requires** these services to be implemented first:
- **S2 Cost Tracker**: For usage metrics recording
- **S3 Cache Service**: For response caching

**External Dependency:** Ollama must be installed and running.

---

## Technical Requirements

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Ollama | v0.5.0+ | Latest |
| RAM (Pi 5) | 8GB | 8GB |
| Storage | 5GB free | 10GB free |
| Model: Qwen 2.5 3B | ~2GB | - |
| Model: Gemma 2 2B | ~1.6GB | - |

### Python Dependencies

```toml
[tool.poetry.dependencies]
ollama = "^0.4.0"  # Ollama Python SDK
```

### File Structure

```
src/
├── services/
│   └── llm_service/
│       ├── __init__.py           # Package exports
│       ├── models.py             # LLM data models
│       ├── exceptions.py         # LLM exceptions
│       ├── service.py            # Main LLM Service
│       └── providers/            # Provider implementations
│           ├── __init__.py       # Provider exports
│           ├── base.py           # Abstract LLMProvider
│           └── ollama_provider.py # Ollama implementation
└── tests/
    └── test_llm.py               # LLM Service tests
```

---

## Data Models

Update `src/services/llm_service/models.py`:

```python
"""
LLM Service Data Models

Models for Ollama-based local LLM integration.
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
    model: str = "qwen2.5:3b"  # Default local model
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
    ollama_connected: bool = True  # Renamed from api_connected
    model_loaded: str | None = None  # Currently loaded model
    last_request_time: Optional[datetime] = None
    last_error: Optional[str] = None
    total_requests: int = 0
    total_tokens: int = 0  # Track tokens instead of cost for local


class LLMConfig(BaseModel):
    """Configuration for LLM Service."""

    # Provider selection
    provider: str = "ollama"  # Currently only "ollama" supported

    # Ollama settings
    ollama_host: str = "http://localhost:11434"
    model: str = "qwen2.5:3b"
    fallback_model: str = "gemma2:2b"

    # Generation parameters
    temperature: float = 0.3
    max_tokens: int = 2000
    timeout: int = 120  # Longer timeout for local inference
    max_retries: int = 3

    # Cost tracking (for metrics, not billing - local is free)
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
```

---

## Configuration

Update `.env.example`:

```bash
# ============================================
# LLM Service Configuration (Local Ollama)
# ============================================
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:3b
LLM_FALLBACK_MODEL=gemma2:2b
OLLAMA_HOST=http://localhost:11434

# Generation Parameters
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2000
LLM_TIMEOUT=120

# Note: No API key required for local Ollama inference
# ANTHROPIC_API_KEY is no longer used
```

### Ollama Setup (Required)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull qwen2.5:3b
ollama pull gemma2:2b

# Start Ollama service
ollama serve
```

---

## Exceptions

Located in `src/services/llm_service/exceptions.py`:

```python
class LLMError(ScoutError):
    """Base error for LLM operations."""
    pass


class LLMProviderError(LLMError):
    """Error from the LLM provider (Ollama)."""

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

> **Note:** For complete implementation details including the OllamaProvider,
> see `docs/guides/Local_LLM_Transition_Guide.md`

Update `src/services/llm_service/service.py`:

```python
"""
LLM Service

Wrapper around Ollama for local LLM inference with caching.

Usage:
    llm = LLMService(cost_tracker, cache)
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
import time
import uuid
from datetime import datetime
from typing import Any

from src.services.cache_service import CacheService
from src.services.cost_tracker import CostTrackerService
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
from src.services.llm_service.providers import LLMProvider, OllamaProvider

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM Service for Scout.

    Provides a simple interface to local LLMs via Ollama with:
    - Provider abstraction for flexibility
    - Response caching via Cache Service
    - Retry logic with exponential backoff
    - Usage metrics tracking

    Attributes:
        cost_tracker: Cost Tracker Service instance (for metrics)
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
        cache: CacheService,
        config: LLMConfig | None = None,
    ):
        """
        Initialize LLM Service.

        Args:
            cost_tracker: Cost Tracker Service for usage metrics
            cache: Cache Service for response caching
            config: Optional configuration overrides
        """
        self._cost_tracker = cost_tracker
        self._cache = cache
        self._config = config or LLMConfig()
        self._provider: LLMProvider | None = None
        self._initialized = False

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
            LLMInitializationError: If Ollama not running or model not found
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
                timeout=float(self._config.timeout),
            )
            await self._provider.initialize()

            self._initialized = True
            logger.info(f"LLM Service initialized with Ollama: {self._config.model}")

        except Exception as e:
            raise LLMInitializationError(
                f"Failed to initialize Ollama provider: {e}"
            ) from e

    async def shutdown(self) -> None:
        """Gracefully shutdown the LLM Service."""
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
    # CACHE OPERATIONS (unchanged from original)
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
    # PROVIDER CALL
    # =========================================================================

    async def _call_api(
        self,
        request: LLMRequest,
        request_id: str
    ) -> LLMResponse:
        """
        Make actual call to LLM provider (Ollama).

        Args:
            request: The LLM request
            request_id: Unique request identifier

        Returns:
            LLMResponse with content and usage

        Raises:
            LLMProviderError: On provider errors
            LLMTimeoutError: On timeout
        """
        if self._provider is None:
            raise LLMError("LLM provider not initialized")

        return await self._provider.generate(request, request_id)
    
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

        # Check cache first
        if use_cache:
            cached = await self._check_cache(cache_key)
            if cached is not None:
                return cached

        # Check budget before making request
        await self._check_budget()

        # Make API call with retry
        response = await self._call_with_retry(request, request_id)

        # Record usage in cost tracker (cost is 0 for local inference)
        cost = self._calculate_cost(
            response.usage.input_tokens, response.usage.output_tokens
        )
        await self._cost_tracker.record_cost(
            service_name="ollama",
            model=self._model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost=cost,  # Will be 0.0 for local inference
            module=module,
        )

        # Update stats
        self._total_requests += 1
        self._total_tokens += response.usage.total_tokens
        self._last_request_time = datetime.now()

        # Cache response
        if use_cache:
            await self._store_in_cache(cache_key, response, cache_ttl)

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
        
        Instructs LLM to respond in JSON and parses the result.
        
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
        ollama_connected = True
        model_loaded: str | None = self._model

        if not self._initialized:
            status = "unavailable"
            ollama_connected = False
            model_loaded = None
        elif self._last_error:
            status = "degraded"

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
```

---

## Test Implementation

Tests are located in `tests/test_llm_service.py` with 52 tests covering:

- Model validation (PromptMessage, LLMRequest, TokenUsage, LLMResponse, LLMHealth, LLMConfig)
- Service initialization with Ollama provider
- Cache integration (hit, miss, disabled)
- Budget enforcement
- Retry logic with exponential backoff
- Text generation and JSON parsing
- Health checks and statistics
- Provider abstraction (OllamaProvider)

Run tests:
```bash
pytest tests/test_llm_service.py -v
```

---

## Implementation Status

**Status:** Implemented and tested

The LLM Service has been fully implemented with Ollama as the provider. Key components:

1. **Provider abstraction** (`src/services/llm_service/providers/`)
   - `base.py` - Abstract LLMProvider interface
   - `ollama_provider.py` - Ollama implementation with fallback support

2. **Service** (`src/services/llm_service/service.py`)
   - Uses provider abstraction for LLM calls
   - Integrates with Cache and Cost Tracker services
   - Supports JSON mode for structured output

3. **Tests** (`tests/test_llm_service.py`)
   - 52 tests passing
   - Mocks OllamaProvider for unit testing

## Verification Commands

```bash
# Syntax check
python -m py_compile src/services/llm_service/service.py

# Type check
mypy src/services/llm_service --ignore-missing-imports

# Lint
ruff check src/services/llm_service

# Run tests
pytest tests/test_llm_service.py -v
```

## Integration Test

Requires Ollama to be running with models pulled:

```bash
# Ensure Ollama is running
ollama serve &

# Pull models if not already present
ollama pull qwen2.5:3b
ollama pull gemma2:2b

# Test integration
python -c "
import asyncio
from src.services.llm_service import get_llm_service
from src.services.llm_service.models import PromptMessage, MessageRole

async def test():
    llm = await get_llm_service()
    response = await llm.generate(
        messages=[
            PromptMessage(role=MessageRole.USER, content='Say hello in exactly 3 words')
        ],
        module='integration_test'
    )
    print(f'Response: {response.content}')
    print(f'Tokens: {response.usage.total_tokens}')
    print(f'Latency: {response.latency_ms}ms')

asyncio.run(test())
"
```

---

## Success Criteria

| Metric | Target | Status |
|--------|--------|--------|
| Ollama integration | Working connection | ✅ Implemented |
| Budget enforcement | Check before request | ✅ Implemented |
| Cache integration | Hit returns cached, miss stores | ✅ Implemented |
| Retry logic | 3 attempts with backoff | ✅ Implemented |
| JSON parsing | Handles plain and markdown | ✅ Implemented |
| Test coverage | >90% | ✅ 52 tests passing |

---

## Edge Cases Handled

| Edge Case | Handling |
|-----------|----------|
| Ollama not running | LLMInitializationError with helpful message |
| Model not found | LLMInitializationError with `ollama pull` instruction |
| Timeout | Retry up to 3 times with exponential backoff |
| Provider error | LLMProviderError with status code |
| Invalid JSON response | LLMResponseError with content preview |
| Budget exceeded | BudgetExceededError before request |
| Empty response | Return empty string |
| Markdown-wrapped JSON | Strip code blocks before parsing |

---

*This specification is aligned with Scout PoC Scope Document v1.1 (Local LLM Transition)*
