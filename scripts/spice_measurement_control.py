#!/usr/bin/env python3
"""SPICE block measurement-control (mirror of measurement_control.py for Family B).

Block shape: fullpath_check (L2) -> candidate subset -> fullpath_check (L2).
SYMMETRIC whole-block invalidation: a block is admissible ONLY if BOTH bookends are healthy;
if either is unhealthy, the ENTIRE enclosed block is measurement-invalid (a 1.0 inside an
out-of-control block is invalid, just as a 0.0 is — candidate outcomes are NOT selectively
discarded; all preserved as diagnostic evidence, block rerun in a later healthy window).
If both bookends are healthy, every candidate result is AUTHORITATIVE and a valid candidate
score that differs from the EXPECTED fairness value is a HARD fairness failure (block_hard_fail):
EXPECTED = {golden: 1.0, wrong: 0.0}.

Replay/retry is validity-only (fairness_retry): a None result / None total_score / present
infra error -> retry up to max_replacements; a VALID score (favorable or not) NEVER retries.
Recovered transport degradation in a gradeable episode does NOT trigger replacement.
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile, math
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "generators"))
import spice_fullpath_check as L2
import fairness_retry as FR
import p16_spice_handoff_gen as GB  # noqa: E402

EXPECTED = {"golden": 1.0, "wrong": 0.0}


def _grade_candidate(task_dir: Path, binding: dict, role: str, env: dict, timeout: float = 240.0) -> dict:
    """Run one candidate binding through the full SPICE path and return a graded result."""
    hs = env.get("EDA_HSPICE_CMD", "hspice")
    work = Path(tempfile.mkdtemp(prefix="spice_cand_"))
    try:
        shutil.copytree(task_dir / "files", work, dirs_exist_ok=True)
        shutil.copytree(task_dir / "hidden", work, dirs_exist_ok=True)
        (work / "meas_config.json").write_text(json.dumps(binding) + "\n")
        subprocess.run(["python3", "build_deck.py"], cwd=str(work), env=env, capture_output=True, text=True, timeout=60)
        r = subprocess.run([hs, "-i", "circuit_built.sp", "-o", "hspice_run"], cwd=str(work), env=env,
                           capture_output=True, text=True, timeout=timeout)
        metric = binding.get("metric", "gain")
        lis = work / "hspice_run.lis"
        val = GB.parse_lis_value(lis.read_text(errors="ignore"), metric) if (lis.is_file() and r.returncode == 0) else None
        sim_ok = (r.returncode == 0 and val is not None and math.isfinite(val))
        (work / "measure_result.json").write_text(json.dumps({"sim_ok": sim_ok, "value": val, "metric": metric, "analysis": GB.METRIC_ANALYSIS[metric]}) + "\n")
        (work / "provenance_attestation.json").write_text(json.dumps({"roles": {"metric": "char_spec", "corner": "mission_profile", "load_condition": "application_note"}, "protocol_completed": True}) + "\n")
        (work / "measurement_report.md").write_text(f"{metric}={val}\nFINISH\n")
        g = subprocess.run(["python3", "grade_spice_handoff.py"], cwd=str(work), env=env, capture_output=True, text=True, timeout=60)
        try:
            m = json.loads(g.stdout)
            sem = bool(m.get("dimensions", {}).get("semantic_binding"))
        except Exception:
            return {"role": role, "total_score": None, "error": "grade_failed"}
        return {"role": role, "total_score": 1.0 if sem else 0.0, "sim_ok": sim_ok, "value": val, "semantic_binding": sem}
    except subprocess.TimeoutExpired:
        return {"role": role, "total_score": None, "error": "candidate_timeout"}
    except Exception as e:  # noqa: BLE001
        return {"role": role, "total_score": None, "error": f"{type(e).__name__}: {e}"}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_block(task_dir: Path, candidates: list, env: dict, max_replacements: int = 1) -> dict:
    """candidates: list of (role, binding) where role in {'golden','wrong'}.
    Returns block record with bookends, admissibility, per-candidate results, hard-fail list."""
    before = L2.check(task_dir, env)
    graded = []
    for role, binding in candidates:
        attempt = 0
        while True:
            res = _grade_candidate(task_dir, binding, role, env)
            if FR.should_retry(res, EXPECTED.get(role), attempt, max_replacements):
                attempt += 1; continue
            graded.append(res); break
    after = L2.check(task_dir, env)
    admissible = bool(before["healthy"] and after["healthy"])
    hard_fails = []
    if admissible:
        for res in graded:
            exp = EXPECTED.get(res["role"])
            if res.get("total_score") is not None and res["total_score"] != exp:
                hard_fails.append({"role": res["role"], "expected": exp, "got": res["total_score"]})
    return {"task": task_dir.name, "before": before, "after": after, "admissible": admissible,
            "candidates": graded, "hard_fails": hard_fails,
            "invalid_reason": (None if admissible else
                               ("before-check unhealthy" if not before["healthy"] else "after-check unhealthy"))}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--task", required=True)
    a = ap.parse_args()
    env = dict(os.environ)
    env.setdefault("EDA_HSPICE_CMD", "/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/hspice/V-2023.12/hspice/bin/hspice")
    td = REPO / "tasks" / "p16_spice_handoff" / a.task
    truth = json.loads((td / "hidden" / "meas_request_truth.json").read_text())
    cands = [("golden", truth["golden_join"]), ("wrong", truth["wrong_join_plausible"])]
    print(json.dumps(run_block(td, cands, env), indent=2))
