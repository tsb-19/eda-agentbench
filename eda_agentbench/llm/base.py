"""Base LLM provider abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    text: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging/caching."""
        ...

    @property
    @abstractmethod
    def model(self) -> str:
        """Model identifier."""
        ...

    @abstractmethod
    def generate(self, prompt: str, system: str = "", **kwargs: Any) -> LLMResponse:
        """Generate text from a prompt.

        Args:
            prompt: User prompt text.
            system: Optional system prompt.
            **kwargs: Provider-specific parameters (temperature, max_tokens, etc.)

        Returns:
            LLMResponse with generated text.
        """
        ...
