"""Prompt safety checker — rejects prompts that leak task internals."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SafetyResult:
    """Result of a safety check."""
    passed: bool
    violations: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        if self.passed:
            return "SAFETY PASS"
        return f"SAFETY FAIL: {'; '.join(self.violations)}"


class SafetyChecker:
    """Checks that rewritten prompts don't leak task internals.

    Rejects prompts containing:
    - Bug type labels (from metadata.generator.bug_type)
    - Hidden test file names
    - Solution/oracle file paths
    - Exact patch hints from the original prompt
    - Local paths (/EDA/, /home/, /data1/, /tmp/)
    - License variables
    - Raw EDA tool output / banners
    - Commercial tool version strings
    """

    # Known bug type labels that must not appear
    BUG_TYPE_LABELS = {
        "sensitivity_list", "blocking_nonblocking", "reset_polarity",
        "width_truncation", "comparison_boundary", "wrong_mux_select",
        "priority_order", "fsm_transition_error", "counter_off_by_one",
        "enable_condition",
    }

    # Patterns for local paths
    PATH_PATTERNS = [
        re.compile(r"/EDA/"),
        re.compile(r"/home/\w"),
        re.compile(r"/data1/"),
        re.compile(r"/tmp/"),
        re.compile(r"/usr/local/"),
        re.compile(r"/share_x86/"),
    ]

    # License-related patterns
    LICENSE_PATTERNS = [
        re.compile(r"SNPSLMD_LICENSE_FILE", re.IGNORECASE),
        re.compile(r"CDS_LIC_FILE", re.IGNORECASE),
        re.compile(r"LM_LICENSE_FILE", re.IGNORECASE),
        re.compile(r"synopsys\.com", re.IGNORECASE),
        re.compile(r"cadence\.com", re.IGNORECASE),
    ]

    # Tool banner patterns
    TOOL_BANNER_PATTERNS = [
        re.compile(r"VCS.*Release", re.IGNORECASE),
        re.compile(r"HSPICE.*\d{4}", re.IGNORECASE),
        re.compile(r"Spectre.*\d+\.\d+", re.IGNORECASE),
        re.compile(r"Synopsys.*Inc", re.IGNORECASE),
        re.compile(r"Cadence.*Design", re.IGNORECASE),
    ]

    # Hidden test file names
    HIDDEN_FILE_PATTERNS = [
        re.compile(r"tb_hidden"),
        re.compile(r"run_hidden"),
        re.compile(r"hidden_run"),
    ]

    # Solution/oracle patterns
    SOLUTION_PATTERNS = [
        re.compile(r"solution/design"),
        re.compile(r"solution/circuit"),
        re.compile(r"oracle/"),
    ]

    def check(self, text: str, metadata: dict | None = None) -> SafetyResult:
        """Check a prompt for safety violations.

        Args:
            text: The rewritten prompt text.
            metadata: Optional task metadata for additional checks.

        Returns:
            SafetyResult with pass/fail and list of violations.
        """
        violations = []
        text_lower = text.lower()

        # Check for bug type labels
        for label in self.BUG_TYPE_LABELS:
            if label in text_lower:
                violations.append(f"Contains bug_type label: {label}")

        # Check for human-readable bug type names (with spaces)
        for label in self.BUG_TYPE_LABELS:
            readable = label.replace("_", " ")
            if readable in text_lower:
                violations.append(f"Contains readable bug_type: {readable}")

        # Check for local paths
        for pattern in self.PATH_PATTERNS:
            if pattern.search(text):
                violations.append(f"Contains local path: {pattern.pattern}")

        # Check for license variables
        for pattern in self.LICENSE_PATTERNS:
            if pattern.search(text):
                violations.append(f"Contains license reference: {pattern.pattern}")

        # Check for tool banners
        for pattern in self.TOOL_BANNER_PATTERNS:
            if pattern.search(text):
                violations.append(f"Contains tool banner: {pattern.pattern}")

        # Check for hidden file references
        for pattern in self.HIDDEN_FILE_PATTERNS:
            if pattern.search(text):
                violations.append(f"Contains hidden file reference: {pattern.pattern}")

        # Check for solution/oracle references
        for pattern in self.SOLUTION_PATTERNS:
            if pattern.search(text):
                violations.append(f"Contains solution reference: {pattern.pattern}")

        # Metadata-based checks
        if metadata:
            gen = metadata.get("generator", {})
            bug_type = gen.get("bug_type", "")
            if bug_type and bug_type.lower() in text_lower:
                violations.append(f"Contains exact bug_type from metadata: {bug_type}")

            # Check for hidden files from metadata
            hidden_files = metadata.get("files", {}).get("hidden", [])
            for hf in hidden_files:
                if hf.lower() in text_lower:
                    violations.append(f"References hidden file from metadata: {hf}")

        return SafetyResult(passed=len(violations) == 0, violations=violations)
