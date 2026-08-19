#!/usr/bin/env python3
"""Phase-8A — FROZEN position-balanced schedule for the STA power expansion (NO model calls).

Phase-7A measured the same 12 STA instances at k=2. A per-instance rate could therefore only be
0, 0.5 or 1, which is what produced 6 floor instances, 1 ceiling instance, only 5 informative
contrasts, and a band of [-12.5, +41.7] pp spanning zero. Phase-8A re-runs that identical design at
k=6 so a per-instance rate takes 7 values instead of 3 and ties become rare.

The ONLY intended differences from Phase-7A are k and the backend. Instances, conditions, blocking
principle, analysis unit and statistical hierarchy are carried over unchanged.

BACKEND NOTE (load-bearing): the frozen program's gateway no longer entitles this account to the two
models, so Phase-8A necessarily runs on a different provider. Its episodes are a DIFFERENT
measurement and are never pooled with the frozen 72. See docs/phase8a_prereg.md.

Block = (instance x model) = 18 slots = 3 conditions x 6 reps. The 18 slots are built by
concatenating 6 independent permutations of the 3 conditions, so every condition appears exactly
once per consecutive triple -- hence exactly twice in each third of the block. This generalises
phase7a_sta72_schedule.py's 6-slot construction (2 permutations, once per half).

Emits phase8a/evidence/schedule_arm<N>.json (the frozen execution order).

WHY NOT reports/evidence/ -- `scripts/frozen_membership_verify.py` scans ALL of `reports/` for
`path -> sha256` pairs, so any Phase-8A custody record written there would inflate the frozen pin
count and could mask a real mutation in the frozen set. Keeping this study's records outside
`reports/` leaves the frozen monitor's scan region byte-for-byte what it was at the experiment
freeze, with no exemption added to the verifier. See phase8a/README.md.

Generates a schedule ONLY; it executes nothing.
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from itertools import permutations
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import phase7a_sta12_specs as SPECS  # noqa: E402  (the SAME frozen 12 instances as Phase-7A)

OUT = REPO / "phase8a" / "evidence"
CONDITIONS = ["Base", "BundleS", "TypedContract"]
TRACK = "p15_sta_handoff"
SEED_BASE = 20260817
GROUP = len(CONDITIONS)  # 3 -- one full permutation per group
# The preregistered k ladder, docs/phase8a_prereg.md section 2.2. k is fixed ONCE per arm before that
# arm's first paid episode: arm 1 at 6, arm 2 at whatever the cost gate returns from this set.
#
# This replaces an earlier `reps % 3 == 0` guard whose stated reason -- "position balance is defined
# over thirds" -- was wrong in both directions. Blocks are built as `reps` concatenated permutations,
# so EVERY consecutive triple is a permutation; that is the finer property and it holds for any reps.
# The per-third count is implied by it whenever reps % 3 == 0, and is the only part needing
# divisibility. So the old guard refused k=4 and k=2 -- two of the three preregistered values, which
# is why the ladder below 6 had never once been generated -- while admitting k=3 and k=9, which were
# never preregistered at all. Constraining k to the ladder is strictly tighter for the values that
# matter and makes an adaptive k unrepresentable rather than merely forbidden in prose.
PREREG_K = (6, 4, 2)


def _templates():
    """All permutations of the condition triple; a block template is 'reps' of them concatenated."""
    return list(permutations(CONDITIONS))


def _block_slots(rng, inst, model, reps, arm):
    """One block: reps x perm(conditions). Balanced by construction; verified, not assumed."""
    tmpl = []
    for _ in range(reps):
        tmpl.extend(rng.choice(_templates()))

    # Position balance: every condition appears exactly `reps/3 * 1` times per group of 3 (once),
    # and exactly reps/3 times in each third of the block when reps is divisible by 3.
    per_group_ok = all(
        sorted(tmpl[g * GROUP:(g + 1) * GROUP]) == sorted(CONDITIONS) for g in range(reps))
    third = len(tmpl) // GROUP
    per_third_ok = all(
        tmpl[t * third:(t + 1) * third].count(c) == third // GROUP
        for t in range(GROUP) for c in CONDITIONS) if third % GROUP == 0 else per_group_ok

    slots = []
    for k, c in enumerate(tmpl):
        rep = sum(1 for j in range(k) if tmpl[j] == c) + 1
        slots.append({
            "block_id": f"8A_sta:{inst}:{model}",
            "position_in_block": k,
            "condition": c,
            "task_id": f"{inst}_{c.lower()}",
            "track": TRACK,
            "model": model,
            "rep": rep,
            "arm": arm,
            "planned_results_dir": f"/tmp/p8a{arm}_{inst}_{c}_{k}_a1",
        })
    return slots, (per_group_ok and per_third_ok)


def _head():
    try:
        return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def build(model: str, reps: int, arm: int):
    if reps not in PREREG_K:
        raise SystemExit(f"--reps must be one of the preregistered k values {PREREG_K}, got {reps}; "
                         f"k is chosen before an arm's first paid episode, never after seeing one")
    rng = random.Random(SEED_BASE + arm)
    flat, n_balanced, blocks = [], 0, 0
    for tid, *_ in SPECS.STA12_SPECS:
        slots, bal = _block_slots(rng, tid, model, reps, arm)
        flat.extend(slots)
        n_balanced += int(bal)
        blocks += 1
    return {
        "schema": "phase8a_randomization_manifest/v1",
        "study": "Phase-8A STA power expansion (k=6) on a replacement backend",
        "arm": arm,
        "seed": SEED_BASE + arm,
        "model": model,
        "conditions": CONDITIONS,
        "reps_per_condition": reps,
        "n_instances": len(SPECS.STA12_SPECS),
        "blocks": blocks,
        "episodes": len(flat),
        "episodes_per_block": reps * GROUP,
        # The per-third clause is only TRUE when reps is divisible by 3, so it is only claimed then.
        # For reps=6 this reproduces the arm-1 string byte-for-byte, which --check requires.
        "method": ("seeded blocked randomization; each block is `reps` concatenated permutations of "
                   "the 3 conditions, so every condition appears exactly once per consecutive triple"
                   + (" and exactly reps/3 times in each third of the block"
                      if reps % GROUP == 0 else "")),
        "position_balance_all_blocks": (n_balanced == blocks),
        "code_commit_at_freeze_base": _head(),
        "analysis_unit": "task instance (n=12); repetitions nested; paired Base/BundleS/"
                         "TypedContract per instance",
        "rule": "FROZEN before any paid call; instance is the principal unit; reps nested; no "
                "adaptive k; no wording change after the first model result; no trajectory-pooled "
                "p-value",
        "not_poolable_with": "reports/synthetic_phase7a_sta72_report.json -- different backend, "
                             "therefore a different measurement; report side by side, never summed",
        "counts": {c: len(SPECS.STA12_SPECS) * reps for c in CONDITIONS},
        "frozen_execution_order": flat,
        "flat": flat,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit the frozen Phase-8A schedule (no model calls).")
    ap.add_argument("--model", required=True, help="model name as it appears in baseline_models.json")
    ap.add_argument("--reps", type=int, required=True, help="k per condition per instance")
    ap.add_argument("--arm", type=int, required=True, choices=(1, 2))
    ap.add_argument("--check", action="store_true", help="verify the committed schedule reproduces")
    args = ap.parse_args()

    manifest = build(args.model, args.reps, args.arm)
    if not manifest["position_balance_all_blocks"]:
        print("FAIL: position balance not achieved in every block", file=sys.stderr)
        return 1

    target = OUT / f"schedule_arm{args.arm}.json"
    blob = json.dumps(manifest, indent=2) + "\n"
    if args.check:
        if not target.exists():
            print(f"FAIL: {target} missing", file=sys.stderr)
            return 1
        try:
            committed = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"FAIL: {target} is not valid JSON", file=sys.stderr)
            return 1
        # `code_commit_at_freeze_base` records WHICH code state the schedule was frozen against.
        # It is a recorded fact, not a reproducible one: the freeze commit necessarily lands after
        # the schedule is generated, so comparing it would make --check fail on every later commit.
        # Everything that defines the DESIGN must reproduce exactly; the stamp is only required to
        # be a well-formed commit id.
        stamp = committed.get("code_commit_at_freeze_base", "")
        if not (isinstance(stamp, str) and len(stamp) == 40
                and all(c in "0123456789abcdef" for c in stamp)):
            print(f"FAIL: code_commit_at_freeze_base is not a commit id: {stamp!r}",
                  file=sys.stderr)
            return 1
        lhs = {k: v for k, v in committed.items() if k != "code_commit_at_freeze_base"}
        rhs = {k: v for k, v in manifest.items() if k != "code_commit_at_freeze_base"}
        if lhs != rhs:
            differing = sorted(k for k in set(lhs) | set(rhs) if lhs.get(k) != rhs.get(k))
            print(f"FAIL: {target} does not reproduce; fields differ: {differing}",
                  file=sys.stderr)
            return 1
        print(json.dumps({"ok": True, "arm": args.arm, "episodes": manifest["episodes"],
                          "code_commit_at_freeze_base": stamp[:8]}))
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    target.write_text(blob, encoding="utf-8")
    print(json.dumps({"ok": True, "arm": args.arm, "model": args.model,
                      "episodes": manifest["episodes"], "blocks": manifest["blocks"],
                      "position_balance_all_blocks": True, "out": str(target)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
