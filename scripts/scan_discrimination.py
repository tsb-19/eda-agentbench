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

# Continuous-graded components: tracks whose primary signal is a fractional score
# carried in ONE component (graded closeness / fraction-of-specs), not a binary
# pass/fail. For these, total_score adds a fixed overhead (tool_run + output +
# explanation ~0.4) that compresses the dynamic range and makes a do-nothing floor
# read like a partial pass — which blinds the saturation/spread stats (a P4-damping
# floor totals 0.60 and looks "mostly passing"). The dashboard must aggregate the
# ISOLATED continuous component instead. Extend this set as continuous tracks land.
CONTINUOUS_COMPONENTS = {"spec_score"}


# --------------------------------------------------------------------------- #
# Pure stats (unit-tested without any results tree)
# --------------------------------------------------------------------------- #
def primary_score(result: dict) -> float:
    """The per-episode score the discrimination dashboard should aggregate.

    Continuous-graded track -> the isolated continuous component's raw (clean
    [0,1], no tool/output/explanation overhead). Otherwise -> total_score
    (unchanged for binary tracks). Anti-cheat-zeroed episodes serialize no
    components with total_score 0.0, so they correctly return 0.0.
    """
    for c in result.get("components") or []:
        if c.get("name") in CONTINUOUS_COMPONENTS:
            raw = c.get("raw")
            return 0.0 if raw is None else max(0.0, min(1.0, float(raw)))
    return float(result.get("total_score", 0.0))


def task_stats(scores: list[float], *, spread_thresh: float = 0.1) -> dict:
    """Across-model stats for one task's total_scores."""
    n = len(scores)
    mean = statistics.mean(scores)
    lo, hi = min(scores), max(scores)
    spread = hi - lo
    n_perfect = sum(1 for v in scores if v >= PERFECT)
    n_zero = sum(1 for v in scores if v <= 0.0)
    return {
        "n": n, "mean": mean, "min": lo, "max": hi, "spread": spread,
        "std": statistics.pstdev(scores) if n > 1 else 0.0,
        "n_perfect": n_perfect,
        "emp_difficulty": 1.0 - mean,
        "saturated": n_perfect == n,                 # everyone aced it
        "dead": hi < FAIL,                           # nobody passed
        "all_zero": n > 0 and n_zero == n,           # nobody scored anything at all
        "discriminating": spread >= spread_thresh,   # separates models
    }


def classify(s: dict) -> str:
    if s["saturated"]:
        return "saturated"
    # All models scored exactly 0 AND the golden isn't confirmed valid -> the task
    # is more likely BROKEN (unmatchable expected answer, the P8 artifact) than hard.
    # With a validate-cache confirming golden==1.0, it falls through to "dead" (hard).
    if s.get("all_zero") and not s.get("golden_valid"):
        return "suspect_broken"
    if s["dead"]:
        return "dead"
    if s["discriminating"]:
        return "discriminating"
    return "weak"


# --------------------------------------------------------------------------- #
# Load
# --------------------------------------------------------------------------- #
def load_infra_episodes(results_root: Path) -> dict[tuple[str, str], str]:
    """(task_id, model) -> infra reason for agentic episodes that measure the
    HARNESS, not the model: a non-null driver error (e.g. an HTTP 429 off the LLM
    gateway) or zero parsed actions (the model never produced a usable turn).

    Reads the *.agentlog.json sidecars the score scan otherwise skips. Such episodes
    MUST be excluded from capability stats — counted as a genuine 0 they drag a task
    toward "dead" and slander the model (e.g. Kimi's all-429 columns on P6/P7)."""
    infra: dict[tuple[str, str], str] = {}
    for f in glob.glob(str(results_root / "*" / "*" / "*.agentlog.json")):
        try:
            d = json.loads(Path(f).read_text())
        except (json.JSONDecodeError, OSError):
            continue
        tid, model = d.get("task_id"), d.get("model")
        if not tid or not model:
            continue
        err = d.get("error")
        if err:
            infra[(tid, model)] = "http_429" if "429" in str(err) else f"error:{str(err).split(':', 1)[0][:24]}"
        elif not (d.get("actions") or []):
            infra[(tid, model)] = "zero_actions"
    return infra


