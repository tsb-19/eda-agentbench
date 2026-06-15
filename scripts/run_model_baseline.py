#!/usr/bin/env python3
"""Grade model submissions and aggregate a model-vs-model baseline leaderboard.

Pairs with scripts/generate_model_submissions.py. Inference (LLM) already happened
there; this step only RUNS THE GRADER, so it needs no internet and can run on the
EDA host (b04). Split by track:

  * report-QA tracks (no commercial tool) -> grade locally  (`grade --only local`)
  * real-tool tracks (VCS/HSPICE/DC/PT/SpyGlass) -> grade on b04 (`grade --only tool`)

Results are written one JSON per (model, track, task) so local + b04 runs merge into
one results tree; `leaderboard` then renders the comparison.

Subcommands:
    grade       --submissions DIR [--only local|tool|all] [--results DIR]
    leaderboard --results DIR [--out reports/model_baseline_<stamp>.md]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from eda_agentbench.task.loader import TaskLoader  # noqa: E402

LOCAL_QA_TRACKS = {
    "p3_timing_report_qa",
    "p6_dc_synthesis_qa",
    "p8_pnr_report_qa",
}

TRACK_DISPLAY = {
    "p1_rtl_debug": "P1 RTL Debug",
    "p2_tb_sva_gen": "P2 Testbench/SVA Gen",
    "p3_timing_report_qa": "P3 Timing Report QA",
    "p4_spice_sim": "P4 SPICE Sim",
    "p5_spice_deck_debug": "P5 SPICE Deck Debug",
    "p6_dc_constraint_debug": "P6 DC Constraint Debug",
    "p6_dc_synthesis_qa": "P6 DC Synthesis QA",
    "p7_primetime_sta_debug": "P7 PrimeTime STA Debug",
    "p7_spyglass_lint_debug": "P7 SpyGlass Lint Debug",
    "p8_pnr_report_qa": "P8 PnR Report QA",
}


# --------------------------------------------------------------------------- #
# grade
# --------------------------------------------------------------------------- #
def _grade_one(task_path: Path, submission_dir: Path, runs_root: Path):
    """Return a result dict for one (task, submission). Never raises."""
    from eda_agentbench.cli import _evaluate_single
    from eda_agentbench.task.loader import TaskLoader as _TL, TaskValidationError

    loader = _TL(Path("."))
    try:
        meta = loader.load(task_path)
    except TaskValidationError as e:
        return {"ok": False, "total_score": 0.0, "passed": False, "error": f"load: {e}"}

    timeout = meta.get("timeout_sec", 300)
    try:
        _runs_dir, score = _evaluate_single(task_path, submission_dir, meta, timeout,
                                            runs_root=runs_root)
        return {"ok": True, "total_score": score.total_score, "passed": score.passed,
                "objective_score": score.objective_score,
                "components": [{"name": c.name, "raw": c.raw_score, "weight": c.weight}
                               for c in score.components],
                "anti_cheat": score.anti_cheat, "error": None}
    except RuntimeError as e:
        # Anti-cheat hard-fail or missing required tool.
        msg = str(e)
        return {"ok": True, "total_score": 0.0, "passed": False,
                "anti_cheat_fail": "Anti-cheat" in msg, "error": msg}
    except Exception as e:
        return {"ok": False, "total_score": 0.0, "passed": False,
                "error": f"{type(e).__name__}: {e}"}


def cmd_grade(args) -> int:
    sub_root = Path(args.submissions).resolve()
    manifest = json.loads((sub_root / "manifest.json").read_text())
    results_root = Path(args.results).resolve() if args.results \
        else sub_root.parent / "results"
    results_root.mkdir(parents=True, exist_ok=True)
    runs_root = Path(tempfile.mkdtemp(prefix="baseline_eval_"))

    n_done = n_skip = 0
    for t in manifest["tasks"]:
        track = t["track"]
        is_tool = track not in LOCAL_QA_TRACKS
        if args.only == "local" and is_tool:
            n_skip += 1
            continue
        if args.only == "tool" and not is_tool:
            n_skip += 1
            continue

        task_path = Path(t["task_path"])
        if not task_path.is_absolute():
            task_path = (REPO_ROOT / task_path).resolve()
        for model, rec in t["submissions"].items():
            sub_dir = Path(rec["submission_dir"])
            if not sub_dir.is_absolute():
                sub_dir = (REPO_ROOT / sub_dir).resolve()
            res = _grade_one(task_path, sub_dir, runs_root)
            res.update({"model": model, "track": track, "task_id": t["task_id"]})
            dest = results_root / model / track / f"{t['task_id']}.json"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(res, indent=2))
            flag = "PASS" if res.get("passed") else f"{res.get('total_score', 0):.2f}"
            print(f"  [{model}] {track}/{t['task_id']}: {flag}"
                  + (f"  ({res['error']})" if res.get("error") else ""))
            n_done += 1

    print(f"\nGraded {n_done} (model,task) pairs; skipped {n_skip}. Results -> {results_root}")
    return 0


# --------------------------------------------------------------------------- #
# leaderboard
# --------------------------------------------------------------------------- #
def _load_results(results_root: Path) -> list[dict]:
    out = []
    for p in results_root.rglob("*.json"):
        try:
            out.append(json.loads(p.read_text()))
        except json.JSONDecodeError:
            continue
    return out


def cmd_leaderboard(args) -> int:
    results_root = Path(args.results).resolve()
    rows = _load_results(results_root)
    if not rows:
        raise SystemExit(f"No result JSONs under {results_root}")

    models = sorted({r["model"] for r in rows})
    tracks = sorted({r["track"] for r in rows})

    # agg[(model, track)] -> [scores], pass count
    scores: dict[tuple, list] = defaultdict(list)
    passes: dict[tuple, int] = defaultdict(int)
    for r in rows:
        k = (r["model"], r["track"])
        scores[k].append(float(r.get("total_score", 0.0)))
        passes[k] += 1 if r.get("passed") else 0

    def avg(lst):
        return sum(lst) / len(lst) if lst else 0.0

    stamp = args.stamp or "latest"
    out_md = Path(args.out) if args.out else REPORTS_DIR / f"model_baseline_{stamp}.md"
    out_csv = out_md.with_suffix(".csv")
    out_md.parent.mkdir(parents=True, exist_ok=True)

    # CSV: one row per (model, track)
    with out_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "track", "tasks", "avg_score", "pass_rate"])
        for m in models:
            for tr in tracks:
                k = (m, tr)
                if k in scores:
                    w.writerow([m, tr, len(scores[k]),
                                f"{avg(scores[k]):.4f}",
                                f"{passes[k] / len(scores[k]):.4f}"])

    # MD: comparison table (avg_score) with tracks as rows, models as columns
    lines = [f"# EDA-AgentBench — Model Baseline ({stamp})", "",
             f"**Models:** {', '.join(models)}  ",
             f"**Tracks:** {len(tracks)}  ",
             "**Mode:** single-shot submission (no tool-feedback iteration)  ",
             "**Score:** mean total_score in [0,1]; PASS = total_score >= 0.5", "",
             "## Average score by track", "",
             "| Track | " + " | ".join(models) + " | spread |",
             "|---|" + "---|" * (len(models) + 1)]
    overall: dict[str, list] = defaultdict(list)
    for tr in tracks:
        cells = []
        vals = []
        for m in models:
            k = (m, tr)
            if k in scores:
                a = avg(scores[k])
                cells.append(f"{a:.2f}")
                vals.append(a)
                overall[m].append(a)
            else:
                cells.append("—")
        spread = f"{max(vals) - min(vals):.2f}" if len(vals) > 1 else "—"
        lines.append(f"| {TRACK_DISPLAY.get(tr, tr)} | " + " | ".join(cells) + f" | {spread} |")
    # overall mean across tracks (macro)
    macro = [f"{avg(overall[m]):.2f}" if overall[m] else "—" for m in models]
    lines.append(f"| **Macro avg** | " + " | ".join(macro) + " | |")

    lines += ["", "## Pass rate by track", "",
              "| Track | " + " | ".join(models) + " |",
              "|---|" + "---|" * len(models)]
    for tr in tracks:
        cells = []
        for m in models:
            k = (m, tr)
            cells.append(f"{passes[k] / len(scores[k]):.0%}" if k in scores else "—")
        lines.append(f"| {TRACK_DISPLAY.get(tr, tr)} | " + " | ".join(cells) + " |")

    # discrimination hint: tracks with the widest model spread
    lines += ["", "## Most discriminating tracks (widest avg-score spread)", ""]
    spreads = []
    for tr in tracks:
        vals = [avg(scores[(m, tr)]) for m in models if (m, tr) in scores]
        if len(vals) > 1:
            spreads.append((max(vals) - min(vals), tr))
    for sp, tr in sorted(spreads, reverse=True)[:5]:
        lines.append(f"- {TRACK_DISPLAY.get(tr, tr)}: spread {sp:.2f}")

    errs = [r for r in rows if r.get("error")]
    if errs:
        lines += ["", "## Errors / parse failures", "",
                  f"{len(errs)} graded with errors (recorded as scored, often 0):"]
        for r in errs[:20]:
            lines.append(f"- [{r['model']}] {r['track']}/{r['task_id']}: {r['error']}")

    out_md.write_text("\n".join(lines) + "\n")
    print(f"Wrote {out_md}\nWrote {out_csv}")
    return 0


REPORTS_DIR = REPO_ROOT / "reports"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Grade + aggregate model baseline.")
    sub = ap.add_subparsers(dest="command", required=True)

    g = sub.add_parser("grade", help="Grade submissions into a results tree")
    g.add_argument("--submissions", required=True, help="Submissions dir (has manifest.json)")
    g.add_argument("--only", choices=["local", "tool", "all"], default="all",
                   help="local = report-QA tracks; tool = real-tool tracks (b04)")
    g.add_argument("--results", default=None, help="Results output dir")

    lb = sub.add_parser("leaderboard", help="Render comparison from a results tree")
    lb.add_argument("--results", required=True)
    lb.add_argument("--out", default=None, help="Output .md path")
    lb.add_argument("--stamp", default=None, help="Label used in the report title/filename")

    args = ap.parse_args(argv)
    if args.command == "grade":
        return cmd_grade(args)
    if args.command == "leaderboard":
        return cmd_leaderboard(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
