"""P9 PrimeTime Exception Debug evaluator: path-level execution grading via pt_shell.

Grading model (see generators/p9_pt_exception_debug_gen.py for the full contract):
  - The hidden runner (run_hidden.sh) launders the agent SDC in one pt_shell session,
    then GRADES in a fresh session that asserts each must-meet holdout path is still
    analyzed AND meets. It emits, at line start:
        EXC_EXEC_OK / EXC_EXEC_FAIL: <reason>   (the SDC applied + PT ran)
        EXC_SCORE: <fraction>                    (passed must-meet checks / total)
        EXC_DETAIL: <per-path OK/VIOL/EXCLUDED>
  - Apply-session output is prefixed with "[apply] ", so an agent-injected EXC_SCORE
    line cannot match the ^-anchored markers below — the only authoritative score comes
    from the laundered grade session.
  - The evaluator only reads those markers; it never re-implements timing.
"""

from __future__ import annotations

import re
from pathlib import Path

from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent

_CRASH = r"Segmentation fault|core dumped|pt_shell.*aborted"


class PTExceptionDebugEvaluator(BaseEvaluator):
    """Evaluates P9 PrimeTime Exception Debug tasks using path-level execution grading."""

    def __init__(self, task_dir: Path, metadata: dict):
        super().__init__(task_dir, metadata)

    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str,
                           mode: str = "submission") -> ScoreComponent:
        weight = self.weights.get(component_name, 0.0)

        if component_name == "exception_check":
            return self._eval_exception(weight, run_log)
        elif component_name == "execution_pass":
            return self._eval_execution(weight, run_log)
        elif component_name == "explanation":
            # Phase 1: decorative in submission mode (path-level EXC_SCORE is the real
            # signal). Replaced by a checkable structured diagnosis in a later phase.
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
        """1.0 iff the agent SDC applied and PT ran both phases (EXC_EXEC_OK)."""
        crashed = bool(re.search(_CRASH, run_log))
        exec_ok = bool(re.search(r"^EXC_EXEC_OK", run_log, re.MULTILINE))
        if crashed:
            score, details = 0.0, "pt_shell crashed"
        elif exec_ok:
            score, details = 1.0, "pt_shell applied constraints and ran both phases"
        else:
            score, details = 0.0, "pt_shell did not apply constraints (no EXC_EXEC_OK)"
        return ScoreComponent(
            name="execution_pass", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[:500] if run_log else None,
        )

    def _eval_exception(self, weight: float, run_log: str) -> ScoreComponent:
        """Path-level score: fraction of must-meet holdout paths that stay analyzed AND meet.

        Reads the ^-anchored EXC_SCORE emitted by the laundered grade session. An
        over-constrainer that cuts a must-meet path scores 0 on that path (the path is
        EXCLUDED), so silencing a violation can never reach the golden score.
        """
        crashed = bool(re.search(_CRASH, run_log))
        score_match = re.search(r"^EXC_SCORE:\s*([0-9.]+)", run_log, re.MULTILINE)
        detail_match = re.search(r"^EXC_DETAIL:\s*(.*)", run_log, re.MULTILINE)
        if crashed:
            score, details = 0.0, "pt_shell crashed during exception check"
        elif score_match:
            score = max(0.0, min(1.0, float(score_match.group(1))))
            detail = detail_match.group(1).strip() if detail_match else ""
            details = f"Path-level exception score {score:.3f}" + (f" [{detail}]" if detail else "")
        else:
            score, details = 0.0, "Exception check did not run (no EXC_SCORE)"
        return ScoreComponent(
            name="exception_check", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[:500] if run_log else None,
        )
