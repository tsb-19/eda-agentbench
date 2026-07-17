#!/usr/bin/env python3
"""Phase-4W Run-2 real-PT fairness gate: 4 candidates x {0015 BundleS, 0016 BundleD} (+ 0009/0010 source).
Reuses the per-candidate evidence-regen + grade path from phase4w_fairness_gate.
"""
import sys, os
REPO="/data1/tongsb/eda-agentbench-synthetic-phase0a"
sys.path.insert(0, REPO); sys.path.insert(0, REPO+"/scripts"); os.chdir(REPO)
import json, tempfile, shutil, subprocess
from pathlib import Path
import phase4w_fairness_gate as G
from eda_agentbench.task.loader import TaskLoader
from eda_agentbench.tools.detector import ToolEnvironmentDetector
from eda_agentbench.tools.env_shim import EnvShim

TASKS = ["workflow_handoff_0009", "workflow_handoff_0010", "workflow_handoff_0015", "workflow_handoff_0016"]
OUT = Path("reports/evidence/p14_phase4w_run2/fairness"); OUT.mkdir(parents=True, exist_ok=True)
loader = TaskLoader(Path(REPO))
det = ToolEnvironmentDetector(); tools=[t for t in [det.detect_one("pt")] if t and t.available]
env = EnvShim(tools).get_env()
runs = Path(tempfile.mkdtemp(prefix="p4w_run2_gate_runs_"))
results={}
for tid in TASKS:
    task = G.TRACK/tid; meta=loader.load(task); results[tid]={"task_id":tid,"candidates":{}}
    for cand in G.CANDIDATES:
        fc=G.build_candidate_fc(task,cand)
        work=Path(tempfile.mkdtemp(prefix=f"ev_{tid}_{cand}_")); shutil.copytree(task/"files",work,dirs_exist_ok=True); shutil.copytree(task/"hidden",work,dirs_exist_ok=True)
        (work/"flow_config.json").write_text(json.dumps(fc,indent=2)+"\n")
        try:
            G.regen_evidence(work, env, 300)
            sub=Path(tempfile.mkdtemp(prefix=f"sub_{tid}_{cand}_"))
            for ef in G.EDITABLE:
                if (work/ef).exists(): shutil.copy2(work/ef, sub/ef)
            res=G._grade_one(task, sub, runs/tid)
        except Exception as e:
            res={"ok":False,"total_score":None,"error":f"{type(e).__name__}: {e}"}
        comps={c["name"]:round(c["raw"],2) for c in res.get("components",[])}
        res["submitted"]={k:fc.get(k) for k in ("netlist","scenario","corner")}; res["candidate"]=cand
        results[tid]["candidates"][cand]=res
        print(f"[{tid}] {cand:16s} score={res.get('total_score')} signoff={comps.get('signoff')} evgen={comps.get('evidence_generation')} sub={res['submitted']} err={res.get('error')}", flush=True)
(OUT/"gate_results.json").write_text(json.dumps(results,indent=2)+"\n")
print("\n=== SUMMARY ===", flush=True)
for tid in TASKS:
    row=[f"{c[:6]}={results[tid]['candidates'][c].get('total_score')}" for c in G.CANDIDATES]
    print(f"{tid}: "+"  ".join(row), flush=True)