def load_golden_valid(cache_path: Path) -> dict[str, bool]:
    """task_id -> is the golden known-valid? (read from validate_dataset.py's cache).

    Lets the scan tell a genuinely-hard task (golden passes, no model does -> dead)
    apart from a BROKEN task (no model can ever match -> suspect_broken)."""
    gv: dict[str, bool] = {}
    if not (cache_path and cache_path.is_file()):
        return gv
    try:
        cache = json.loads(cache_path.read_text())
    except (json.JSONDecodeError, OSError):
        return gv
    for entry in cache.values():
        v = (entry or {}).get("verdict") or {}
        tid, g = v.get("task_id"), v.get("golden")
        if tid:
            gv[tid] = g is not None and g >= PERFECT
    return gv


def load_results(results_root: Path, infra: dict | None = None):
    """task_id -> {model: primary_score}; task_id -> track; continuous tracks; excluded.

    Episodes in `infra` (harness artifacts, see load_infra_episodes) are dropped from
    the scores and returned separately as `excluded` so the report can show them
    without letting them corrupt the difficulty stats."""
    infra = infra or {}
    scores: dict[str, dict[str, float]] = defaultdict(dict)
    track_of: dict[str, str] = {}
    cont_tracks: set[str] = set()
    excluded: list[tuple[str, str, str]] = []
    for f in glob.glob(str(results_root / "*" / "*" / "*.json")):
        # Skip sidecars (e.g. <task>.agentlog.json from the agentic runner): they
        # share task_id+model with the real result but carry no total_score.
        if f.endswith(".agentlog.json"):
            continue
        d = json.loads(Path(f).read_text())
        if "total_score" not in d:
            continue
        tid = d.get("task_id") or Path(f).stem
        model = d.get("model", Path(f).parts[-3])
        track = d.get("track", Path(f).parts[-2])
        if (tid, model) in infra:
            excluded.append((tid, model, infra[(tid, model)]))
            continue
        scores[tid][model] = primary_score(d)
        track_of[tid] = track
        if any((c.get("name") in CONTINUOUS_COMPONENTS) for c in (d.get("components") or [])):
            cont_tracks.add(track)
    return scores, track_of, cont_tracks, excluded


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def build_rows(scores, track_of, diff_of, spread_thresh, golden_valid_of=None):
    golden_valid_of = golden_valid_of or {}
    rows = []
    for tid, ms in scores.items():
        if not ms:
            continue  # every episode was infra-excluded; nothing left to score
        s = task_stats(list(ms.values()), spread_thresh=spread_thresh)
        s.update({"task_id": tid, "track": track_of.get(tid, "?"),
                  "difficulty": diff_of.get(tid, "?"),
                  "golden_valid": golden_valid_of.get(tid), "scores": ms})
        s["klass"] = classify(s)  # needs golden_valid already set
        rows.append(s)
    return rows


def _render_excluded(excluded: list) -> str:
    """Summarize infra-excluded episodes by (model, reason)."""
    if not excluded:
        return ""
    by: dict[tuple[str, str], int] = defaultdict(int)
    for _tid, model, reason in excluded:
        by[(model, reason)] += 1
    lines = [f"## Infra-excluded episodes ({len(excluded)}) — harness artifacts, NOT counted as capability",
             "| model | reason | episodes |", "|---|---|---|"]
    for (model, reason), c in sorted(by.items()):
        lines.append(f"| {model} | {reason} | {c} |")
    return "\n".join(lines)


