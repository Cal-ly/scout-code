# Scout Local LLM Transition Guide

**Version:** 1.0
**Created:** December 13, 2025
**Status:** Approved for Implementation

---

## Executive Summary

This guide documents the transition from Anthropic Claude Haiku 3.5 API to local LLM inference using **Ollama** with **Qwen 2.5 3B** as the primary model. This change aligns with the thesis objective of exploring edge computing on Raspberry Pi 5.

### Key Changes

| Aspect | Before | After |
|--------|--------|-------|
| Provider | Anthropic API | Ollama (Local) |
| Model | Claude 3.5 Haiku | Qwen 2.5 3B (Q4) |
| Fallback | None | Gemma 2 2B |
| Cost | $0.001/$0.005 per 1K tokens | Free (electricity only) |
| Structured Output | Prompt-based JSON | Ollama JSON schema constraints |

---

## Part 1: Prerequisites

### 1.1 Install Ollama

#### Development Machine (Windows/Linux/macOS)

```bash
# Windows (PowerShell as Administrator)
winget install Ollama.Ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama
```

#### Raspberry Pi 5 (64-bit Raspberry Pi OS)

```bash
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version
```

### 1.2 Pull Required Models

```bash
# Primary model - Qwen 2.5 3B (Q4 quantization)
ollama pull qwen2.5:3b

# Fallback model - Gemma 2 2B
ollama pull gemma2:2b

# Verify models
ollama list
```

**Expected output:**
```
NAME            ID              SIZE    MODIFIED
qwen2.5:3b      abc123def456    2.0 GB  Just now
gemma2:2b       def456abc789    1.6 GB  Just now
```

### 1.3 Test Ollama is Running

```bash
# Start Ollama service (if not auto-started)
ollama serve &

# Test basic inference
ollama run qwen2.5:3b "Hello, respond with exactly 3 words"

# Test JSON mode
curl http://localhost:11434/api/chat -d '{
  "model": "qwen2.5:3b",
  "messages": [{"role": "user", "content": "Return a JSON object with name and age"}],
  "format": "json",
  "stream": false
}'
```

---

## Part 2: Implementation Steps

### Phase 1: Add Ollama Dependencies

#### Step 1.1: Update requirements.txt

```diff
# LLM Integration
- anthropic>=0.18.0
+ ollama>=0.4.0
+ # anthropic>=0.18.0  # Kept for reference, not used in PoC
```

#### Step 1.2: Install New Dependencies

```bash
# Activate venv and install
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

pip install ollama>=0.4.0
```

---

### Phase 2: Create Local LLM Provider

#### Step 2.1: Create Provider Abstraction

Create `src/services/llm_service/providers/__init__.py`:

```python
"""LLM Provider abstractions for Scout."""

from src.services.llm_service.providers.base import LLMProvider
from src.services.llm_service.providers.ollama_provider import OllamaProvider

__all__ = ["LLMProvider", "OllamaProvider"]
```

#### Step 2.2: Create Base Provider Interface

Create `src/services/llm_service/providers/base.py`:

```python
"""Base LLM Provider interface."""

from abc import ABC, abstractmethod
from typing import Any

from src.services.llm_service.models import LLMRequest, LLMResponse


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider connection."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the provider connection."""
        pass

    @abstractmethod
    async def generate(
        self,
        request: LLMRequest,
        request_id: str,
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check provider health status."""
        pass
```

#### Step 2.3: Create Ollama Provider

Create `src/services/llm_service/providers/ollama_provider.py`:

