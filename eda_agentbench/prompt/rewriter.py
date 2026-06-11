"""Prompt rewriter using LLM provider."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from eda_agentbench.llm.base import BaseLLMProvider
from eda_agentbench.llm.cache import LLMCache
from eda_agentbench.prompt.safety import SafetyChecker, SafetyResult


_REWRITE_SYSTEM = """\
You are an expert EDA technical writer. Your job is to rewrite task prompts for a benchmark.

Rules:
1. Preserve ALL technical accuracy — do not change circuit values, signal names, or constraints.
2. Do NOT reveal bug type labels, hidden test names, solution file names, or internal paths.
3. Do NOT add hints that weren't in the original.
4. Vary sentence structure, wording, and formatting while keeping meaning identical.
5. Keep the same file references (design.sv, circuit.sp, etc.).
6. Output ONLY the rewritten prompt, no preamble or explanation.
"""


class PromptRewriter:
    """Rewrites task prompts using an LLM provider with caching and safety checks."""

    def __init__(
        self,
        provider: BaseLLMProvider,
        cache: LLMCache | None = None,
        safety: SafetyChecker | None = None,
    ):
        self.provider = provider
        self.cache = cache
        self.safety = safety or SafetyChecker()

    def rewrite(
        self,
        original_prompt: str,
        metadata: dict | None = None,
        policy: str = "default",
        max_attempts: int = 3,
    ) -> tuple[str, SafetyResult]:
        """Rewrite a prompt with caching and safety validation.

        Args:
            original_prompt: The original prompt.md content.
            metadata: Task metadata for safety checks.
            policy: Rewrite policy identifier for cache key.
            max_attempts: Max attempts to get a safe rewrite.

        Returns:
            Tuple of (rewritten_text, safety_result).
            If all attempts fail safety, returns (original_prompt, failed_result).
        """
        # Check cache first
        if self.cache:
            cached = self.cache.get(
                prompt=original_prompt,
                system=_REWRITE_SYSTEM,
                provider_name=self.provider.name,
                model=self.provider.model,
                policy=policy,
            )
            if cached is not None:
                result = self.safety.check(cached.text, metadata)
                if result.passed:
                    return cached.text, result

        # Generate new rewrite
        for attempt in range(max_attempts):
            response = self.provider.generate(
                prompt=original_prompt,
                system=_REWRITE_SYSTEM,
                temperature=0.7 + attempt * 0.1,  # Increase variety on retry
            )

            result = self.safety.check(response.text, metadata)

            # Cache the response regardless of safety (for debugging)
            if self.cache:
                self.cache.put(
                    prompt=original_prompt,
                    system=_REWRITE_SYSTEM,
                    provider_name=self.provider.name,
                    model=self.provider.model,
                    response=response,
                    policy=f"{policy}_attempt{attempt}",
                )

            if result.passed:
                # Cache the successful response
                if self.cache:
                    self.cache.put(
                        prompt=original_prompt,
                        system=_REWRITE_SYSTEM,
                        provider_name=self.provider.name,
                        model=self.provider.model,
                        response=response,
                        policy=policy,
                    )
                return response.text, result

        # All attempts failed — return original with failure info
        return original_prompt, SafetyResult(
            passed=False,
            violations=[f"All {max_attempts} attempts failed safety check"] + result.violations,
        )
