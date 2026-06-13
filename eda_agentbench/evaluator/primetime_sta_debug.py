"""P7 PrimeTime STA Debug evaluator: execution-based grading via pt_shell.

Grading model:
  - The run script (TCL + bash) is the authority for pass/fail.
  - The TCL script performs explicit timing-constraint checks after sourcing
    the SDC (clocks exist, ports resolve, report_timing succeeds).
  - The bash script checks pt_shell exit code AND the TCL-generated markers.
  - The evaluator only reads the markers from the combined log.
"""

from __future__ import annotations

import re
from pathlib import Path

from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent


class PrimeTimeSTADebugEvaluator(BaseEvaluator):
    """Evaluates P7 PrimeTime STA Debug tasks using execution-based grading."""

    def __init__(self, task_dir: Path, metadata: dict):
        super().__init__(task_dir, metadata)

    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str,
                           mode: str = "submission") -> ScoreComponent:
        weight = self.weights.get(component_name, 0.0)

        if component_name == "timing_check":
            return self._eval_timing_check(weight, run_log)
        elif component_name == "execution_pass":
            return self._eval_execution(weight, run_log)
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

    def _eval_execution(self, weight: float, run_log: str) -> ScoreComponent:
        """Check if pt_shell ran to completion and timing checks passed."""
        crashed = bool(re.search(r"Segmentation fault|core dumped|pt_shell.*aborted", run_log))
        # Use ^ anchor to match actual markers, not echoed TCL code
        timing_ok = bool(re.search(r"^TIMING_CHECK_OK", run_log, re.MULTILINE))

        if crashed:
            score = 0.0
            details = "pt_shell crashed"
        elif timing_ok:
            score = 1.0
            details = "pt_shell execution completed"
        else:
            score = 0.0
            details = "pt_shell execution failed (timing check not OK)"

        return ScoreComponent(
            name="execution_pass", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[:500] if run_log else None,
        )

    def _eval_timing_check(self, weight: float, run_log: str) -> ScoreComponent:
        """Check if timing constraints were correctly applied.

        The TCL script emits TIMING_CHECK_OK or TIMING_CHECK_FAIL with details.
        """
        # Use ^ anchor to match actual markers, not echoed TCL code
        ok = bool(re.search(r"^TIMING_CHECK_OK", run_log, re.MULTILINE))
        fail_match = re.search(r"^TIMING_CHECK_FAIL:\s*(.*)", run_log, re.MULTILINE)
        crashed = bool(re.search(r"Segmentation fault|core dumped|pt_shell.*aborted", run_log))

        if crashed:
            score = 0.0
            details = "pt_shell crashed during timing check"
        elif ok:
            score = 1.0
            details = "All timing constraints applied correctly"
        elif fail_match:
            score = 0.0
            details = f"Timing check failure: {fail_match.group(1)}"
        else:
            score = 0.0
            details = "Timing check did not run"

        return ScoreComponent(
            name="timing_check", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[:500] if run_log else None,
        )
