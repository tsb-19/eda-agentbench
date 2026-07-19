#!/usr/bin/env python3
"""Phase-4W held-out real-PT fairness gate: 4 candidates x {0011 baseline, 0017 BundleS-heldout}.
Reuses the per-candidate evidence-regen + grade path from phase4w_fairness_gate.
Expected vectors (hard gates): golden=1.0; wrong_axis=0.2 with signoff=1.0/evgen=0.0 (signoff-green,
typed-binding-rejected); stale_decoy=0.1 with signoff=0.0 (netlist-family RED); unchanged_mutant=0.1.
"""
import sys, os
REPO="/data1/tongsb/eda-agentbench-synthetic-phase0a"
sys.path.insert(0, REPO); sys.path.insert(0, REPO+"/scripts"); os.chdir(REPO)
import json, tempfile, shutil
from pathlib import Path
import phase4w_fairness_gate as G
from eda_agentbench.task.loader import TaskLoader
from eda_agentbench.tools.detector import ToolEnvironmentDetector
from eda_agentbench.tools.env_shim import EnvShim

TASKS = ["workflow_handoff_0011", "workflow_handoff_0017"]
OUT = Path("reports/evidence/p14_phase4w_heldout/fairness"); OUT.mkdir(parents=True, exist_ok=True)
loader = TaskLoader(Path(REPO))
det = ToolEnvironmentDetector(); tools=[t for t in [det.detect_one("pt")] if t and t.available]
if not tools: print("FATAL: pt tool not detected"); sys.exit(2)
env = EnvShim(tools).get_env()
runs = Path(tempfile.mkdtemp(prefix="p4w_heldout_gate_runs_"))
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

def comp(res, name):
    for c in res.get("components", []):
        if c["name"] == name: return round(c["raw"], 2)
    return None

hard = {}
for tid in TASKS:
    c = results[tid]["candidates"]
    hard[tid] = {
        "golden_1.0": c["golden"].get("total_score") == 1.0,
        "wrong_axis_green_but_rejected": c["wrong_axis"].get("total_score") == 0.2
            and comp(c["wrong_axis"], "signoff") == 1.0 and comp(c["wrong_axis"], "evidence_generation") == 0.0,
        "stale_decoy_signoff_red": comp(c["stale_decoy"], "signoff") == 0.0
            and (c["stale_decoy"].get("total_score") or 1.0) <= 0.1,
        "unchanged_mutant_low": (c["unchanged_mutant"].get("total_score") or 1.0) <= 0.1,
    }
verdict = {"gate": "Phase-4W held-out real-PT fairness", "hard_gates": hard,
           "ALL_PASS": all(all(v.values()) for v in hard.values())}
(OUT/"fairness_verdict.json").write_text(json.dumps(verdict,indent=2)+"\n")
print("\n=== SUMMARY ===", flush=True)
for tid in TASKS:
    row=[f"{c[:6]}={results[tid]['candidates'][c].get('total_score')}" for c in G.CANDIDATES]
    print(f"{tid}: "+"  ".join(row), flush=True)
print("ALL_PASS:", verdict["ALL_PASS"])
sys.exit(0 if verdict["ALL_PASS"] else 1)