```python
"""Ollama LLM Provider implementation."""

import json
import logging
import time
from typing import Any

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
            model: Primary model name (default: qwen2.5:3b)
            fallback_model: Fallback model name (default: gemma2:2b)
            host: Ollama server URL
            timeout: Request timeout in seconds
        """
        self._model = model
        self._fallback_model = fallback_model
        self._host = host
        self._timeout = timeout
        self._client: ollama.AsyncClient | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Ollama client and verify model availability."""
        if self._initialized:
            logger.warning("Ollama provider already initialized")
            return

        try:
            self._client = ollama.AsyncClient(host=self._host)

            # Verify primary model is available
            models = await self._client.list()
            model_names = [m["name"] for m in models.get("models", [])]

            if not any(self._model in name for name in model_names):
                raise LLMInitializationError(
                    f"Model {self._model} not found. "
                    f"Run: ollama pull {self._model}"
                )

            self._initialized = True
            logger.info(f"Ollama provider initialized with model: {self._model}")

        except ResponseError as e:
            raise LLMInitializationError(
                f"Failed to connect to Ollama: {e}. "
                "Ensure Ollama is running: ollama serve"
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
            request: LLM request with messages and parameters
            request_id: Unique request identifier

        Returns:
            LLMResponse with content and usage metrics
        """
        if not self._initialized or self._client is None:
            raise LLMError("Ollama provider not initialized")

        start_time = time.time()

        # Build messages for Ollama
        messages = [m.to_api_format() for m in request.messages]

        # Add system message if provided
        if request.system:
            messages.insert(0, {"role": "system", "content": request.system})

        try:
            # Determine format based on request
            format_param = "json" if request.purpose == "json_extraction" else None

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

            # Extract content
            content = response.get("message", {}).get("content", "")

            # Ollama provides token counts in response
            prompt_tokens = response.get("prompt_eval_count", 0)
            completion_tokens = response.get("eval_count", 0)

            usage = TokenUsage(
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
            )

            # Local inference has no API cost (track for metrics only)
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
            if "timeout" in str(e).lower():
                raise LLMTimeoutError(
                    f"Request timed out after {self._timeout}s"
                ) from e
            raise LLMProviderError(f"Ollama error: {e}") from e

    async def health_check(self) -> dict[str, Any]:
        """Check Ollama server and model health."""
        if not self._initialized or self._client is None:
            return {
                "status": "unavailable",
                "provider": "ollama",
                "error": "Not initialized",
            }

        try:
            models = await self._client.list()
            return {
                "status": "healthy",
                "provider": "ollama",
                "model": self._model,
                "available_models": len(models.get("models", [])),
            }
        except Exception as e:
            return {
                "status": "degraded",
                "provider": "ollama",
                "error": str(e),
            }
```

---

### Phase 3: Update LLM Service

#### Step 3.1: Update LLMConfig Model

Edit `src/services/llm_service/models.py`:

```python
class LLMConfig(BaseModel):
    """Configuration for LLM Service."""

    # Provider selection
    provider: str = "ollama"  # Changed from "anthropic"

    # Model configuration
    model: str = "qwen2.5:3b"  # Changed from claude-3-5-haiku
    fallback_model: str = "gemma2:2b"

    # Ollama-specific settings
    ollama_host: str = "http://localhost:11434"

    # Generation parameters (unchanged)
    temperature: float = 0.3
    max_tokens: int = 2000
    timeout: int = 120  # Increased for local inference
    max_retries: int = 3

    # Cost tracking (for metrics, not billing)
    input_cost_per_1k: float = 0.0  # Local = free
    output_cost_per_1k: float = 0.0
```

#### Step 3.2: Update LLMService to Use Provider

Edit `src/services/llm_service/service.py`:

Key changes:
1. Replace `anthropic.AsyncAnthropic` with provider abstraction
2. Use `OllamaProvider` by default
3. Keep cache and retry logic unchanged
4. Update initialization to use Ollama

```python
# Replace Anthropic imports with:
from src.services.llm_service.providers import OllamaProvider, LLMProvider

# In __init__:
def __init__(
    self,
    cost_tracker: CostTrackerService,
    cache: CacheService,
    config: LLMConfig | None = None,
):
    # ... existing setup ...
    self._provider: LLMProvider | None = None

# In initialize:
async def initialize(self) -> None:
    if self._initialized:
        return

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

# Update _call_api to delegate to provider:
async def _call_api(
    self,
    request: LLMRequest,
    request_id: str,
) -> LLMResponse:
    if self._provider is None:
        raise LLMError("LLM provider not initialized")

    return await self._provider.generate(request, request_id)
```

