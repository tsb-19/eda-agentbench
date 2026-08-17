#!/usr/bin/env python3
"""Phase-8A NO-MODEL preflight (required before the first paid episode).

Zero model calls except one metadata listing (`GET /v1/models`), which is not billed and is the
only way to prove the replacement backend actually serves the two model IDs before committing ¥200
to it. No `/chat/completions` request is made here.

Gates, all fail-closed:
   1. canonical tree clean (git status);
   2. the preregistration exists in BOTH languages and its sha256 is recorded;
   3. freeze + verify a prerun canonical-integrity manifest at HEAD;
   4. the frozen arm-1 schedule is present, 216 episodes, position-balanced, and reproduces;
   5. all 36 agent-facing run_public.sh commands resolve (12 instances x 3 conditions);
   6. PrimeTime health/full-path control passes on the real tool, and its version matches the
      version recorded in the frozen custody records (apparatus drift check);
   7. the entry the PINNED runner resolves points at the replacement backend, the gateway
      credential file exists, and the backend serves that exact model ID;
   8. run-state + custody destinations writable;
   9. hidden evaluator evidence is unreachable from the agent workspace;
  10. the frozen membership baseline and all four frozen analyses are untouched;
  11. no Phase-8A artefact exists anywhere under reports/ (it would pollute the frozen pin scan).

Writes phase8a/evidence/preflight.json. Exit 0 only if every gate passes.

All Phase-8A artefacts live OUTSIDE reports/, because frozen_membership_verify.py scans all of
reports/ for `path -> sha256` pairs: a custody record written there would inflate the frozen pin
count (1065 -> 1979 when first tried) and mask a real mismatch. See phase8a/README.md.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "generators"))
import canonical_integrity as cig  # noqa: E402
import sta_fairness as STA  # noqa: E402
import phase7a_sta12_specs as SPECS  # noqa: E402

TOOL_ROOT = "/data1/tongsb/eda-remote-shim/EDA"
PT_CMD = f"{TOOL_ROOT}/soft2/synopsys/prime/V-2023.12/bin/pt_shell"
HS_CMD = f"{TOOL_ROOT}/soft2/synopsys/hspice/V-2023.12/hspice/bin/hspice"
# The PrimeTime build the frozen episodes ran on (recorded 495x under reports/evidence/).
FROZEN_PT_VERSION = "S-2021.06-SP5"
CONDITIONS = {"Base": "base", "BundleS": "bundles", "TypedContract": "typedcontract"}
RUNNER_MODEL_NAME = "Qwen3.7-Max"   # hardcoded in the pinned scripts/phase5c_run.py:46
INFO_MODELS = ("Qwen3.7-Max-TR", "DeepSeek-V4-Pro-TR")  # informational duplicates
TR_BASE = "https://tokenrhythm.studio/v1"
GATEWAY = REPO / "phase8a" / "gateway.env"
P8A = REPO / "phase8a" / "evidence"
OUT = P8A / "preflight.json"


def _env():
    e = dict(os.environ)
    e["EDA_TOOL_ROOT"] = TOOL_ROOT
    e["B04_HOST"] = e.get("B04_HOST", "tsb@b04")
    e["EDA_PT_CMD"] = PT_CMD
    e["EDA_HSPICE_CMD"] = HS_CMD
    return e


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _dotenv():
    """Read .env into a dict WITHOUT printing any value."""
    out = {}
    f = REPO / ".env"
    if f.is_file():
        for line in f.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                out[k.strip()] = v.strip().strip("'\"")
    return out


def _pt_version(env) -> str:
    """Read PrimeTime's version banner. No design is loaded.

    CRITICAL -- cwd MUST be outside the repository. The pt_shell on PATH is a forwarder to host
    b04 (`/data1/tongsb/eda-remote-shim/bin/forwarder`), and it syncs the CURRENT WORKING DIRECTORY
    from the remote copy. Invoking it from the repo root therefore RESURRECTS files that b04 still
    holds but that have been deleted locally, with their original mtimes intact. That is how three
    stray `reports/evidence/phase8a_*` leftovers from an early draft of this script kept
    reappearing, driving the frozen pin count from 1065 to 1979 and silently resolving one of the
    two expected mismatches.

    The sync is additive: it restores remote-only files but never deletes local files nor reverts
    local edits (verified). `sta_fairness.check` is unaffected because it runs task-scoped rather
    than from the repo root.

    This is the same class of hazard as docs/incident_golden_corruption.md -- a remote tool path
    writing into the canonical tree, where the naive attribution is "the script is buggy".
    """
    import re
    import tempfile
    with tempfile.TemporaryDirectory(prefix="p8a_ptver_") as tmp:
        tcl = Path(tmp) / "v.tcl"
        tcl.write_text('puts "PTVER=[get_app_var sh_product_version]"\nquit\n')
        try:
            r = subprocess.run([PT_CMD, "-f", str(tcl)], capture_output=True, text=True,
                               timeout=300, env=env, cwd=tmp)
            blob = r.stdout + r.stderr
        except Exception as e:  # noqa: BLE001
            return f"unavailable:{type(e).__name__}"
    m = re.search(r"PTVER=([STV]-20\d{2}\.\d{2}(?:-SP\d+)?)", blob)
    return m.group(1) if m else "unparsed"


def _backend_serves(models_needed) -> dict:
    """GET /v1/models -- metadata only, zero tokens billed, no /chat/completions."""
    key = os.environ.get("TR_API_KEY") or _dotenv().get("TR_API_KEY", "")
    if not key:
        return {"credential_present": False, "served": {}, "http": None}
    req = urllib.request.Request(f"{TR_BASE}/models",
                                headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            body = json.loads(r.read().decode())
            code = r.status
    except Exception as e:  # noqa: BLE001
        return {"credential_present": True, "served": {}, "http": f"error:{type(e).__name__}"}
    ids = {m.get("id") for m in body.get("data", [])}
    return {"credential_present": True, "http": code,
            "served": {m: (m in ids) for m in models_needed}}


def main() -> int:
    gates, detail = {}, {}

    # 1. clean tree
    st = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"],
                        capture_output=True, text=True).stdout.strip()
    gates["clean_tree"] = (st == "")
    detail["dirty_paths"] = st.splitlines()[:10]

    # 2. preregistration present in both languages, hashed
    prereg = REPO / "docs/phase8a_prereg.md"
    prereg_zh = REPO / "docs/phase8a_prereg.zh.md"
    gates["prereg_bilingual_present"] = prereg.is_file() and prereg_zh.is_file()
    detail["prereg_sha256"] = {
        "docs/phase8a_prereg.md": _sha(prereg) if prereg.is_file() else None,
        "docs/phase8a_prereg.zh.md": _sha(prereg_zh) if prereg_zh.is_file() else None,
    }

    # 3. canonical integrity manifest at HEAD
    task_roots = [str(p.relative_to(REPO))
                  for p in (REPO / "tasks/p15_sta_handoff").glob("p15_eval_*")]
    code = ["generators/p15_sta_handoff_gen.py",
            "generators/p15_sta_handoff/grade_sta_handoff.py",
            "eda_agentbench/evaluator/sta_handoff.py",
            "scripts/llm_agent_driver.py", "scripts/episode_arbiter.py",
            "scripts/chain_executor.py", "scripts/fairness_retry.py",
            "scripts/measurement_control.py"]
    manifest = cig.freeze(str(REPO), task_roots, code_files=code)
    ok, _inc = cig.verify(str(REPO), manifest)
    P8A.mkdir(parents=True, exist_ok=True)
    (P8A / "prerun_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    gates["canonical_hashes_match"] = bool(ok)

    # 4. frozen schedule present, correct size, balanced, reproduces
    sched = P8A / "schedule_arm1.json"
    sd = json.loads(sched.read_text()) if sched.is_file() else {}
    rc = subprocess.run([sys.executable, str(REPO / "scripts/phase8a_schedule.py"),
                         "--model", "Qwen3.7-Max-TR", "--reps", "6", "--arm", "1", "--check"],
                        capture_output=True, text=True, cwd=str(REPO)).returncode
    gates["schedule_216_balanced_reproduces"] = (
        sd.get("episodes") == 216 and sd.get("blocks") == 12
        and sd.get("reps_per_condition") == 6
        and sd.get("position_balance_all_blocks") is True and rc == 0)
    detail["schedule_sha256"] = _sha(sched) if sched.is_file() else None

    # 5. all 36 agent-facing commands resolve
    need = resolved = 0
    for tid, *_ in SPECS.STA12_SPECS:
        for suffix in CONDITIONS.values():
            rp = REPO / "tasks/p15_sta_handoff" / f"{tid}_{suffix}" / "files" / "run_public.sh"
            need += 1
            resolved += int(rp.is_file() and os.access(rp, os.X_OK))
    gates["agent_facing_commands_resolve"] = (need == 36 and resolved == 36)
    detail["run_public_resolved"] = f"{resolved}/{need}"

    # 6. PrimeTime health + version match (apparatus drift check)
    env = _env()
    ptd = REPO / "tasks/p15_sta_handoff/p15_eval_0004_bundles"
    try:
        gates["PT_health_fullpath"] = bool(ptd.is_dir() and STA.check(ptd, env)["healthy"])
    except Exception as e:  # noqa: BLE001
        gates["PT_health_fullpath"] = False
        detail["PT_health_error"] = f"{type(e).__name__}: {e}"
    ver = _pt_version(env)
    gates["PT_version_matches_frozen"] = (ver == FROZEN_PT_VERSION)
    detail["PT_version"] = {"live": ver, "frozen_record": FROZEN_PT_VERSION}

    # 7. the entry the PINNED runner will actually resolve, plus backend liveness.
    # scripts/phase5c_run.py hardcodes MODEL_NAME='Qwen3.7-Max', so checking any other entry would
    # verify something the run does not use.
    cfg_path = REPO / "configs/baseline_models.json"
    cfg = json.loads(cfg_path.read_text()) if cfg_path.is_file() else {"models": []}
    by_name = {m.get("name"): m for m in cfg.get("models", [])}
    envd = _dotenv()
    gw = {}
    if GATEWAY.is_file():
        for line in GATEWAY.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                gw[k.strip()] = v.strip().strip("'\"")

    spec = by_name.get(RUNNER_MODEL_NAME, {})
    resolved_base = spec.get("api_base") or (
        gw.get(spec.get("api_base_env", ""), "").rstrip("/") + spec.get("api_base_suffix", ""))
    model_id = spec.get("model_id", "")
    gates["gateway_env_present"] = bool(gw.get("API_KEY") and gw.get("BASE_URL"))
    gates["runner_entry_resolves_to_replacement_backend"] = (resolved_base == TR_BASE
                                                             and bool(model_id))
    detail["runner_model_resolution"] = {
        "runner": "scripts/phase5c_run.py",
        "hardcoded_model_name": RUNNER_MODEL_NAME,
        "resolved_api_base": resolved_base,
        "resolved_model_id": model_id,
        "temperature": spec.get("temperature"),
        "max_tokens": spec.get("max_tokens"),
        "rates_cny_per_M": {"input": spec.get("price_in_per_m"),
                            "output": spec.get("price_out_per_m")},
        "credential_env": spec.get("api_key_env"),
        "gateway_file": str(GATEWAY.relative_to(REPO)),
    }

    wanted = sorted({model_id} | {by_name[n]["model_id"] for n in INFO_MODELS if n in by_name})
    backend = _backend_serves([m for m in wanted if m])
    gates["backend_serves_the_runner_model"] = bool(
        backend.get("http") == 200 and backend.get("served", {}).get(model_id) is True)
    detail["backend"] = backend
    detail["frozen_endpoint_note"] = (
        "the frozen endpoint llmapi.paratera.com no longer entitles this account to these models "
        "(403); Phase-8A episodes are therefore a different measurement and are never pooled with "
        "the frozen 72 -- see docs/phase8a_prereg.md section 1.1")
    _ = envd

    # 8. destinations writable
    for d in ("runs/phase8a", "phase8a/evidence/episodes"):
        (REPO / d).mkdir(parents=True, exist_ok=True)
        gates[f"writable_{d.replace('/', '_')}"] = os.access(REPO / d, os.W_OK)

    # 9. hidden-evidence isolation
    t = subprocess.run([sys.executable, "-m", "pytest",
                        str(REPO / "tests/test_phase5_hidden_isolation.py"), "-q"],
                       capture_output=True, text=True, cwd=str(REPO))
    gates["hidden_evidence_isolation"] = (t.returncode == 0)

    # 10. nothing frozen moved
    checks = {
        "frozen_membership": [sys.executable, "scripts/frozen_membership_verify.py",
                              "--expect", "docs/frozen_membership_baseline.json"],
        "phase7c_study1_ledger": [sys.executable, "scripts/phase7c_study1_ledger.py", "--check"],
        "phase7c_claim_statistics": [sys.executable, "scripts/phase7c_claim_statistics.py", "--check"],
        "phase7d_semantic_proxy_gap": [sys.executable, "scripts/phase7d_semantic_proxy_gap.py", "--check"],
        "phase7e_answer_identifiability": [sys.executable, "scripts/phase7e_answer_identifiability.py", "--check"],
    }
    for name, cmd in checks.items():
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
        gates[f"frozen_intact_{name}"] = (r.returncode == 0)

    # 11. no Phase-8A artefact may exist anywhere under reports/.
    # This is not hygiene. frozen_membership_verify.py scans ALL of reports/ for `path -> sha256`
    # pairs; an early draft of this preflight wrote its prerun manifest to reports/evidence/ and
    # drove the frozen pin count from 1065 to 1979, which also silently RESOLVED one of the two
    # expected mismatches -- i.e. a Phase-8A file masked a real property of the frozen set. The
    # rule is written down in phase8a/README.md; this gate makes the code assert it.
    strays = sorted(str(p.relative_to(REPO)) for p in (REPO / "reports").rglob("*phase8a*"))
    gates["no_phase8a_artifact_under_reports"] = (strays == [])
    detail["phase8a_strays_under_reports"] = strays

    gates["ALL_PASS"] = all(gates.values())
    payload = {"schema": "phase8a_preflight/v1", "model_calls_made": 0,
               "metadata_listings_made": 1, "gates": gates, "detail": detail}
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"ALL_PASS": gates["ALL_PASS"],
                      "failed": [k for k, v in gates.items() if not v and k != "ALL_PASS"]},
                     indent=2))
    return 0 if gates["ALL_PASS"] else 1


if __name__ == "__main__":
    sys.exit(main())
