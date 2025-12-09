---
updated: 2025-10-04, 19:16
---


## LLM Service - Claude Code Instructions

## Context & Objective

You're building the **LLM Service** for Scout, a critical abstraction layer that manages all Large Language Model interactions. This service handles API calls to Anthropic Claude (primary) and OpenAI (fallback), implements cost tracking, retry logic, caching, and provides a unified interface for all modules.

## Module Specifications

**Purpose**: Provide a robust, cost-efficient, provider-agnostic interface for LLM operations with built-in safety features, fallback mechanisms, and comprehensive monitoring.

**Key Responsibilities**:
1. Abstract LLM provider APIs (Anthropic, OpenAI)
2. Implement intelligent retry and fallback logic
3. Track costs and enforce budget limits
4. Cache responses to minimize API calls
5. Handle rate limiting and throttling
6. Parse and validate LLM responses
7. Provide structured output extraction

## Technical Requirements

**Dependencies**:
- FastAPI framework
- Pydantic for data validation
- Anthropic Python SDK
- OpenAI Python SDK
- Tenacity for retry logic
- Redis/diskcache for response caching
- Tiktoken for token counting

**File Structure**:
```
scout/
├── app/
│   ├── services/
│   │   ├── llm.py                  # Main LLM service
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Abstract provider interface
│   │   │   ├── anthropic.py       # Anthropic Claude implementation
│   │   │   ├── openai.py          # OpenAI implementation
│   │   │   └── mock.py            # Mock provider for testing
│   │   ├── prompt_manager.py      # Prompt template management
│   │   ├── response_parser.py     # Response parsing utilities
│   │   └── token_counter.py       # Token counting utilities
│   ├── models/
│   │   └── llm.py                 # LLM-related models
│   └── config/
│       └── llm_config.py          # LLM-specific configuration
├── prompts/
│   ├── templates/                  # Reusable prompt templates
│   │   ├── extraction.yaml
│   │   ├── generation.yaml
│   │   └── analysis.yaml
│   └── examples/                   # Few-shot examples
│       └── structured_output.yaml
├── data/
│   └── llm_cache/                  # Cached responses
└── tests/
    └── test_llm_service.py
```

## Data Models to Implement

Create these models in `app/models/llm.py`:

