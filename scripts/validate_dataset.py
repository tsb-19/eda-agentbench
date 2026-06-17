#!/usr/bin/env python3
"""Validate dataset tasks through the REAL grading path.

Generalizes the manual fairness gate: for each task it grades the golden AND the
buggy submission (the exact same inputs the official ``evaluate-dataset`` uses —
see eda_agentbench.cli.solution_submission_path / build_buggy_submission) and
applies machine checks that need no human judgement:

  C1 golden-valid     golden total_score >= 1 - eps              (else: false-negative golden)
  C2 discrimination   golden.objective - buggy.objective >= tau  (else: non-discriminating task)
  C3 determinism      (opt-in) golden graded twice, |delta| < eps
  C4 anti-cheat       (opt-in) an empty submission must fail

A content-hash cache makes "validate on every change" affordable: ``--changed``
re-grades only tasks whose files changed since the last run, but still reports the
cached verdict of unchanged tasks (so a known failure is never hidden).

Requires the EDA tools (or the b04 shim env) reachable for tool tracks, same as
grading. Mirrors scripts/calibrate_p4_settling_windows.py.

    source /data1/tongsb/eda-remote-shim/env.sh
    python3 scripts/validate_dataset.py --tasks-root tasks/p4_spice_sim \
        --glob 'generated_*/*_rlc_settling_*' --concurrency 4
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from eda_agentbench.cli import (  # noqa: E402
    _evaluate_single,
    build_buggy_submission,
    solution_submission_path,
)
from eda_agentbench.task.loader import TaskLoader  # noqa: E402

EPS = 1e-3
DEFAULT_MARGIN = 0.15
DEFAULT_CACHE = "runs/validate_cache.json"


# --------------------------------------------------------------------------- #
# Pure helpers (unit-tested without any EDA tool)
# --------------------------------------------------------------------------- #
def task_hash(task_dir: Path) -> str:
    """sha1 over sorted (relpath, bytes) of every file under the task dir."""
    h = hashlib.sha1()
    for p in sorted(task_dir.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(task_dir).as_posix().encode())
            h.update(b"\0")
            h.update(p.read_bytes())
            h.update(b"\0")
    return h.hexdigest()


def evaluate_verdict(golden_total, golden_obj, buggy_obj, *, margin_tau=DEFAULT_MARGIN,
                     det_total=None, empty_passed=None,
                     check_determinism=False, check_empty=False, eps=EPS) -> dict:
    """Apply C1-C4 to already-measured scores. Returns {ok, failures, margin}."""
    failures: list[str] = []

    # C1 golden-valid
    if golden_total is None:
        failures.append("C1:golden_grading_error")
    elif golden_total < 1.0 - eps:
        failures.append(f"C1:golden={golden_total:.3f}<1.0")

    # C2 discrimination margin
    margin = None
    if golden_obj is None or buggy_obj is None:
        failures.append("C2:buggy_grading_error")
    else:
        margin = golden_obj - buggy_obj
        if margin < margin_tau:
            failures.append(f"C2:margin={margin:.3f}<{margin_tau}")

    # C3 determinism (opt-in)
    if check_determinism and golden_total is not None:
        if det_total is None:
            failures.append("C3:determinism_grading_error")
        elif abs(det_total - golden_total) >= eps:
            failures.append(f"C3:nondeterministic_delta={abs(det_total - golden_total):.3f}")

    # C4 anti-cheat empty probe (opt-in)
    if check_empty:
        if empty_passed is None:
            failures.append("C4:empty_grading_error")
        elif empty_passed:
            failures.append("C4:empty_submission_passed")

    return {"ok": not failures, "failures": failures, "margin": margin}


def load_cache(path: Path) -> dict:
    if path and path.is_file():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_cache(path: Path, cache: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2, sort_keys=True))


def _fmt(x) -> str:
    """Console-friendly number (full precision is kept in the JSON report)."""
    return f"{x:.3f}" if isinstance(x, (int, float)) else str(x)


# --------------------------------------------------------------------------- #
# Grading (needs EDA tools / shim)
# --------------------------------------------------------------------------- #
def _grade(task_dir: Path, submission: Path, meta: dict, timeout: int):
    """Grade one submission through the real path. Returns ScoreResult or None."""
    rr = Path(tempfile.mkdtemp(prefix="val_runs_"))
    try:
        _, score = _evaluate_single(task_dir, submission, meta, timeout, runs_root=rr)
        return score
    except Exception:  # noqa: BLE001  (a grading crash is itself a finding -> None)
        return None
    finally:
        shutil.rmtree(rr, ignore_errors=True)


def _empty_submission(task_dir: Path, meta: dict) -> Path:
    """A submission with empty editable files (anti-cheat probe)."""
    d = Path(tempfile.mkdtemp(prefix="eda_empty_"))
    is_p5 = meta.get("track") == "p5_spice_deck_debug"
    for ef in meta["files"]["editable"]:
        target = d / (Path(ef).name if is_p5 else ef)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("")
    return d


def validate_one(task_dir: Path, loader: TaskLoader, *, margin_tau, check_determinism,
                 check_empty) -> dict:
    """Grade golden + buggy (+ optional probes) and apply the verdict."""
    try:
        meta = loader.load(task_dir)
    except Exception as e:  # noqa: BLE001
        return {"task_id": task_dir.name, "track": "?", "ok": False,
                "failures": [f"load_error:{type(e).__name__}"], "golden": None,
                "buggy": None, "margin": None}

    track = meta["track"]
    task_id = meta["task_id"]
    timeout = meta.get("timeout_sec", 300)

    golden = _grade(task_dir, solution_submission_path(task_dir, meta), meta, timeout)
    g_total = golden.total_score if golden else None
    g_obj = golden.objective_score if golden else None

    buggy_dir = build_buggy_submission(task_dir, meta)
    try:
        buggy = _grade(task_dir, buggy_dir, meta, timeout)
    finally:
        shutil.rmtree(buggy_dir, ignore_errors=True)
    b_total = buggy.total_score if buggy else None
    b_obj = buggy.objective_score if buggy else None

    det_total = None
    if check_determinism:
        det = _grade(task_dir, solution_submission_path(task_dir, meta), meta, timeout)
        det_total = det.total_score if det else None

    empty_passed = None
    if check_empty:
        edir = _empty_submission(task_dir, meta)
        try:
            ep = _grade(task_dir, edir, meta, timeout)
        finally:
            shutil.rmtree(edir, ignore_errors=True)
        empty_passed = ep.passed if ep else None

    v = evaluate_verdict(g_total, g_obj, b_obj, margin_tau=margin_tau,
                         det_total=det_total, empty_passed=empty_passed,
                         check_determinism=check_determinism, check_empty=check_empty)
    return {"task_id": task_id, "track": track, "golden": g_total, "buggy": b_total,
            "margin": v["margin"], "ok": v["ok"], "failures": v["failures"]}


# --------------------------------------------------------------------------- #
# Selection + orchestration
# --------------------------------------------------------------------------- #
def select_tasks(args, loader: TaskLoader) -> list[Path]:
    if args.glob:
        base = Path(args.tasks_root)
        dirs = sorted(d for d in base.glob(args.glob) if (d / "metadata.json").is_file())
    else:
        dirs = loader.discover(track=args.track)
    if args.limit:
        dirs = dirs[: args.limit]
    return dirs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate dataset tasks through the real grading path.")
    ap.add_argument("--tasks-root", default="tasks")
    ap.add_argument("--track", default=None, help="Restrict to one track (ignored if --glob)")
    ap.add_argument("--glob", default=None, help="Glob under --tasks-root selecting task dirs")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--margin", type=float, default=DEFAULT_MARGIN,
                    help="Min golden.objective - buggy.objective (C2)")
    ap.add_argument("--check-determinism", action="store_true", help="C3: grade golden twice")
    ap.add_argument("--check-empty", action="store_true", help="C4: empty submission must fail")
    ap.add_argument("--cache", default=DEFAULT_CACHE, help="Per-task hash cache path")
    ap.add_argument("--no-cache", action="store_true", help="Ignore + don't write the cache")
    ap.add_argument("--changed", action="store_true",
                    help="Re-grade only tasks whose hash changed; reuse cached verdict otherwise")
    ap.add_argument("--report", default=None, help="Write machine-readable JSON report here")
    args = ap.parse_args(argv)

    loader = TaskLoader(Path("tasks"))
    dirs = select_tasks(args, loader)
    if not dirs:
        raise SystemExit(f"No tasks match (tasks-root={args.tasks_root} track={args.track} glob={args.glob})")

    cache_path = None if args.no_cache else (REPO / args.cache if not Path(args.cache).is_absolute() else Path(args.cache))
    cache = {} if args.no_cache else load_cache(cache_path)

    # Decide per task: reuse cached verdict (unchanged, --changed) or grade fresh.
    # Key the cache by the resolved task-dir path (stable across runs; dir name and
    # task_id can differ, e.g. hspice_rlc_settling_000210 vs task_004210).
    hashes = {d: task_hash(d) for d in dirs}
    keys = {d: str(d.resolve()) for d in dirs}
    to_grade, reused = [], []
    for d in dirs:
        c = cache.get(keys[d])
        if args.changed and c and c.get("hash") == hashes[d]:
            reused.append(c["verdict"])
        else:
            to_grade.append(d)

    print(f"validate: {len(dirs)} selected | grading {len(to_grade)} | reused-from-cache {len(reused)} "
          f"| concurrency {args.concurrency} | margin {args.margin}"
          f"{' | +determinism' if args.check_determinism else ''}"
          f"{' | +empty' if args.check_empty else ''}", flush=True)

    fresh: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as ex:
        futs = {ex.submit(validate_one, d, loader, margin_tau=args.margin,
                          check_determinism=args.check_determinism,
                          check_empty=args.check_empty): d for d in to_grade}
        for f in as_completed(futs):
            r = f.result()
            fresh.append(r)
            tag = "ok " if r["ok"] else "FAIL"
            extra = "" if r["ok"] else "  " + "; ".join(r["failures"])
            print(f"  [{tag}] {r['track']}/{r['task_id']}  "
                  f"golden={_fmt(r['golden'])} margin={_fmt(r['margin'])}{extra}", flush=True)
            if not args.no_cache:
                cache[keys[futs[f]]] = {"hash": hashes[futs[f]], "verdict": r}

    if not args.no_cache:
        save_cache(cache_path, cache)

    results = fresh + reused

    # Report
    by_track = defaultdict(list)
    for r in results:
        by_track[r["track"]].append(r)
    print(f"\n{'track':<26}{'n':>4}{'pass':>9}")
    for track in sorted(by_track):
        rows = by_track[track]
        npass = sum(1 for r in rows if r["ok"])
        print(f"{track:<26}{len(rows):>4}{npass:>6}/{len(rows):<3}")

    offenders = [r for r in results if not r["ok"]]
    print()
    if offenders:
        print(f"OFFENDERS ({len(offenders)}):")
        for r in sorted(offenders, key=lambda x: (x["track"], x["task_id"])):
            print(f"  {r['track']}/{r['task_id']}: {'; '.join(r['failures'])}")
    else:
        print("ALL TASKS VALID (golden=1.0, discriminating, + any opt-in checks).")
    print(f"\nTOTAL: {len(results) - len(offenders)}/{len(results)} valid"
          f"{f' ({len(reused)} from cache)' if reused else ''}")

    if args.report:
        rp = Path(args.report)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps({
            "selected": len(dirs), "graded": len(fresh), "reused": len(reused),
            "valid": len(results) - len(offenders), "offenders": offenders,
            "margin": args.margin, "checks": {"determinism": args.check_determinism,
                                              "empty": args.check_empty},
            "results": results,
        }, indent=2))
        print(f"report -> {rp}")

    return 1 if offenders else 0


if __name__ == "__main__":
    raise SystemExit(main())
