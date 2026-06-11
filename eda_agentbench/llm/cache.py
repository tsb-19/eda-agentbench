"""File-based LLM request/response cache."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from eda_agentbench.llm.base import LLMResponse


def _canonical_key(
    prompt: str,
    system: str,
    provider_name: str,
    model: str,
    policy: str = "",
) -> str:
    """Compute a deterministic cache key from request parameters."""
    payload = json.dumps({
        "prompt": prompt,
        "system": system,
        "provider": provider_name,
        "model": model,
        "policy": policy,
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


class LLMCache:
    """File-based cache for LLM responses.

    Cache entries are stored as JSON files under a cache directory.
    No secrets (API keys, tokens) are stored in cache entries.
    """

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _entry_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(
        self,
        prompt: str,
        system: str,
        provider_name: str,
        model: str,
        policy: str = "",
    ) -> LLMResponse | None:
        """Look up a cached response. Returns None on miss."""
        key = _canonical_key(prompt, system, provider_name, model, policy)
        path = self._entry_path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return LLMResponse(
                text=data["text"],
                model=data["model"],
                usage=data.get("usage", {}),
                metadata=data.get("metadata", {}),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    @staticmethod
    def _sanitize_metadata(metadata: dict) -> dict:
        """Remove sensitive fields from metadata before caching."""
        sensitive_keys = {"api_key", "api_secret", "token", "password", "secret"}
        return {k: v for k, v in metadata.items() if k.lower() not in sensitive_keys}

    def put(
        self,
        prompt: str,
        system: str,
        provider_name: str,
        model: str,
        response: LLMResponse,
        policy: str = "",
    ) -> None:
        """Store a response in the cache."""
        key = _canonical_key(prompt, system, provider_name, model, policy)
        path = self._entry_path(key)
        entry = {
            "text": response.text,
            "model": response.model,
            "usage": response.usage,
            "metadata": self._sanitize_metadata(response.metadata),
            "cache_key": key,
        }
        path.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n")

    def contains(
        self,
        prompt: str,
        system: str,
        provider_name: str,
        model: str,
        policy: str = "",
    ) -> bool:
        """Check if a cache entry exists."""
        key = _canonical_key(prompt, system, provider_name, model, policy)
        return self._entry_path(key).exists()

    def clear(self) -> int:
        """Remove all cache entries. Returns count of removed files."""
        count = 0
        for f in self.cache_dir.glob("*.json"):
            f.unlink()
            count += 1
        return count

    @property
    def size(self) -> int:
        """Number of cached entries."""
        return len(list(self.cache_dir.glob("*.json")))
