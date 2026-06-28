#!/usr/bin/env python3
"""Batch driver for the p14 workflow-handoff generator (Phase-4B: exactly two tasks).

Generates the skeleton(s) into tasks/p14_workflow_handoff/ and, with --bake, runs the evidence chain
on the golden inputs (via pt_shell / the b04 shim) to fill solution/ with real golden evidence. Then,
with --accept, runs the acceptance-filter matrix on real PrimeTime for each task.

This is intentionally tiny: it builds workflow_handoff_0001 (evidence_steps=1, p13-reproduction
baseline) and workflow_handoff_0002 (evidence_steps=2, cross-stage digest chain). It does NOT generate
more than two tasks.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from generators.p14_workflow_handoff_gen import build_task_skeleton, bake_golden  # noqa: E402

TASKS = [
    # (task_id, seed, evidence_steps, hazard_type)
    ("workflow_handoff_0001", 0, 1, None),
    ("workflow_handoff_0002", 0, 2, None),
    ("workflow_handoff_0003", 0, 2, "cross_source_conflict"),   # p14 v2 hazard preset
    ("workflow_handoff_0004", 0, 2, "scenario_corner_cross_source_conflict"),  # p14 v3 hazard preset
]


def main() -> int:
    ap = argparse.ArgumentParser(description="generate the p14 workflow handoff tasks")
    ap.add_argument("--out", default=str(REPO / "tasks" / "p14_workflow_handoff"))
    ap.add_argument("--bake", action="store_true", help="run the chain to bake golden evidence (needs pt)")
    ap.add_argument("--pt-cmd", default=os.environ.get("EDA_PT_CMD", "pt_shell"))
    ap.add_argument("--only", default="", help="comma-separated task_ids to build (default: all)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    only = set(x for x in a.only.split(",") if x)
    for task_id, seed, steps, hazard in TASKS:
        if only and task_id not in only:
            continue
        td = build_task_skeleton(out, task_id, seed, steps, hazard_type=hazard)
        print(f"built {task_id} (evidence_steps={steps}, hazard={hazard}) -> {td}")
        if a.bake:
            bake_golden(td, a.pt_cmd, steps)
            print(f"  baked golden evidence for {task_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
