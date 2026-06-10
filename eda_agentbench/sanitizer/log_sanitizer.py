"""Log sanitizer: applies regex rules to strip sensitive info from logs."""

from __future__ import annotations

from pathlib import Path

from eda_agentbench.sanitizer.rules import DEFAULT_RULES, SanitizeRule


class LogSanitizer:
    """Applies regex substitution rules to log text."""

    def __init__(self, extra_rules: list[SanitizeRule] | None = None):
        self.rules = list(DEFAULT_RULES)
        if extra_rules:
            self.rules.extend(extra_rules)

    def sanitize(self, text: str) -> str:
        for rule in self.rules:
            text = rule.pattern.sub(rule.replacement, text)
        return text

    def sanitize_file(self, input_path: Path, output_path: Path) -> None:
        text = input_path.read_text(errors="replace")
        sanitized = self.sanitize(text)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(sanitized)
