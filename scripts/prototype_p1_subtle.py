#!/usr/bin/env python3
"""Prototype: P1 SUBTLE-bug hardening pilot.

Identical bundling to scripts/prototype_p1_multifault.py (K independent modules,
one bug each, compiled/simulated separately so every module contributes its
PASS:/FAIL: lines) — the ONLY changed variable is the bug source: curated
corner-case bugs from generators.p1_subtle_bugs.SUBTLE_BUG_TYPES instead of the
easy generators.p1_rtl_debug_gen.BUG_TYPES. This makes the pilot a clean A/B
against the multi-fault-easy run (same K, same scoring, same hints style): any
extra discrimination is attributable to bug subtlety, not bundling.

Each module's public test only exercises the common case; the hidden suite hits
the corners, so a partial fix scores fractionally via the existing evaluator.

    python3 scripts/prototype_p1_subtle.py --count 10 --k 3 --out pilot_p1subtle
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from generators.p1_subtle_bugs import SUBTLE_BUG_TYPES  # noqa: E402


def _run_script(pairs: list[tuple[str, str]]) -> str:
    """Compile+sim each (design, tb) pair, never aborting on one module's failure
    so every module contributes its PASS:/FAIL: lines to the combined log."""
    lines = ["#!/bin/bash", 'cd "$(dirname "$0")"']
    for design, tb in pairs:
        sim = tb.replace(".sv", "").replace("tb_", "simv_")
        lines.append(f"vcs -full64 -sverilog {design} {tb} -o {sim} -quiet || true")
        lines.append(f"./{sim} || true")
    return "\n".join(lines) + "\n"


def gen_one(out_dir: Path, idx: int, k: int, rng: random.Random, hint: bool = True) -> Path:
    bugs = [fn() for fn in rng.sample(SUBTLE_BUG_TYPES, k)]
    # 991xxx pilot range: distinct from the multi-fault pilot (990xxx) and the real
    # P1 tasks (task_000001..task_001001).
    task_id = f"task_{991000 + idx:06d}"
    d = out_dir / "p1_rtl_debug" / task_id
    (d / "files").mkdir(parents=True, exist_ok=True)
    (d / "hidden").mkdir(exist_ok=True)
    (d / "solution").mkdir(exist_ok=True)

    visible, editable, forbidden = [], [], []
    pub_pairs, hid_pairs = [], []
    for j, bug in enumerate(bugs):
        (d / "files" / f"design_{j}.sv").write_text(bug["buggy"])
        (d / "solution" / f"design_{j}.sv").write_text(bug["correct"])
        (d / "files" / f"tb_public_{j}.sv").write_text(bug["tb_public"])
        (d / "hidden" / f"tb_hidden_{j}.sv").write_text(bug["tb_hidden"])
        visible += [f"design_{j}.sv", f"tb_public_{j}.sv"]
        editable.append(f"design_{j}.sv")
        forbidden += [f"tb_public_{j}.sv", f"tb_hidden_{j}.sv"]
        pub_pairs.append((f"design_{j}.sv", f"tb_public_{j}.sv"))
        hid_pairs.append((f"design_{j}.sv", f"tb_hidden_{j}.sv"))
    visible.append("run_public.sh")
    forbidden += ["run_public.sh", "run_hidden.sh"]
    (d / "files" / "run_public.sh").write_text(_run_script(pub_pairs))
    (d / "hidden" / "run_hidden.sh").write_text(_run_script(hid_pairs))

    # No-hint mode drops the per-module pointer so the model must also LOCALISE the
    # bug — the strongest cheap difficulty lever, isolated from everything else.
    if hint:
        hint_lines = "\n".join(
            f"- `design_{j}.sv` (one corner-case bug): {bugs[j]['prompt_hint']}" for j in range(k))
    else:
        hint_lines = "\n".join(f"- `design_{j}.sv` (one corner-case bug)" for j in range(k))
    (d / "prompt.md").write_text(
        f"# RTL debug — {k} independent modules\n\n"
        f"There are {k} separate Verilog modules, each in its own file with exactly one "
        f"functional bug. The bug is a *corner-case* defect: the module behaves correctly "
        f"on common inputs (and on the provided public test) but is wrong on boundary, "
        f"sign, or wrap-around inputs. Reason about those corners — the public test does "
        f"not cover them.\n\n{hint_lines}\n\n"
        f"Fix the bug in EVERY module. Return the full corrected content of each "
        f"`design_j.sv` file. Do not edit the testbenches.\n")

    meta = {
        "task_id": task_id, "track": "p1_rtl_debug", "tool": ["vcs"],
        "difficulty": "hard", "data_type": "mutation_synthetic",
        "resource_preset": "standard", "timeout_sec": 300,
        "max_tool_calls": 30, "max_patch_attempts": 8, "max_output_tokens": 32000,
        "files": {
            "visible": visible, "editable": editable,
            "hidden": [f"tb_hidden_{j}.sv" for j in range(k)] + ["run_hidden.sh"],
            "forbidden": forbidden,
        },
        "run_command": "bash run_public.sh && bash run_hidden.sh",
        "scoring": {
            "weights": {"compile": 0.1, "public_test": 0.3, "hidden_test": 0.5, "explanation": 0.1},
            "explanation_weight": 0.1,
        },
        "sanitizer": {"enabled": True},
        "generator": {"script": "prototype_p1_subtle.py", "k": k, "hinted": hint,
                      "bug_types": [b["name"] for b in bugs]},
        "version": "1.0.0",
    }
    (d / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate P1 subtle-bug pilot tasks.")
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--k", type=int, default=3, help="independent bugs per task")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="pilot_p1subtle", help="tasks-root for the pilot")
    ap.add_argument("--no-hint", dest="hint", action="store_false",
                    help="Drop per-module bug hints (model must localise the bug too)")
    ap.set_defaults(hint=True)
    args = ap.parse_args(argv)
    if args.k > len(SUBTLE_BUG_TYPES):
        raise SystemExit(f"k={args.k} > {len(SUBTLE_BUG_TYPES)} available subtle bug types")

    out = (REPO / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    rng = random.Random(args.seed)
    made = [gen_one(out, i, args.k, rng, hint=args.hint) for i in range(args.count)]
    print(f"Generated {len(made)} subtle-bug P1 tasks (k={args.k}, "
          f"{'hinted' if args.hint else 'NO-HINT'}) under {out}/p1_rtl_debug/")
    for d in made:
        meta = json.loads((d / "metadata.json").read_text())
        print(f"  {d.name}: {meta['generator']['bug_types']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
