#!/usr/bin/env python3
"""Phase-4W real-PrimeTime fairness gate: 4 candidates x 6 tasks, full vectors, WITH per-candidate
evidence regeneration.

For each candidate the harness STAGES a workspace, sets the candidate flow_config, REGENERATES the
evidence (run_evidence_stage1.sh + run_evidence_stage2.sh via real PT) so the submitted evidence is
consistent with the candidate binding, then grades through the official path (_evaluate_single ->
run_public.sh + run_hidden.sh). This makes evidence_generation reflect the candidate's actual binding
(so a wrong-axis candidate is rejected by typed-binding, not by stale-evidence mismatch).

Candidates: golden, wrong_axis, stale_decoy, unchanged_mutant.
Tasks: 0009, 0010 (source), 0011, 0012 (held-out), 0013 (V1), 0014 (V9).

Output: reports/evidence/p14_phase4w_fairness/gate_results.json
Requires: source <eda-remote-shim>/env.sh (EDA_TOOL_ROOT, B04_HOST).
"""
import json, sys, tempfile, copy, subprocess, shutil, os
from pathlib import Path
sys.path.insert(0, ".")
from eda_agentbench.task.loader import TaskLoader
from eda_agentbench.tools.detector import ToolEnvironmentDetector
from eda_agentbench.tools.env_shim import EnvShim
from run_model_baseline import _grade_one

REPO = Path(".")
TRACK = REPO / "tasks/p14_workflow_handoff"
OUT = REPO / "reports/evidence/p14_phase4w_fairness"
TASKS = ["workflow_handoff_0009", "workflow_handoff_0010", "workflow_handoff_0011",
         "workflow_handoff_0012", "workflow_handoff_0013", "workflow_handoff_0014"]
CANDIDATES = ["golden", "wrong_axis", "stale_decoy", "unchanged_mutant"]
EDITABLE = ["flow_config.json", "constraints.sdc", "timing_report.rpt", "evidence_manifest.json", "stage2_summary.json"]

def build_candidate_fc(task: Path, name: str) -> dict:
    golden = json.loads((task / "solution/flow_config.json").read_text())
    mutant = json.loads((task / "files/flow_config.json").read_text())
    if name == "golden": return golden
    if name == "unchanged_mutant": return mutant
    if name == "wrong_axis":
        fc = copy.deepcopy(golden); fc["scenario"] = mutant["scenario"]; fc["corner"] = mutant["corner"]; return fc
    if name == "stale_decoy":
        fc = copy.deepcopy(golden); fc["netlist"] = mutant["netlist"]; return fc
    raise ValueError(name)

def regen_evidence(work: Path, env: dict, timeout: int = 300):
    """Run stage1 + stage2 in the workspace to regenerate evidence for the current flow_config."""
    for script in ("run_evidence_stage1.sh", "run_evidence_stage2.sh"):
        sp = work / script
        if not sp.exists(): raise RuntimeError(f"missing {script} in workspace")
        r = subprocess.run(["bash", script], cwd=str(work), env=env, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            raise RuntimeError(f"{script} rc={r.returncode}: {r.stderr[-300:]}")

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    loader = TaskLoader(REPO)
    # build the tool env once (pt_shell on PATH via EnvShim mirror tree)
    det = ToolEnvironmentDetector()
    tools = [t for tn in ["pt"] for t in [det.detect_one(tn)] if t and t.available]
    if not tools:
        print("FATAL: pt tool not detected"); sys.exit(2)
    env = EnvShim(tools).get_env()
    runs_root = Path(tempfile.mkdtemp(prefix="phase4w_gate_runs_"))
    results = {}
    for tid in TASKS:
        task = TRACK / tid
        meta = loader.load(task)
        results[tid] = {"task_id": tid, "candidates": {}}
        for cand in CANDIDATES:
            fc = build_candidate_fc(task, cand)
            # stage workspace: files/ + hidden/
            work = Path(tempfile.mkdtemp(prefix=f"ev_{tid}_{cand}_"))
            shutil.copytree(task / "files", work, dirs_exist_ok=True)
            shutil.copytree(task / "hidden", work, dirs_exist_ok=True)
            (work / "flow_config.json").write_text(json.dumps(fc, indent=2) + "\n")
            try:
                regen_evidence(work, env, meta.get("timeout_sec", 300))
                # submission = the regenerated editables
                sub = Path(tempfile.mkdtemp(prefix=f"sub_{tid}_{cand}_"))
                for ef in EDITABLE:
                    src = work / ef
                    if src.exists(): shutil.copy2(src, sub / ef)
                res = _grade_one(task, sub, runs_root / tid)
            except Exception as e:
                res = {"ok": False, "total_score": None, "passed": None, "error": f"{type(e).__name__}: {e}"}
            res["submitted"] = {k: fc.get(k) for k in ("netlist", "scenario", "corner")}
            res["candidate"] = cand
            results[tid]["candidates"][cand] = res
            comps = {c["name"]: round(c["raw"], 2) for c in res.get("components", [])}
            print(f"[{tid}] {cand:16s} score={res.get('total_score')} passed={res.get('passed')} "
                  f"sub={res['submitted']} signoff={comps.get('signoff')} evgen={comps.get('evidence_generation')} "
                  f"typed={comps.get('typed_binding_score', comps.get('axis_schema_score'))} err={res.get('error')}",
                  flush=True)
            shutil.rmtree(work, ignore_errors=True)
    (OUT / "gate_results.json").write_text(json.dumps(results, indent=2) + "\n")
    print("\n=== SUMMARY (score | signoff/evidence_gen) ===", flush=True)
    for tid in TASKS:
        row = []
        for cand in CANDIDATES:
            r = results[tid]["candidates"][cand]
            comps = {c["name"]: c["raw"] for c in r.get("components", [])}
            row.append(f"{cand[:6]}={r.get('total_score')}:{comps.get('signoff')}/{comps.get('evidence_generation')}")
        print(f"{tid}: " + "  ".join(row), flush=True)

if __name__ == "__main__":
    main()
