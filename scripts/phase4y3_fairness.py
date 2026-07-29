#!/usr/bin/env python3
"""Phase-4Y Stage-3 real-PT fairness gate UNDER BLOCK MEASUREMENT-CONTROL.
Per task: full-path check (L2) -> 4 candidates -> full-path check (L2). A block is admissible only if
both bookends healthy. Inadmissible block -> all outcomes diagnostic (rerun block later). Admissible
block -> authoritative; a valid unexpected score is a HARD FAIRNESS FAIL.
"""
import sys, os
REPO = "/data1/tongsb/eda-agentbench-synthetic-phase0a"
sys.path.insert(0, REPO); sys.path.insert(0, REPO + "/scripts"); os.chdir(REPO)
import json, tempfile
from pathlib import Path
import phase4w_fairness_gate as G
import pt_health_sentinel as SEN
import measurement_control as MC
from eda_agentbench.task.loader import TaskLoader
from eda_agentbench.tools.detector import ToolEnvironmentDetector
from eda_agentbench.tools.env_shim import EnvShim

TASKS = ["workflow_handoff_0009", "workflow_handoff_0022", "workflow_handoff_0023"]
OUT = Path("reports/evidence/p14_phase4y3/fairness"); OUT.mkdir(parents=True, exist_ok=True)
loader = TaskLoader(Path(REPO))
det = ToolEnvironmentDetector(); tools = [t for t in [det.detect_one("pt")] if t and t.available]
if not tools: print("FATAL: pt tool not detected"); sys.exit(2)
env = EnvShim(tools).get_env()
runs = Path(tempfile.mkdtemp(prefix="p4y3_mc_runs_"))

# Level-1 sentinel (first-line health detection)
sentinel = SEN.check_pt_health(G.TRACK / "workflow_handoff_0009", env, deadline=180.0)
(OUT / "sentinel.json").write_text(json.dumps([sentinel], indent=2) + "\n")
print(f"[L1-sentinel] healthy={sentinel['healthy']} elapsed={sentinel['elapsed_s']}s", flush=True)

blocks = []
for tid in TASKS:
    task = G.TRACK / tid; loader.load(task)
    blk = MC.run_block(task, tid, G.CANDIDATES, env, runs, max_replacements=2)
    blocks.append(blk)
    status = "ADMISSIBLE" if blk["admissible"] else f"INADMISSIBLE ({blk['invalid_reason']})"
    hf = MC.block_hard_fail(blk)
    print(f"[block {tid}] {status} | hard_fails={hf}", flush=True)
    for cand, res in blk["candidates"].items():
        comps = {c["name"]: round(c["raw"], 2) for c in res.get("components", [])}
        tag = "" if blk["admissible"] else " [diagnostic-only, block out-of-control]"
        print(f"    {cand:16s} score={res.get('total_score')} signoff={comps.get('signoff')} "
              f"evgen={comps.get('evidence_generation')}{tag}", flush=True)

(OUT / "gate_results.json").write_text(json.dumps({"blocks": blocks, "sentinel": sentinel}, indent=2) + "\n")

inadmissible = [b["task"] for b in blocks if not b["admissible"]]
hard_fails = {b["task"]: MC.block_hard_fail(b) for b in blocks if b["admissible"] and MC.block_hard_fail(b)}
verdict = {"gate": "Phase-4Y Stage-3 fairness (block measurement-control)",
           "blocks": [{"task": b["task"], "admissible": b["admissible"],
                       "before_healthy": b["before"]["healthy"], "after_healthy": b["after"]["healthy"],
                       "invalid_reason": b["invalid_reason"]} for b in blocks],
           "inadmissible_blocks": inadmissible,
           "hard_fairness_fails": hard_fails,
           "ALL_PASS": (not inadmissible and not hard_fails)}
(OUT / "fairness_verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")
print("\n=== VERDICT ===", flush=True)
print(f"inadmissible_blocks={inadmissible} hard_fails={hard_fails} ALL_PASS={verdict['ALL_PASS']}", flush=True)
if inadmissible:
    print("Block(s) out-of-control: rerun unchanged in a healthy b04 window (results diagnostic-only).", flush=True)
    sys.exit(4)  # distinct code: b04 window unhealthy
sys.exit(0 if verdict["ALL_PASS"] else 1)
