"""Family B (SPICE measurement handoff, p16) evaluator.

The hidden runner (run_hidden.sh) builds the deck from the agent's meas_config, runs real
HSPICE, writes measure_result.json, and runs grade_spice_handoff.py (six-dimension markers
JSON). This evaluator RE-RUNS grade_spice_handoff.py in the evaluator workspace for clean
markers and maps each metadata-weighted component to the corresponding grader dimension.
semantic_binding IS a weighted component here (per the p16 metadata weights); the grader
never uses a hidden exact numeric answer (numeric_validity only checks the frozen plausible
range).
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent

_DIM_COMPONENTS = {"semantic_binding", "evidence_provenance", "simulation_success",
                   "numeric_validity", "artifact_completion", "protocol_completion"}


class SPICEHandoffEvaluator(BaseEvaluator):
    def __init__(self, task_dir: Path, metadata: dict):
        super().__init__(task_dir, metadata)
        self._markers = None

    def _markers_for(self, work_dir: Path) -> dict:
        if self._markers is None:
            grader = Path(work_dir) / "grade_spice_handoff.py"
            markers = {}
            if grader.is_file():
                try:
                    r = subprocess.run([sys.executable, "grade_spice_handoff.py"], cwd=str(work_dir),
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
        dims = m.get("dimensions", {})
        if component_name in _DIM_COMPONENTS:
            raw = 1.0 if dims.get(component_name) else 0.0
            return ScoreComponent(name=component_name, weight=weight, raw_score=raw,
                                  weighted_score=raw * weight, details=f"dim={dims.get(component_name)}")
        return ScoreComponent(name=component_name, weight=weight, raw_score=0.0,
                              weighted_score=0.0, details=f"unknown component: {component_name}")