```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from enum import Enum
import hashlib
import json

class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    MOCK = "mock"  # For testing

class ModelType(str, Enum):
    # Anthropic models
    CLAUDE_3_5_HAIKU = "claude-3-5-haiku-20241022"
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    
    # OpenAI models (fallback)
    GPT_4_TURBO = "gpt-4-turbo-preview"
    GPT_4 = "gpt-4"
    GPT_3_5_TURBO = "gpt-3.5-turbo"

class ResponseFormat(str, Enum):
    TEXT = "text"
    JSON = "json"
    STRUCTURED = "structured"
    MARKDOWN = "markdown"

class PromptMessage(BaseModel):
    """Single message in a conversation"""
    role: str  # 'system', 'user', 'assistant'
    content: str
    name: Optional[str] = None  # For function messages
    
    def to_anthropic_format(self) -> Dict:
        """Convert to Anthropic message format"""
        return {
            "role": self.role if self.role != "system" else "user",
            "content": self.content
        }
    
    def to_openai_format(self) -> Dict:
        """Convert to OpenAI message format"""
        return {
            "role": self.role,
            "content": self.content
        }

class LLMRequest(BaseModel):
    """Unified LLM request format"""
    messages: List[PromptMessage]
    model: Optional[ModelType] = None
    provider: Optional[LLMProvider] = None
    
    # Generation parameters
    temperature: float = Field(ge=0, le=2, default=0.7)
    max_tokens: int = Field(ge=1, le=4000, default=1000)
    top_p: float = Field(ge=0, le=1, default=1.0)
    frequency_penalty: float = Field(ge=-2, le=2, default=0)
    presence_penalty: float = Field(ge=-2, le=2, default=0)
    stop_sequences: Optional[List[str]] = None
    
    # Response format
    response_format: ResponseFormat = ResponseFormat.TEXT
    json_schema: Optional[Dict[str, Any]] = None  # For structured output
    
    # Cost control
    max_cost: Optional[float] = None  # Maximum cost for this request
    cache_key: Optional[str] = None  # Custom cache key
    use_cache: bool = True
    cache_ttl: int = 3600  # seconds
    
    # Metadata
    module: Optional[str] = None  # Which module is making the request
    purpose: Optional[str] = None  # Purpose of the request
    job_id: Optional[str] = None  # Associated job ID
    
    def generate_cache_key(self) -> str:
        """Generate cache key from request"""
        if self.cache_key:
            return self.cache_key
        
        key_data = {
            'messages': [m.dict() for m in self.messages],
            'model': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'response_format': self.response_format
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()

class TokenUsage(BaseModel):
    """Token usage tracking"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    
    # Cost calculation
    prompt_cost: float
    completion_cost: float
    total_cost: float
    
    # Model info
    model: ModelType
    provider: LLMProvider

class LLMResponse(BaseModel):
    """Unified LLM response format"""
    content: str  # Raw response content
    parsed_content: Optional[Any] = None  # Parsed JSON/structured data
    
    # Metadata
    model: ModelType
    provider: LLMProvider
    response_format: ResponseFormat
    
    # Usage and cost
    usage: TokenUsage
    cached: bool = False
    
    # Timing
    request_time: datetime
    response_time: datetime
    latency: float  # seconds
    
    # Request tracking
    request_id: str
    cache_key: Optional[str] = None
    
    # Error handling
    error: Optional[str] = None
    retry_count: int = 0
    fallback_used: bool = False

class ModelConfig(BaseModel):
    """Configuration for a specific model"""
    model: ModelType
    provider: LLMProvider
    
    # Pricing (per 1K tokens)
    input_cost: float
    output_cost: float
    
    # Limits
    max_tokens: int
    max_context: int  # Context window size
    
    # Rate limits
    requests_per_minute: int
    tokens_per_minute: int
    
    # Features
    supports_json: bool = True
    supports_functions: bool = False
    supports_vision: bool = False
    
    # Performance
    average_latency: float  # seconds
    reliability_score: float = Field(ge=0, le=1)  # 0-1

class ProviderStatus(BaseModel):
    """Current status of an LLM provider"""
    provider: LLMProvider
    available: bool
    
    # Rate limit status
    requests_remaining: int
    tokens_remaining: int
    reset_time: Optional[datetime] = None
    
    # Error tracking
    consecutive_errors: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    
    # Performance metrics
    average_latency: float  # Moving average
    success_rate: float = Field(ge=0, le=1)
    
    # Cost tracking
    total_cost_today: float = 0
    total_requests_today: int = 0

class CostTrackingEntry(BaseModel):
    """Individual cost tracking entry"""
    timestamp: datetime
    provider: LLMProvider
    model: ModelType
    
    # Request details
    module: Optional[str] = None
    purpose: Optional[str] = None
    job_id: Optional[str] = None
    
    # Usage
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    
    # Cost
    cost: float
    cumulative_daily_cost: float
    cumulative_monthly_cost: float
    
    # Limits
    daily_limit: float
    monthly_limit: float
    approaching_limit: bool = False

class PromptTemplate(BaseModel):
    """Reusable prompt template"""
    id: str
    name: str
    description: str
    
    # Template content
    system_prompt: Optional[str] = None
    user_prompt: str
    
    # Variables
    required_variables: List[str]
    optional_variables: List[str] = []
    
    # Examples
    example_values: Optional[Dict[str, Any]] = None
    example_output: Optional[str] = None
    
    # Configuration
    recommended_model: Optional[ModelType] = None
    recommended_temperature: float = 0.7
    recommended_max_tokens: int = 1000
    
    # Metadata
    category: str  # 'extraction', 'generation', 'analysis'
    version: str = "1.0"
    last_updated: datetime = Field(default_factory=datetime.now)

class RetryConfig(BaseModel):
    """Retry configuration for failed requests"""
    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    exponential_base: float = 2.0
    max_delay: float = 60.0
    
    # Retry conditions
    retry_on_timeout: bool = True
    retry_on_rate_limit: bool = True
    retry_on_server_error: bool = True
    
    # Fallback
    fallback_to_secondary: bool = True
    fallback_model: Optional[ModelType] = None
```

