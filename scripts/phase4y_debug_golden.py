#!/usr/bin/env python3
"""Focused debug: reproduce the fairness-gate golden regen for 0009 vs 0018 via EnvShim (exactly as
the gate does), capture the regenerated timing_report header + PT stderr. No grading."""
import sys, os, tempfile, shutil, time, subprocess
REPO = "/data1/tongsb/eda-agentbench-synthetic-phase0a"
sys.path.insert(0, REPO); sys.path.insert(0, REPO + "/scripts"); os.chdir(REPO)
import json
from pathlib import Path
from eda_agentbench.tools.detector import ToolEnvironmentDetector
from eda_agentbench.tools.env_shim import EnvShim
import phase4w_fairness_gate as G

det = ToolEnvironmentDetector(); tools = [t for t in [det.detect_one("pt")] if t and t.available]
print("pt detected:", bool(tools))
env = EnvShim(tools).get_env()
print("which pt_shell ->", shutil.which("pt_shell") or subprocess.run(["bash","-lc","which pt_shell"],capture_output=True,text=True,env=env).stdout.strip())

for tid in ("workflow_handoff_0009", "workflow_handoff_0018"):
    task = G.TRACK / tid
    fc = json.loads((task / "solution/flow_config.json").read_text())
    work = Path(tempfile.mkdtemp(prefix=f"dbg_{tid}_"))
    shutil.copytree(task / "files", work, dirs_exist_ok=True)
    shutil.copytree(task / "hidden", work, dirs_exist_ok=True)
    (work / "flow_config.json").write_text(json.dumps(fc, indent=2) + "\n")
    # run stage1 directly, capture stderr
    t0 = time.monotonic()
    r = subprocess.run(["bash", "run_evidence_stage1.sh"], cwd=str(work), env=env,
                       capture_output=True, text=True, timeout=600)
    el = time.monotonic() - t0
    tr = work / "timing_report.rpt"
    hdr = tr.read_text().splitlines()[1] if tr.is_file() else "(no timing_report)"
    print(f"\n=== {tid} golden (rc={r.returncode}, {el:.0f}s) ===")
    print("  timing_report line1:", hdr[:120])
    skip = [l for l in (r.stderr + r.stdout).splitlines() if "SKIP" in l or "pt_shell" in l or "Error" in l or "VIOLATED" in l or "cannot" in l]
    for l in skip[:6]: print("  LOG:", l[:120])
    shutil.rmtree(work, ignore_errors=True)
