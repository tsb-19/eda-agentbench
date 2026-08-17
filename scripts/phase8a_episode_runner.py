#!/usr/bin/env python3
"""Phase-8A per-episode runner, invoked by the PINNED scripts/chain_executor.py via --runner.

Why this exists. Phase-8A needs a larger retry budget than the frozen program used, because the
replacement backend throttles: measured 503 rates were 35% on back-to-back requests and 8.3% at
15 s spacing. The driver backs off 3*2^attempt, so with the frozen `--max-chat-retries 1` the two
attempts land 3 s apart -- inside the throttled regime -- and most episodes would terminate as
measurement-invalid infrastructure failures. `scripts/phase5c_run.py` passes that flag on the
command line and CLI beats env, so the retry budget cannot be raised through it.

`chain_executor.py` takes `--runner` as a parameter. That is the seam. Everything that decides
membership or semantics stays pinned and byte-identical -- chain_executor (schedule iteration,
replacement policy, canonical-integrity verification, durable state), episode_arbiter (sole
membership authority), llm_agent_driver (transport + telemetry), the p15 grader and evaluator. Only
this thin per-episode step is new, and it decides nothing: it runs one episode and writes the two
files chain_executor's classify() reads.

Raising the retry budget is the project's own rule applied, not a departure from it: an
infrastructure timeout or gateway error is measurement-invalid and must never be recorded as a
capability failure. Retries re-issue an identical request, so they cannot change task semantics, and
the arbiter still decides validity. The deviation is transport-only and is declared in
docs/phase8a_prereg.md.

CLI is dictated by chain_executor._runner_cmd:
  <runner> tasks --models CFG --track TRACK --task-ids ID --max-actions N --timeout T
           --temperature X --results DIR --concurrency 1 [--elicit-confidence] [extra...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
from eda_agentbench.agentic.runner import run_single_agentic  # noqa: E402
from eda_agentbench.task.loader import TaskLoader  # noqa: E402  (kept for parity/import checks)

DRIVER = REPO / "scripts" / "llm_agent_driver.py"
# PHASE8A_CUSTODY lets a smoke run write outside the analysis custody tree, so a test episode can
# never be mistaken for collected data.
CUSTODY = Path(os.environ.get("PHASE8A_CUSTODY",
                                   str(REPO / "phase8a" / "evidence" / "episodes")))
RUNS = REPO / "runs" / "phase8a" / "episodes"
# Transport: frozen values EXCEPT max_chat_retries, raised for the throttling backend (see docstring).
RETRIES = os.environ.get("EDA_BENCH_MAX_CHAT_RETRIES", "6")
REQ_TIMEOUT = os.environ.get("EDA_BENCH_LLM_REQUEST_TIMEOUT_SEC", "120")
REQ_DEADLINE = os.environ.get("EDA_BENCH_LLM_REQUEST_DEADLINE_SEC", "300")
RATE_IN_DEFAULT, RATE_OUT_DEFAULT = 12.0, 36.0


def _sha16(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def _edit_file_of(task_id: str) -> str:
    return "exception_config.json" if task_id.startswith("p15") else "meas_config.json"


def _rates(models_cfg: Path, model_name: str):
    try:
        for m in json.loads(models_cfg.read_text()).get("models", []):
            if m.get("name") == model_name:
                return (float(m.get("price_in_per_m", RATE_IN_DEFAULT)),
                        float(m.get("price_out_per_m", RATE_OUT_DEFAULT)))
    except Exception:  # noqa: BLE001
        pass
    return RATE_IN_DEFAULT, RATE_OUT_DEFAULT


def _cost(agentlog: dict, rate_in: float, rate_out: float) -> float:
    ti = to = 0
    u = agentlog.get("usage") or {}
    ti += int(u.get("prompt_tokens") or u.get("tokens_in") or 0)
    to += int(u.get("completion_tokens") or u.get("tokens_out") or 0)
    for r in (agentlog.get("request_telemetry") or []):
        ti += int(r.get("tokens_in") or 0)
        to += int(r.get("tokens_out") or 0)
    return round(ti * rate_in / 1e6 + to * rate_out / 1e6, 4)


def _semantic_binding(score):
    if score is None:
        return None
    for c in score.components:
        if c.name == "semantic_binding":
            return bool(c.raw_score and c.raw_score >= 1.0)
    return None


def _slot_from_results_path(results: str):
    """Recover (block_id, condition, position, rep) for this episode.

    chain_executor._runner_cmd does not pass the rep index, but it does encode the slot in the
    results directory name: `<prefix>_<block_id>_<condition>_<position>_a<attempt>/results`, where
    block_id is `8A_sta:<instance>:<model>`. Parsing that and looking the slot up in the frozen block
    schedule (PHASE8A_SCHEDULE) recovers the rep without guessing -- and it fails loudly rather than
    mislabelling an episode, because a wrong rep would corrupt the nesting the analysis depends on.
    """
    import re
    name = Path(results).parent.name
    m = re.match(r"^.*?_(?P<block>8A_[A-Za-z]+:[^:]+:[^_]+)"
                 r"_(?P<cond>Base|BundleS|TypedContract)_(?P<pos>\d+)_a(?P<att>\d+)$", name)
    if not m:
        raise SystemExit(f"phase8a_episode_runner: cannot parse slot from results dir {name!r}")
    block_id, cond, pos = m.group("block"), m.group("cond"), int(m.group("pos"))
    sched_path = os.environ.get("PHASE8A_SCHEDULE", "")
    if not sched_path or not Path(sched_path).is_file():
        raise SystemExit("phase8a_episode_runner: PHASE8A_SCHEDULE must point at the frozen "
                         "block schedule so the rep index is read, never guessed")
    slots = json.loads(Path(sched_path).read_text())["frozen_execution_order"]
    for s in slots:
        if s["block_id"] == block_id and s["position_in_block"] == pos:
            if s["condition"] != cond:
                raise SystemExit(f"phase8a_episode_runner: condition mismatch at {block_id} pos "
                                 f"{pos}: schedule says {s['condition']}, path says {cond}")
            return block_id, cond, pos, int(s["rep"])
    raise SystemExit(f"phase8a_episode_runner: no slot {block_id} pos {pos} in {sched_path}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run ONE Phase-8A episode (chain_executor --runner).")
    ap.add_argument("tasks_root")                       # positional, unused; CLI parity
    ap.add_argument("--models", required=True)
    ap.add_argument("--track", required=True)
    ap.add_argument("--task-ids", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--max-actions", type=int, default=60)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--elicit-confidence", action="store_true")
    ap.add_argument("--model-name", default=os.environ.get("PHASE8A_MODEL_NAME", "qwen3.7-max"))
    a = ap.parse_args()

    # The driver runs with CWD set to the agent workspace, so a relative --models path (which
    # chain_executor passes through verbatim) would not resolve there. Absolutise it here.
    models_abs = Path(a.models).resolve()
    if not models_abs.is_file():
        raise SystemExit(f"phase8a_episode_runner: models config not found: {a.models}")
    # Same reason: --results (and hence the --log path derived from it) must be absolute, or the
    # driver writes its agentlog relative to the agent workspace and the log is never found.
    results_abs = Path(a.results).resolve()

    task_id = a.task_ids.split(",")[0].strip()
    if a.concurrency != 1:
        raise SystemExit("phase8a_episode_runner: concurrency must be 1 (frozen design)")
    block_id, cond, pos, rep = _slot_from_results_path(a.results)

    task_path = REPO / "tasks" / a.track / task_id
    meta = json.loads((task_path / "metadata.json").read_text())
    results_base = results_abs / a.model_name / a.track
    results_base.mkdir(parents=True, exist_ok=True)
    logp = results_base / f"{task_id}.agentlog.json"

    # Deterministic runs_root so `preserved/` is findable. run_agentic_baseline.py uses a random
    # tempfile.mkdtemp(), which would leave the submitted artifact unlocatable for re-grading.
    runs_root = RUNS / f"{task_id}_r{rep}"

    agent_cmd = (f'python3 "{DRIVER}" --model "{a.model_name}" --models "{models_abs}" '
                 f'--max-actions {a.max_actions} --temperature {a.temperature} '
                 f'--stream-responses 1 --request-timeout-sec {REQ_TIMEOUT} '
                 f'--request-deadline-sec {REQ_DEADLINE} --max-chat-retries {RETRIES} '
                 f'--log "{logp}"'
                 + (" --elicit-confidence" if a.elicit_confidence else ""))

    score = None
    err = None
    try:
        runs_dir, score, ag = run_single_agentic(task_path, agent_cmd, meta,
                                                timeout=a.timeout, runs_root=runs_root)
        timed_out = bool(getattr(ag, "timed_out", False))
    except Exception as e:  # noqa: BLE001
        runs_dir, timed_out, err = None, False, f"{type(e).__name__}: {e}"

    # The two files chain_executor.classify() reads. Shape mirrors phase5c_run.py's arbiter input.
    result = {"total_score": score.total_score if score is not None else None,
              "agent": {"timed_out": timed_out},
              "task_id": task_id, "track": a.track, "model": a.model_name}
    if err:
        result["error"] = err
    (results_base / f"{task_id}.json").write_text(json.dumps(result, indent=2) + "\n")
    if not logp.is_file():
        logp.write_text(json.dumps({"error": err or "driver produced no log"}, indent=2) + "\n")

    # Per-episode custody, keyed by trial exactly as Phase-7A's evidence tree is.
    agentlog = {}
    try:
        agentlog = json.loads(logp.read_text())
    except Exception:  # noqa: BLE001
        pass
    rin, rout = _rates(models_abs, a.model_name)
    trial = f"{task_id}_r{rep}"
    ev = CUSTODY / trial
    ev.mkdir(parents=True, exist_ok=True)
    custody = {}
    ef = _edit_file_of(task_id)
    if runs_dir is not None and (Path(runs_dir) / "preserved" / ef).is_file():
        dst = ev / f"{ef[:-5]}.submitted.json"
        shutil.copy(Path(runs_dir) / "preserved" / ef, dst)
        custody[ef] = _sha16(dst)
    if runs_dir is not None and (Path(runs_dir) / "score.json").is_file():
        shutil.copy(Path(runs_dir) / "score.json", ev / "result.json")
        custody["result.json"] = _sha16(ev / "result.json")
    if logp.is_file():
        shutil.copy(logp, ev / "agentlog.sanitized.json")
        custody["agentlog.sanitized.json"] = _sha16(ev / "agentlog.sanitized.json")
    (ev / "SHA256SUMS").write_text("\n".join(f"{h}  {n}" for n, h in custody.items()) + "\n")
    (ev / "episode.json").write_text(json.dumps({
        "trial": trial, "task_id": task_id, "track": a.track, "family": "A_sta",
        "rep": rep, "condition": cond, "position_in_block": pos,
        "block_id": block_id, "model_name": a.model_name, "total_cost": _cost(agentlog, rin, rout),
        "rates_cny_per_M": {"input": rin, "output": rout},
        "transport": {"max_chat_retries": int(RETRIES), "stream_responses": True,
                      "request_inactivity_timeout_sec": int(REQ_TIMEOUT),
                      "hard_request_deadline_sec": int(REQ_DEADLINE)},
        "custody": custody, "semantic_binding": _semantic_binding(score),
        "total_score": result["total_score"], "error": err,
    }, indent=2) + "\n")

    print(json.dumps({"trial": trial, "total_score": result["total_score"],
                      "cost": _cost(agentlog, rin, rout), "error": err}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
