#!/usr/bin/env python3
"""Phase-5B frozen schedules (NO model calls; emits frozen blocked-randomized schedules only).

Task instance is the primary experimental unit; 2 stochastic reps are nested observations.
Base/BundleS ORDER is balanced within every family x instance x model block (each condition
appears exactly twice per block, position-balanced).

Emits three randomization manifests under reports/evidence/phase5b_schedules/:
  - qwen24_core.json        : Qwen3.7-Max x {Base,BundleS} x 6 instances x 2 reps = 24 (BINDING core)
  - full48_variant.json     : + DeepSeek-V4-Pro                                   = 48 (if >=CNY650-700 confirmed)
  - deepseek24_extension.json: DeepSeek x {Base,BundleS} x 6 instances x 2 reps = 24 (separately authorized, ALL tasks)

None executed in Phase-5B. Seeded; exact-counterbalanced; position-balance asserted.
"""
from __future__ import annotations
import json, random
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "reports" / "evidence" / "phase5b_schedules"
SEED = 20260805

A_INSTANCES = ["p15_eval_0001", "p15_eval_0002", "p15_eval_0003"]
B_INSTANCES = ["p16_eval_0001", "p16_eval_0002", "p16_eval_0003"]
INSTANCES = ([(i, "A_sta", "p15_sta_handoff") for i in A_INSTANCES]
             + [(i, "B_spice", "p16_spice_handoff") for i in B_INSTANCES])
CONDITIONS = ["Base", "BundleS"]  # core conditions (TypedContract is a separately-authorized secondary)


_BALANCED_TEMPLATES = [["Base", "BundleS", "Base", "BundleS"], ["Base", "BundleS", "BundleS", "Base"],
                       ["BundleS", "Base", "Base", "BundleS"], ["BundleS", "Base", "BundleS", "Base"]]


def _block_slots(rng, inst, family, track, model):
    """One block = 4 slots (Base x2, BundleS x2), deterministic choice among the 4 balanced
    (interleaved) templates -> each condition appears in BOTH the first and second half (order balanced)."""
    cond = rng.choice(_BALANCED_TEMPLATES)
    pos = {c: [k for k, x in enumerate(cond) if x == c] for c in CONDITIONS}
    bal = all(any(p < 2 for p in pos[c]) and any(p >= 2 for p in pos[c]) for c in CONDITIONS)
    slots = []
    for k, c in enumerate(cond):
        rep = (sum(1 for j in range(k) if cond[j] == c)) + 1
        slots.append({"block_id": f"{family}:{inst}:{model}", "position_in_block": k, "condition": c,
                      "task_id": f"{inst}_{c.lower()}", "track": track, "model": model, "rep": rep})
    return slots, bal


def _build(model_set, seed_offset, name, note):
    rng = random.Random(SEED + seed_offset)
    flat = []; n_blocks_balanced = 0
    for inst, family, track in INSTANCES:
        for model in model_set:
            slots, bal = _block_slots(rng, inst, family, track, model)
            flat.extend(slots)
            n_blocks_balanced += int(bal)
    n_blocks = len(INSTANCES) * len(model_set)
    manifest = {
        "schema": "phase5b_randomization_manifest/v1", "seed": SEED + seed_offset, "seed_name": name,
        "method": "seeded exact-counterbalanced blocked randomization; Base/BundleS order balanced within every family x instance x model block",
        "models": list(model_set), "conditions": CONDITIONS, "reps_per_condition": 2,
        "blocks": n_blocks, "episodes": len(flat),
        "position_balance_all_blocks": (n_blocks_balanced == n_blocks),
        "frozen_execution_order": flat,
        "rule": "FROZEN before any paid call; no adaptive k; no task/wording change after the first model result; task instance is the primary unit",
        "note": note,
    }
    return manifest


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    qwen = _build(["Qwen3.7-Max"], 0, "qwen24_core",
                  "BINDING core under the committed budget ledger (~CNY318 remaining); 24 episodes; within-task 2-rep replication preserved")
    full = _build(["Qwen3.7-Max", "DeepSeek-V4-Pro"], 1, "full48_variant",
                  "selected ONLY if >=CNY650-700 usable confirmed at review; 48 episodes; otherwise the Qwen-24 core runs")
    ds = _build(["DeepSeek-V4-Pro"], 2, "deepseek24_extension",
                  "separately authorized; ALL 6 tasks (never selectively on favorable families); 24 episodes")
    for m in (qwen, full, ds):
        (OUT / f"{m['seed_name']}.json").write_text(json.dumps(m, indent=2) + "\n")
        print(f"{m['seed_name']}: episodes={m['episodes']} blocks={m['blocks']} position_balance_all={m['position_balance_all_blocks']}")
    summary = {"schema": "phase5b_schedules_summary/v1",
               "binding_core": "qwen24_core (24 ep) under committed-ledger budget",
               "alternative": "full48_variant (48 ep) if >=CNY650-700 confirmed",
               "extension": "deepseek24_extension (24 ep, all tasks, separately authorized)",
               "typedcontract_secondary": "not in any schedule (separately authorized)",
               "all_position_balanced": all(m["position_balance_all_blocks"] for m in (qwen, full, ds))}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("ALL position-balanced:", summary["all_position_balanced"])


if __name__ == "__main__":
    main()
