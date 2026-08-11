"""Synthetic project evaluator (Phase-0A constraint-drift): execution-based grading.

Grading model (see docs/phases/synthetic_phase0a_design.md and the task's hidden/ scripts):
  - The hidden runner (run_hidden.sh) launders the agent SDC, signs it off in a FRESH
    pt_shell session, and grades spec-equivalence with grade_spec.py against the hidden
    spec_truth.json. It emits, at line start:
        SIGNOFF_OK / SIGNOFF_FAIL ...              (real PrimeTime setup sign-off)
        CONSTRAINT_SPEC_OK                          (only iff EVERY spec property holds)
        CONSTRAINT_SPEC_SCORE: <frac>               (diagnostic fraction)
        CONSTRAINT_SPEC_DETAIL: <per-property>
  - Apply-session output is prefixed with "[apply] ", so an agent-injected marker in
    constraints.sdc cannot match the ^-anchored markers below.

The mechanism score (constraint_spec) is credited in FULL only on CONSTRAINT_SPEC_OK, so
symptom-suppression (PT goes green but a constraint drifts from the spec) cannot reach the
golden score even when sign-off passes. With weights constraint_spec 0.6 / signoff 0.3 /
explanation 0.1, total >= 0.5 (the harness pass threshold) holds iff SIGNOFF_OK AND
CONSTRAINT_SPEC_OK — exactly the intended pass predicate.
"""

from __future__ import annotations

import re
from pathlib import Path

from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent

_CRASH = r"Segmentation fault|core dumped|pt_shell.*aborted"


class SyntheticProjectEvaluator(BaseEvaluator):
    """Evaluates the synthetic constraint-drift project via marker-anchored execution grading."""

    def __init__(self, task_dir: Path, metadata: dict):
        super().__init__(task_dir, metadata)

    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str,
                           mode: str = "submission") -> ScoreComponent:
        weight = self.weights.get(component_name, 0.0)
        if component_name == "constraint_spec":
            return self._eval_constraint_spec(weight, run_log)
        elif component_name == "signoff":
            return self._eval_signoff(weight, run_log)
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
        return ScoreComponent(
            name=component_name, weight=weight, raw_score=0.0,
            weighted_score=0.0, details=f"Unknown component: {component_name}",
        )

    def _eval_constraint_spec(self, weight: float, run_log: str) -> ScoreComponent:
        """1.0 iff the laundered SDC matches the spec on EVERY property (^CONSTRAINT_SPEC_OK).

        The diagnostic fraction (^CONSTRAINT_SPEC_SCORE) and per-property detail are surfaced
        in `details` but do NOT grant partial credit — the gate is strict so symptom-suppression
        (sign-off green, a constraint drifted) scores 0 here.
        """
        crashed = bool(re.search(_CRASH, run_log))
        spec_ok = bool(re.search(r"^CONSTRAINT_SPEC_OK", run_log, re.MULTILINE))
        frac_m = re.search(r"^CONSTRAINT_SPEC_SCORE:\s*([0-9.]+)", run_log, re.MULTILINE)
        detail_m = re.search(r"^CONSTRAINT_SPEC_DETAIL:\s*(.*)", run_log, re.MULTILINE)
        frac = frac_m.group(1) if frac_m else "?"
        detail = detail_m.group(1).strip() if detail_m else ""

        if crashed:
            score, details = 0.0, "pt_shell crashed during spec grading"
        elif spec_ok:
            score, details = 1.0, f"spec fully satisfied (frac {frac})"
        elif frac_m:
            score = 0.0
            details = f"spec NOT fully satisfied (frac {frac})" + (f" [{detail}]" if detail else "")
        else:
            score, details = 0.0, "spec check did not run (no CONSTRAINT_SPEC_SCORE)"
        return ScoreComponent(
            name="constraint_spec", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[:500] if run_log else None,
        )

    def _eval_signoff(self, weight: float, run_log: str) -> ScoreComponent:
        """1.0 iff real PrimeTime setup sign-off reports no negative-slack path (^SIGNOFF_OK)."""
        crashed = bool(re.search(_CRASH, run_log))
        ok = bool(re.search(r"^SIGNOFF_OK", run_log, re.MULTILINE))
        fail = re.search(r"^SIGNOFF_FAIL\s*(.*)", run_log, re.MULTILINE)
        if crashed:
            score, details = 0.0, "pt_shell crashed during sign-off"
        elif ok:
            score, details = 1.0, "PrimeTime sign-off passed (no negative-slack path)"
        elif fail:
            score, details = 0.0, f"sign-off failed: {fail.group(1).strip()}"
        else:
            score, details = 0.0, "sign-off did not run (no SIGNOFF marker)"
        return ScoreComponent(
            name="signoff", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[:500] if run_log else None,
        )