---

### Phase 4: Update Configuration

#### Step 4.1: Update .env.example

```diff
# ============================================
# LLM Service Configuration
# ============================================
- ANTHROPIC_API_KEY=your_anthropic_api_key_here
- LLM_MODEL=claude-3-5-haiku-20241022
+ LLM_PROVIDER=ollama
+ LLM_MODEL=qwen2.5:3b
+ LLM_FALLBACK_MODEL=gemma2:2b
+ OLLAMA_HOST=http://localhost:11434
LLM_MAX_TOKENS=4096
- LLM_TEMPERATURE=0.7
+ LLM_TEMPERATURE=0.3

- # Budget Controls
- MONTHLY_BUDGET_LIMIT=50.00
- COST_WARNING_THRESHOLD=40.00
+ # Performance Monitoring (no cost for local inference)
+ LLM_REQUEST_TIMEOUT=120
```

#### Step 4.2: Update requirements.txt

```diff
# LLM Integration
- anthropic>=0.18.0
+ ollama>=0.4.0
```

---

### Phase 5: Update Tests

#### Step 5.1: Create Mock Ollama Provider for Tests

Create `tests/mocks/ollama_mock.py`:

```python
"""Mock Ollama provider for testing."""

from unittest.mock import AsyncMock, MagicMock


def create_mock_ollama_response(
    content: str = "Test response",
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
) -> dict:
    """Create a mock Ollama API response."""
    return {
        "message": {"content": content},
        "prompt_eval_count": prompt_tokens,
        "eval_count": completion_tokens,
    }


def create_mock_ollama_client() -> AsyncMock:
    """Create a mock Ollama AsyncClient."""
    client = AsyncMock()
    client.list.return_value = {
        "models": [
            {"name": "qwen2.5:3b"},
            {"name": "gemma2:2b"},
        ]
    }
    client.chat.return_value = create_mock_ollama_response()
    return client
```

#### Step 5.2: Update test_llm.py

Replace Anthropic mocks with Ollama mocks in existing tests.

---

### Phase 6: Verify Implementation

#### Step 6.1: Run Syntax Check

```bash
python -m py_compile src/services/llm_service/providers/ollama_provider.py
python -m py_compile src/services/llm_service/service.py
```

#### Step 6.2: Run Type Check

```bash
mypy src/services/llm_service/ --ignore-missing-imports
```

#### Step 6.3: Run Tests

```bash
pytest tests/test_llm.py -v
```

#### Step 6.4: Integration Test

```python
import asyncio
from src.services.llm_service import get_llm_service
from src.services.llm_service.models import PromptMessage, MessageRole

async def test_local_llm():
    llm = await get_llm_service()

    response = await llm.generate(
        messages=[
            PromptMessage(
                role=MessageRole.USER,
                content="Say hello in exactly 3 words"
            )
        ],
        module="integration_test"
    )

    print(f"Response: {response.content}")
    print(f"Tokens: {response.usage.total_tokens}")
    print(f"Latency: {response.latency_ms}ms")

asyncio.run(test_local_llm())
```

---

## Part 3: Raspberry Pi 5 Deployment

### 3.1 Pi 5 Specific Setup

```bash
# Ensure 64-bit Raspberry Pi OS
uname -m  # Should show: aarch64

# Install Ollama for ARM64
curl -fsSL https://ollama.com/install.sh | sh

# Configure swap for larger models (optional but recommended)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=4096
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Pull models
ollama pull qwen2.5:3b
ollama pull gemma2:2b
```

### 3.2 Ollama Service Configuration

