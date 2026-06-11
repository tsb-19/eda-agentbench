"""P5 SPICE Deck Debug evaluator: execution-based grading via HSPICE.

Unlike P4 (metric-based), P5 tasks pass if and only if:
  1. HSPICE exit code == 0
  2. No normalized fatal errors in output
  3. success_criteria.execution_based == true (from grader_contract.json)

Exact diff with oracle is NOT required.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent


def _load_grader_contract(task_dir: Path) -> dict:
    """Load grader_contract.json from task directory."""
    path = task_dir / "grader_contract.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text())


def _check_fatal_errors(run_log: str, contract: dict) -> list[str]:
    """Check for fatal error patterns defined in grader_contract.failure_patterns."""
    fatal_patterns = contract.get("failure_patterns", [])
    found: list[str] = []
    for pat in fatal_patterns:
        if pat.get("severity") == "error":
            desc = pat.get("description", "")
            if desc and desc in run_log:
                found.append(pat.get("category", "unknown"))
    # Also check generic HSPICE abort
    if re.search(r"hspice job aborted", run_log, re.IGNORECASE):
        if "abort" not in found:
            found.append("abort")
    return found


class SPICEDeckDebugEvaluator(BaseEvaluator):
    """Evaluates P5 SPICE deck debug tasks using execution-based grading."""

    def __init__(self, task_dir: Path, metadata: dict):
        super().__init__(task_dir, metadata)
        self.contract = _load_grader_contract(task_dir)

    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str,
                           mode: str = "submission") -> ScoreComponent:
        weight = self.weights.get(component_name, 0.0)

        if component_name == "execution_pass":
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
        """Check if HSPICE ran successfully with no fatal errors."""
        # Check for HSPICE success indicators
        hspice_abort = bool(re.search(r"hspice job aborted", run_log, re.IGNORECASE))
        hspice_concluded = bool(re.search(r"job concluded", run_log, re.IGNORECASE))
        hspice_error = bool(re.search(r"\*\*error\*\*", run_log, re.IGNORECASE))

        # Check for fatal errors from grader contract patterns
        fatal_categories = _check_fatal_errors(run_log, self.contract)

        if hspice_abort or (hspice_error and not hspice_concluded):
            score = 0.0
            details = f"HSPICE failed: abort={hspice_abort}, errors={fatal_categories}"
        elif hspice_concluded or (not hspice_abort and not hspice_error):
            score = 1.0
            details = "HSPICE execution passed"
        else:
            score = 0.0
            details = f"HSPICE inconclusive: errors={fatal_categories}"

        return ScoreComponent(
            name="execution_pass", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[:500] if run_log else None,
        )
