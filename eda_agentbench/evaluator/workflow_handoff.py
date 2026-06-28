"""Workflow / multi-stage evidence-chain handoff evaluator (Phase-4B, p14).

Generalizes the p13 trajectory evaluator to multi-stage evidence chains. The repair requires fixing
the broken handoff inputs AND running an ORDERED evidence-generation workflow whose later stages bind
to the fresh digests of earlier stages (cross-stage `upstream_evidence_digest`). The hidden runner
launders the agent's editable inputs, signs off the consumed netlist in a FRESH pt_shell session,
RE-RUNS the full trusted evidence chain on the submitted package, and runs grade_workflow.py (stdlib,
all inputs read as data) to compare the submitted evidence chain against that hidden reference.

Markers consumed (line-anchored):
    SIGNOFF_OK / SIGNOFF_FAIL ...       real PrimeTime sign-off of the CONSUMED netlist
    EVIDENCE_OK / _SCORE / _DETAIL      MASTER GATE: every required stage's submitted evidence EQUALS
                                        the hidden re-run (report_digest, input_hashes, run_nonce,
                                        signoff==OK, paths>=min) AND describes the authority-correct
                                        package. Folds in fresh + right-package + not-hand-edited.
    FINAL_STATE_OK / _SCORE / _DETAIL   consumed selection == authority netlist + clock + corner
    STAGE_CHAIN_OK / _SCORE / _DETAIL   every required stage present & fresh, and each stage's
                                        upstream_evidence_digest == the fresh prior stage's digest
                                        (ordered chain). For evidence_steps=1 this is trivially OK
                                        (single stage, no upstream edge) -- the same evaluator serves
                                        the p13-reproduction baseline and the deep chain.
    PROVENANCE_OK / _SCORE / _DETAIL    evidence selected_* match the authority contract
    HANDOFF_MASKING_DETECTED: <what>    timing weakening/exceptions (zeroes consistency)

EVIDENCE_OK is a HARD PRECONDITION for final_state, stage_chain, and provenance (the trajectory gate):
without a fresh evidence chain bound to the repaired inputs those axes score 0 even if the final files
are correct. With weights signoff 0.15 / final_state 0.20 / evidence_generation 0.25 / stage_chain 0.15
/ provenance 0.15 / explanation 0.10, the pass gate (total >= 0.5) coincides with
SIGNOFF_OK ∧ EVIDENCE_OK ∧ FINAL_STATE_OK ∧ STAGE_CHAIN_OK ∧ PROVENANCE_OK ∧ no forbidden edit.
"final files fixed but no chain rerun" = signoff 0.15 + explanation 0.10 = 0.25 < 0.5 (fails).
"stage1 fresh but stage2 missing/stale" (evidence_steps=2) => no EVIDENCE_OK / no STAGE_CHAIN_OK => fail.

Apply-session output is prefixed "[apply] " so an agent-injected marker cannot match the ^-anchored
real markers.
"""

from __future__ import annotations

import re
from pathlib import Path

from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent

_CRASH = r"Segmentation fault|core dumped|pt_shell.*aborted"


class WorkflowHandoffEvaluator(BaseEvaluator):
    """Evaluates state + ordered multi-stage evidence chain via marker-anchored grading."""

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
        if component_name == "final_state":
            return self._eval_marker(weight, run_log, "final_state",
                                     "FINAL_STATE", require_signoff=True, require_evidence=True)
        if component_name == "stage_chain":
            return self._eval_marker(weight, run_log, "stage_chain",
                                     "STAGE_CHAIN", require_signoff=True, require_evidence=True)
        if component_name == "provenance":
            return self._eval_marker(weight, run_log, "provenance",
                                     "PROVENANCE", require_signoff=True, require_evidence=True)
        if component_name == "authority_consistency":
            # p14 v2 hazard-recovery gate: the repaired package equals the manifest authority and the
            # fresh evidence describes it. Gated behind EVIDENCE_OK (same trajectory precondition).
            return self._eval_marker(weight, run_log, "authority_consistency",
                                     "AUTHORITY_CONSISTENCY", require_signoff=True, require_evidence=True)
        if component_name == "hazard_recovery":
            # p14 v2 hazard-recovery gate: the full fresh ordered chain was produced (the hazard is gone).
            return self._eval_marker(weight, run_log, "hazard_recovery",
                                     "HAZARD_RECOVERY", require_signoff=True, require_evidence=True)
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
          - require_evidence: the full required evidence chain was produced and matches the hidden
            re-run (^EVIDENCE_OK) -- the trajectory gate. final_state/stage_chain/provenance cannot be
            credited unless the agent regenerated a valid, ordered evidence chain from the repaired
            package.
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
            score, details = 0.0, "evidence precondition not met (no EVIDENCE_OK; fresh chain required)"
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
