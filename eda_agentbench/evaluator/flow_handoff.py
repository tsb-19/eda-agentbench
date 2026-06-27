"""FlowHandoff evaluator (Phase-1A Variant A — manifest→stale-netlist drift).

Cross-artifact handoff consistency grading. The hidden runner (run_hidden.sh) resolves the
agent's repaired handoff_manifest.json, signs off the manifest-SELECTED netlist in a FRESH
pt_shell session, and runs grade_handoff.py to check the handoff CONTRACT (which netlist the
manifest selects, its provenance hash, and the consumed interface) against the hidden
handoff_truth.json. It emits, at line start:

    SIGNOFF_OK / SIGNOFF_FAIL ...               (real PrimeTime setup sign-off of the SELECTED netlist)
    HANDOFF_CONSISTENCY_OK                       (only iff the consumed netlist matches the contract: provenance + interface)
    HANDOFF_CONSISTENCY_SCORE: <frac>           (diagnostic fraction)
    HANDOFF_CONSISTENCY_DETAIL: <per-check>
    MANIFEST_OK                                  (only iff the manifest fields match the golden contract)
    MANIFEST_SCORE: <frac>
    MANIFEST_DETAIL: <per-field>
    HANDOFF_MASKING_DETECTED: <what>            (symptom-suppression flag; zeroes consistency credit)

Apply-session / agent output is prefixed with "[apply] " so an agent-injected marker cannot
match the ^-anchored real markers.

The headline anti-collapse property: a green PrimeTime sign-off on the STALE netlist
("PT green") earns the signoff component only. Full credit (and the pass gate) requires
HANDOFF_CONSISTENCY_OK AND SIGNOFF_OK -- i.e. the handoff contract is restored, not merely the
tool made green. Sign-off is a PRECONDITION for any handoff/manifest credit. With weights
signoff 0.20 / handoff_consistency 0.55 / manifest_correctness 0.15 / explanation 0.10, total
>= 0.5 holds iff SIGNOFF_OK AND HANDOFF_CONSISTENCY_OK (manifest_correctness refines the score
to full but is not individually sufficient).
"""

from __future__ import annotations

import re
from pathlib import Path

from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent

_CRASH = r"Segmentation fault|core dumped|pt_shell.*aborted"


class FlowHandoffEvaluator(BaseEvaluator):
    """Evaluates synthetic FlowHandoff drift via marker-anchored cross-artifact grading."""

    def __init__(self, task_dir: Path, metadata: dict):
        super().__init__(task_dir, metadata)

    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str,
                           mode: str = "submission") -> ScoreComponent:
        weight = self.weights.get(component_name, 0.0)
        if component_name == "signoff":
            return self._eval_signoff(weight, run_log)
        elif component_name == "handoff_consistency":
            return self._eval_handoff_consistency(weight, run_log)
        elif component_name == "manifest_correctness":
            return self._eval_manifest_correctness(weight, run_log)
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

    def _eval_signoff(self, weight: float, run_log: str) -> ScoreComponent:
        """1.0 iff PrimeTime setup sign-off of the manifest-selected netlist is clean (^SIGNOFF_OK)."""
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

    def _eval_handoff_consistency(self, weight: float, run_log: str) -> ScoreComponent:
        """1.0 iff the consumed netlist matches the contract (^HANDOFF_CONSISTENCY_OK).

        Strict gate: provenance (hash/version) AND interface (ports/clock/top) must agree with
        the golden contract. Symptom-suppression (^HANDOFF_MASKING_DETECTED) forces 0 so a
        green-but-wrong-artifact handoff cannot earn this component. Sign-off is a PRECONDITION:
        without ^SIGNOFF_OK the handoff is not credited (the pass gate requires BOTH a clean
        sign-off AND a restored handoff contract).
        """
        crashed = bool(re.search(_CRASH, run_log))
        signoff_ok = bool(re.search(r"^SIGNOFF_OK", run_log, re.MULTILINE))
        consistency_ok = bool(re.search(r"^HANDOFF_CONSISTENCY_OK", run_log, re.MULTILINE))
        masking = re.search(r"^HANDOFF_MASKING_DETECTED:\s*(.*)", run_log, re.MULTILINE)
        frac_m = re.search(r"^HANDOFF_CONSISTENCY_SCORE:\s*([0-9.]+)", run_log, re.MULTILINE)
        detail_m = re.search(r"^HANDOFF_CONSISTENCY_DETAIL:\s*(.*)", run_log, re.MULTILINE)
        frac = frac_m.group(1) if frac_m else "?"
        detail = detail_m.group(1).strip() if detail_m else ""

        if crashed:
            score, details = 0.0, "pt_shell crashed during handoff grading"
        elif not signoff_ok:
            score, details = 0.0, "signoff precondition not met (no SIGNOFF_OK)"
        elif masking:
            score = 0.0
            details = f"masking rejected: {masking.group(1).strip()}"
        elif consistency_ok:
            score, details = 1.0, f"handoff consistent (frac {frac})"
        elif frac_m:
            score = 0.0
            details = f"handoff inconsistent (frac {frac})" + (f" [{detail}]" if detail else "")
        else:
            score, details = 0.0, "handoff check did not run (no HANDOFF_CONSISTENCY_SCORE)"
        return ScoreComponent(
            name="handoff_consistency", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[:500] if run_log else None,
        )

    def _eval_manifest_correctness(self, weight: float, run_log: str) -> ScoreComponent:
        """1.0 iff the repaired manifest fields match the golden contract (^MANIFEST_OK).

        Sign-off is a PRECONDITION here too: a manifest that matches the contract but does not
        sign off cleanly is not a completed handoff.
        """
        crashed = bool(re.search(_CRASH, run_log))
        signoff_ok = bool(re.search(r"^SIGNOFF_OK", run_log, re.MULTILINE))
        ok = bool(re.search(r"^MANIFEST_OK", run_log, re.MULTILINE))
        frac_m = re.search(r"^MANIFEST_SCORE:\s*([0-9.]+)", run_log, re.MULTILINE)
        detail_m = re.search(r"^MANIFEST_DETAIL:\s*(.*)", run_log, re.MULTILINE)
        frac = frac_m.group(1) if frac_m else "?"
        detail = detail_m.group(1).strip() if detail_m else ""
        if crashed:
            score, details = 0.0, "pt_shell crashed during manifest grading"
        elif not signoff_ok:
            score, details = 0.0, "signoff precondition not met (no SIGNOFF_OK)"
        elif ok:
            score, details = 1.0, f"manifest matches contract (frac {frac})"
        elif frac_m:
            score = 0.0
            details = f"manifest drifted (frac {frac})" + (f" [{detail}]" if detail else "")
        else:
            score, details = 0.0, "manifest check did not run (no MANIFEST_SCORE)"
        return ScoreComponent(
            name="manifest_correctness", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[:500] if run_log else None,
        )
