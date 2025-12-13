"""
LLM Service Data Models

Pydantic models for Ollama-based local LLM integration.
"""

import hashlib
import json
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Valid message roles for Claude API."""

    USER = "user"
    ASSISTANT = "assistant"


class PromptMessage(BaseModel):
    """
    A single message in the conversation.

    Note: System prompts are handled separately,
    so role is only 'user' or 'assistant'.
    """

    role: MessageRole
    content: str

    def to_api_format(self) -> dict[str, str]:
        """Convert to LLM API format (Ollama/Anthropic compatible)."""
        return {"role": self.role.value, "content": self.content}


class LLMRequest(BaseModel):
    """
    Request to the LLM Service.

    Simplified for PoC - no model selection, no provider selection.
    """

    # Messages (required)
    messages: list[PromptMessage]
    system: str | None = None  # System prompt

    # Generation parameters
    temperature: float = Field(default=0.3, ge=0, le=1)
    max_tokens: int = Field(default=2000, ge=1, le=4096)

    # Context for cost tracking
    module: str | None = None  # e.g., "rinser", "analyzer", "creator"
    purpose: str | None = None  # e.g., "extract_job_structure"

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
            "max_tokens": self.max_tokens,
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
        """Total tokens used in this request."""
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
    request_id: str | None = None

    # Retry info
    retry_count: int = 0


class LLMHealth(BaseModel):
    """
    Health status for the LLM Service.
    """

    status: str = "healthy"  # "healthy", "degraded", "unavailable"
    ollama_connected: bool = True  # Renamed from api_connected
    model_loaded: str | None = None  # Currently loaded model
    last_request_time: datetime | None = None
    last_error: str | None = None
    total_requests: int = 0
    total_tokens: int = 0  # Track tokens instead of cost for local


class LLMConfig(BaseModel):
    """
    Configuration for LLM Service.

    All values can be overridden via environment variables.
    """

    # Provider selection
    provider: str = "ollama"  # Currently only "ollama" supported

    # Ollama settings
    ollama_host: str = "http://localhost:11434"
    model: str = "qwen2.5:3b"  # Primary model
    fallback_model: str = "gemma2:2b"  # Fallback model

    # Generation parameters
    temperature: float = 0.3
    max_tokens: int = 2000
    timeout: int = 120  # Longer timeout for local inference
    max_retries: int = 3

    # Cost tracking (for metrics, not billing - local is free)
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
