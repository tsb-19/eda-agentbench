"""Family A (STA constraint/exception handoff, p15) evaluator.

The hidden runner (run_hidden.sh) launders the agent's exception binding to an SDC, signs off
on real PrimeTime, writes signoff_result.json + applied_hidden.sdc, and runs grade_sta_handoff.py
(emitting a markers JSON). This evaluator RE-RUNS grade_sta_handoff.py in the evaluator workspace
for a clean markers dict (robust to interleaved [apply] PT output) and maps each metadata-weighted
component to the corresponding grader check. The PRIMARY outcome (semantic_binding) is also exposed
as a zero-weight component so the analysis can read it; the weighted total_score is the secondary
artifact/tool-correctness measure.
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent

_CHECK_COMPONENTS = {"provenance_attested", "coverage_cell_consistent", "check_view_legal",
                     "pt_signoff_green", "not_masking"}


class STAHandoffEvaluator(BaseEvaluator):
    def __init__(self, task_dir: Path, metadata: dict):
        super().__init__(task_dir, metadata)
        self._markers = None

    def _markers_for(self, work_dir: Path) -> dict:
        if self._markers is None:
            grader = Path(work_dir) / "grade_sta_handoff.py"
            markers = {}
            if grader.is_file():
                try:
                    r = subprocess.run([sys.executable, "grade_sta_handoff.py"], cwd=str(work_dir),
                                       capture_output=True, text=True, timeout=60)
                    markers = json.loads(r.stdout) if r.stdout.strip() else {}
                except Exception:
                    markers = {}
            self._markers = markers
        return self._markers

    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str,
                           mode: str = "submission") -> ScoreComponent:
        weight = self.weights.get(component_name, 0.0)
        m = self._markers_for(work_dir)
        checks = m.get("checks", {})
        if component_name in _CHECK_COMPONENTS:
            raw = 1.0 if checks.get(component_name) else 0.0
            return ScoreComponent(name=component_name, weight=weight, raw_score=raw,
                                  weighted_score=raw * weight, details=f"check={checks.get(component_name)}")
        if component_name == "explanation":
            # decorative in submission mode (the provenance/coverage checks are the real signal)
            return ScoreComponent(name=component_name, weight=weight, raw_score=1.0,
                                  weighted_score=1.0 * weight, details="no structured explanation required")
        if component_name == "semantic_binding":
            # zero-weight PRIMARY outcome, exposed for the analysis
            raw = 1.0 if checks.get("semantic_binding") else 0.0
            return ScoreComponent(name=component_name, weight=0.0, raw_score=raw,
                                  weighted_score=0.0, details=f"primary outcome (zero-weight); check={checks.get('semantic_binding')}")
        return ScoreComponent(name=component_name, weight=weight, raw_score=0.0,
                              weighted_score=0.0, details=f"unknown component: {component_name}")
