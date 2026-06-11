"""P2 Testbench/SVA Generation evaluator: mutation-based scoring with VCS."""

from __future__ import annotations

import re
from pathlib import Path

from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent


class RTLGenEvaluator(BaseEvaluator):
    """Evaluates testbench/SVA generation tasks using VCS and mutation-based grading."""

    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str,
                           mode: str = "submission") -> ScoreComponent:
        weight = self.weights.get(component_name, 0.0)

        if component_name == "compile":
            return self._eval_compile(weight, run_log)
        elif component_name == "golden_pass":
            return self._eval_golden(weight, run_log)
        elif component_name.startswith("mutant_"):
            return self._eval_mutant(component_name, weight, run_log)
        elif component_name == "explanation":
            return ScoreComponent(
                name=component_name, weight=weight, raw_score=1.0,
                weighted_score=1.0 * weight,
                details="No explanation required in submission mode",
            )
        else:
            return ScoreComponent(
                name=component_name, weight=weight, raw_score=0.0,
                weighted_score=0.0, details=f"Unknown component: {component_name}",
            )

    def _eval_compile(self, weight: float, run_log: str) -> ScoreComponent:
        """Check if VCS compilation succeeded (no Error in compile log)."""
        has_error = bool(re.search(r"^Error", run_log, re.MULTILINE | re.IGNORECASE))
        has_fatal = bool(re.search(r"(compilation aborted|cannot open|not found)", run_log, re.IGNORECASE))
        has_simv = "simv_golden" in run_log or "simv" in run_log

        if has_error or has_fatal:
            score = 0.0
            details = "Compilation failed"
        elif not has_simv and not run_log.strip():
            score = 0.0
            details = "No compilation output"
        else:
            score = 1.0
            details = "Compilation succeeded"

        return ScoreComponent(
            name="compile", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[:500] if run_log else None,
        )

    def _eval_golden(self, weight: float, run_log: str) -> ScoreComponent:
        """Check if golden design simulation passed."""
        if not run_log.strip():
            return ScoreComponent(
                name="golden_pass", weight=weight, raw_score=0.0,
                weighted_score=0.0, details="No golden simulation output",
            )

        has_pass = "ALL_TESTS_PASS" in run_log
        has_fail = "TEST_FAIL" in run_log
        has_error = bool(re.search(r"^Error", run_log, re.MULTILINE | re.IGNORECASE))

        if has_pass and not has_fail and not has_error:
            score = 1.0
            details = "Golden design passed all tests"
        elif has_fail:
            score = 0.0
            details = "Golden design failed tests"
        elif has_error:
            score = 0.0
            details = "Golden simulation had errors"
        else:
            score = 0.0
            details = "No test pass/fail indicators found"

        return ScoreComponent(
            name="golden_pass", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[-500:] if run_log else None,
        )

    def _eval_mutant(self, component_name: str, weight: float, run_log: str) -> ScoreComponent:
        """Check if mutant design was caught (test explicitly failed or error).

        Score = 1.0 if the mutant was detected (TEST_FAIL or VCS error),
        0.0 if the mutant was not caught (ALL_TESTS_PASS or no test output).
        """
        if not run_log.strip():
            return ScoreComponent(
                name=component_name, weight=weight, raw_score=0.0,
                weighted_score=0.0,
                details=f"Mutant NOT caught: no simulation output",
            )

        has_pass = "ALL_TESTS_PASS" in run_log
        has_fail = "TEST_FAIL" in run_log
        has_error = bool(re.search(r"^Error", run_log, re.MULTILINE | re.IGNORECASE))

        if has_fail or has_error:
            # Mutant caught — testbench explicitly detected the bug
            score = 1.0
            if has_fail:
                details = "Mutant caught: test detected failure"
            else:
                details = "Mutant caught: simulation error"
        elif has_pass:
            # Mutant NOT caught — testbench passed on buggy design
            score = 0.0
            details = "Mutant NOT caught: testbench passed on buggy design"
        else:
            # No clear indicator — treat as not caught (weak testbench)
            score = 0.0
            details = "Mutant NOT caught: no test pass/fail indicators"

        return ScoreComponent(
            name=component_name, weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[-500:] if run_log else None,
        )
