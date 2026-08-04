#!/usr/bin/env python3
"""Lightweight b04/HSPICE health sentinel for heavy SPICE fairness-gate batches.

Mirror of pt_health_sentinel.py for Family B: stages a known-good (golden) p16 deck in a
temp workspace, runs real HSPICE, and reports whether the simulator exited 0, produced a
parseable .measure result, and the value fell inside the FROZEN plausible range — within a
health deadline. PROACTIVE infrastructure health metadata: recorded SEPARATELY from task
fairness results; a sentinel failure PAUSES/ABORTS the gate; it never changes candidate
membership or candidate outcomes (generalized rule).

Usage:
  hspice_health_sentinel.py --task <p16_eval_0001_bundles> --out <sentinel.json> [--deadline 180]
  (importable: check_hspice_health(task_dir, env, deadline) -> dict)
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, tempfile, time, math
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "generators"))
import p16_spice_handoff_gen as GB  # noqa: E402  (for parse_lis_value + METRIC_RANGE)


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_hspice_health(task_dir: Path, env: dict, deadline: float = 180.0) -> dict:
    rec = {"ts": _now_iso(), "deadline_s": deadline, "task": task_dir.name, "healthy": False,
           "sim_exit_zero": None, "measure_present": None, "value_in_range": None,
           "value": None, "metric": None, "elapsed_s": None, "error": None}
    hs = env.get("EDA_HSPICE_CMD", "hspice")
    work = Path(tempfile.mkdtemp(prefix="hspice_sentinel_"))
    try:
        shutil.copytree(task_dir / "files", work, dirs_exist_ok=True)
        shutil.copytree(task_dir / "hidden", work, dirs_exist_ok=True)
        truth = json.loads((task_dir / "hidden" / "meas_request_truth.json").read_text())
        golden = truth["golden_join"]
        (work / "meas_config.json").write_text(json.dumps(golden) + "\n")
        metric = golden["metric"]
        rec["metric"] = metric
        r = subprocess.run(["python3", "build_deck.py"], cwd=str(work), env=env, capture_output=True, text=True, timeout=60)
        t0 = time.monotonic()
        r = subprocess.run([hs, "-i", "circuit_built.sp", "-o", "hspice_run"], cwd=str(work), env=env,
                           capture_output=True, text=True, timeout=deadline)
        rec["elapsed_s"] = round(time.monotonic() - t0, 2)
        rec["sim_exit_zero"] = (r.returncode == 0)
        lis = work / "hspice_run.lis"
        val = GB.parse_lis_value(lis.read_text(errors="ignore"), metric) if lis.is_file() else None
        rec["value"] = val
        rec["measure_present"] = val is not None and math.isfinite(val)
        lo, hi = GB.METRIC_RANGE[metric]
        rec["value_in_range"] = bool(rec["measure_present"] and lo <= val <= hi)
        rec["healthy"] = bool(rec["sim_exit_zero"] and rec["measure_present"] and rec["value_in_range"])
        return rec
    except subprocess.TimeoutExpired:
        rec["error"] = f"hspice exceeded {deadline}s health deadline"
        return rec
    except Exception as e:  # noqa: BLE001
        rec["error"] = f"{type(e).__name__}: {e}"
        return rec
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--deadline", type=float, default=180.0)
    a = ap.parse_args()
    env = dict(os.environ)
    env.setdefault("EDA_TOOL_ROOT", "/data1/tongsb/eda-remote-shim/EDA")
    env.setdefault("B04_HOST", "tsb@b04")
    env.setdefault("EDA_HSPICE_CMD", "/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/hspice/V-2023.12/hspice/bin/hspice")
    task_dir = REPO / "tasks" / "p16_spice_handoff" / a.task
    rec = check_hspice_health(task_dir, env, a.deadline)
    Path(a.out).write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps({"healthy": rec["healthy"], "task": rec["task"], "value": rec["value"]}, indent=2))
    return 0 if rec["healthy"] else 2


if __name__ == "__main__":
    sys.exit(main())
