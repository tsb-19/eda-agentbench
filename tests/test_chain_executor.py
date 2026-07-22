"""Regression tests for the frozen-schedule chain executor (scripts/chain_executor.py).

Locks in two infrastructure fixes:
  1. EXECUTOR STDIN ISOLATION — the bug where scheduler iteration shared stdin with the runner
     (`while read <<< "$SCHEDULE"` + a runner that reads stdin) prematurely ended the first Phase-4X
     Stage-1C chain after block 2. The executor runs each attempt with stdin=DEVNULL, so a runner that
     reads stdin CANNOT consume scheduler state and the full schedule completes.
  2. DURABLE RUN-STATE — RUNNING -> COMPLETE/FAILED with expected/completed slot counts + excluded
     attempts; written atomically; orchestration metadata only (never influences membership).

Also covers arbiter-driven ACCEPT / REPLACE / STOP through the executor.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import chain_executor as ex  # noqa: E402

MOCK_RUNNER = r"""
import argparse, json, os, sys
from pathlib import Path
ap = argparse.ArgumentParser()
ap.add_argument("sub")  # "tasks"
ap.add_argument("--models"); ap.add_argument("--track"); ap.add_argument("--task-ids")
ap.add_argument("--results"); ap.add_argument("--max-actions"); ap.add_argument("--timeout")
ap.add_argument("--temperature"); ap.add_argument("--concurrency")
ap.add_argument("--elicit-confidence", action="store_true")
a = ap.parse_args()
# THE BUG TRIGGER: a runner that reads/consumes stdin. Under the old shared-stdin scheduler this ate
# the remaining schedule lines. Record how many stdin bytes we actually saw (must be 0 under DEVNULL).
data = sys.stdin.read()
model = json.load(open(a.models))["models"][0]["name"]
attempt_tag = "_a" in a.results and a.results.split("_a")[-1]
out = Path(a.results) / model / a.track
out.mkdir(parents=True, exist_ok=True)
stdin_log = Path(a.results).parent / "stdin_seen.txt"
# if this is the designated REPLACE_ONCE task on attempt 1, write NOTHING (missing_results -> REPLACE)
if a.task_ids == "workflow_handoff_REPLACE_ONCE" and a.results.rstrip("/").endswith("_a1/results"):
    stdin_log.write_text(str(len(data)))
    sys.exit(0)
rec = {"total_score": 1.0, "passed": True, "agent": {"timed_out": False, "anti_cheat_clean": True},
       "components": [], "error": None}
(out / f"{a.task_ids}.json").write_text(json.dumps(rec))
(out / f"{a.task_ids}.agentlog.json").write_text(json.dumps({
    "model": model, "transport_summary": {"logical_requests": 1, "total_physical_attempts": 1,
    "recovered_failed_attempts": 0, "recovered_hard_deadlines": 0, "cumulative_retry_wall_s": 0.0,
    "terminal_transport_valid": True, "recovered_transport_degradation": False},
    "actions": [{"type": "finish"}], "usage": {}, "error": None, "retries": 0, "confidence": "high"}))
