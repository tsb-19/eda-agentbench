#!/usr/bin/env python3
"""Agentic baseline orchestrator — run the baseline models UNDER FULL TOOLS.

Pairs with scripts/llm_agent_driver.py. For each (task, model) it invokes the
existing two-phase agentic runner (eda_agentbench.agentic.runner.run_single_agentic)
with the LLM driver as the agent command, so the model gets real tools + iteration
while the runner keeps hidden/solution out of the workspace and withholds the
verdict. Writes one result JSON per (model, track, task) in the SAME shape as
scripts/run_model_baseline.py, so scan_discrimination.py and the leaderboard work
unchanged on the output.

Must be run where the EDA tools resolve (source the shim env first) AND where the
gateway/.env is reachable (the driver makes the API calls). Concurrency is low by
default: every episode can hit b04 several times (each `bash run_public.sh` the
model runs, plus grading), so it is bounded by license seats, not CPU.

    source /data1/tongsb/eda-remote-shim/env.sh
    python3 scripts/run_agentic_baseline.py pilot_or_tasks_root \
        --models configs/baseline_models.json --track p7_primetime_sta_debug \
        --limit 4 --max-actions 12 --timeout 1200 --concurrency 2 \
        --results runs/agentic_p7/results
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from eda_agentbench.task.loader import TaskLoader  # noqa: E402
from eda_agentbench.agentic.runner import run_single_agentic  # noqa: E402
from eda_agentbench import reliability as R  # noqa: E402
from scripts.generate_model_submissions import load_model_specs, sample_tasks  # noqa: E402
from scripts.scan_discrimination import CONTINUOUS_COMPONENTS  # noqa: E402

DRIVER = REPO / "scripts" / "llm_agent_driver.py"


def _agentic_reliability_block(logp: Path, *, passed, clean: bool, timed_out: bool,
                               run_error=None) -> dict:
    """Join one episode's driver log (confidence + episode signals) with the runner-side outcome
    (anti-cheat, timeout) into the canonical reliability block, mirroring single-shot
    run_model_baseline._reliability_block. Protocol status is meaningful even without confidence
    elicitation (NOCOMMIT / BUDGET_EXHAUSTED / ANTI_CHEAT / infra), so this is always emitted."""
    lg: dict = {}
    if logp and Path(logp).is_file():
        try:
            lg = json.loads(Path(logp).read_text())
        except Exception:  # noqa: BLE001
            lg = {}
    error = run_error or lg.get("error")
    actions = lg.get("actions") or []
    n_valid = sum(1 for a in actions if a.get("type") in ("run", "write", "finish"))
    conf = lg.get("confidence", "")
    proto = R.agentic_protocol(
        clean=clean, error=error, timed_out=timed_out, finished=bool(lg.get("finished")),
        n_edits=len(lg.get("edited") or []), n_actions=len(actions),
        n_valid_actions=n_valid if actions else None)
    graded = None if (proto != "ok" or conf == "abstain" or passed is None) else bool(passed)
    b = R.calibration_bucket(graded, conf)
    return {"confidence_decision": conf, "confidence_format_ok": lg.get("confidence_format_ok"),
            "protocol_status": proto, "overconfident_wrong": b == "overconfident_wrong",
            "underconfident_correct": b == "underconfident_correct", "abstained": b == "abstain"}


def _cost_block(logp: Path, wall_time_sec=None) -> dict:
    """Secondary cost metrics for one episode, from the driver log: tokens, tool calls (RUN/WRITE),
    transient retries, and the agent's wall time. Reported alongside reliability (scope point 6)."""
    lg: dict = {}
    if logp and Path(logp).is_file():
        try:
            lg = json.loads(Path(logp).read_text())
        except Exception:  # noqa: BLE001
            lg = {}
    u = lg.get("usage", {})
    tool_calls = sum(1 for a in (lg.get("actions") or []) if a.get("type") in ("run", "write"))
    return {"tokens_in": u.get("prompt_tokens", 0), "tokens_out": u.get("completion_tokens", 0),
            "tool_calls": tool_calls, "retries": lg.get("retries", 0),
            "wall_time_sec": wall_time_sec}


