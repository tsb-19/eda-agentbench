"""Multi-artifact FlowHandoff escalation evaluator (Phase-2B, stale-package triangle).

Grades the FULL handoff contract restoration, not just sign-off. The hidden runner laundres the
agent's editable data files (flow_config.json selection + constraints.sdc), signs off the
flow-CONSUMED netlist in a FRESH pt_shell session, and runs grade_handoff.py (stdlib, reads all
inputs as data) to check the cross-artifact contract against the hidden handoff_truth.json. It
emits, at line start:

    SIGNOFF_OK / SIGNOFF_FAIL ...                  real PrimeTime sign-off of the CONSUMED netlist
                                                   (zero constrained paths => FAIL, not a clean run)
    ARTIFACT_CONSISTENCY_OK / _SCORE / _DETAIL     downstream selection consumes the manifest's
                                                   netlist + that netlist's provenance hash matches
    SCENARIO_CLOCK_OK / _SCORE / _DETAIL           SDC binds the manifest/spec clock + intended
                                                   sequential paths actually constrained (coverage)
    PROVENANCE_OK / _SCORE / _DETAIL               consumed design provenance matches the MANIFEST
                                                   AUTHORITY (not the stale report evidence)
    HANDOFF_MASKING_DETECTED: <what>               symptom-suppression (timing weakening/exceptions)

Apply-session output is prefixed "[apply] " so an agent-injected marker cannot match the
^-anchored real markers.

Escalation property: the stale-package triangle (selection->v1, SDC->clk_old, report->v1) signs off
GREEN on the wrong island, but ARTIFACT/SCENARIO/PROVENANCE all fail. ANY single local edit leaves
another check failing (fixing the selection alone, or the clock alone, yields zero constrained
paths => SIGNOFF_FAIL + the other axis still wrong). Full credit requires the coordinated
selection->v2 AND SDC->clk_main repair. With weights signoff 0.15 / artifact_consistency 0.35 /
scenario_clock_consistency 0.25 / provenance_report_consistency 0.15 / explanation 0.10, the pass
gate (total >= 0.5) coincides with SIGNOFF_OK AND ARTIFACT_CONSISTENCY_OK AND SCENARIO_CLOCK_OK:
the largest single-axis partial is artifact-only = 0.35 + 0.10 = 0.45 < 0.5, and PT-green on the
wrong package = signoff-only = 0.15 + 0.10 = 0.25. Protocol/format is tracked by the reliability
layer (not a scored component here), as in p10/p11.
"""

from __future__ import annotations

import re
from pathlib import Path

from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent

_CRASH = r"Segmentation fault|core dumped|pt_shell.*aborted"


class MultiFactHandoffEvaluator(BaseEvaluator):
    """Evaluates the multi-artifact handoff escalation via marker-anchored full-contract grading."""

    def __init__(self, task_dir: Path, metadata: dict):
        super().__init__(task_dir, metadata)

    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str,
                           mode: str = "submission") -> ScoreComponent:
        weight = self.weights.get(component_name, 0.0)
        if component_name == "signoff":
            return self._eval_signoff(weight, run_log)
        if component_name == "artifact_consistency":
            return self._eval_marker(weight, run_log, "artifact_consistency",
                                     "ARTIFACT_CONSISTENCY", require_signoff=True)
        if component_name == "scenario_clock_consistency":
            return self._eval_marker(weight, run_log, "scenario_clock_consistency",
                                     "SCENARIO_CLOCK", require_signoff=True)
        if component_name == "provenance_report_consistency":
            return self._eval_marker(weight, run_log, "provenance_report_consistency",
                                     "PROVENANCE", require_signoff=True)
        if component_name == "explanation":
            if mode == "submission":
                return ScoreComponent(name=component_name, weight=weight, raw_score=1.0,
                                      weighted_score=1.0 * weight,
                                      details="No explanation required in submission mode")
            return ScoreComponent(name=component_name, weight=weight, raw_score=0.0,
                                  weighted_score=0.0, details="Explanation scoring not implemented")
        return ScoreComponent(name=component_name, weight=weight, raw_score=0.0,
                              weighted_score=0.0, details=f"Unknown component: {component_name}")

    def _eval_signoff(self, weight: float, run_log: str) -> ScoreComponent:
        """1.0 iff PrimeTime sign-off of the flow-CONSUMED netlist is clean and non-empty."""
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
        return ScoreComponent(name="signoff", weight=weight, raw_score=score,
                              weighted_score=score * weight, details=details,
                              tool_output_snippet=run_log[:500] if run_log else None)

    def _eval_marker(self, weight: float, run_log: str, comp: str, prefix: str,
                     require_signoff: bool) -> ScoreComponent:
        """Generic strict-gate consistency component keyed on ^<prefix>_OK / _SCORE / _DETAIL.

        Sign-off is a PRECONDITION (require_signoff): a consistency axis cannot be credited unless
        the consumed design actually signs off, so a partial repair that leaves zero constrained
        paths earns nothing. Masking (^HANDOFF_MASKING_DETECTED) forces 0.
        """
        crashed = bool(re.search(_CRASH, run_log))
        signoff_ok = bool(re.search(r"^SIGNOFF_OK", run_log, re.MULTILINE))
        ok = bool(re.search(rf"^{prefix}_OK", run_log, re.MULTILINE))
        masking = re.search(r"^HANDOFF_MASKING_DETECTED:\s*(.*)", run_log, re.MULTILINE)
        frac_m = re.search(rf"^{prefix}_SCORE:\s*([0-9.]+)", run_log, re.MULTILINE)
        detail_m = re.search(rf"^{prefix}_DETAIL:\s*(.*)", run_log, re.MULTILINE)
        frac = frac_m.group(1) if frac_m else "?"
        detail = detail_m.group(1).strip() if detail_m else ""

        if crashed:
            score, details = 0.0, f"pt_shell crashed during {comp} grading"
        elif require_signoff and not signoff_ok:
            score, details = 0.0, "signoff precondition not met (no SIGNOFF_OK)"
        elif masking:
            score, details = 0.0, f"masking rejected: {masking.group(1).strip()}"
        elif ok:
            score, details = 1.0, f"{comp} consistent (frac {frac})"
        elif frac_m:
            score, details = 0.0, f"{comp} inconsistent (frac {frac})" + (f" [{detail}]" if detail else "")
        else:
            score, details = 0.0, f"{comp} check did not run (no {prefix}_SCORE)"
        return ScoreComponent(name=comp, weight=weight, raw_score=score,
                              weighted_score=score * weight, details=details,
                              tool_output_snippet=run_log[:500] if run_log else None)
