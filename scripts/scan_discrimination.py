#!/usr/bin/env python3
"""Tier-2 discrimination scan: a no-golden health check over a results tree.

Where validate_dataset.py uses goldens to find *broken* tasks, this uses a model
run itself as the probe to find *useless* tasks — ones that give no signal about
model ability. It needs no EDA tools (just reads the scored JSON), so it runs
anywhere and is the dashboard for "is the benchmark hard enough / discriminating
enough?".

Per task (across the N models that were run) it computes mean, spread, std and
flags:
  saturated      all models scored ~1.0  -> too easy, zero discrimination
  dead           all models scored <0.5  -> too hard / broken
  discriminating spread >= --spread       -> separates models (the useful tasks)
Per track + per labeled-difficulty it aggregates saturation/discrimination, and
contrasts the generator's difficulty LABEL with empirical difficulty (1 - mean).

    python3 scripts/run_model_baseline.py ... grade   # produce a results tree
    python3 scripts/scan_discrimination.py \
        --results runs/baseline/<stamp>/results \
        --manifest runs/baseline/<stamp>/submissions/manifest.json \
        --md reports/discrimination_<stamp>.md
"""
from __future__ import annotations

import argparse
import glob
import json
import statistics
from collections import defaultdict
from pathlib import Path

PERFECT = 0.999
FAIL = 0.5


# --------------------------------------------------------------------------- #
# Pure stats (unit-tested without any results tree)
# --------------------------------------------------------------------------- #
def task_stats(scores: list[float], *, spread_thresh: float = 0.1) -> dict:
    """Across-model stats for one task's total_scores."""
    n = len(scores)
    mean = statistics.mean(scores)
    lo, hi = min(scores), max(scores)
    spread = hi - lo
    n_perfect = sum(1 for v in scores if v >= PERFECT)
    return {
        "n": n, "mean": mean, "min": lo, "max": hi, "spread": spread,
        "std": statistics.pstdev(scores) if n > 1 else 0.0,
        "n_perfect": n_perfect,
        "emp_difficulty": 1.0 - mean,
        "saturated": n_perfect == n,                 # everyone aced it
        "dead": hi < FAIL,                           # nobody passed
        "discriminating": spread >= spread_thresh,   # separates models
    }


def classify(s: dict) -> str:
    if s["saturated"]:
        return "saturated"
    if s["dead"]:
        return "dead"
    if s["discriminating"]:
        return "discriminating"
    return "weak"


# --------------------------------------------------------------------------- #
# Load
# --------------------------------------------------------------------------- #
def load_results(results_root: Path):
    """task_id -> {model: total_score}; plus task_id -> track."""
    scores: dict[str, dict[str, float]] = defaultdict(dict)
    track_of: dict[str, str] = {}
    for f in glob.glob(str(results_root / "*" / "*" / "*.json")):
        d = json.loads(Path(f).read_text())
        tid = d.get("task_id") or Path(f).stem
        scores[tid][d.get("model", Path(f).parts[-3])] = float(d.get("total_score", 0.0))
        track_of[tid] = d.get("track", Path(f).parts[-2])
    return scores, track_of


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def build_rows(scores, track_of, diff_of, spread_thresh):
    rows = []
    for tid, ms in scores.items():
        s = task_stats(list(ms.values()), spread_thresh=spread_thresh)
        s.update({"task_id": tid, "track": track_of.get(tid, "?"),
                  "difficulty": diff_of.get(tid, "?"), "klass": classify(s),
                  "scores": ms})
        rows.append(s)
    return rows