## LLM Service Implementation

Create the main service in `app/services/llm.py`:

```python
import asyncio
import json
import time
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_retry
)

from app.models.llm import (
    LLMRequest, LLMResponse, TokenUsage, ProviderStatus,
    LLMProvider, ModelType, ResponseFormat, RetryConfig,
    CostTrackingEntry, ModelConfig
)
from app.services.providers.anthropic import AnthropicProvider
from app.services.providers.openai import OpenAIProvider
from app.services.providers.mock import MockProvider
from app.services.prompt_manager import PromptManager
from app.services.response_parser import ResponseParser
from app.services.token_counter import TokenCounter
from app.services.cache import CacheService
from app.config.settings import settings

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(
        self,
        primary_provider: LLMProvider = LLMProvider.ANTHROPIC,
        fallback_provider: LLMProvider = LLMProvider.OPENAI,
        cache_service: Optional[CacheService] = None
    ):
        # Initialize providers
        self.providers = {
            LLMProvider.ANTHROPIC: AnthropicProvider(),
            LLMProvider.OPENAI: OpenAIProvider(),
            LLMProvider.MOCK: MockProvider()
        }
        
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider
        
        # Initialize services
        self.cache = cache_service or CacheService()
        self.prompt_manager = PromptManager()
        self.response_parser = ResponseParser()
        self.token_counter = TokenCounter()
        
        # Provider status tracking
        self.provider_status = {
            provider: ProviderStatus(provider=provider, available=True)
            for provider in self.providers
        }
        
        # Cost tracking
        self.daily_cost = 0.0
        self.monthly_cost = 0.0
        self.cost_history: List[CostTrackingEntry] = []
        
        # Model configurations
        self.model_configs = self._load_model_configs()
        
        # Rate limiting
        self.request_semaphores = {
            provider: asyncio.Semaphore(10)  # Max concurrent requests
            for provider in self.providers
        }
        
        # Retry configuration
        self.retry_config = RetryConfig()
    
    def _load_model_configs(self) -> Dict[ModelType, ModelConfig]:
        """Load model configurations with pricing"""
        return {
            ModelType.CLAUDE_3_5_HAIKU: ModelConfig(
                model=ModelType.CLAUDE_3_5_HAIKU,
                provider=LLMProvider.ANTHROPIC,
                input_cost=0.001,  # $0.001 per 1K tokens
                output_cost=0.005,  # $0.005 per 1K tokens
                max_tokens=4096,
                max_context=200000,
                requests_per_minute=50,
                tokens_per_minute=100000,
                average_latency=1.5,
                reliability_score=0.95
            ),
            ModelType.GPT_4_TURBO: ModelConfig(
                model=ModelType.GPT_4_TURBO,
                provider=LLMProvider.OPENAI,
                input_cost=0.01,
                output_cost=0.03,
                max_tokens=4096,
                max_context=128000,
                requests_per_minute=60,
                tokens_per_minute=150000,
                average_latency=2.0,
                reliability_score=0.93
            ),
            # Add more model configs as needed
        }
    
    async def generate(
        self,
        prompt: Union[str, List[PromptMessage]],
        model: Optional[ModelType] = None,
        **kwargs
    ) -> LLMResponse:
        """Main generation method with automatic retries and fallbacks"""
        
        # Prepare request
        if isinstance(prompt, str):
            messages = [PromptMessage(role="user", content=prompt)]
        else:
            messages = prompt
        
        request = LLMRequest(
            messages=messages,
            model=model or settings.default_llm_model,
            provider=self.primary_provider,
            **kwargs
        )
        
        # Check cache
        if request.use_cache:
            cache_key = request.generate_cache_key()
            cached_response = await self.cache.get(f"llm:{cache_key}")
            if cached_response:
                logger.info(f"Cache hit for request: {cache_key}")
                response = LLMResponse(**cached_response)
                response.cached = True
                return response
        
        # Check budget limits
        if not await self._check_budget(request):
            raise Exception("Budget limit exceeded")
        
        # Try primary provider
        try:
            response = await self._generate_with_retry(request)
            
            # Cache successful response
            if request.use_cache and not response.error:
                await self.cache.set(
                    f"llm:{cache_key}",
                    response.dict(),
                    ttl=request.cache_ttl
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Primary provider failed: {e}")
            
            # Try fallback provider
            if self.fallback_provider and self.retry_config.fallback_to_secondary:
                logger.info(f"Attempting fallback to {self.fallback_provider}")
                request.provider = self.fallback_provider
                
                # Adjust model for fallback provider
                request.model = self._get_equivalent_model(
                    request.model, 
                    self.fallback_provider
                )
                
                response = await self._generate_with_retry(request)
                response.fallback_used = True
                return response
            
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError))
    )
    async def _generate_with_retry(self, request: LLMRequest) -> LLMResponse:
        """Generate with retry logic"""
        provider = self.providers[request.provider]
        
        # Apply rate limiting
        async with self.request_semaphores[request.provider]:
            # Check provider status
            if not self.provider_status[request.provider].available:
                raise Exception(f"Provider {request.provider} is unavailable")
            
            start_time = time.time()
            
            try:
                # Make API call
                raw_response = await provider.generate(request)
                
                # Parse response
                parsed_content = None
                if request.response_format == ResponseFormat.JSON:
                    parsed_content = self.response_parser.parse_json(
                        raw_response['content']
                    )
                elif request.response_format == ResponseFormat.STRUCTURED:
                    parsed_content = self.response_parser.parse_structured(
                        raw_response['content'],
                        request.json_schema
                    )
                
                # Calculate usage and cost
                usage = self._calculate_usage(
                    request,
                    raw_response,
                    request.model
                )
                
                # Track cost
                await self._track_cost(request, usage)
                
                # Create response
                response = LLMResponse(
                    content=raw_response['content'],
                    parsed_content=parsed_content,
                    model=request.model,
                    provider=request.provider,
                    response_format=request.response_format,
                    usage=usage,
                    request_time=datetime.now(),
                    response_time=datetime.now(),
                    latency=time.time() - start_time,
                    request_id=raw_response.get('id', ''),
                    cache_key=request.generate_cache_key()
                )
                
                # Update provider status
                self._update_provider_status(request.provider, success=True, latency=response.latency)
                
                return response
                
            except Exception as e:
                # Update provider status
                self._update_provider_status(request.provider, success=False, error=str(e))
                raise
    
    async def extract_json(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Extract structured JSON from LLM response"""
        messages = []
        
        if system_message:
            messages.append(PromptMessage(role="system", content=system_message))
        
        # Add JSON instruction to prompt
        json_prompt = f"{prompt}\n\nRespond with valid JSON only, no other text."
        messages.append(PromptMessage(role="user", content=json_prompt))
        
        response = await self.generate(
            messages,
            response_format=ResponseFormat.JSON,
            json_schema=schema,
            temperature=0.1,  # Low temperature for consistency
            **kwargs
        )
        
        if response.parsed_content:
            return response.parsed_content
        
        # Fallback to manual parsing
        return self.response_parser.parse_json(response.content)
    
    async def generate_with_examples(
        self,
        prompt: str,
        examples: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """Generate with few-shot examples"""
        messages = []
        
        # Add examples as conversation history
        for example in examples:
            messages.append(PromptMessage(role="user", content=example['input']))
            messages.append(PromptMessage(role="assistant", content=example['output']))
        
        # Add actual prompt
        messages.append(PromptMessage(role="user", content=prompt))
        
        return await self.generate(messages, **kwargs)
    
    async def stream_generate(
        self,
        prompt: str,
        callback: callable,
        **kwargs
    ):
        """Stream generation with callbacks"""
        # Implementation depends on provider support
        # This is a placeholder for streaming functionality
        pass
    
    def _calculate_usage(
        self,
        request: LLMRequest,
        response: Dict,
        model: ModelType
    ) -> TokenUsage:
        """Calculate token usage and cost"""
        # Get token counts
        if 'usage' in response:
            prompt_tokens = response['usage'].get('prompt_tokens', 0)
            completion_tokens = response['usage'].get('completion_tokens', 0)
        else:
            # Estimate tokens
            prompt_tokens = self.token_counter.count_tokens(
                ' '.join([m.content for m in request.messages]),
                model
            )
            completion_tokens = self.token_counter.count_tokens(
                response.get('content', ''),
                model
            )
        
        total_tokens = prompt_tokens + completion_tokens
        
        # Get model config
        config = self.model_configs.get(model)
        if not config:
            # Default pricing
            prompt_cost = prompt_tokens * 0.001 / 1000
            completion_cost = completion_tokens * 0.005 / 1000
        else:
            prompt_cost = (prompt_tokens / 1000) * config.input_cost
            completion_cost = (completion_tokens / 1000) * config.output_cost
        
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            prompt_cost=prompt_cost,
            completion_cost=completion_cost,
            total_cost=prompt_cost + completion_cost,
            model=model,
            provider=request.provider
        )
    
    async def _check_budget(self, request: LLMRequest) -> bool:
        """Check if request is within budget limits"""
        # Estimate cost for this request
        estimated_tokens = request.max_tokens + 500  # Rough estimate
        config = self.model_configs.get(request.model)
        
        if config:
            estimated_cost = (estimated_tokens / 1000) * config.output_cost
        else:
            estimated_cost = (estimated_tokens / 1000) * 0.005  # Default
        
        # Check daily limit
        if settings.max_daily_spend > 0:
            if self.daily_cost + estimated_cost > settings.max_daily_spend:
                logger.warning(f"Daily budget limit approaching: ${self.daily_cost:f}")
                return False
        
        # Check monthly limit
        if settings.max_monthly_spend > 0:
            if self.monthly_cost + estimated_cost > settings.max_monthly_spend:
                logger.warning(f"Monthly budget limit approaching: ${self.monthly_cost:f}")
                return False
        
        # Check per-request limit
        if request.max_cost and estimated_cost > request.max_cost:
            return False
        
        return True
    
    async def _track_cost(self, request: LLMRequest, usage: TokenUsage):
        """Track cost for budget management"""
        self.daily_cost += usage.total_cost
        self.monthly_cost += usage.total_cost
        
        # Create tracking entry
        entry = CostTrackingEntry(
            timestamp=datetime.now(),
            provider=request.provider,
            model=request.model,
            module=request.module,
            purpose=request.purpose,
            job_id=request.job_id,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            cost=usage.total_cost,
            cumulative_daily_cost=self.daily_cost,
            cumulative_monthly_cost=self.monthly_cost,
            daily_limit=settings.max_daily_spend,
            monthly_limit=settings.max_monthly_spend,
            approaching_limit=(
                self.daily_cost > settings.max_daily_spend * 0.8 or
                self.monthly_cost > settings.max_monthly_spend * 0.8
            )
        )
        
        self.cost_history.append(entry)
        
        # Log if approaching limits
        if entry.approaching_limit:
            logger.warning(
                f"Approaching cost limit - Daily: ${self.daily_cost:f}/"
                f"${settings.max_daily_spend}, Monthly: ${self.monthly_cost:f}/"
                f"${settings.max_monthly_spend}"
            )
    
    def _update_provider_status(
        self,
        provider: LLMProvider,
        success: bool,
        latency: Optional[float] = None,
        error: Optional[str] = None
    ):
        """Update provider status after request"""
        status = self.provider_status[provider]
        
        if success:
            status.consecutive_errors = 0
            status.total_requests_today += 1
            
            # Update latency (moving average)
            if latency:
                alpha = 0.1  # Smoothing factor
                status.average_latency = (
                    alpha * latency + (1 - alpha) * status.average_latency
                )
            
            # Update success rate
            status.success_rate = min(status.success_rate * 1.01, 1.0)
            
        else:
            status.consecutive_errors += 1
            status.last_error = error
            status.last_error_time = datetime.now()
            
            # Update success rate
            status.success_rate = max(status.success_rate * 0.95, 0)
            
            # Mark unavailable if too many errors
            if status.consecutive_errors >= 5:
                status.available = False
                logger.error(f"Provider {provider} marked unavailable after {status.consecutive_errors} errors")
    
    def _get_equivalent_model(
        self,
        model: ModelType,
        provider: LLMProvider
    ) -> ModelType:
        """Get equivalent model for different provider"""
        equivalents = {
            LLMProvider.ANTHROPIC: {
                ModelType.GPT_4_TURBO: ModelType.CLAUDE_3_5_SONNET,
                ModelType.GPT_4: ModelType.CLAUDE_3_5_HAIKU,
                ModelType.GPT_3_5_TURBO: ModelType.CLAUDE_3_5_HAIKU
            },
            LLMProvider.OPENAI: {
                ModelType.CLAUDE_3_5_SONNET: ModelType.GPT_4_TURBO,
                ModelType.CLAUDE_3_5_HAIKU: ModelType.GPT_4,
                ModelType.CLAUDE_3_OPUS: ModelType.GPT_4_TURBO
            }
        }
        
        provider_map = equivalents.get(provider, {})
        return provider_map.get(model, model)
    
    async def reset_daily_costs(self):
        """Reset daily cost tracking (call from scheduler)"""
        self.daily_cost = 0.0
        for status in self.provider_status.values():
            status.total_cost_today = 0
            status.total_requests_today = 0
        logger.info("Daily costs reset")
    
    async def reset_monthly_costs(self):
        """Reset monthly cost tracking"""
        self.monthly_cost = 0.0
        self.cost_history = []
        logger.info("Monthly costs reset")
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get current cost summary"""
        return {
            'daily': {
                'spent': self.daily_cost,
                'limit': settings.max_daily_spend,
                'percentage': (self.daily_cost / settings.max_daily_spend * 100) 
                            if settings.max_daily_spend > 0 else 0
            },
            'monthly': {
                'spent': self.monthly_cost,
                'limit': settings.max_monthly_spend,
                'percentage': (self.monthly_cost / settings.max_monthly_spend * 100)
                             if settings.max_monthly_spend > 0 else 0
            },
            'by_provider': {
                provider.value: sum(
                    e.cost for e in self.cost_history 
                    if e.provider == provider
                )
                for provider in LLMProvider
            },
            'by_module': self._aggregate_costs_by_module()
        }
    
    def _aggregate_costs_by_module(self) -> Dict[str, float]:
        """Aggregate costs by module"""
        costs = {}
        for entry in self.cost_history:
            if entry.module:
                costs[entry.module] = costs.get(entry.module, 0) + entry.cost
        return costs
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of LLM service"""
        health = {
            'status': 'healthy',
            'providers': {},
            'cost_status': self.get_cost_summary()
        }
        
        for provider, status in self.provider_status.items():
            health['providers'][provider.value] = {
                'available': status.available,
                'success_rate': status.success_rate,
                'average_latency': status.average_latency,
                'consecutive_errors': status.consecutive_errors
            }
            
            if not status.available:
                health['status'] = 'degraded'
        
        return health
```

