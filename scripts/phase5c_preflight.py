#!/usr/bin/env python3
"""Phase-5C NO-MODEL execution-path check (required before the first paid episode).
NOT a paid endpoint preflight (zero model calls) — the Qwen streaming production path is
already validated; this validates the infrastructure path only.

Checks:
  1. canonical-tree clean (git status);
  2. freeze + verify a prerun integrity manifest at HEAD (canonical hashes match);
  3. frozen schedule present + hash-stable;
  4. all 6x2 agent-facing run_public.sh commands resolve (Base + BundleS);
  5. PT (STA) + HSPICE (SPICE) health/full-path controls pass on real tools;
  6. run-state + custody destinations writable;
  7. hidden evaluator evidence inaccessible from the agent workspace.
"""
from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts")); sys.path.insert(0, str(REPO / "generators"))
import canonical_integrity as cig
import sta_fairness as STA
import hspice_health_sentinel as HS

os.environ.setdefault("EDA_TOOL_ROOT", "/data1/tongsb/eda-remote-shim/EDA")
os.environ.setdefault("B04_HOST", "tsb@b04")
os.environ.setdefault("EDA_PT_CMD", "/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/prime/V-2023.12/bin/pt_shell")
os.environ.setdefault("EDA_HSPICE_CMD", "/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/hspice/V-2023.12/hspice/bin/hspice")


def _env():
    e = dict(os.environ); e["EDA_TOOL_ROOT"] = "/data1/tongsb/eda-remote-shim/EDA"; e["B04_HOST"] = "tsb@b04"
    e["EDA_PT_CMD"] = "/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/prime/V-2023.12/bin/pt_shell"
    e["EDA_HSPICE_CMD"] = "/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/hspice/V-2023.12/hspice/bin/hspice"
    return e


def main():
    gates = {}
    # 1. clean tree
    st = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
    gates["clean_tree"] = (st == "")
    # 2. freeze + verify at HEAD
    task_roots = [str(p.relative_to(REPO)) for track in ("p15_sta_handoff", "p16_spice_handoff")
                  for p in (REPO / "tasks" / track).glob("p1*_eval_*")]
    code = ["generators/p15_sta_handoff_gen.py", "generators/p16_spice_handoff_gen.py",
            "generators/p15_sta_handoff/grade_sta_handoff.py", "generators/p16_spice_handoff/grade_spice_handoff.py",
            "eda_agentbench/evaluator/sta_handoff.py", "eda_agentbench/evaluator/spice_handoff.py",
            "scripts/phase5c_run.py", "scripts/llm_agent_driver.py", "scripts/episode_arbiter.py"]
    manifest = cig.freeze(str(REPO), task_roots, code_files=code)
    ok, inc = cig.verify(str(REPO), manifest)
    (REPO / "reports/evidence/phase5c_prerun_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    gates["canonical_hashes_match"] = ok
    # 3. schedule present + stable
    sched = REPO / "reports/evidence/phase5b_schedules/qwen24_core.json"
    sd = json.loads(sched.read_text()) if sched.is_file() else {}
    gates["schedule_present_24_position_balanced"] = (sd.get("episodes") == 24 and sd.get("position_balance_all_blocks") is True)
    # 4. 12 agent-facing commands resolve (6 instances x Base/BundleS)
    cmds_resolve = 0; need = 0
    for track in ("p15_sta_handoff", "p16_spice_handoff"):
        for inst in (REPO / "tasks" / track).glob("p1*_eval_*_base"):
            for cond in ("base", "bundles"):
                tid = inst.name.replace("_base", f"_{cond}")
                rp = REPO / "tasks" / track / tid / "files" / "run_public.sh"
                need += 1; cmds_resolve += int(rp.is_file() and os.access(rp, os.X_OK))
    gates["agent_facing_commands_resolve"] = (cmds_resolve == need and need == 12)
    # 5. PT + HSPICE health on real tools
    env = _env()
    ptd = REPO / "tasks/p15_sta_handoff/p15_eval_0001_bundles"
    hsd = REPO / "tasks/p16_spice_handoff/p16_eval_0001_bundles"
    gates["PT_health_fullpath"] = bool(ptd.is_dir() and STA.check(ptd, env)["healthy"])
    gates["HSPICE_health_fullpath"] = bool(hsd.is_dir() and HS.check_hspice_health(hsd, env, deadline=240)["healthy"])
    # 6. destinations writable
    for d in ("runs/phase5c", "reports/evidence/phase5c_episodes"):
        (REPO / d).mkdir(parents=True, exist_ok=True)
        gates[f"writable_{d.replace('/','_')}"] = os.access(REPO / d, os.W_OK)
    # 7. hidden-evidence isolation
    t = subprocess.run([sys.executable, "-m", "pytest", str(REPO / "tests/test_phase5_hidden_isolation.py"), "-q"],
                       capture_output=True, text=True, cwd=str(REPO))
    gates["hidden_evidence_isolation"] = (t.returncode == 0 and "passed" in t.stdout)
    gates["ALL_PASS"] = all(gates.values())
    print(json.dumps(gates, indent=2))
    return 0 if gates["ALL_PASS"] else 1


if __name__ == "__main__":
    sys.exit(main())