def _result_dict(score, agentic, name, track, task_id) -> dict:
    """Mirror run_model_baseline._grade_one output so the scan/leaderboard match."""
    return {
        "ok": True,
        "total_score": score.total_score,
        "passed": score.passed,
        "objective_score": getattr(score, "objective_score", None),
        "components": [{"name": c.name, "raw": c.raw_score, "weight": c.weight}
                       for c in score.components],
        "anti_cheat": score.anti_cheat,
        "agent": {
            "exit_code": agentic.agent_exit_code,
            "timed_out": agentic.agent_timed_out,
            "anti_cheat_clean": agentic.anti_cheat_clean,
            "wall_time_sec": agentic.agent_wall_time_sec,
        },
        "error": None, "model": name, "track": track, "task_id": task_id, "mode": "agentic",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run baseline models agentically (full tools).")
    ap.add_argument("tasks_root")
    ap.add_argument("--models", required=True, help="baseline_models.json")
    ap.add_argument("--track", default=None)
    ap.add_argument("--sample-per-track", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--limit", type=int, default=None, help="Cap total tasks")
    ap.add_argument("--task-ids", default=None,
                    help="Comma-separated task_ids to run EXACTLY (overrides sampling; "
                         "use to task-match a prior single-shot run)")
    ap.add_argument("--max-actions", type=int, default=12)
    ap.add_argument("--timeout", type=int, default=1200, help="Per-episode wall budget (sec)")
    ap.add_argument("--results", required=True)
    ap.add_argument("--concurrency", type=int, default=2,
                    help="Concurrent episodes (each can hit the tool host several times)")
    ap.add_argument("--elicit-confidence", action="store_true",
                    help="Ask each agent to declare CONFIDENCE on FINISH (reliability layer); "
                         "off by default so capability runs are unchanged.")
    ap.add_argument("--temperature", type=float, default=None,
                    help="Override sampling temperature for every episode. Use >0 for reliability "
                         "k-trials so identical inputs produce run-to-run variance.")
    args = ap.parse_args(argv)

    tasks_root = Path(args.tasks_root).resolve()
    results_root = Path(args.results).resolve()
    results_root.mkdir(parents=True, exist_ok=True)
    cfg = Path(args.models).resolve()

    loader = TaskLoader(tasks_root)
    model_names = [n for n, _, _ in load_model_specs(cfg, allow_mock=False)]
    if args.task_ids:
        want = [t.strip() for t in args.task_ids.split(",") if t.strip()]
        found: dict[str, Path] = {}
        for tp in loader.discover(track=args.track, recursive=True):
            try:
                m = loader.load(tp)
            except Exception:  # noqa: BLE001
                continue
            if m["task_id"] in want:
                found[m["task_id"]] = tp
        missing = [w for w in want if w not in found]
        if missing:
            raise SystemExit(f"--task-ids not found under {tasks_root}: {missing}")
        sampled = [found[w] for w in want]  # preserve given order
    else:
        sampled = sample_tasks(loader, args.track, args.sample_per_track, args.seed, stratify=True)
        if args.limit is not None:
            sampled = sampled[: args.limit]
    if not sampled:
        raise SystemExit("No tasks discovered")

    base_runs = Path(tempfile.mkdtemp(prefix="agentic_eval_"))
    jobs = []
    for tp in sampled:
        meta = loader.load(tp)
        for name in model_names:
            jobs.append({"task_path": tp, "meta": meta, "name": name,
                         "track": meta["track"], "task_id": meta["task_id"]})

    print(f"Agentic baseline: {len(sampled)} tasks x {len(model_names)} models = {len(jobs)} "
          f"episodes | max-actions {args.max_actions} | timeout {args.timeout}s | "
          f"concurrency {args.concurrency}")

    def run_job(job: dict) -> str:
        name, track, task_id = job["name"], job["track"], job["task_id"]
        dest = results_root / name / track / f"{task_id}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        logp = dest.with_suffix(".agentlog.json")
        agent_cmd = (f'python3 "{DRIVER}" --model "{name}" --models "{cfg}" '
                     f'--max-actions {args.max_actions} --log "{logp}"'
                     + (" --elicit-confidence" if args.elicit_confidence else "")
                     + (f" --temperature {args.temperature}" if args.temperature is not None else ""))
        try:
            _runs, score, agentic = run_single_agentic(
                job["task_path"].resolve(), agent_cmd, job["meta"], args.timeout,
                runs_root=base_runs / name)
            res = _result_dict(score, agentic, name, track, task_id)
            res["reliability"] = _agentic_reliability_block(
                logp, passed=score.passed, clean=agentic.anti_cheat_clean,
                timed_out=agentic.agent_timed_out)
            res["cost"] = _cost_block(logp, agentic.agent_wall_time_sec)
        except Exception as e:  # noqa: BLE001
            res = {"ok": False, "total_score": 0.0, "passed": False, "error":
                   f"{type(e).__name__}: {e}", "model": name, "track": track,
                   "task_id": task_id, "mode": "agentic"}
            res["reliability"] = _agentic_reliability_block(
                logp, passed=None, clean=True, timed_out=False, run_error=res["error"])
            res["cost"] = _cost_block(logp)
        dest.write_text(json.dumps(res, indent=2))
        # For continuous-graded tracks the binary "PASS" is misleading (a do-nothing
        # floor still totals ~0.6 and reads as PASS), so show the isolated continuous
        # score instead; binary tracks keep the PASS / total_score flag.
        cont = next((c.get("raw") for c in (res.get("components") or [])
                     if c.get("name") in CONTINUOUS_COMPONENTS), None)
        if cont is not None:
            flag = f"spec={float(cont):.2f}"
        else:
            flag = "PASS" if res.get("passed") else f"{res.get('total_score', 0):.2f}"
        clean = res.get("agent", {}).get("anti_cheat_clean", True)
        return (f"  [{name}] {track}/{task_id}: {flag}"
                + ("" if clean else " ANTI-CHEAT-DIRTY")
                + (f"  ({res['error']})" if res.get("error") else ""))

    n_done = 0
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as ex:
        futs = [ex.submit(run_job, j) for j in jobs]
        for fut in as_completed(futs):
            print(fut.result(), flush=True)
            n_done += 1

    # Cost summary from the per-episode driver logs.
    prices = {}
    pc = json.loads(cfg.read_text())
    for s in pc.get("models", []):
        if not str(s.get("name", "")).startswith("_"):
            prices[s["name"]] = (s.get("price_in_per_m", 0.0), s.get("price_out_per_m", 0.0))
    tot_in = tot_out = 0
    cny = 0.0
    for lp in results_root.rglob("*.agentlog.json"):
        try:
            lg = json.loads(lp.read_text())
        except json.JSONDecodeError:
            continue
        u = lg.get("usage", {})
        pin, pout = prices.get(lg.get("model", ""), (0.0, 0.0))
        tot_in += u.get("prompt_tokens", 0)
        tot_out += u.get("completion_tokens", 0)
        cny += u.get("prompt_tokens", 0) / 1e6 * pin + u.get("completion_tokens", 0) / 1e6 * pout

    print(f"\nGraded {n_done} episodes -> {results_root}")
    print(f"Tokens in/out: {tot_in}/{tot_out}   |   est cost: ¥{cny:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