## Provider Implementations

Create `app/services/providers/anthropic.py`:

```python
import anthropic
from typing import Dict, Any
import os

from app.models.llm import LLMRequest, ModelType
from app.services.providers.base import BaseLLMProvider

class AnthropicProvider(BaseLLMProvider):
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        # Model mapping
        self.model_map = {
            ModelType.CLAUDE_3_5_HAIKU: "claude-3-5-haiku-20241022",
            ModelType.CLAUDE_3_5_SONNET: "claude-3-5-sonnet-20241022",
            ModelType.CLAUDE_3_OPUS: "claude-3-opus-20240229"
        }
    
    async def generate(self, request: LLMRequest) -> Dict[str, Any]:
        """Generate response using Anthropic API"""
        # Convert messages to Anthropic format
        messages = [msg.to_anthropic_format() for msg in request.messages]
        
        # Extract system message if present
        system_message = None
        if messages and messages[0]['role'] == 'user':
            # Check if first message was originally system
            if request.messages[0].role == 'system':
                system_message = messages[0]['content']
                messages = messages[1:]
        
        # Make API call
        response = await self.client.messages.create(
            model=self.model_map.get(request.model, request.model.value),
            messages=messages,
            system=system_message,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stop_sequences=request.stop_sequences
        )
        
        return {
            'content': response.content[0].text,
            'id': response.id,
            'usage': {
                'prompt_tokens': response.usage.input_tokens,
                'completion_tokens': response.usage.output_tokens,
                'total_tokens': response.usage.input_tokens + response.usage.output_tokens
            },
            'model': response.model,
            'stop_reason': response.stop_reason
        }
```

