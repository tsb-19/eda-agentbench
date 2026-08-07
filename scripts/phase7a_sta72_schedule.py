#!/usr/bin/env python3
"""Phase-7A Study A — FROZEN 72-episode position-balanced schedule (NO model calls).

Qwen3.7-Max x {Base, BundleS, TypedContract} x 12 STA instances x 2 reps = 72 primary
episodes. Task instance is the principal unit; 2 stochastic reps are nested
observations. Each block (instance x model) = 6 slots (3 conditions x 2 reps),
position-balanced: every condition appears exactly once in the first half
(slots 0-2) and once in the second half (slots 3-5). Seeded; no adaptive k;
no task/wording change after the first model result.

Emits reports/evidence/phase7a_sta72_schedule.json (the frozen execution order).
NOT executed in Phase-7A.
"""
from __future__ import annotations
import json, random
from itertools import permutations
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
import sys; sys.path.insert(0, str(REPO / "scripts"))
import phase7a_sta12_specs as SPECS

OUT = REPO / "reports" / "evidence"
SEED = 20260808
MODEL = "Qwen3.7-Max"
CONDITIONS = ["Base", "BundleS", "TypedContract"]
REPS = 2
TRACK = "p15_sta_handoff"


def _balanced_templates():
    """6-slot templates: perm(first half) + perm(second half) over 3 conditions.
    Each condition appears once in slots 0-2 and once in slots 3-5 => position-balanced."""
    perms = list(permutations(CONDITIONS))
    return [a + b for a in perms for b in perms]


def _block_slots(rng, inst):
    tmpl = rng.choice(_balanced_templates())
    pos = {c: [k for k, x in enumerate(tmpl) if x == c] for c in CONDITIONS}
    bal = all(any(p < 3 for p in pos[c]) and any(p >= 3 for p in pos[c]) for c in CONDITIONS)
    slots = []
    for k, c in enumerate(tmpl):
        rep = sum(1 for j in range(k) if tmpl[j] == c) + 1
        slots.append({"block_id": f"A_sta:{inst}:{MODEL}", "position_in_block": k, "condition": c,
                      "task_id": f"{inst}_{c.lower()}", "track": TRACK, "model": MODEL, "rep": rep})
    return slots, bal


def main():
    rng = random.Random(SEED)
    flat = []; n_balanced = 0; blocks = 0
    for tid, *_ in SPECS.STA12_SPECS:
        slots, bal = _block_slots(rng, tid)
        flat.extend(slots); n_balanced += int(bal); blocks += 1
    manifest = {
        "schema": "phase7a_sta72_randomization_manifest/v1", "seed": SEED,
        "study": "Phase-7A Study A (prospective STA confirmatory expansion)",
        "model": MODEL, "conditions": CONDITIONS, "reps_per_condition": REPS,
        "n_instances": len(SPECS.STA12_SPECS), "blocks": blocks, "episodes": len(flat),
        "episodes_per_block": 6, "method": "seeded position-balanced blocked randomization; "
        "each condition appears once in slots 0-2 and once in slots 3-5 of every block",
        "position_balance_all_blocks": (n_balanced == blocks),
        "frozen_execution_order": flat,
        "rule": "FROZEN before any paid call; instance is the principal unit; reps nested; "
        "no adaptive k; no wording change after the first model result; no trajectory-pooled p-value",
        "analysis_unit": "task instance (n=12); repetitions nested; paired Base/BundleS/TypedContract per instance",
        "not_executed_in_phase7a": True,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "phase7a_sta72_schedule.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"episodes={manifest['episodes']} blocks={manifest['blocks']} "
          f"position_balance_all={manifest['position_balance_all_blocks']}")
    assert manifest["episodes"] == 72, manifest["episodes"]
    assert manifest["position_balance_all_blocks"]


if __name__ == "__main__":
    main()
