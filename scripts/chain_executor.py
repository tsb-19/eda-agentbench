#!/usr/bin/env python3
"""Frozen-schedule chain executor (orchestration). Iterates a predeclared schedule, runs the agentic
runner per slot with ISOLATED STDIN (subprocess stdin=DEVNULL) so the runner can never consume
scheduler state — the bug that prematurely ended the first Phase-4X Stage-1C chain after block 2
(`while read <<< "$SCHEDULE"` shared the loop's stdin with run_agentic_baseline.py). Applies the
committed `episode_arbiter` for ACCEPT/REPLACE/STOP, and writes a DURABLE run-state artifact that
separates execution from report processing.

Run-state is ORCHESTRATION METADATA ONLY: it records progress and is NEVER read by the arbiter or any
primary-sample-membership logic (generalized infrastructure rule). The arbiter remains the sole
membership authority; this executor merely obeys its verdicts.

Usage:
  chain_executor.py --schedule <randomization_manifest.json>
                    --models <model_config.json> --track <track> --runner <run_agentic_baseline.py>
                    --results-prefix /tmp/pREFIX --state <run_state.json> --log <chain.log>
                    [--max-replacements 2] [--max-actions 60] [--timeout 1800] [--temperature 0.7]
                    [--elicit-confidence] [--extra-runner-args ...]

The schedule JSON must contain a `flat` list; each entry needs block_id, position_in_block, condition,
task_id. Results dir per attempt = <results-prefix>_<block>_<cond>_<pos>_a<attempt>.
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import episode_arbiter as arb  # noqa: E402  (sole membership authority)


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_schedule(path: Path):
    m = json.loads(path.read_text())
    return m["flat"], m.get("counts", {})


def _atomic_write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _runner_cmd(runner, models, track, task_id, results_dir, args):
    cmd = [sys.executable, str(runner), "tasks", "--models", str(models), "--track", track,
           "--task-ids", task_id, "--max-actions", str(args.max_actions), "--timeout", str(args.timeout),
           "--temperature", str(args.temperature), "--results", str(results_dir), "--concurrency", "1"]
    if args.elicit_confidence:
        cmd.append("--elicit-confidence")
    if args.extra_runner_args:
        cmd += args.extra_runner_args.split()
    return cmd


def classify(results_dir, model, track, task_id):
    """Load one attempt's result + agentlog and classify via the arbiter (telemetry-first)."""
    base = Path(results_dir) / model / track
    try:
        result = json.loads((base / f"{task_id}.json").read_text())
        agentlog = json.loads((base / f"{task_id}.agentlog.json").read_text())
    except Exception as e:
        result, agentlog = {}, {"error": f"missing_results:{type(e).__name__}"}
    return arb.classify_episode(result, agentlog), result, agentlog


def run_slot(runner_cmd, log):
    """Run ONE attempt with stdin ISOLATED (DEVNULL). Returns (rc, stdout_tail)."""
    with open(log, "a") as lf:
        lf.write(f"[executor] run: {' '.join(runner_cmd)}\n")
    # stdin=DEVNULL is the stdin-isolation fix: the runner cannot read/consume scheduler state.
    p = subprocess.run(runner_cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True)
    with open(log, "a") as lf:
        lf.write(p.stdout[-2000:] + ("\n[stderr]\n" + p.stderr[-1000:] if p.stderr else ""))
    return p.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schedule", required=True)
    ap.add_argument("--models", required=True)
    ap.add_argument("--track", required=True)
    ap.add_argument("--runner", required=True)
    ap.add_argument("--model-name", required=True, help="model dir name under results (e.g. Qwen3.7-Max)")
    ap.add_argument("--results-prefix", required=True)
    ap.add_argument("--state", required=True, help="durable run-state JSON path")
    ap.add_argument("--log", required=True)
    ap.add_argument("--max-replacements", type=int, default=arb.MAX_REPLACEMENTS_DEFAULT)
    ap.add_argument("--max-actions", type=int, default=60)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--elicit-confidence", action="store_true")
    ap.add_argument("--extra-runner-args", default=None)
    a = ap.parse_args()

    schedule, counts = _load_schedule(Path(a.schedule))
    expected = len(schedule)
    state_path = Path(a.state)
    state = {
        "state": "RUNNING", "started_at": _now_iso(), "executor_finished_at": None,
        "executor_exit_code": None, "expected_primary_slots": expected,
        "completed_primary_slots": 0, "excluded_invalid_attempts": [],
        "report_pending": True,
        "note": "orchestration metadata only; never read by the arbiter or any membership logic",
    }
    _atomic_write_json(state_path, state)
    open(a.log, "w").close()

    completed, exit_code = 0, 0
    try:
        for e in schedule:
            blk = e["block_id"].replace("block", "")
            pos = e["position_in_block"]
            cond = e["condition"]
            task_id = e["task_id"]
            accepted = False
            for attempt in range(1, a.max_replacements + 2):
                res_dir = Path(f"{a.results_prefix}_{blk}_{cond}_{pos}_a{attempt}/results")
                cmd = _runner_cmd(a.runner, a.models, a.track, task_id, res_dir, a)
                rc = run_slot(cmd, a.log)
                cls, result, agentlog = classify(res_dir, a.model_name, a.track, task_id)
                decision = arb.replacement_decision(cls, attempt, a.max_replacements)
                with open(a.log, "a") as lf:
                    lf.write(f"[arbiter] block{blk}:{cond} pos{pos} attempt{attempt} -> {decision} "
                             f"(terminal_valid={cls['terminal_transport_valid']} "
                             f"recovered={cls['recovered_transport_degradation']} "
                             f"gradeable={cls['workspace_gradeable']})\n")
                if decision == "ACCEPT":
                    accepted = True
                    break
                if decision == "STOP":
                    state["excluded_invalid_attempts"].append(
                        {"slot": f"block{blk}:{cond}/pos{pos}", "attempt": attempt,
                         "reason": "terminal_invalid_after_cap", "classification": cls})
                    _atomic_write_json(state_path, {**state, "executor_finished_at": _now_iso(),
                                                     "executor_exit_code": 2})
                    raise SystemExit(2)
                # REPLACE: record the excluded attempt, try again same slot
                state["excluded_invalid_attempts"].append(
                    {"slot": f"block{blk}:{cond}/pos{pos}", "attempt": attempt,
                     "reason": "terminal_invalid_replaced", "classification": cls})
                _atomic_write_json(state_path, state)
            if not accepted:
                exit_code = 2
                raise RuntimeError(f"slot block{blk}:{cond}/pos{pos} unfilled")
            completed += 1
            state["completed_primary_slots"] = completed
            _atomic_write_json(state_path, state)
        state.update({"state": "COMPLETE", "executor_finished_at": _now_iso(),
                       "executor_exit_code": 0, "completed_primary_slots": completed})
        _atomic_write_json(state_path, state)
        print(json.dumps({"state": "COMPLETE", "completed": completed, "expected": expected}))
        return 0
    except SystemExit:
        state.update({"state": "FAILED", "executor_finished_at": _now_iso(), "executor_exit_code": 2})
        _atomic_write_json(state_path, state)
        raise
    except Exception as e:
        exit_code = 1
        state.update({"state": "FAILED", "executor_finished_at": _now_iso(),
                       "executor_exit_code": 1, "error": f"{type(e).__name__}: {e}"})
        _atomic_write_json(state_path, state)
        print(json.dumps({"state": "FAILED", "error": str(e)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
