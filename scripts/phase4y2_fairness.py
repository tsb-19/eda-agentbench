#!/usr/bin/env python3
"""Phase-4Y Stage-2 real-PT fairness gate: 4 candidates x {0020 C1, 0021 C24} (+ 0009 source).
Sentinel-guarded; corrected validity-based retry (infra-only; a valid wrong score is a hard failure).
Hard gates: golden=1.0; wrong_axis=0.2 signoff-green/evgen-0; stale=0.1 signoff-red; mutant=0.1.
"""
import sys, os
REPO = "/data1/tongsb/eda-agentbench-synthetic-phase0a"
sys.path.insert(0, REPO); sys.path.insert(0, REPO + "/scripts"); os.chdir(REPO)
import json, tempfile, shutil
from pathlib import Path
import phase4w_fairness_gate as G
import fairness_retry as FR
import pt_health_sentinel as SEN
from eda_agentbench.task.loader import TaskLoader
from eda_agentbench.tools.detector import ToolEnvironmentDetector
from eda_agentbench.tools.env_shim import EnvShim

TASKS = ["workflow_handoff_0009", "workflow_handoff_0020", "workflow_handoff_0021"]
OUT = Path("reports/evidence/p14_phase4y2/fairness"); OUT.mkdir(parents=True, exist_ok=True)
loader = TaskLoader(Path(REPO))
det = ToolEnvironmentDetector(); tools = [t for t in [det.detect_one("pt")] if t and t.available]
if not tools:
    print("FATAL: pt tool not detected"); sys.exit(2)
env = EnvShim(tools).get_env()
runs = Path(tempfile.mkdtemp(prefix="p4y2_fairness_runs_"))
results = {}

# b04/PT health sentinel (proactive; separate record; aborts on failure; never changes membership)
sentinel_recs = [SEN.check_pt_health(G.TRACK / "workflow_handoff_0009", env, deadline=180.0)]
(OUT / "sentinel.json").write_text(json.dumps(sentinel_recs, indent=2) + "\n")
print(f"[sentinel] healthy={sentinel_recs[0]['healthy']} elapsed={sentinel_recs[0]['elapsed_s']}s", flush=True)
if not all(s["healthy"] for s in sentinel_recs):
    print("ABORT: PT sentinel unhealthy (no candidate membership change)"); sys.exit(3)


def _grade_candidate(task, tid, cand, env, runs, max_replacements):
    fc = G.build_candidate_fc(task, cand)
    attempts = []
    a = 0
    while True:
        a += 1
        work = Path(tempfile.mkdtemp(prefix=f"ev_{tid}_{cand}_a{a}_"))
        shutil.copytree(task / "files", work, dirs_exist_ok=True)
        shutil.copytree(task / "hidden", work, dirs_exist_ok=True)
        (work / "flow_config.json").write_text(json.dumps(fc, indent=2) + "\n")
        try:
            G.regen_evidence(work, env, 600)
            sub = Path(tempfile.mkdtemp(prefix=f"sub_{tid}_{cand}_a{a}_"))
            for ef in G.EDITABLE:
                if (work / ef).exists(): shutil.copy2(work / ef, sub / ef)
            res = G._grade_one(task, sub, runs / tid)
        except Exception as e:
            res = {"ok": False, "total_score": None, "error": f"{type(e).__name__}: {e}"}
        res["submitted"] = {k: fc.get(k) for k in ("netlist", "scenario", "corner")}
        res["candidate"] = cand; res["attempt"] = a
        attempts.append(res)
        if not FR.should_retry(res, None, a, max_replacements):  # infra-only retry; valid score -> stop
            break
    return attempts


for tid in TASKS:
    task = G.TRACK / tid; loader.load(task); results[tid] = {"task_id": tid, "candidates": {}}
    for cand in G.CANDIDATES:
        attempts = _grade_candidate(task, tid, cand, env, runs, max_replacements=2)
        res = attempts[-1]
        res["all_attempts"] = ([{"attempt": x["attempt"], "score": x.get("total_score"),
                                 "error": x.get("error"), "infra_retry": FR.is_measurement_infra_failure(x)}
                                for x in attempts] if len(attempts) > 1 else None)
        results[tid]["candidates"][cand] = res
        comps = {c["name"]: round(c["raw"], 2) for c in res.get("components", [])}
        tag = f" (a{len(attempts)},infra)" if len(attempts) > 1 else ""
        print(f"[{tid}] {cand:16s} score={res.get('total_score')} signoff={comps.get('signoff')} "
              f"evgen={comps.get('evidence_generation')} sub={res['submitted']}{tag} err={res.get('error')}", flush=True)
(OUT / "gate_results.json").write_text(json.dumps(results, indent=2) + "\n")


def comp(res, name):
    for c in res.get("components", []):
        if c["name"] == name: return round(c["raw"], 2)
    return None


hard = {}
for tid in TASKS:
    c = results[tid]["candidates"]
    hard[tid] = {"golden_1.0": c["golden"].get("total_score") == 1.0,
                 "wrong_axis_green_but_rejected": c["wrong_axis"].get("total_score") == 0.2
                 and comp(c["wrong_axis"], "signoff") == 1.0 and comp(c["wrong_axis"], "evidence_generation") == 0.0,
                 "stale_decoy_signoff_red": comp(c["stale_decoy"], "signoff") == 0.0
                 and (c["stale_decoy"].get("total_score") or 1.0) <= 0.1,
                 "unchanged_mutant_low": (c["unchanged_mutant"].get("total_score") or 1.0) <= 0.1}
verdict = {"gate": "Phase-4Y Stage-2 real-PT fairness (sentinel-guarded, infra-only retry)",
           "sentinel": sentinel_recs, "hard_gates": hard, "ALL_PASS": all(all(v.values()) for v in hard.values())}
(OUT / "fairness_verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")
print("\n=== SUMMARY ===", flush=True)
for tid in TASKS:
    print(f"{tid}: " + "  ".join(f"{c[:6]}={results[tid]['candidates'][c].get('total_score')}" for c in G.CANDIDATES), flush=True)
print("ALL_PASS:", verdict["ALL_PASS"])
sys.exit(0 if verdict["ALL_PASS"] else 1)
