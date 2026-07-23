#!/usr/bin/env python3
"""Isolated FULL-grade reproduction for 0018 golden (regen + _grade_one) with evidence detail, vs
0009 golden control. Clean, single-task, no concurrent PT. If 0018 golden grades 1.0 here, the full
gate's 0018 failures are b04-load transients, not a variant defect."""
import sys, os, tempfile, shutil
REPO = "/data1/tongsb/eda-agentbench-synthetic-phase0a"
sys.path.insert(0, REPO); sys.path.insert(0, REPO + "/scripts"); os.chdir(REPO)
import json
from pathlib import Path
from eda_agentbench.task.loader import TaskLoader
from eda_agentbench.tools.detector import ToolEnvironmentDetector
from eda_agentbench.tools.env_shim import EnvShim
import phase4w_fairness_gate as G
from run_model_baseline import _grade_one

det = ToolEnvironmentDetector(); tools = [t for t in [det.detect_one("pt")] if t and t.available]
env = EnvShim(tools).get_env()
loader = TaskLoader(Path(REPO))
runs = Path(tempfile.mkdtemp(prefix="p4y_iso_grade_"))
for tid in ("workflow_handoff_0018", "workflow_handoff_0009"):
    task = G.TRACK / tid
    fc = G.build_candidate_fc(task, "golden")
    work = Path(tempfile.mkdtemp(prefix=f"iso_{tid}_"))
    shutil.copytree(task / "files", work, dirs_exist_ok=True)
    shutil.copytree(task / "hidden", work, dirs_exist_ok=True)
    (work / "flow_config.json").write_text(json.dumps(fc, indent=2) + "\n")
    G.regen_evidence(work, env, 600)
    sub = Path(tempfile.mkdtemp(prefix=f"isosub_{tid}_"))
    for ef in G.EDITABLE:
        if (work / ef).exists(): shutil.copy2(work / ef, sub / ef)
    res = _grade_one(task, sub, runs / tid)
    comps = {c["name"]: round(c["raw"], 2) for c in res.get("components", [])}
    print(f"\n=== {tid} golden FULL grade ===")
    print("  score:", res.get("total_score"), "| signoff:", comps.get("signoff"),
          "| evgen:", comps.get("evidence_generation"), "| stage_chain:", comps.get("stage_chain"))
    # dump the evidence detail markers if present
    for k, v in res.items():
        if k not in ("components",) and isinstance(v, (str, list)) and v:
            print(f"  {k}: {str(v)[:400]}")
