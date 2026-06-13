"""P6 DC Constraint Debug evaluator: execution-based grading via dc_shell.

Grading model:
  - The run script (TCL + bash) is the authority for pass/fail.
  - The TCL script performs explicit constraint-validation checks after
    sourcing the SDC (e.g. clocks exist, ports resolve, no unconstrained paths).
  - The bash script checks DC exit code AND the TCL-generated markers.
  - The evaluator only reads the markers from the combined log.

This avoids the problem where DC outputs "Error:" lines for non-fatal issues
(library warnings) while still detecting real constraint failures.
"""

from __future__ import annotations

import re
from pathlib import Path

from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent


class DCConstraintDebugEvaluator(BaseEvaluator):
    """Evaluates P6 DC Constraint Debug tasks using execution-based grading."""

    def __init__(self, task_dir: Path, metadata: dict):
        super().__init__(task_dir, metadata)

    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str,
                           mode: str = "submission") -> ScoreComponent:
        weight = self.weights.get(component_name, 0.0)

        if component_name == "constraint_pass":
            return self._eval_constraint(weight, run_log)
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
        """Check if DC ran to completion and constraints passed."""
        crashed = bool(re.search(r"Segmentation fault|core dumped|dc_shell.*aborted", run_log))
        # Use ^ anchor to match actual markers, not echoed TCL code
        constraints_ok = bool(re.search(r"^CONSTRAINTS_OK", run_log, re.MULTILINE))

        if crashed:
            score = 0.0
            details = "DC crashed"
        elif constraints_ok:
            score = 1.0
            details = "DC execution completed"
        else:
            score = 0.0
            details = "DC execution failed (constraints not OK)"

        return ScoreComponent(
            name="execution_pass", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[:500] if run_log else None,
        )

    def _eval_constraint(self, weight: float, run_log: str) -> ScoreComponent:
        """Check if constraints were correctly applied.

        The TCL script emits CONSTRAINTS_OK or CONSTRAINTS_FAIL with details.
        """
        # Use ^ anchor to match actual markers, not echoed TCL code
        ok = bool(re.search(r"^CONSTRAINTS_OK", run_log, re.MULTILINE))
        fail_match = re.search(r"^CONSTRAINTS_FAIL:\s*(.*)", run_log, re.MULTILINE)
        crashed = bool(re.search(r"Segmentation fault|core dumped|dc_shell.*aborted", run_log))

        if crashed:
            score = 0.0
            details = "DC crashed during constraint check"
        elif ok:
            score = 1.0
            details = "All constraints applied correctly"
        elif fail_match:
            score = 0.0
            details = f"Constraint failure: {fail_match.group(1)}"
        else:
            score = 0.0
            details = "Constraint check did not run"

        return ScoreComponent(
            name="constraint_pass", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[:500] if run_log else None,
        )
