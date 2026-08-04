#!/usr/bin/env python3
"""SPICE same-path full-path fairness check (mirror of fullpath_check.py for Family B).

SCORE-INDEPENDENT (takes no candidate argument, never inspects any candidate result).
Runs the FIXED golden reference of a p16 instance through the SAME path the grader uses
(build_deck -> HSPICE -> parse .lis -> grade_spice_handoff) and verifies invariants:
sim_exit_zero, measure_present, value within the FROZEN plausible range, and the golden
binding grades semantic_binding=True. healthy = all invariants. This is the Level-2
measurement-control bookend (a candidate block is admissible iff BOTH bookends healthy).
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile, math
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "generators"))
import p16_spice_handoff_gen as GB  # noqa: E402


def check(task_dir: Path, env: dict, regen_timeout: float = 240.0) -> dict:
    rec = {"task": task_dir.name, "healthy": False, "sim_exit_zero": None,
           "measure_present": None, "value_in_range": None, "golden_verdict_ok": None,
           "value": None, "metric": None, "error": None}
    hs = env.get("EDA_HSPICE_CMD", "hspice")
    work = Path(tempfile.mkdtemp(prefix="spice_fullpath_"))
    try:
        shutil.copytree(task_dir / "files", work, dirs_exist_ok=True)
        shutil.copytree(task_dir / "hidden", work, dirs_exist_ok=True)
        truth = json.loads((task_dir / "hidden" / "meas_request_truth.json").read_text())
        golden = truth["golden_join"]; metric = golden["metric"]
        rec["metric"] = metric
        (work / "meas_config.json").write_text(json.dumps(golden) + "\n")
        subprocess.run(["python3", "build_deck.py"], cwd=str(work), env=env, capture_output=True, text=True, timeout=60)
        r = subprocess.run([hs, "-i", "circuit_built.sp", "-o", "hspice_run"], cwd=str(work), env=env,
                           capture_output=True, text=True, timeout=regen_timeout)
        rec["sim_exit_zero"] = (r.returncode == 0)
        lis = work / "hspice_run.lis"
        val = GB.parse_lis_value(lis.read_text(errors="ignore"), metric) if lis.is_file() else None
        rec["value"] = val
        rec["measure_present"] = val is not None and math.isfinite(val)
        lo, hi = GB.METRIC_RANGE[metric]
        rec["value_in_range"] = bool(rec["measure_present"] and lo <= val <= hi)
        (work / "measure_result.json").write_text(json.dumps({"sim_ok": rec["sim_exit_zero"], "value": val, "metric": metric, "analysis": GB.METRIC_ANALYSIS[metric]}) + "\n")
        (work / "provenance_attestation.json").write_text(json.dumps({"roles": {"metric": "char_spec", "corner": "mission_profile", "load_condition": "application_note"}, "protocol_completed": True}) + "\n")
        (work / "measurement_report.md").write_text(f"{metric}={val}\nFINISH\n")
        g = subprocess.run(["python3", "grade_spice_handoff.py"], cwd=str(work), env=env, capture_output=True, text=True, timeout=60)
        try:
            m = json.loads(g.stdout)
            rec["golden_verdict_ok"] = bool(m.get("dimensions", {}).get("semantic_binding"))
        except Exception:
            rec["golden_verdict_ok"] = False
        rec["healthy"] = all([rec["sim_exit_zero"], rec["measure_present"], rec["value_in_range"], rec["golden_verdict_ok"]])
        return rec
    except Exception as e:  # noqa: BLE001
        rec["error"] = f"{type(e).__name__}: {e}"
        return rec
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--task", required=True)
    a = ap.parse_args()
    env = dict(os.environ)
    env.setdefault("EDA_HSPICE_CMD", "/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/hspice/V-2023.12/hspice/bin/hspice")
    td = REPO / "tasks" / "p16_spice_handoff" / a.task
    print(json.dumps(check(td, env), indent=2))
