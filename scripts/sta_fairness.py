#!/usr/bin/env python3
"""Family A (STA/PrimeTime) fairness-gate analog: health sentinel + same-path full-path
check + block measurement-control. Mirror of the SPICE fairness infra (hspice_health_sentinel /
spice_fullpath_check / spice_measurement_control) but invoking the p15 launder+signoff+grade
path (run_hidden.sh) on real PrimeTime. Same contract: proactive health metadata (never
changes candidate membership/outcomes); score-independent full-path reference; block
admissible iff BOTH bookends healthy (symmetric whole-block invalidation); validity-only
retry (fairness_retry); recovered degradation in a gradeable episode does NOT replace.
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile, re
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import fairness_retry as FR
EXPECTED = {"golden": 1.0, "wrong": 0.0}


def _env():
    e = dict(os.environ)
    e.setdefault("EDA_TOOL_ROOT", "/data1/tongsb/eda-remote-shim/EDA")
    e.setdefault("B04_HOST", "tsb@b04")
    e.setdefault("EDA_PT_CMD", "/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/prime/V-2023.12/bin/pt_shell")
    return e


def _run_hidden_get_markers(task_dir: Path, binding: dict, env: dict, deadline: float = 240.0):
    """Stage flat workspace, set exception_config=binding, run run_hidden.sh, extract grade markers JSON."""
    work = Path(tempfile.mkdtemp(prefix="sta_fair_"))
    try:
        shutil.copytree(task_dir / "files", work, dirs_exist_ok=True)
        shutil.copytree(task_dir / "hidden", work, dirs_exist_ok=True)
        (work / "exception_config.json").write_text(json.dumps(binding) + "\n")
        r = subprocess.run(["bash", "run_hidden.sh"], cwd=str(work), env=env, capture_output=True, text=True, timeout=deadline)
        # re-run the grader directly for a CLEAN markers JSON (it reads signoff_result.json / applied_hidden.sdc
        # that run_hidden.sh wrote; avoids parsing interleaved [apply] PT output)
        r2 = subprocess.run(["python3", "grade_sta_handoff.py"], cwd=str(work), env=env, capture_output=True, text=True, timeout=60)
        try:
            markers = json.loads(r2.stdout)
        except Exception:
            markers = {}
        signoff_green = markers.get("checks", {}).get("pt_signoff_green")
        return {"rc": r.returncode, "markers": markers, "signoff_green": signoff_green, "stdout_tail": r.stdout[-200:]}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def check_health(task_dir: Path, env: dict, deadline: float = 240.0) -> dict:
    truth = json.loads((task_dir / "hidden" / "signoff_intent_truth.json").read_text())
    g = _run_hidden_get_markers(task_dir, truth["golden_binding"], env, deadline)
    ok = bool(g["signoff_green"] and g["markers"].get("checks", {}).get("semantic_binding"))
    return {"task": task_dir.name, "healthy": ok, "signoff_green": g["signoff_green"],
            "golden_verdict_ok": bool(g["markers"].get("checks", {}).get("semantic_binding")), "error": None if ok else g.get("stdout_tail")}


def check(task_dir: Path, env: dict, deadline: float = 240.0) -> dict:
    """Score-independent full-path reference: golden binding through the full launder+signoff+grade path."""
    return check_health(task_dir, env, deadline)


def _grade_candidate(task_dir: Path, binding: dict, role: str, env: dict, deadline: float = 240.0) -> dict:
    g = _run_hidden_get_markers(task_dir, binding, env, deadline)
    sem = bool(g["markers"].get("checks", {}).get("semantic_binding")) if g["markers"] else False
    if not g["markers"]:
        return {"role": role, "total_score": None, "error": "no_markers"}
    return {"role": role, "total_score": 1.0 if sem else 0.0, "semantic_binding": sem, "signoff_green": g["signoff_green"]}


def run_block(task_dir: Path, candidates: list, env: dict, max_replacements: int = 1) -> dict:
    before = check(task_dir, env)
    graded = []
    for role, binding in candidates:
        attempt = 0
        while True:
            res = _grade_candidate(task_dir, binding, role, env)
            if FR.should_retry(res, EXPECTED.get(role), attempt, max_replacements):
                attempt += 1; continue
            graded.append(res); break
    after = check(task_dir, env)
    admissible = bool(before["healthy"] and after["healthy"])
    hard_fails = []
    if admissible:
        for res in graded:
            exp = EXPECTED.get(res["role"])
            if res.get("total_score") is not None and res["total_score"] != exp:
                hard_fails.append({"role": res["role"], "expected": exp, "got": res["total_score"]})
    return {"task": task_dir.name, "before": before, "after": after, "admissible": admissible,
            "candidates": graded, "hard_fails": hard_fails,
            "invalid_reason": (None if admissible else ("before unhealthy" if not before["healthy"] else "after unhealthy"))}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--task", required=True)
    a = ap.parse_args()
    td = REPO / "tasks" / "p15_sta_handoff" / a.task
    truth = json.loads((td / "hidden" / "signoff_intent_truth.json").read_text())
    cands = [("golden", truth["golden_binding"]), ("wrong", truth["wrong_binding_green"])]
    print(json.dumps(run_block(td, cands, _env()), indent=2))
