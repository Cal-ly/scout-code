"""
LLM Provider Abstractions for Scout.

Provides a pluggable provider system for LLM inference.
Currently supports Ollama for local inference.
"""

from src.services.llm_service.providers.base import LLMProvider
from src.services.llm_service.providers.ollama_provider import OllamaProvider

__all__ = ["LLMProvider", "OllamaProvider"]
