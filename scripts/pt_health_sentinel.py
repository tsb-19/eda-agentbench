#!/usr/bin/env python3
"""Lightweight b04/PT health sentinel for heavy fairness-gate batches.

Runs a tiny PT signoff on a known-good config (the acc_stage golden: netlist_v2 / clk_main / slow-func
on tiny.db) and reports whether PT produced a valid MET signoff within a health deadline. The sentinel
is PROACTIVE infrastructure health metadata: its results + timestamps are recorded SEPARATELY from task
fairness results, and a sentinel failure PAUSES/ABORTS the gate. It never changes candidate membership
or candidate outcomes (generalized rule).

Usage:
  pt_health_sentinel.py --task <workflow_handoff_0009> --out <sentinel.json> [--deadline 120]
  (importable: check_pt_health(task_dir, env, deadline) -> dict)
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_pt_health(task_dir: Path, env: dict, deadline: float = 120.0) -> dict:
    """Stage the golden config in a temp workspace, run run_evidence_stage1.sh, and inspect the
    regenerated timing_report header for a MET signoff. Returns a health record (no task-fairness data)."""
    rec = {"ts": _now_iso(), "deadline_s": deadline, "task": task_dir.name, "healthy": False,
           "signoff_ok": None, "elapsed_s": None, "error": None}
    work = Path(tempfile.mkdtemp(prefix="pt_sentinel_"))
    try:
        shutil.copytree(task_dir / "files", work, dirs_exist_ok=True)
        shutil.copytree(task_dir / "hidden", work, dirs_exist_ok=True)
        golden = json.loads((task_dir / "solution/flow_config.json").read_text())
        (work / "flow_config.json").write_text(json.dumps(golden, indent=2) + "\n")
        t0 = time.monotonic()
        r = subprocess.run(["bash", "run_evidence_stage1.sh"], cwd=str(work), env=env,
                           capture_output=True, text=True, timeout=deadline)
        rec["elapsed_s"] = round(time.monotonic() - t0, 2)
        tr = work / "timing_report.rpt"
        if r.returncode != 0 or not tr.is_file():
            rec["error"] = (f"stage1 rc={r.returncode}; " + (r.stderr[-200:] if r.stderr else "")).strip()
            return rec
        hdr = tr.read_text(errors="replace").splitlines()[1] if tr.is_file() else ""
        ok = ("signoff=OK" in hdr) and ("netlist_v2.v" in hdr) and ("clk_main" in hdr)
        rec["signoff_ok"] = bool(ok)
        rec["healthy"] = bool(ok)
        return rec
    except subprocess.TimeoutExpired:
        rec["error"] = f"stage1 exceeded {deadline}s health deadline"
        return rec
    except Exception as e:  # noqa: BLE001
        rec["error"] = f"{type(e).__name__}: {e}"
        return rec
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="workflow_handoff_0009")
    ap.add_argument("--out", required=True)
    ap.add_argument("--deadline", type=float, default=120.0)
    a = ap.parse_args()
    env = os.environ.copy()
    rec = check_pt_health(REPO / "tasks/p14_workflow_handoff" / a.task, env, a.deadline)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps(rec, indent=2))
    sys.exit(0 if rec["healthy"] else 2)


if __name__ == "__main__":
    main()
