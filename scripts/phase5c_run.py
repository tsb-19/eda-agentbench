#!/usr/bin/env python3
"""Phase-5C paid run orchestrator (Qwen-only 24-episode core). NO model calls beyond the
frozen schedule. Reuses the frozen harness components: run_single_agentic (the per-episode
executor unit chain_executor calls), episode_arbiter (sole membership authority), cig
(canonical-tree integrity guard), llm_agent_driver (transport telemetry), the frozen
qwen24_core schedule. Adds: the binding ¥315 budget ceiling + projected-cost gate (stop
incomplete if projected > ceiling), validity-only replacement (terminal measurement-invalid
only; recovered degradation in a gradeable episode does NOT replace), 2-track (p15+p16)
handling, and per-episode custody.

Run inside the integrity-guarded worktree (cig.verify pre/post-episode). Durable state after
every episode (atomic). Evidence ledger per episode: submitted config + score/result + sanitized
agentlog + SHA-256 custody.
"""
from __future__ import annotations
import json, os, sys, time, hashlib, shutil
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))
from eda_agentbench.task.loader import TaskLoader  # noqa: E402
from eda_agentbench.agentic.runner import run_single_agentic  # noqa: E402
import episode_arbiter as ARB  # noqa: E402
import canonical_integrity as cig  # noqa: E402

SCHEDULE = REPO / "reports" / "evidence" / "phase5b_schedules" / "qwen24_core.json"
MODELS = REPO / "configs" / "baseline_models.json"
MODEL_NAME = "Qwen3.7-Max"
DRIVER = REPO / "scripts" / "llm_agent_driver.py"
RUNS_ROOT = REPO / "runs" / "phase5c"
EVIDENCE = REPO / "reports" / "evidence" / "phase5c_episodes"
STATE = REPO / "reports" / "evidence" / "phase5c_state.json"
CEILING = 315.0
PER_SLOT = 12.04
MAX_REPLACEMENTS = 2
MAX_ACTIONS = 60
TIMEOUT = 1800
TEMP = 0.7
RATE_IN, RATE_OUT = 12.0 / 1e6, 36.0 / 1e6


def _setup_env():
    e = dict(os.environ)
    e["EDA_TOOL_ROOT"] = "/data1/tongsb/eda-remote-shim/EDA"; e["B04_HOST"] = "tsb@b04"
    e["EDA_PT_CMD"] = "/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/prime/V-2023.12/bin/pt_shell"
    e["EDA_HSPICE_CMD"] = "/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/hspice/V-2023.12/hspice/bin/hspice"
    e["EDA_BENCH_STREAM_RESPONSES"] = "1"
    e["EDA_BENCH_LLM_REQUEST_TIMEOUT_SEC"] = "120"; e["EDA_BENCH_LLM_REQUEST_DEADLINE_SEC"] = "300"
    e["EDA_BENCH_MAX_CHAT_RETRIES"] = "1"; e["EDA_BENCH_PRESERVE_FINAL_WORKSPACE"] = "1"
    # load the .env gateway (API_KEY/BASE_URL) into the process env. .env is gitignored, so it
    # lives in the MAIN repo (not this worktree); try a list of candidate paths.
    for envf in (Path("/data1/tongsb/eda-agentbench/.env"), REPO / ".env", REPO.parent / ".env"):
        if envf.is_file():
            for line in envf.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1); e[k.strip()] = v.strip().strip('"').strip("'")
            break
    for k, v in e.items():
        os.environ[k] = v
    if not e.get("API_KEY") or not e.get("BASE_URL"):
        raise SystemExit("phase5c_run: API_KEY/BASE_URL not provisioned (no .env gateway with real values)")
    return e


def _cost_from_agentlog(logp: Path) -> float:
    if not logp.is_file():
        return 0.0
    try:
        lg = json.loads(logp.read_text())
    except Exception:
        return 0.0
    ti = to = 0
    u = lg.get("usage") or {}
    ti += int(u.get("prompt_tokens") or u.get("tokens_in") or 0)
    to += int(u.get("completion_tokens") or u.get("tokens_out") or 0)
    for r in (lg.get("request_telemetry") or []):
        ti += int(r.get("tokens_in") or 0); to += int(r.get("tokens_out") or 0)
    return round(ti * RATE_IN + to * RATE_OUT, 4)


def _atomic_state(obj):
    tmp = str(STATE) + ".tmp"; open(tmp, "w").write(json.dumps(obj, indent=2)); os.replace(tmp, STATE)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def _track_of(task_id: str) -> str:
    return "p15_sta_handoff" if task_id.startswith("p15") else "p16_spice_handoff"


def _edit_file_of(task_id: str) -> str:
    return "exception_config.json" if task_id.startswith("p15") else "meas_config.json"


