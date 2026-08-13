#!/usr/bin/env python3
"""Study I (workflow-handoff) episode ledger for the manuscript — principled inclusion rule.

No paid calls. Re-derives every cell from the frozen per-episode records and the frozen phase
reports, under an inclusion rule that is stated here and *mechanically enforced* against the
frozen program manifest.

INCLUSION RULE
--------------
The ledger universe is every paid, gradeable workflow episode in two declared parts:

  1. the **program-primary** episodes of the workflow-handoff clarity-bundle ablation program
     (Phases 4W / 4X / 4Y and the C24 bridge) as declared by the frozen phase manifests --- 58
     episodes, whose only omissions are the ones a frozen manifest marks ``excluded``,
     ``invalid`` or ``aborted`` (3 / 0 / 1);
  2. the **12 earlier controlled-pair** episodes (Phase-4U/4V1/4V2), which are paid and gradeable
     but predate the phase-matrix accounting and are counted in no row of it --- neither in its
     58-episode primary total nor in its 682.25 CNY cost ledger.

This descriptive ledger (70) is therefore deliberately broader than the 58-episode program-primary
accounting the manuscript reports in its reproducibility statement; the two numbers are different
quantities and both are stated as such. A cell is keyed by (stage, condition, model, task) ---
repeat measurements of the same condition in different run windows stay distinct rows and are
**never** deduplicated.

Two consequences worth stating, because both differ from the earlier Phase-4Z aggregation:
  * Phase-4X Stage-1 (the position-confounded cross-model arm) is *included*. Its treatment
    contrast is not directionally interpretable — the frozen report says so and the manuscript
    repeats it — but its episodes are valid paid primary measurements and belong in a failure
    taxonomy. Interpretability of a contrast is not a membership criterion.
  * Phase-4W Run-1 (the C6 ablation, V1/V9) is *included*. It has no preserved per-episode
    directory, so its submitted tuples are read from its frozen report JSON.

This supersedes, for manuscript purposes, the ``Table 2`` aggregation in
``scripts/phase4z_figures_tables.py``. That script keys cells by ``(label, model)`` in a dict, so
a condition measured in two run windows silently overwrites itself; the surviving set was an
artifact of dict ordering rather than a declared sampling frame. That script is left untouched as
the historical Phase-4Z deliverable.

Usage:  python3 scripts/phase7c_study1_ledger.py [--check]
        --check  recompute and diff against the committed JSON; non-zero exit on drift.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_JSON = REPO / "reports/synthetic_p14_study1_ledger.json"
OUT_TEX = REPO / "submission/tables/study1_ledger.tex"
FREEZE = REPO / "reports/synthetic_p14_phase4z_freeze_manifest.json"

SCENARIO_AXIS = {"slow", "typ", "fast"}
CORNER_AXIS = {"func", "test", "lowpower"}
TASK_GOLDEN = {"0011": ("typ", "test"), "0017": ("typ", "test")}
DEV_GOLDEN = ("slow", "func")
GOLDEN_NETLIST = "netlist_v2.v"

# Episodes a frozen manifest marks as non-primary, by preserved-directory name.
EXCLUDED_TRIALS = {
    # 4X Stage-1 diagnostic extra; frozen report scope: "6 primary slots + excluded extra
    # episode (diagnostics)". The manifest's primary=6 vs ledger=7 discrepancy is disclosed.
    "Base_ep2_extra_a2",
}

# (stage, evidence dir, trial prefix, task, model, condition label)
LEDGER_CELLS = [
    ("4W-Run2", "p14_phase4w_run2_episodes", "BundleS", "0015", "Qwen", "BundleS"),
    ("4W-Run2", "p14_phase4w_run2_episodes", "BundleD", "0016", "Qwen", "BundleD"),
    ("4W-Held", "p14_phase4w_heldout_episodes", "Base", "0011", "Qwen", "Base(0011)"),
    ("4W-Held", "p14_phase4w_heldout_episodes", "Held", "0017", "Qwen", "Held(0017)"),
    ("4X-S1", "p14_phase4x_dev_episodes", "Base", "0009", "DeepSeek", "Base(0009)"),
    ("4X-S1", "p14_phase4x_dev_episodes", "BundleS", "0015", "DeepSeek", "BundleS"),
    ("4X-S1C", "p14_phase4x_stage1c_episodes", "Base", "0009", "DeepSeek", "Base(0009)"),
    ("4X-S1C", "p14_phase4x_stage1c_episodes", "BundleS", "0015", "DeepSeek", "BundleS"),
    ("4Y-S1", "p14_phase4y_episodes", "Schema", "0018", "Qwen", "Schema"),
    ("4Y-S1", "p14_phase4y_episodes", "Contract", "0019", "Qwen", "Contract"),
    ("4Y-S2", "p14_phase4y2_episodes", "C1", "0020", "Qwen", "C1"),
    ("4Y-S2", "p14_phase4y2_episodes", "C24", "0021", "Qwen", "C24"),
    ("4Y-S3", "p14_phase4y3_episodes", "C2", "0022", "Qwen", "C2"),
    ("4Y-S3", "p14_phase4y3_episodes", "C4", "0023", "Qwen", "C4"),
    ("4Y-Bridge", "p14_phase4y3_c24_bridge_episodes", "C24", "0021", "Qwen", "C24"),
]

STAGE_ORDER = ["4V-pair", "4W-Run1", "4W-Run2", "4W-Held",
               "4X-S1", "4X-S1C", "4Y-S1", "4Y-S2", "4Y-S3", "4Y-Bridge"]

STAGE_TEX = {
    "4V-pair": "controlled pair", "4W-Run1": "C6 ablation", "4W-Run2": "screening",
    "4W-Held": "held-out", "4X-S1": "cross-model 1", "4X-S1C": "cross-model 1C",
    "4Y-S1": "decomp.\\ 1", "4Y-S2": "decomp.\\ 2", "4Y-S3": "decomp.\\ 3",
    "4Y-Bridge": "C24 bridge",
}


def classify(scenario, corner, netlist, golden):
    """Typed-binding verdict for one submitted package. Mirrors the frozen grader's taxonomy."""
    if (scenario, corner) == golden:
        return "correct" if netlist == GOLDEN_NETLIST else "value"
    if scenario not in SCENARIO_AXIS or corner not in CORNER_AXIS:
        return "axis"
    return "value"