stdin_log.write_text(str(len(data)))
"""


def _make_schedule(tmp, slots):
    flat = []
    for i, (cond, task) in enumerate(slots):
        flat.append({"block_id": f"block{i//2 + 1}", "position_in_block": i % 2,
                     "condition": cond, "task_id": task})
    man = {"flat": flat, "counts": {"Base": 2, "Schema": 2}}
    p = tmp / "schedule.json"
    p.write_text(json.dumps(man))
    return p


def _run_executor(tmp, slots, model_name="TestModel", track="p14_workflow_handoff", max_replacements=2):
    mock = tmp / "mock_runner.py"
    mock.write_text(MOCK_RUNNER)
    models = tmp / "models.json"
    models.write_text(json.dumps({"models": [{"name": model_name}]}))
    sched = _make_schedule(tmp, slots)
    state = tmp / "run_state.json"
    log = tmp / "chain.log"
    prefix = str(tmp / "ep")
    r = subprocess.run([sys.executable, str(REPO / "scripts/chain_executor.py"),
                        "--schedule", str(sched), "--models", str(models), "--track", track,
                        "--runner", str(mock), "--model-name", model_name,
                        "--results-prefix", prefix, "--state", str(state), "--log", str(log),
                        "--max-replacements", str(max_replacements)], capture_output=True, text=True)
    return r, state, log


def test_stdin_isolation_full_schedule_completes(tmp_path):
    """A runner that CONSUMES stdin must not truncate the schedule. Old bug: only block1-2 ran."""
    slots = [("Base", "workflow_handoff_t0"), ("Schema", "workflow_handoff_t1"),
             ("Schema", "workflow_handoff_t2"), ("Base", "workflow_handoff_t3")]
    r, state, log = _run_executor(tmp_path, slots)
    assert r.returncode == 0, r.stderr[-800:]
    s = json.loads(state.read_text())
    assert s["state"] == "COMPLETE"
    assert s["expected_primary_slots"] == 4
    assert s["completed_primary_slots"] == 4          # ALL slots completed (not truncated)
    # every mock-runner call saw ZERO stdin bytes (stdin=DEVNULL isolated it)
    seen = [int(p.read_text()) for p in tmp_path.glob("ep_*_a1/stdin_seen.txt")]
    assert seen and all(n == 0 for n in seen), seen


def test_durable_run_state_fields_and_atomicity(tmp_path):
    slots = [("Base", "workflow_handoff_t0"), ("Schema", "workflow_handoff_t1")]
    r, state, log = _run_executor(tmp_path, slots)
    s = json.loads(state.read_text())
    for k in ("state", "started_at", "executor_finished_at", "executor_exit_code",
              "expected_primary_slots", "completed_primary_slots", "excluded_invalid_attempts",
              "report_pending"):
        assert k in s, k
    assert s["state"] == "COMPLETE"
    assert s["executor_exit_code"] == 0
    assert s["report_pending"] is True
    assert s["started_at"] and s["executor_finished_at"]
    assert s["excluded_invalid_attempts"] == []


def test_replacement_recording_and_excluded_attempts(tmp_path):
    """A terminal-invalid attempt (missing_results) is REPLACED; the excluded attempt is recorded."""
    slots = [("Base", "workflow_handoff_REPLACE_ONCE"), ("Schema", "workflow_handoff_t1")]
    r, state, log = _run_executor(tmp_path, slots)
    assert r.returncode == 0, r.stderr[-800:]
    s = json.loads(state.read_text())
    assert s["completed_primary_slots"] == 2
    excl = s["excluded_invalid_attempts"]
    assert len(excl) == 1
    assert excl[0]["reason"] == "terminal_invalid_replaced"
    assert "block1:Base" in excl[0]["slot"]
    # the slot's attempt-2 results exist (the replacement filled it)
    assert (tmp_path / "ep_1_Base_0_a2" / "stdin_seen.txt").exists()


def test_stop_fail_closed_when_cap_exhausted(tmp_path):
    """A slot that is terminal-invalid on every attempt up to the cap STOPs the chain (fail-closed)."""
    slots = [("Base", "workflow_handoff_REPLACE_ONCE"), ("Schema", "workflow_handoff_t1")]
    r, state, log = _run_executor(tmp_path, slots, max_replacements=0)  # cap=0 -> only 1 attempt allowed
    assert r.returncode == 2
    s = json.loads(state.read_text())
    assert s["state"] == "FAILED"
    assert s["completed_primary_slots"] == 0
    assert s["excluded_invalid_attempts"][0]["reason"] == "terminal_invalid_after_cap"


def test_classify_uses_arbiter_telemetry_first(tmp_path):
    """Executor.classify delegates to episode_arbiter.classify_episode (telemetry-first)."""
    base = tmp_path / "ModelX" / "track_t"
    base.mkdir(parents=True)
    (base / "task.json").write_text(json.dumps({"total_score": 0.2, "agent": {"timed_out": False}}))
    (base / "task.agentlog.json").write_text(json.dumps({
        "transport_summary": {"terminal_transport_valid": True, "recovered_transport_degradation": True,
        "recovered_failed_attempts": 2, "recovered_hard_deadlines": 1, "cumulative_retry_wall_s": 5.0,
        "logical_requests": 10, "total_physical_attempts": 12}, "error": None}))
    cls, res, lg = ex.classify(tmp_path, "ModelX", "track_t", "task")
    assert cls["measurement_valid"] is True            # terminally valid + gradeable
    assert cls["recovered_transport_degradation"] is True
    assert cls["recovered_hard_deadlines"] == 1
