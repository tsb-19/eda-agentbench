"""Optional OpenAI-compatible LLM provider.

Priority: MIMO_API_KEY > OPENAI_API_KEY > LLM_API_KEY
Loads from .env if not already in environment.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from eda_agentbench.llm.base import BaseLLMProvider, LLMResponse


def _load_dotenv() -> None:
    """Load .env file into environment if not already set."""
    for candidate in [Path(".env"), Path.home() / ".env"]:
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = value


# Provider configs: (env_key, default_api_base, default_model)
_PROVIDER_CONFIGS = [
    ("MIMO_API_KEY", "https://token-plan-sgp.xiaomimimo.com/v1", "mimo-v2.5-pro"),
    ("OPENAI_API_KEY", "https://api.openai.com/v1", "gpt-4o-mini"),
    ("LLM_API_KEY", "https://api.openai.com/v1", "gpt-4o-mini"),
]


def create_provider() -> BaseLLMProvider:
    """Create the best available LLM provider.

    Priority: MIMO > OPENAI > LLM. Falls back to MockLLMProvider.
    """
    _load_dotenv()

    for env_key, default_base, default_model in _PROVIDER_CONFIGS:
        api_key = os.environ.get(env_key, "")
        if api_key:
            api_base = os.environ.get("LLM_API_BASE", default_base).rstrip("/")
            model = os.environ.get("LLM_MODEL", default_model)
            return OpenAIProvider(api_key=api_key, api_base=api_base, model=model)

    from eda_agentbench.llm.mock import MockLLMProvider
    return MockLLMProvider()


class OpenAIProvider(BaseLLMProvider):
    """OpenAI-compatible API provider."""

    def __init__(self, api_key: str, api_base: str = "", model: str = ""):
        self._api_key = api_key
        self._api_base = (api_base or "https://api.openai.com/v1").rstrip("/")
        self._model = model or "gpt-4o-mini"

    @property
    def name(self) -> str:
        return "mimo" if "mimo" in self._api_base.lower() or "mimo" in self._model.lower() else "openai"

    @property
    def model(self) -> str:
        return self._model

    def generate(self, prompt: str, system: str = "", **kwargs: Any) -> LLMResponse:
        """Generate text via OpenAI-compatible API."""
        if not self._api_key:
            raise RuntimeError("No API key set. Use MockLLMProvider for testing.")

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

        with urlopen(req, timeout=120) as resp:
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