```bash
# Create systemd service override for Pi optimizations
sudo mkdir -p /etc/systemd/system/ollama.service.d/
sudo nano /etc/systemd/system/ollama.service.d/override.conf
```

Add:
```ini
[Service]
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### 3.3 Expected Performance on Pi 5 (8GB)

| Model | Speed | Memory | Quality |
|-------|-------|--------|---------|
| Qwen 2.5 3B (Q4) | 2-4 tok/s | ~3GB | Best |
| Gemma 2 2B | 4-6 tok/s | ~2GB | Good |

**Estimated Pipeline Times:**
- Rinser (500 tokens): 2-4 minutes
- Analyzer (800 tokens): 3-6 minutes
- Creator (2000 tokens): 8-15 minutes
- **Total Pipeline: 15-30 minutes**

---

## Part 4: Fallback Strategy

### 4.1 Automatic Model Fallback

If primary model fails, switch to fallback:

```python
async def generate_with_fallback(
    self,
    request: LLMRequest,
    request_id: str,
) -> LLMResponse:
    """Generate with automatic fallback to secondary model."""
    try:
        return await self._generate_with_model(
            request, request_id, self._model
        )
    except LLMProviderError as e:
        logger.warning(f"Primary model failed: {e}, trying fallback")
        return await self._generate_with_model(
            request, request_id, self._fallback_model
        )
```

### 4.2 Remote Ollama Server (Optional)

For faster inference during development, run Ollama on a powerful machine:

```bash
# On powerful machine (dev machine with GPU)
OLLAMA_HOST=0.0.0.0 ollama serve

# In Scout .env on Pi
OLLAMA_HOST=http://dev-machine-ip:11434
```

---

## Part 5: Structured Output Handling

### 5.1 JSON Mode with Ollama

Ollama v0.5+ supports native JSON mode:

```python
# In generate_json method
response = await self._client.chat(
    model=self._model,
    messages=messages,
    format="json",  # Enforces JSON output
    options={"temperature": 0.1},
)
```

### 5.2 JSON Schema Constraints (Advanced)

For strict schema compliance, pass schema in format parameter:

```python
from pydantic import BaseModel

class JobExtraction(BaseModel):
    title: str
    company: str
    requirements: list[str]

response = await self._client.chat(
    model=self._model,
    messages=messages,
    format=JobExtraction.model_json_schema(),
    options={"temperature": 0.1},
)
```

---

## Part 6: Checklist

### Pre-Implementation
- [ ] Ollama installed and running
- [ ] Models pulled (qwen2.5:3b, gemma2:2b)
- [ ] Basic Ollama test successful

### Phase 1: Dependencies
- [ ] requirements.txt updated
- [ ] ollama package installed

### Phase 2: Provider Implementation
- [ ] providers/ directory created
- [ ] base.py implemented
- [ ] ollama_provider.py implemented

### Phase 3: Service Update
- [ ] LLMConfig updated
- [ ] LLMService refactored to use provider
- [ ] Backward compatibility maintained

### Phase 4: Configuration
- [ ] .env.example updated
- [ ] Config documentation updated

### Phase 5: Testing
- [ ] Mock Ollama provider created
- [ ] Existing tests updated
- [ ] New provider tests added
- [ ] Integration test passing

### Phase 6: Verification
- [ ] Syntax check passing
- [ ] Type check passing
- [ ] All tests passing
- [ ] End-to-end pipeline test

### Raspberry Pi Deployment
- [ ] Ollama installed on Pi
- [ ] Models pulled
- [ ] Performance validated
- [ ] Service configured for auto-start

---

## Rollback Plan

If issues arise, revert to Anthropic API:

1. Restore `anthropic` in requirements.txt
2. Set `LLM_PROVIDER=anthropic` in .env
3. Add `ANTHROPIC_API_KEY` to .env
4. Restart service

The provider abstraction allows switching without code changes.

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-13 | Initial transition guide |

---

*This document is part of the Scout PoC documentation. For implementation questions, consult the S1 LLM Service specification.*
