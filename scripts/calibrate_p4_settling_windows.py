#!/usr/bin/env python3
"""Calibrate P4 rlc_settling metric windows from a golden tool run.

The generator sets each task's public/hidden acceptance window analytically
(``_rlc_trise``). That model is inaccurate for some RLC parameter ranges: the
golden's *simulated* tdrise/tdfall can land outside the *analytical* window, so
even the correct solution fails its own metric. This pass runs each task's
golden through the real tool, reads the actual measured values, and recenters
the windows on them — preserving each task's original fractional half-width.

This is the tool-grounded (flow_synthetic) way to set acceptance windows and is
intended to run AFTER ``generate_p4_spice_tasks.py`` for the rlc_settling type.
Requires the EDA tools (or the b04 shim env) reachable, same as grading.

    python scripts/calibrate_p4_settling_windows.py --concurrency 6
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from eda_agentbench.cli import _evaluate_single  # noqa: E402
from eda_agentbench.task.loader import TaskLoader  # noqa: E402


def _measured(components, comp_name: str, measure: str):
    """Pull the measured float for `measure` out of a component's details string."""
    for c in components:
        if c.name == comp_name:
            m = re.search(rf"{re.escape(measure)}\s*=\s*([-\d.eE+]+)", c.details or "")
            if m:
                return float(m.group(1))
    return None


def _half_width(cfg: dict) -> float:
    """Recover the original fractional half-width from an existing [min,max] window."""
    lo, hi = cfg.get("min"), cfg.get("max")
    if lo and hi and (hi + lo) > 0:
        return (hi - lo) / (hi + lo)
    return 0.25


def calibrate_one(task_dir: Path, loader: TaskLoader) -> tuple:
    meta = loader.load(task_dir)
    metrics = meta.get("scoring", {}).get("metrics", {})
    pub_meas = metrics.get("public", {}).get("measure", "")
    hid_meas = metrics.get("hidden", {}).get("measure", "")
    rr = Path(tempfile.mkdtemp(prefix="calib_"))
    try:
        _, score = _evaluate_single(task_dir, task_dir / "solution", meta,
                                    meta.get("timeout_sec", 300), runs_root=rr)
    except Exception as e:  # noqa: BLE001
        return (task_dir.name, f"ERR:{type(e).__name__}", None, None)
    pub_v = _measured(score.components, "public_metric", pub_meas)
    hid_v = _measured(score.components, "hidden_metric", hid_meas)
    if not pub_v or not hid_v or pub_v <= 0 or hid_v <= 0:
        return (task_dir.name, "SKIP", pub_v, hid_v)

    mp = task_dir / "metadata.json"
    md = json.loads(mp.read_text())
    m = md["scoring"]["metrics"]
    for key, val in (("public", pub_v), ("hidden", hid_v)):
        hw = _half_width(m[key])
        m[key]["min"] = val * (1.0 - hw)
        m[key]["max"] = val * (1.0 + hw)
    mp.write_text(json.dumps(md, indent=2))
    return (task_dir.name, "OK", pub_v, hid_v)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Calibrate P4 rlc_settling windows from golden sims.")
    ap.add_argument("--tasks-root", default="tasks/p4_spice_sim")
    ap.add_argument("--glob", default="generated_*/*_rlc_settling_*",
                    help="Glob (under --tasks-root) selecting tasks to calibrate")
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args(argv)

    loader = TaskLoader(Path("tasks"))
    dirs = sorted((REPO / args.tasks_root).glob(args.glob))
    if not dirs:
        raise SystemExit(f"No tasks match {args.tasks_root}/{args.glob}")
    print(f"Calibrating {len(dirs)} tasks at concurrency {args.concurrency} ...")

    ok = bad = 0
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as ex:
        futs = {ex.submit(calibrate_one, d, loader): d for d in dirs}
        for f in as_completed(futs):
            name, status, pv, hv = f.result()
            if status == "OK":
                ok += 1
            else:
                bad += 1
                print(f"  {status} {name}: pub={pv} hid={hv}")
    print(f"\nCalibrated {ok}, skipped/errored {bad}.")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