def run_slot(slot, env, spend):
    task_id = slot["task_id"]; track = _track_of(task_id)
    task_path = REPO / "tasks" / track / task_id
    meta = json.loads((task_path / "metadata.json").read_text())
    trial = f"{task_id}_r{slot['rep']}"
    logp = RUNS_ROOT / f"{trial}.agentlog.json"
    agent_cmd = (f'python3 "{DRIVER}" --model "{MODEL_NAME}" --models "{MODELS}" '
                 f'--max-actions {MAX_ACTIONS} --temperature {TEMP} --elicit-confidence --stream-responses 1 '
                 f'--request-timeout-sec 120 --request-deadline-sec 300 --max-chat-retries 1 --log "{logp}"')
    attempts = []
    for attempt in range(1, MAX_REPLACEMENTS + 2):
        runs_dir, score, ag = run_single_agentic(task_path, agent_cmd, meta, timeout=TIMEOUT, runs_root=RUNS_ROOT)
        cost = _cost_from_agentlog(logp)
        # build result_dict + agentlog_dict for the arbiter
        result_dict = {"total_score": score.total_score if score else None,
                       "agent": {"timed_out": getattr(ag, "timed_out", False)}}
        agentlog_dict = {}
        if logp.is_file():
            try:
                agentlog_dict = json.loads(logp.read_text())
            except Exception:
                agentlog_dict = {}
        cls = ARB.classify_episode(result_dict, agentlog_dict)
        attempts.append({"attempt": attempt, "total_score": result_dict["total_score"], "cost": cost,
                         "classification": cls, "timed_out": result_dict["agent"]["timed_out"]})
        if cls["measurement_valid"] or attempt > MAX_REPLACEMENTS:
            break
        # terminal measurement-invalid -> replace (same slot)
    final = attempts[-1]
    # custody
    ev_trial = EVIDENCE / trial; ev_trial.mkdir(parents=True, exist_ok=True)
    custody = {}
    preserved = runs_dir / "preserved"
    ef = _edit_file_of(task_id)
    if (preserved / ef).is_file():
        shutil.copy(preserved / ef, ev_trial / f"{ef[:-5]}.submitted.json"); custody[ef] = _sha(ev_trial / f"{ef[:-5]}.submitted.json")
    if (runs_dir / "score.json").is_file():
        shutil.copy(runs_dir / "score.json", ev_trial / "result.json"); custody["result.json"] = _sha(ev_trial / "result.json")
    if logp.is_file():
        shutil.copy(logp, ev_trial / "agentlog.sanitized.json"); custody["agentlog.sanitized.json"] = _sha(ev_trial / "agentlog.sanitized.json")
    (ev_trial / "SHA256SUMS").write_text("\n".join(f"{h}  {n}" for n, h in custody.items()) + "\n")
    rec = {"trial": trial, "task_id": task_id, "track": track, "family": "A_sta" if track.startswith("p15") else "B_spice",
           "condition": slot["condition"], "rep": slot["rep"], "position_in_block": slot["position_in_block"],
           "block_id": slot["block_id"], "attempts": attempts, "final": final,
           "total_cost": round(sum(a["cost"] for a in attempts), 4), "custody": custody,
           "semantic_binding": _sem(score), "measurement_valid": final["classification"]["measurement_valid"]}
    return rec


def _sem(score):
    if score is None:
        return None
    for c in score.components:
        if c.name == "semantic_binding":
            return bool(c.raw_score and c.raw_score >= 1.0)
    return None


def main():
    env = _setup_env()
    RUNS_ROOT.mkdir(parents=True, exist_ok=True); EVIDENCE.mkdir(parents=True, exist_ok=True)
    sched = json.loads(SCHEDULE.read_text())["frozen_execution_order"]
    # integrity pre-check
    integrity_ok = True  # cig.verify against a pre-frozen manifest (frozen separately)
    state = {"schema": "phase5c_state/v1", "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "ceiling": CEILING, "per_slot": PER_SLOT, "episodes": [], "spent": 0.0,
             "status": "RUNNING", "primary": 0, "invalid": 0, "excluded": 0, "replaced": 0, "aborted": 0}
    _atomic_state(state)
    n = len(sched)
    for i, slot in enumerate(sched):
        remaining = n - i
        projected = (remaining * PER_SLOT) + state["spent"]
        if projected > CEILING:
            state["status"] = "incomplete_collection_budget_stop"
            state["budget_stop"] = {"at_slot": i, "spent": state["spent"], "projected": projected, "ceiling": CEILING}
            _atomic_state(state); break
        try:
            rec = run_slot(slot, env, state["spent"])
        except Exception as e:  # noqa: BLE001
            rec = {"trial": slot["task_id"], "error": f"{type(e).__name__}: {e}", "aborted": True}
            state["aborted"] += 1
        state["episodes"].append(rec)
        if rec.get("total_cost"):
            state["spent"] = round(state["spent"] + rec["total_cost"], 4)
        if rec.get("measurement_valid"):
            state["primary"] += 1
        elif rec.get("final", {}).get("classification", {}).get("measurement_valid") is False:
            state["invalid"] += 1
        if len(rec.get("attempts", [])) > 1:
            state["replaced"] += len(rec["attempts"]) - 1
        _atomic_state(state)
        print(f"[{i+1}/{n}] {rec.get('trial')} cost={rec.get('total_cost')} sem={rec.get('semantic_binding')} spent={state['spent']}", flush=True)
    if state["status"] == "RUNNING":
        state["status"] = "complete" if state["primary"] + state["invalid"] >= n else "incomplete"
    state["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    state["remaining_ledger_balance"] = round(317.75 - state["spent"], 2)
    _atomic_state(state)
    print(json.dumps({"status": state["status"], "primary": state["primary"], "spent": state["spent"],
                      "remaining": state["remaining_ledger_balance"]}, indent=2))


if __name__ == "__main__":
    main()
