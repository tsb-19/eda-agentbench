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
    # (task_id, seed, evidence_steps, hazard_type, variant)
    ("workflow_handoff_0001", 0, 1, None, None),
    ("workflow_handoff_0002", 0, 2, None, None),
    ("workflow_handoff_0003", 0, 2, "cross_source_conflict", None),            # p14 v2 hazard preset
    ("workflow_handoff_0004", 0, 2, "scenario_corner_cross_source_conflict", None),  # p14 v3
    ("workflow_handoff_0005", 0, 2, "multi_conflict_partially_truthful_decoy", None),  # p14 v4
    ("workflow_handoff_0006", 0, 2, "constraint_graph_multi_source_recovery", None),  # p14 v5
    ("workflow_handoff_0007", 0, 2, "axis_binding_value_invention", None),     # p14 v6
    ("workflow_handoff_0008", 0, 2, "implicit_axis_binding", None),            # p14 v7
    # p14 v8: semantic-role-binding REPRODUCTION (controlled pair). ONE hazard_type, TWO variants passed
    # explicitly (the schema requires numeric task_ids workflow_handoff_[0-9]{4}, so the variant is NOT
    # encoded in the id). workflow_handoff_0009 = ambiguous (reproduce 0006); workflow_handoff_0010 =
    # clear_control (negative control). Both share the identical hidden truth + byte-identical grader; they
    # differ only in the visible clarity bundle (report-label semantics + inference anchors). This is a
    # task-construction + acceptance phase, NOT a model probe.
    ("workflow_handoff_0009", 0, 2, "semantic_role_binding_reproduction", "ambiguous"),       # reproduce 0006
    ("workflow_handoff_0010", 0, 2, "semantic_role_binding_reproduction", "clear_control"),   # negative control
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
    for task_id, seed, steps, hazard, variant in TASKS:
        if only and task_id not in only:
            continue
        td = build_task_skeleton(out, task_id, seed, steps, hazard_type=hazard, variant=variant)
        print(f"built {task_id} (evidence_steps={steps}, hazard={hazard}, variant={variant}) -> {td}")
        if a.bake:
            bake_golden(td, a.pt_cmd, steps)
            print(f"  baked golden evidence for {task_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
