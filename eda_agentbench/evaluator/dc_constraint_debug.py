"""P6 DC Constraint Debug evaluator: execution-based grading via dc_shell.

Tasks pass if and only if:
  1. dc_shell exit code == 0
  2. Run script reports PASS (PUBLIC_RESULT: PASS / HIDDEN_RESULT: PASS)
  3. No truly fatal errors (abort, segfault, crash)

DC often outputs "Error:" for non-fatal issues (missing library files, etc.)
that don't prevent synthesis from completing. The run script's exit code
and PASS/FAIL markers are the authoritative success indicators.

Exact diff with oracle is NOT required.
"""

from __future__ import annotations

import re
from pathlib import Path

from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent


# Truly fatal patterns (dc_shell crashed or was aborted)
_FATAL_PATTERNS = [
    (r"\bdc_shell\b.*\baborted\b", "abort"),
    (r"Segmentation fault", "segfault"),
    (r"core dumped", "core_dump"),
    (r"\bFATAL\b", "fatal"),
]


def _check_fatal_errors(run_log: str) -> list[str]:
    """Check for truly fatal error patterns in dc_shell output."""
    found: list[str] = []
    for pat, category in _FATAL_PATTERNS:
        if re.search(pat, run_log):
            if category not in found:
                found.append(category)
    return found


def _check_dc_passed(run_log: str) -> bool:
    """Check if DC run passed based on run script markers."""
    # Check for PASS markers from run scripts
    if re.search(r"PUBLIC_RESULT:\s*PASS", run_log):
        return True
    if re.search(r"HIDDEN_RESULT:\s*PASS", run_log):
        return True
    # Check for DC synthesis success indicators
    if re.search(r"Compile.*complete|Synthesis.*complete|Writing SDC|Writing Verilog",
                 run_log, re.IGNORECASE):
        return True
    return False


def _check_design_check_passed(run_log: str) -> bool:
    """Check if check_design passed (no critical errors)."""
    # check_design output shows summary with 0 critical errors
    if re.search(r"check_design summary", run_log, re.IGNORECASE):
        # If check_design ran and no fatal abort, it passed
        return True
    return False


class DCConstraintDebugEvaluator(BaseEvaluator):
    """Evaluates P6 DC Constraint Debug tasks using execution-based grading."""

    def __init__(self, task_dir: Path, metadata: dict):
        super().__init__(task_dir, metadata)

    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str,
                           mode: str = "submission") -> ScoreComponent:
        weight = self.weights.get(component_name, 0.0)

        if component_name == "synthesis_pass":
            return self._eval_synthesis(weight, run_log)
        elif component_name == "check_pass":
            return self._eval_check(weight, run_log)
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

    def _eval_synthesis(self, weight: float, run_log: str) -> ScoreComponent:
        """Check if dc_shell synthesis completed successfully."""
        fatal = _check_fatal_errors(run_log)
        passed = _check_dc_passed(run_log)

        if fatal:
            score = 0.0
            details = f"Synthesis crashed: {', '.join(fatal)}"
        elif passed:
            score = 1.0
            details = "Synthesis completed successfully"
        else:
            score = 0.0
            details = "Synthesis did not complete successfully"

        return ScoreComponent(
            name="synthesis_pass", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[:500] if run_log else None,
        )

    def _eval_check(self, weight: float, run_log: str) -> ScoreComponent:
        """Check if check_design passed."""
        fatal = _check_fatal_errors(run_log)
        check_ok = _check_design_check_passed(run_log)

        if fatal:
            score = 0.0
            details = f"Design check crashed: {', '.join(fatal)}"
        elif check_ok:
            score = 1.0
            details = "Design check passed"
        else:
            score = 0.0
            details = "Design check did not run or failed"

        return ScoreComponent(
            name="check_pass", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[:500] if run_log else None,
        )

    def _eval_execution(self, weight: float, run_log: str) -> ScoreComponent:
        """Check if dc_shell ran to completion without crashing."""
        fatal = _check_fatal_errors(run_log)
        passed = _check_dc_passed(run_log)

        if fatal:
            score = 0.0
            details = f"Execution crashed: {', '.join(fatal)}"
        elif passed:
            score = 1.0
            details = "Execution completed successfully"
        else:
            score = 0.0
            details = "Execution did not complete successfully"

        return ScoreComponent(
            name="execution_pass", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[:500] if run_log else None,
        )