def render(rows, top: int, cont_tracks: set | None = None, excluded: list | None = None) -> str:
    cont_tracks = cont_tracks or set()
    excluded = excluded or []
    out = []
    n = len(rows)
    if n == 0:
        out.append("# Discrimination scan (0 scorable tasks)\n")
        out.append(_render_excluded(excluded))
        return "\n".join(s for s in out if s)
    allv = [v for r in rows for v in r["scores"].values()]
    nmodels = max((r["n"] for r in rows), default=0)
    sat = [r for r in rows if r["saturated"]]
    disc = [r for r in rows if r["discriminating"]]
    dead = [r for r in rows if r["dead"]]
    broken = [r for r in rows if r.get("klass") == "suspect_broken"]

    def pct(x):
        return f"{x/len(allv):.0%}" if allv else "-"

    out.append(f"# Discrimination scan ({n} tasks, {nmodels} models, {len(allv)} pairs)\n")
    out.append("## Overall")
    out.append(f"- perfect pairs (==1.0): {sum(1 for v in allv if v>=PERFECT)}/{len(allv)} = {pct(sum(1 for v in allv if v>=PERFECT))}")
    out.append(f"- pairs >= 0.9: {pct(sum(1 for v in allv if v>=0.9))}   |   pairs < 0.5 (fail): {pct(sum(1 for v in allv if v<FAIL))}")
    out.append(f"- **saturated tasks (all models 1.0, zero signal): {len(sat)}/{n} = {len(sat)/n:.0%}**")
    out.append(f"- discriminating (spread >= 0.1): {len(disc)}/{n} = {len(disc)/n:.0%}   |   dead (all <0.5): {len(dead)}/{n}")
    if broken:
        out.append(f"- ⚠️ **suspect_broken (all models ==0, golden NOT confirmed valid): {len(broken)}/{n}** — likely broken tasks, not hard ones")
    if excluded:
        out.append(f"- infra-excluded episodes (harness artifacts, not capability): {len(excluded)}")
    out.append("")

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
        mark = " °" if tr in cont_tracks else ""
        out.append(f"| {tr}{mark} | {len(rs)} | {ns}/{len(rs)}{flag} | {nd}/{len(rs)} | {mean:.2f} | {msp:.2f} |")
    if cont_tracks:
        out.append("\n° continuous-graded track — `mean`/`mean spread` and the "
                   "saturated/discriminating flags are computed on the ISOLATED "
                   "continuous component (e.g. spec_score), not pass-rate; a "
                   "do-nothing floor shows as its true low fraction, not ~0.6.")
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
    if broken:
        out.append(f"\n## ⚠️ Suspect broken (all models scored 0, golden not confirmed) — up to {top}")
        for r in sorted(broken, key=lambda r: r["track"])[:top]:
            out.append(f"- {r['track']}/{r['task_id']} (label={r['difficulty']}) — verify the golden/expected answer is matchable")
    exc = _render_excluded(excluded)
    if exc:
        out.append("\n" + exc)
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Tier-2 no-golden discrimination scan over a results tree.")
    ap.add_argument("--results", required=True, help="Results root (…/<model>/<track>/<task>.json)")
    ap.add_argument("--manifest", default=None, help="manifest.json for difficulty labels (optional)")
    ap.add_argument("--validate-cache", default=None,
                    help="validate_dataset.py cache (runs/validate_cache.json); a golden-valid task "
                         "with all-0 scores is hard (dead), not broken")
    ap.add_argument("--spread", type=float, default=0.1, help="Min spread to count as discriminating")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--md", default=None, help="Write the dashboard markdown here")
    ap.add_argument("--report", default=None, help="Write per-task JSON here")
    args = ap.parse_args(argv)

    results_root = Path(args.results)
    infra = load_infra_episodes(results_root)
    scores, track_of, cont_tracks, excluded = load_results(results_root, infra)
    if not scores and not excluded:
        raise SystemExit(f"No result JSONs under {args.results}")
    diff_of = {}
    if args.manifest and Path(args.manifest).is_file():
        man = json.loads(Path(args.manifest).read_text())
        diff_of = {t["task_id"]: t.get("difficulty", "?") for t in man.get("tasks", [])}
    golden_valid_of = load_golden_valid(Path(args.validate_cache)) if args.validate_cache else {}

    rows = build_rows(scores, track_of, diff_of, args.spread, golden_valid_of)
    dashboard = render(rows, args.top, cont_tracks, excluded)
    print(dashboard)

    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md).write_text(dashboard + "\n")
        print(f"\nmd -> {args.md}")
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps({
            "tasks": [{k: v for k, v in r.items() if k != "scores"} | {"scores": r["scores"]} for r in rows],
            "excluded": [{"task_id": t, "model": m, "reason": why} for t, m, why in excluded],
        }, indent=2))
        print(f"report -> {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