def render(rows, top: int) -> str:
    out = []
    n = len(rows)
    allv = [v for r in rows for v in r["scores"].values()]
    nmodels = max((r["n"] for r in rows), default=0)
    sat = [r for r in rows if r["saturated"]]
    disc = [r for r in rows if r["discriminating"]]
    dead = [r for r in rows if r["dead"]]

    def pct(x):
        return f"{x/len(allv):.0%}" if allv else "-"

    out.append(f"# Discrimination scan ({n} tasks, {nmodels} models, {len(allv)} pairs)\n")
    out.append("## Overall")
    out.append(f"- perfect pairs (==1.0): {sum(1 for v in allv if v>=PERFECT)}/{len(allv)} = {pct(sum(1 for v in allv if v>=PERFECT))}")
    out.append(f"- pairs >= 0.9: {pct(sum(1 for v in allv if v>=0.9))}   |   pairs < 0.5 (fail): {pct(sum(1 for v in allv if v<FAIL))}")
    out.append(f"- **saturated tasks (all models 1.0, zero signal): {len(sat)}/{n} = {len(sat)/n:.0%}**")
    out.append(f"- discriminating (spread >= 0.1): {len(disc)}/{n} = {len(disc)/n:.0%}   |   dead (all <0.5): {len(dead)}/{n}\n")

    # per track
    out.append("## By track")
    out.append("| track | tasks | saturated | discriminating | mean | mean spread |")
    out.append("|---|---|---|---|---|---|")
    bt = defaultdict(list)
    for r in rows:
        bt[r["track"]].append(r)
    for tr in sorted(bt):
        rs = bt[tr]
        ns = sum(1 for r in rs if r["saturated"])
        nd = sum(1 for r in rs if r["discriminating"])
        mean = statistics.mean(r["mean"] for r in rs)
        msp = statistics.mean(r["spread"] for r in rs)
        flag = " ⚠️ fully saturated" if ns == len(rs) else ""
        out.append(f"| {tr} | {len(rs)} | {ns}/{len(rs)}{flag} | {nd}/{len(rs)} | {mean:.2f} | {msp:.2f} |")
    out.append("")

    # difficulty-label calibration
    bd = defaultdict(list)
    for r in rows:
        bd[r["difficulty"]].append(r)
    if len(bd) > 1:
        out.append("## Difficulty label vs empirical (label is trustworthy only if empirical difficulty rises easy→hard)")
        out.append("| label | tasks | saturated | mean score | empirical difficulty (1-mean) |")
        out.append("|---|---|---|---|---|")
        for df in sorted(bd):
            rs = bd[df]
            ns = sum(1 for r in rs if r["saturated"])
            mean = statistics.mean(r["mean"] for r in rs)
            out.append(f"| {df} | {len(rs)} | {ns}/{len(rs)} ({ns/len(rs):.0%}) | {mean:.2f} | {1-mean:.2f} |")
        out.append("")

    # worst (saturated) and best (highest spread)
    out.append(f"## Most useless (saturated) — up to {top}")
    for r in sorted(sat, key=lambda r: r["track"])[:top]:
        out.append(f"- {r['track']}/{r['task_id']} (label={r['difficulty']})")
    out.append(f"\n## Best discriminators (highest spread) — up to {top}")
    for r in sorted(rows, key=lambda r: -r["spread"])[:top]:
        if r["spread"] <= 0:
            break
        out.append(f"- {r['track']}/{r['task_id']}  spread={r['spread']:.2f} mean={r['mean']:.2f} (label={r['difficulty']})")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Tier-2 no-golden discrimination scan over a results tree.")
    ap.add_argument("--results", required=True, help="Results root (…/<model>/<track>/<task>.json)")
    ap.add_argument("--manifest", default=None, help="manifest.json for difficulty labels (optional)")
    ap.add_argument("--spread", type=float, default=0.1, help="Min spread to count as discriminating")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--md", default=None, help="Write the dashboard markdown here")
    ap.add_argument("--report", default=None, help="Write per-task JSON here")
    args = ap.parse_args(argv)

    scores, track_of = load_results(Path(args.results))
    if not scores:
        raise SystemExit(f"No result JSONs under {args.results}")
    diff_of = {}
    if args.manifest and Path(args.manifest).is_file():
        man = json.loads(Path(args.manifest).read_text())
        diff_of = {t["task_id"]: t.get("difficulty", "?") for t in man.get("tasks", [])}

    rows = build_rows(scores, track_of, diff_of, args.spread)
    dashboard = render(rows, args.top)
    print(dashboard)

    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md).write_text(dashboard + "\n")
        print(f"\nmd -> {args.md}")
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(
            [{k: v for k, v in r.items() if k != "scores"} | {"scores": r["scores"]} for r in rows],
            indent=2))
        print(f"report -> {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
