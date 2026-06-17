#!/usr/bin/env python3
"""Prototype: P1 multi-fault hardening pilot.

Bundles K independent buggy modules into one P1 task (each in its own
design_j.sv + testbench, compiled/simulated separately by the run scripts). The
model must fix ALL K. The existing VCSRTLEvaluator already scores fractionally
(pass/total over the PASS:/FAIL: lines), so a model that fixes M of K lands
partway → score spreads. No evaluator change; reuses the 10 BUG_TYPES as-is.

Isolates the single lever (1 bug -> K bugs): per-module prompt hints are kept,
matching the original single-bug prompt style, so any drop in score is due to
multi-fault difficulty, not removed hints.

    python3 scripts/prototype_p1_multifault.py --count 10 --k 3 --out pilot_p1mf
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from generators.p1_rtl_debug_gen import BUG_TYPES  # noqa: E402


def _run_script(pairs: list[tuple[str, str]]) -> str:
    """A run script that compiles+sims each (design, tb) pair, never aborting on
    one module's failure so every module contributes its PASS:/FAIL: lines."""
    lines = ["#!/bin/bash", 'cd "$(dirname "$0")"']
    for j, (design, tb) in enumerate(pairs):
        sim = tb.replace(".sv", "").replace("tb_", "simv_")
        lines.append(f"vcs -full64 -sverilog {design} {tb} -o {sim} -quiet || true")
        lines.append(f"./{sim} || true")
    return "\n".join(lines) + "\n"


def gen_one(out_dir: Path, idx: int, k: int, rng: random.Random) -> Path:
    bugs = [fn() for fn in rng.sample(BUG_TYPES, k)]
    # task_id must match the schema pattern ^task_[0-9]{6}$; use a 99xxxx pilot range
    # that can't collide with the real P1 tasks (task_000001..task_001001).
    task_id = f"task_{990000 + idx:06d}"
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

    hint_lines = "\n".join(
        f"- `design_{j}.sv` (module has one bug): {bugs[j]['prompt_hint']}" for j in range(k))
    (d / "prompt.md").write_text(
        f"# RTL debug — {k} independent modules\n\n"
        f"There are {k} separate Verilog modules, each in its own file with exactly one "
        f"functional bug:\n\n{hint_lines}\n\n"
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
        "generator": {"script": "prototype_p1_multifault.py", "k": k,
                      "bug_types": [b["name"] for b in bugs]},
        "version": "1.0.0",
    }
    (d / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate P1 multi-fault pilot tasks.")
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--k", type=int, default=3, help="independent bugs per task")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="pilot_p1mf", help="tasks-root for the pilot")
    args = ap.parse_args(argv)
    if args.k > len(BUG_TYPES):
        raise SystemExit(f"k={args.k} > {len(BUG_TYPES)} available bug types")

    out = (REPO / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    rng = random.Random(args.seed)
    made = [gen_one(out, i, args.k, rng) for i in range(args.count)]
    print(f"Generated {len(made)} multi-fault P1 tasks (k={args.k}) under {out}/p1_rtl_debug/")
    for d in made:
        meta = json.loads((d / "metadata.json").read_text())
        print(f"  {d.name}: {meta['generator']['bug_types']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
