"""Optional OpenAI-compatible LLM provider.

Requires environment variables:
  LLM_API_BASE  - API base URL (default: https://api.openai.com/v1)
  LLM_API_KEY   - API key
  LLM_MODEL     - Model name (default: gpt-4o-mini)
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.request import Request, urlopen

from eda_agentbench.llm.base import BaseLLMProvider, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """OpenAI-compatible API provider.

    Only activated when LLM_API_KEY is set in the environment.
    Falls back to mock provider if not available.
    """

    def __init__(self):
        self._api_base = os.environ.get("LLM_API_BASE", "https://api.openai.com/v1").rstrip("/")
        self._api_key = os.environ.get("LLM_API_KEY", "")
        self._model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    @staticmethod
    def is_available() -> bool:
        """Check if the provider can be activated."""
        return bool(os.environ.get("LLM_API_KEY"))

    def generate(self, prompt: str, system: str = "", **kwargs: Any) -> LLMResponse:
        """Generate text via OpenAI-compatible API."""
        if not self._api_key:
            raise RuntimeError("LLM_API_KEY not set. Use MockLLMProvider for testing.")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": self._model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2000),
        }

        req = Request(
            f"{self._api_base}/chat/completions",
            data=json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )

        with urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())

        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return LLMResponse(
            text=text,
            model=data.get("model", self._model),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            },
            metadata={"api_base": self._api_base},
        )
