"""Deterministic mock LLM provider for testing."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from eda_agentbench.llm.base import BaseLLMProvider, LLMResponse

# EDA context phrases to enrich prompts
_EDA_CONTEXT = [
    "In a typical RTL design flow,",
    "When working with synthesis tools,",
    "During functional verification,",
    "In the context of timing analysis,",
    "For a gate-level netlist,",
    "When debugging simulation failures,",
    "In a standard cell library,",
    "During lint checking,",
]

# Transition phrases for variety
_TRANSITIONS = [
    "Note that",
    "Consider that",
    "Keep in mind that",
    "Observe that",
    "Recall that",
    "Bear in mind that",
]

# Closing phrases
_CLOSINGS = [
    "Ensure your fix is minimal and correct.",
    "Make only the necessary changes.",
    "Verify your solution against all test cases.",
    "Focus on the root cause of the issue.",
    "A correct fix should pass both public and hidden tests.",
]


class MockLLMProvider(BaseLLMProvider):
    """Deterministic mock provider that generates varied prompts from a seed.

    Uses content hashing to produce consistent rewrites for the same input.
    No external API calls are made.
    """

    def __init__(self, seed: int = 42):
        self._seed = seed

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model(self) -> str:
        return "mock-v1"

    # Bug type labels to strip from prompts
    _BUG_LABELS = [
        "sensitivity_list", "blocking_nonblocking", "reset_polarity",
        "width_truncation", "comparison_boundary", "wrong_mux_select",
        "priority_order", "fsm_transition_error", "counter_off_by_one",
        "enable_condition",
    ]

    def generate(self, prompt: str, system: str = "", **kwargs: Any) -> LLMResponse:
        """Generate a deterministic rewrite of the input prompt."""
        # Hash input for deterministic variation selection
        h = hashlib.sha256(f"{self._seed}:{prompt}".encode()).hexdigest()
        h_int = int(h[:8], 16)

        lines = prompt.strip().split("\n")
        rewritten_lines = []

        for line in lines:
            # Vary section headers, stripping bug type labels
            if line.startswith("# "):
                title = line
                for label in self._BUG_LABELS:
                    # Strip "Bug Type Name" from title
                    readable = label.replace("_", " ").title()
                    title = title.replace(f": {readable}", "")
                    title = title.replace(f" {readable}", "")
                    title = title.replace(readable, "Design Issue")
                idx = h_int % len(_EDA_CONTEXT)
                rewritten_lines.append(title)
                rewritten_lines.append("")
                rewritten_lines.append(_EDA_CONTEXT[idx])
                continue

            # Vary hint lines, stripping bug type references
            if line.startswith("## Hint"):
                idx = (h_int >> 4) % len(_TRANSITIONS)
                rewritten_lines.append(line)
                continue
            if line.startswith("Pay attention to") or line.startswith("Check the") or line.startswith("Think about") or line.startswith("Watch out for"):
                # Generic hint that may contain bug type reference
                for label in self._BUG_LABELS:
                    readable = label.replace("_", " ")
                    if readable in line.lower():
                        line = "Examine the design carefully for logical errors."
                        break

            # Vary constraint phrasing
            if line.startswith("- Only modify"):
                rewritten_lines.append("- You should only need to modify the design file")
                continue
            if line.startswith("- Do not modify"):
                rewritten_lines.append("- Leave all other files unchanged")
                continue

            # Add variety to file descriptions
            if "buggy design" in line.lower():
                line = line.replace("buggy design", "design under test")
            if "you may edit" in line.lower():
                line = line.replace("you may edit", "you are allowed to edit")

            rewritten_lines.append(line)

        # Add a contextual closing
        closing_idx = (h_int >> 8) % len(_CLOSINGS)
        if not any(_CLOSINGS[closing_idx] in l for l in rewritten_lines):
            rewritten_lines.append("")
            rewritten_lines.append(_CLOSINGS[closing_idx])

        result = "\n".join(rewritten_lines)

        return LLMResponse(
            text=result,
            model=self.model,
            usage={"prompt_tokens": len(prompt.split()), "completion_tokens": len(result.split())},
            metadata={"seed": self._seed, "hash": h[:16]},
        )
