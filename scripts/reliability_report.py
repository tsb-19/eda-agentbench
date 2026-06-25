#!/usr/bin/env python3
"""Aggregate graded result trees into a reliability/calibration leaderboard.

Each results tree is ONE trial pass (layout: <tree>/<model>/<track>/<task>.json, the dicts written
by run_model_baseline._grade_one, which now carry a `reliability` block). Pass K trees (produced by
running generate+grade K times) to get K trials per (model, task); the report computes pass@1,
pass@k, pass^k (all-of-k), run-to-run variance, calibration (overconfident-wrong, trust), format
compliance, and a protocol-failure tally — the instruments for the 2026-06-24 reliability pivot.

  python scripts/reliability_report.py runs/relA/results runs/relB/results ... \
      [--md out.md] [--json out.json] [--track p3_timing_report_qa]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from eda_agentbench import reliability as R  # noqa: E402


def trial_from_result(res: dict, model: str, task: str, track: str) -> dict:
    """Map one graded result dict -> canonical reliability trial record."""
    rel = res.get("reliability") or {}
    conf = rel.get("confidence_decision", "")
    proto = rel.get("protocol_status", "ok")
    if proto == "ok" and not res.get("ok", True):     # grading failed without a protocol signal
        proto = R.EMPTY
    outcome = R.outcome_from(res.get("passed"), proto, conf)
    cost = res.get("cost") or {}
    return {"model": model, "task": task, "track": track, "outcome": outcome,
            "confidence": conf, "format_ok": bool(rel.get("confidence_format_ok")),
            # secondary cost signals (agentic results carry a `cost` block; absent for QA -> 0)
            "tokens": (cost.get("tokens_in") or 0) + (cost.get("tokens_out") or 0),
            "tool_calls": cost.get("tool_calls"), "latency": cost.get("wall_time_sec"),
            "retries": cost.get("retries")}


def load_trees(trees: list[Path], track_filter: str | None) -> dict[str, list[dict]]:
    """Return {model: [trial, ...]} across all trees (each tree contributes one trial per task)."""
    by_model: dict[str, list[dict]] = {}
    for tree in trees:
        for jp in sorted(tree.glob("*/*/*.json")):
            if jp.name.endswith(".agentlog.json"):    # agentic driver sidecar, not a graded result
                continue
            track = jp.parent.name
            if track_filter and track != track_filter:
                continue
            model = jp.parent.parent.name
            try:
                res = json.loads(jp.read_text())
            except Exception:
                continue
            by_model.setdefault(model, []).append(
                trial_from_result(res, model, jp.stem, track))
    return by_model


_COLS = [("pass@1", "pass1"), ("pass@k", "passk_any"), ("pass^k", "passk_all"),
         ("gap", "reliability_gap"), ("flip", "flip_rate"), ("overconf", "overconf_rate"),
         ("fmt", "format_compliance"), ("abst", "abstain_rate"), ("trust", "trust")]
# secondary cost columns (rendered with their own formatting, not the .2f used for rates)
_COST = [("tok", "mean_tokens"), ("tools", "mean_tool_calls"),
         ("retry", "mean_retries"), ("wall_s", "mean_latency")]


def render_md(rows: dict[str, dict], n_trees: int) -> str:
    out = [f"# Reliability / Calibration leaderboard ({n_trees} trial pass(es))", "",
           "Sorted by trust (reward confident-correct, penalize overconfident-wrong). "
           "`gap`=pass@1−pass^k (capable-but-inconsistent); `overconf`=P(fail | confident); "
           "`fmt`=output-contract compliance. Cost columns (`tok`/`tools`/`retry`/`wall_s`) are "
           "secondary. Infra failures (429/empty) are excluded from capability and shown in "
           "`protocol`.", "",
           "| model | " + " | ".join(c[0] for c in _COLS)
           + " | " + " | ".join(c[0] for c in _COST) + " | n_overconf | protocol |",
           "|" + "---|" * (len(_COLS) + len(_COST) + 3)]
    for m in sorted(rows, key=lambda k: rows[k]["trust"], reverse=True):
        r = rows[m]
        cells = " | ".join(f"{r[k]:.2f}" for _, k in _COLS)
        cost = " | ".join(_fmt_cost(k, r.get(k, 0.0)) for _, k in _COST)
        proto = ",".join(f"{k}:{v}" for k, v in sorted(r["protocol"].items()) if k != R.PASS)
        out.append(f"| {m} | {cells} | {cost} | {r['n_overconf_wrong']} | {proto or '-'} |")
    return "\n".join(out) + "\n"


def _fmt_cost(key: str, v: float) -> str:
    if key == "mean_tokens":
        return f"{v / 1000:.1f}k"
    return f"{v:.1f}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("results", nargs="+", help="One or more results trees (one per trial pass)")
    ap.add_argument("--track", default=None, help="Restrict to a single track")
    ap.add_argument("--md", default=None)
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)

    trees = [Path(p).resolve() for p in args.results]
    by_model = load_trees(trees, args.track)
    if not by_model:
        print("no results found", file=sys.stderr)
        return 1
    rows = {m: R.per_model(ts) for m, ts in by_model.items()}

    md = render_md(rows, len(trees))
    print(md)
    if args.md:
        Path(args.md).write_text(md)
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