def _blank():
    return {"k": 0, "correct": 0, "axis": 0, "value": 0}


def _tally(cell, verdict):
    cell["k"] += 1
    cell[verdict] += 1


def collect():
    """Return OrderedDict[(stage, condition, model, task)] -> counts, in STAGE_ORDER."""
    cells = OrderedDict()

    def cell_for(stage, cond, model, task):
        return cells.setdefault((stage, cond, model, task), _blank())

    # 1. Preserved per-episode ledgers (submitted flow_config is the authoritative artifact).
    for stage, ldir, prefix, task, model, cond in LEDGER_CELLS:
        golden = TASK_GOLDEN.get(task, DEV_GOLDEN)
        cell = cell_for(stage, cond, model, task)
        root = REPO / "reports/evidence" / ldir
        for trial in sorted(p for p in root.iterdir() if p.is_dir()):
            if not trial.name.startswith(prefix + "_") or trial.name in EXCLUDED_TRIALS:
                continue
            sub = json.loads((trial / "flow_config.submitted.json").read_text())
            _tally(cell, classify(sub.get("scenario"), sub.get("corner"),
                                  sub.get("netlist"), golden))

    # 2. Phase-4W Run-1 (C6 ablation): no preserved episode dir; tuples from the frozen report.
    run1 = json.loads((REPO / "reports/synthetic_p14_phase4w_run1.json").read_text())
    for ep in run1["episodes"]:
        netlist, scenario, corner = (x.strip() for x in ep["submitted"].split("/"))
        task = ep["task"][-4:]
        cell = cell_for("4W-Run1", ep["variant"], "Qwen", task)
        _tally(cell, classify(scenario, corner, netlist, TASK_GOLDEN.get(task, DEV_GOLDEN)))

    # 3. Controlled pair: frozen 2x2 matrix reports per-cell verdict counts directly.
    matrix = json.loads((REPO / "reports/synthetic_p14_balanced_controlled_pair.json")
                        .read_text())["matrix_2x2_k3"]
    for key, m in matrix.items():
        model, task = key.split("_")
        cond = ("Base" if task == "0009" else "Full bundle") + f"({task})"
        cell = cell_for("4V-pair", cond, model, task)
        cell["k"] = m["k"]
        cell["correct"] = m["pass"]
        cell["axis"] = m["wrong_axis_fails"]
        cell["value"] = m["k"] - m["pass"] - m["wrong_axis_fails"]

    return OrderedDict(sorted(cells.items(), key=lambda kv: (STAGE_ORDER.index(kv[0][0]),
                                                             kv[0][2], kv[0][1])))


