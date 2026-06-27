"""Trajectory / evidence-generation handoff evaluator (Phase-3B, p13).

Grades a handoff whose repair requires not just fixing inputs but RERUNNING the public evidence
generator so fresh, provenance-bound evidence is produced. The hidden runner laundres the agent's
editable inputs (flow_config.json selection + constraints.sdc), signs off the consumed netlist in a
FRESH pt_shell session, RE-RUNS the evidence generator on the submitted package
(regen_reference.*), and runs grade_trajectory.py (stdlib, reads all inputs as data) to check the
submitted evidence against that hidden reference. It emits, at line start:

    SIGNOFF_OK / SIGNOFF_FAIL ...                  real PrimeTime sign-off of the CONSUMED netlist
                                                   (zero constrained paths => FAIL, not a clean run)
    EVIDENCE_OK / _SCORE / _DETAIL                 submitted timing_report.rpt + evidence_manifest.json
                                                   EQUAL the hidden re-run (report_digest, input_hashes
                                                   of the SUBMITTED repaired inputs, recomputed
                                                   run_nonce, tool_exit==0, signoff==OK, paths>=min).
                                                   This single axis folds in fresh + right-package +
                                                   not-hand-edited; any of those failing breaks it.
    FINAL_ARTIFACT_CONSISTENCY_OK / _SCORE / _DETAIL  consumed selection == authority netlist + hash
    SCENARIO_CLOCK_OK / _SCORE / _DETAIL           SDC binds the authority clock + paths constrained
    PROVENANCE_OK / _SCORE / _DETAIL               evidence selected_* match the authority contract
    HANDOFF_MASKING_DETECTED: <what>               timing weakening/exceptions (zeroes consistency)

Apply-session output is prefixed "[apply] " so an agent-injected marker cannot match the
^-anchored real markers.

Anti-collapse / EVIDENCE-as-precondition (load-bearing): EVIDENCE_OK is a HARD PRECONDITION for
final_artifact_consistency, scenario_clock_consistency, and provenance_consistency. Without fresh
evidence bound to the repaired inputs, those axes score 0 even if the final files are correct, so
"final files fixed but no rerun" = signoff 0.15 + explanation 0.10 = 0.25 < 0.5 (fails). With
weights signoff 0.15 / final 0.25 / scenario 0.15 / evidence 0.25 / provenance 0.10 / explanation
0.10, the pass gate (total >= 0.5) coincides with SIGNOFF_OK ∧ EVIDENCE_OK ∧ FINAL_OK ∧ SCENARIO_OK
∧ PROVENANCE_OK. Sign-off is computed by the hidden re-run on the repaired inputs, so it can read OK
without submitted evidence; that is why signoff alone (0.15) stays far below the gate. Protocol/format
is tracked by the reliability layer (not a scored component here), as in p10/p11/p12.
"""

from __future__ import annotations

import re
from pathlib import Path

from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent

_CRASH = r"Segmentation fault|core dumped|pt_shell.*aborted"


class TrajectoryHandoffEvaluator(BaseEvaluator):
    """Evaluates state + trajectory + regenerated-evidence via marker-anchored grading."""

    def __init__(self, task_dir: Path, metadata: dict):
        super().__init__(task_dir, metadata)

    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str,
                           mode: str = "submission") -> ScoreComponent:
        weight = self.weights.get(component_name, 0.0)
        if component_name == "signoff":
            return self._eval_signoff(weight, run_log)
        if component_name == "evidence_generation":
            # the gating axis: requires SIGNOFF only (its own freshness is self-contained)
            return self._eval_marker(weight, run_log, "evidence_generation",
                                     "EVIDENCE", require_signoff=True, require_evidence=False)
        if component_name == "final_artifact_consistency":
            return self._eval_marker(weight, run_log, "final_artifact_consistency",
                                     "FINAL_ARTIFACT_CONSISTENCY", require_signoff=True,
                                     require_evidence=True)
        if component_name == "scenario_clock_consistency":
            return self._eval_marker(weight, run_log, "scenario_clock_consistency",
                                     "SCENARIO_CLOCK", require_signoff=True, require_evidence=True)
        if component_name == "provenance_consistency":
            return self._eval_marker(weight, run_log, "provenance_consistency",
                                     "PROVENANCE", require_signoff=True, require_evidence=True)
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
                     require_signoff: bool, require_evidence: bool) -> ScoreComponent:
        """Generic strict-gate component keyed on ^<prefix>_OK / _SCORE / _DETAIL.

        Preconditions (all must hold or the axis is 0):
          - require_signoff: the consumed design actually signs off (^SIGNOFF_OK);
          - require_evidence: fresh evidence was produced and matches the hidden re-run (^EVIDENCE_OK)
            -- this is the trajectory gate: final/scenario/provenance cannot be credited unless the
            agent regenerated valid evidence from the repaired package.
        Masking (^HANDOFF_MASKING_DETECTED) forces 0.
        """
        crashed = bool(re.search(_CRASH, run_log))
        signoff_ok = bool(re.search(r"^SIGNOFF_OK", run_log, re.MULTILINE))
        evidence_ok = bool(re.search(r"^EVIDENCE_OK", run_log, re.MULTILINE))
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
        elif require_evidence and not evidence_ok:
            score, details = 0.0, "evidence precondition not met (no EVIDENCE_OK; fresh rerun required)"
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