Create `app/services/providers/openai.py`:

```python
import openai
from typing import Dict, Any
import os

from app.models.llm import LLMRequest, ModelType, ResponseFormat
from app.services.providers.base import BaseLLMProvider

class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        # Model mapping
        self.model_map = {
            ModelType.GPT_4_TURBO: "gpt-4-turbo-preview",
            ModelType.GPT_4: "gpt-4",
            ModelType.GPT_3_5_TURBO: "gpt-3.5-turbo"
        }
    
    async def generate(self, request: LLMRequest) -> Dict[str, Any]:
        """Generate response using OpenAI API"""
        # Convert messages to OpenAI format
        messages = [msg.to_openai_format() for msg in request.messages]
        
        # Prepare request parameters
        params = {
            'model': self.model_map.get(request.model, "gpt-4"),
            'messages': messages,
            'max_tokens': request.max_tokens,
            'temperature': request.temperature,
            'top_p': request.top_p,
            'frequency_penalty': request.frequency_penalty,
            'presence_penalty': request.presence_penalty,
            'stop': request.stop_sequences
        }
        
        # Add response format if JSON
        if request.response_format == ResponseFormat.JSON:
            params['response_format'] = {"type": "json_object"}
        
        # Make API call
        response = await openai.ChatCompletion.acreate(**params)
        
        return {
            'content': response.choices[0].message.content,
            'id': response.id,
            'usage': {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            },
            'model': response.model,
            'finish_reason': response.choices[0].finish_reason
        }
```

