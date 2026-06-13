"""P7 SpyGlass Lint Debug evaluator: execution-based grading via sg_shell.

Grading model:
  - The run script (bash + TCL) is the authority for pass/fail.
  - The TCL script configures SpyGlass and runs lint goals.
  - The bash script checks sg_shell exit code and emits LINT_PASS / LINT_FAIL.
  - The evaluator reads the markers from the combined log.

SpyGlass may emit warnings that are informational-only.  The run script
counts actual lint violations (Waiver/Warning/Error from lint rules) and
only emits LINT_PASS when the violation count is zero.
"""

from __future__ import annotations

import re
from pathlib import Path

from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent


class SpyGlassLintDebugEvaluator(BaseEvaluator):
    """Evaluates P7 SpyGlass Lint Debug tasks using execution-based grading."""

    def __init__(self, task_dir: Path, metadata: dict):
        super().__init__(task_dir, metadata)

    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str,
                           mode: str = "submission") -> ScoreComponent:
        weight = self.weights.get(component_name, 0.0)

        if component_name == "lint_pass":
            return self._eval_lint(weight, run_log)
        elif component_name == "explanation":
            if mode == "submission":
                return ScoreComponent(
                    name=component_name, weight=weight, raw_score=1.0,
                    weighted_score=1.0 * weight,
                    details="No explanation required in submission mode",
                )
            return ScoreComponent(
                name=component_name, weight=weight, raw_score=0.0,
                weighted_score=0.0, details="Explanation scoring not implemented",
            )
        else:
            return ScoreComponent(
                name=component_name, weight=weight, raw_score=0.0,
                weighted_score=0.0, details=f"Unknown component: {component_name}",
            )

    def _eval_lint(self, weight: float, run_log: str) -> ScoreComponent:
        """Check if SpyGlass lint passed with zero violations."""
        crashed = bool(re.search(
            r"Segmentation fault|core dumped|sg_shell.*aborted|"
            r"Cannot checkout license|License checkout failed",
            run_log, re.IGNORECASE,
        ))
        # Use ^ anchor to match actual markers, not echoed TCL code
        lint_ok = bool(re.search(r"^LINT_PASS", run_log, re.MULTILINE))
        lint_fail = bool(re.search(r"^LINT_FAIL", run_log, re.MULTILINE))

        # Extract violation count if available
        violation_match = re.search(r"Lint violations:\s*(\d+)", run_log)
        violation_count = int(violation_match.group(1)) if violation_match else None

        if crashed:
            score = 0.0
            details = "SpyGlass crashed"
        elif lint_ok:
            score = 1.0
            details = "Lint check passed (zero violations)"
        elif lint_fail:
            score = 0.0
            vc = f" ({violation_count} violations)" if violation_count is not None else ""
            details = f"Lint check failed{vc}"
        else:
            score = 0.0
            details = "Lint check did not produce result markers"

        return ScoreComponent(
            name="lint_pass", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[:500] if run_log else None,
        )
