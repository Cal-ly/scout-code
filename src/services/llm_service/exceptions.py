"""
LLM Service - Custom Exceptions
"""


class LLMError(Exception):
    """Base exception for LLM operations."""

    pass


class LLMProviderError(LLMError):
    """Error from the LLM provider (Anthropic)."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class LLMTimeoutError(LLMError):
    """LLM request timed out."""

    pass


class LLMResponseError(LLMError):
    """Error parsing or validating LLM response."""

    pass


class LLMInitializationError(LLMError):
    """Error during LLM service initialization."""

    pass
