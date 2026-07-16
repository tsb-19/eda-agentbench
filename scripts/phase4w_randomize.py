#!/usr/bin/env python3
"""Phase-4W Run-1 blocked randomization (gate #4).

Three two-run blocks. Within each block the seed decides whether V1 or V9 runs first
(deterministic; recorded). Produces the frozen execution order + planned result dirs.
The order is FROZEN here and must not change after the first paid result is observed.

Seed: phase4w_run1_seed = 20260715
V1 = workflow_handoff_0013 ; V9 = workflow_handoff_0014
Output: reports/evidence/p14_phase4w_fairness/randomization_manifest.json
"""
import json, random, hashlib, subprocess
from pathlib import Path

SEED = 20260715
VARIANTS = {"V1": "workflow_handoff_0013", "V9": "workflow_handoff_0014"}
OUT = Path("reports/evidence/p14_phase4w_fairness"); OUT.mkdir(parents=True, exist_ok=True)

def main():
    rng = random.Random(SEED)
    blocks = []
    flat = []
    for b in range(1, 4):
        v1_first = rng.random() < 0.5
        order = ["V1", "V9"] if v1_first else ["V9", "V1"]
        block = {"block_id": f"block{b}", "order": order,
                 "v1_first": v1_first, "draw": round(rng.random(), 6)}
        for pos, v in enumerate(order):
            flat.append({"block_id": block["block_id"], "position_in_block": pos,
                         "variant": v, "task_id": VARIANTS[v],
                         "planned_results_dir": f"/tmp/p4w_run1_{block['block_id']}_{v}_{pos}"})
        blocks.append(block)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    script_sha = hashlib.sha256(Path("scripts/phase4w_randomize.py").read_bytes()).hexdigest()
    manifest = {
        "seed": SEED, "seed_name": "phase4w_run1_seed",
        "method": "random.Random(seed).random()<0.5 per block decides V1-first vs V9-first; 3 blocks",
        "variants": VARIANTS,
        "blocks": blocks,
        "frozen_execution_order": [f"{s['block_id']}:{s['variant']}" for s in flat],
        "flat": flat,
        "code_commit_at_freeze": commit,
        "randomization_script_sha256": script_sha,
        "rule": "Order is FROZEN at this manifest. Must not change after the first paid result is observed.",
        "counts": {"V1": sum(1 for s in flat if s['variant'] == 'V1'),
                   "V9": sum(1 for s in flat if s['variant'] == 'V9')},
    }
    (OUT / "randomization_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"seed": SEED, "order": manifest["frozen_execution_order"],
                      "counts": manifest["counts"], "commit": commit}, indent=2))

if __name__ == "__main__":
    main()