## Test Implementation Requirements

Create `tests/test_llm_service.py`:

1. **Basic Generation Tests**:
   - Test simple text generation
   - Test JSON extraction
   - Test structured output
   - Test with system messages

2. **Provider Tests**:
   - Test Anthropic provider
   - Test OpenAI provider fallback
   - Test provider switching
   - Test mock provider for testing

3. **Cost Tracking Tests**:
   - Test cost calculation accuracy
   - Test budget limit enforcement
   - Test daily/monthly reset
   - Test cost aggregation

4. **Retry Logic Tests**:
   - Test retry on timeout
   - Test retry on rate limit
   - Test fallback to secondary provider
   - Test max retry limit

5. **Caching Tests**:
   - Test cache hit for identical requests
   - Test cache miss for new requests
   - Test cache TTL expiration
   - Test cache key generation

## Success Criteria

1. **Provider Abstraction**: Seamless switching between providers
2. **Cost Control**: Never exceed budget limits
3. **Reliability**: >95% success rate with retries
4. **Performance**: <2s average latency for standard requests
5. **Caching**: >50% cache hit rate for similar requests
6. **Error Recovery**: Graceful degradation with fallbacks
7. **Cost Tracking**: Accurate to within $0.01 per day

## Edge Cases to Handle

1. **API key rotation**: Support for key refresh without restart
2. **Provider outages**: Automatic fallback and recovery
3. **Rate limit handling**: Intelligent backoff and queuing
4. **Malformed responses**: Robust parsing and validation
5. **Token limit exceeded**: Automatic truncation or splitting
6. **Network issues**: Timeout and retry handling
7. **Cost spikes**: Emergency shutdown if costs spike
8. **Concurrent requests**: Thread-safe request handling
9. **Cache corruption**: Graceful cache miss on corruption
10. **Model deprecation**: Automatic model version updates

---

**43. Should we implement prompt versioning to track which prompts perform best?**
*Recommendation: Yes - Version control prompts and correlate with output quality metrics to continuously improve prompt engineering.*

This completes the LLM Service specifications. The service provides a robust, cost-controlled interface for all LLM operations with comprehensive fallback mechanisms and monitoring.