def enforce_inclusion_rule(cells):
    """Assert the derived per-stage episode counts equal the frozen manifest's declared primary."""
    declared = {p["phase"]: p for p in json.loads(FREEZE.read_text())["phase_matrix"]}
    derived = Counter()
    for (stage, _c, _m, _t), cell in cells.items():
        derived[stage] += cell["k"]

    problems = []
    for stage, count in derived.items():
        if stage == "4V-pair":  # Phase-4V predates the 4W-4Y program manifest; checked below.
            continue
        want = declared.get(stage, {}).get("primary")
        if want is None:
            problems.append(f"{stage}: no declared primary count in the frozen manifest")
        elif want != count:
            problems.append(f"{stage}: derived {count} != declared primary {want}")
    for stage, p in declared.items():
        if p["primary"] and stage not in derived:
            problems.append(f"{stage}: declared primary {p['primary']} but no derived episodes")

    program = sum(v for s, v in derived.items() if s != "4V-pair")
    want_program = json.loads(FREEZE.read_text())["program_totals"]["primary"]
    if program != want_program:
        problems.append(f"program total: derived {program} != declared primary {want_program}")

    pair = derived.get("4V-pair", 0)
    if pair != 12:
        problems.append(f"controlled pair: derived {pair} != 12 (2 models x 2 conditions x k=3)")

    if problems:
        raise SystemExit("INCLUSION-RULE VIOLATION:\n  " + "\n  ".join(problems))
    return {"program_primary": program, "controlled_pair": pair, "total": program + pair}


def latex_table(cells):
    """Complete tabular. Emitted whole because \\input inside an alignment breaks \\midrule."""
    lines = [r"\begin{tabular}{l l l c c c}", r"\toprule",
             r"stage & condition (task) & model & correct$/k$ & axis & value \\", r"\midrule"]
    prev, agg = None, Counter()
    for (stage, cond, model, task), c in cells.items():
        if prev is not None and stage != prev:
            lines.append(r"\midrule")
        label = STAGE_TEX[stage] if stage != prev else ""
        prev = stage
        agg.update(c)
        name = cond if cond.endswith(f"({task})") else f"{cond} ({task})"
        lines.append(f"{label} & {name} & {model} & {c['correct']}/{c['k']} & "
                     f"{c['axis']} & {c['value']} \\\\")
    lines += [r"\midrule",
              f"\\textbf{{total}} & & & \\textbf{{{agg['correct']}/{agg['k']}}} & "
              f"\\textbf{{{agg['axis']}}} & \\textbf{{{agg['value']}}} \\\\",
              r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="recompute and diff against the committed JSON; non-zero exit on drift")
    args = ap.parse_args()

    cells = collect()
    totals = enforce_inclusion_rule(cells)
    agg = Counter()
    for c in cells.values():
        agg.update(c)

    payload = {
        "schema": "p14_study1_ledger/v1",
        "inclusion_rule": (
            "Every paid, gradeable workflow episode in two declared parts: (1) the "
            "program-primary episodes of the clarity-bundle ablation program as declared by "
            "the frozen phase manifests (58), omitting only what those manifests mark "
            "excluded/invalid/aborted (3/0/1); plus (2) the 12 earlier controlled-pair "
            "episodes (Phase-4U/4V1/4V2), which are paid and gradeable but predate the "
            "phase-matrix accounting and appear in neither its 58-episode primary total nor "
            "its 682.25 CNY cost ledger. Total 70. Cells are keyed by "
            "(stage, condition, model, task); repeat measurements of the same condition in "
            "different run windows are distinct rows and are never deduplicated."
        ),
        "frozen_manifest": "reports/synthetic_p14_phase4z_freeze_manifest.json",
        "supersedes": ("Table 2 of scripts/phase4z_figures_tables.py, whose (label, model) dict "
                       "key silently collapsed repeat measurements"),
        "totals": {"episodes": agg["k"], "correct": agg["correct"],
                   "axis_binding_failure": agg["axis"],
                   "role_conditioned_value_selection_failure": agg["value"],
                   "cells": len(cells), **totals},
        "cells": [{"stage": s, "condition": c, "model": m, "task": t, **v}
                  for (s, c, m, t), v in cells.items()],
    }

    if args.check:
        if not OUT_JSON.is_file():
            print(f"MISSING {OUT_JSON}", file=sys.stderr)
            return 1
        old = json.loads(OUT_JSON.read_text())
        if old != payload:
            print("LEDGER DRIFT: recomputed ledger differs from the committed JSON",
                  file=sys.stderr)
            return 1
        print(json.dumps({"ok": True, **payload["totals"]}, indent=2))
        return 0

    OUT_JSON.write_text(json.dumps(payload, indent=1) + "\n")
    OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
    OUT_TEX.write_text(latex_table(cells) + "\n")
    print(json.dumps({"ok": True, "json": str(OUT_JSON.relative_to(REPO)),
                      "tex": str(OUT_TEX.relative_to(REPO)), **payload["totals"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
