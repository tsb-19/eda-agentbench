#!/usr/bin/env python3
"""Phase-5D pre-run freeze (NO model calls). Pre-specified secondary TypedContract extension
with a protocol-repaired SPICE replication. 3-condition Qwen study (Base, BundleS, TypedContract)
x 3 instances x 2 families (STA + repaired SPICE) x 2 reps = 36 primary episodes.

Per family, the 6 (instance x rep) blocks are assigned the 6 permutations of the 3 conditions
exactly once -> every condition appears twice at each position (Latin balance). Budget recomputed
from the Phase-5C actual slot-cost distribution (NOT the Phase-4 estimate). Instance = primary unit;
reps nested; semantic-binding primary; no pooled-trajectory headline.

Predeclared contrasts: (1) TypedContract vs Base; (2) TypedContract vs BundleS; (3) BundleS vs Base
(same-window replication).
"""
from __future__ import annotations
import json, itertools, os, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import canonical_integrity as cig

OUT = REPO / "reports/evidence/phase5d_freeze"
SEED = 20260806
CONDITIONS = ["Base", "BundleS", "TypedContract"]
PERMUTATIONS = list(itertools.permutations(CONDITIONS))  # 6 permutations
A_INST = ["p15_eval_0001", "p15_eval_0002", "p15_eval_0003"]
B_INST = ["p16_eval_0001", "p16_eval_0002", "p16_eval_0003"]


def _budget_from_phase5c():
    """Recompute a conservative per-slot + ceiling from the Phase-5C actual slot-cost distribution."""
    st = json.loads((REPO / "reports/evidence/phase5c_state.json").read_text())
    costs = [e.get("total_cost", 0) for e in st["episodes"] if e.get("total_cost")]
    costs += [a.get("cost", 0) for e in st["episodes"] for a in e.get("attempts", []) if a.get("cost")]
    costs = sorted(c for c in costs if c > 0)
    if not costs:
        return {"per_slot_conservative": 0.7, "ceiling": 60.0}
    mean = sum(costs) / len(costs); mx = max(costs)
    per_slot = round(max(mx, mean) * 1.5, 2)  # conservative: 1.5x the max observed
    ceiling = round(per_slot * 36 * 1.5, 2)   # 36 slots + 50% replacement/TypedContract-longer reserve
    return {"phase5c_slot_costs_n": len(costs), "phase5c_mean": round(mean, 4),
            "phase5c_max": round(mx, 4), "per_slot_conservative": per_slot, "ceiling": ceiling}


def build_schedule():
    """Per family: 6 (instance,rep) blocks x 6 permutations (each once) -> 18 slots/family."""
    import random
    rng = random.Random(SEED)
    flat = []
    for family, insts, track in (("A_sta", A_INST, "p15_sta_handoff"), ("B_spice", B_INST, "p16_spice_handoff")):
        blocks = [(i, r) for i in insts for r in (1, 2)]  # 6 blocks
        perms = PERMUTATIONS[:]; rng.shuffle(perms)       # assign the 6 perms to the 6 blocks
        for (inst, rep), perm in zip(blocks, perms):
            block_id = f"{family}:{inst}:r{rep}"
            for pos, cond in enumerate(perm):
                flat.append({"block_id": block_id, "position_in_block": pos, "condition": cond,
                             "task_id": f"{inst}_{cond.lower()}", "track": track, "family": family,
                             "instance": inst, "rep": rep, "permutation": list(perm)})
    # balance check: every condition at each position, per family
    balance_ok = True
    for fam in ("A_sta", "B_spice"):
        for pos in range(3):
            cnt = {}
            for s in flat:
                if s["family"] == fam and s["position_in_block"] == pos:
                    cnt[s["condition"]] = cnt.get(s["condition"], 0) + 1
            if any(v != 2 for v in cnt.values()) or len(cnt) != 3:
                balance_ok = False
    return {"schema": "phase5d_schedule/v1", "seed": SEED, "method": "6-permutation Latin balance: each "
            "(instance,rep) block runs the 3 conditions in a unique permutation; every condition twice per position",
            "conditions": CONDITIONS, "episodes": len(flat), "position_balance_per_family": balance_ok,
            "frozen_execution_order": flat,
            "rule": "FROZEN before any paid call; instance is the primary unit; reps nested; no adaptive k; "
                    "no task/wording change after the first model result"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sched = build_schedule()
    budget = _budget_from_phase5c()
    contrasts = {"primary_predeclared": ["TypedContract vs Base", "TypedContract vs BundleS",
                                          "BundleS vs Base (same-window replication)"],
                 "primary_outcome": "semantic_binding correctness",
                 "separate_secondary": ["artifact/protocol correctness", "provenance", "FINISH", "transport", "cost", "failure subtype"],
                 "no_pooled_trajectory_headline_test": True}
    # custody manifest at HEAD over the 6 instances x 3 conditions + code
    task_roots = []
    for track, insts in (("p15_sta_handoff", A_INST), ("p16_spice_handoff", B_INST)):
        for inst in insts:
            for cond in ("base", "bundles", "typedcontract"):
                task_roots.append(f"tasks/{track}/{inst}_{cond}")
    code = ["scripts/phase5c_run.py", "scripts/phase5c_report.py", "scripts/phase5d_freeze.py",
            "generators/p15_sta_handoff/grade_sta_handoff.py", "generators/p16_spice_handoff/grade_spice_handoff.py",
            "eda_agentbench/evaluator/sta_handoff.py", "eda_agentbench/evaluator/spice_handoff.py",
            "scripts/episode_arbiter.py", "scripts/canonical_integrity.py"]
    manifest = cig.freeze(str(REPO), task_roots, code_files=code)
    freeze = {"schema": "phase5d_prerun_freeze/v1",
              "label": "pre-specified secondary TypedContract extension with a protocol-repaired SPICE replication",
              "model": "Qwen3.7-Max", "schedule": sched, "budget": budget, "contrasts": contrasts,
              "custody_manifest": manifest, "phase5c_remains_frozen_primary": True,
              "phase5d_paid_calls_so_far": 0}
    (OUT / "phase5d_schedule.json").write_text(json.dumps(sched, indent=2) + "\n")
    (OUT / "phase5d_freeze.json").write_text(json.dumps(freeze, indent=2) + "\n")
    # preflight checks (no model calls)
    pf = {}
    st = subprocess_run(["git", "-C", str(REPO), "status", "--porcelain"])
    pf["clean_tree"] = (st == "")
    ok, inc = cig.verify(str(REPO), manifest); pf["canonical_hashes_match"] = ok
    # all 18 task trees resolve (6 instances x 3 conditions)
    need = have = 0
    for track, insts in (("p15_sta_handoff", A_INST), ("p16_spice_handoff", B_INST)):
        for inst in insts:
            for cond in ("base", "bundles", "typedcontract"):
                need += 1; have += int((REPO / f"tasks/{track}/{inst}_{cond}/files/run_public.sh").is_file())
    pf["task_trees_resolve"] = (have == need == 18)
    pf["schedule_position_balanced"] = sched["position_balance_per_family"]
    pf["ALL_PASS"] = all(pf.values())
    (OUT / "phase5d_preflight.json").write_text(json.dumps(pf, indent=2) + "\n")
    print(json.dumps({"schedule_episodes": sched["episodes"], "position_balanced": sched["position_balance_per_family"],
                      "budget": budget, "preflight": pf}, indent=2))


def subprocess_run(cmd):
    import subprocess
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


if __name__ == "__main__":
    main()
