#!/usr/bin/env python3
"""Authoritative paid-episode validity / replacement arbiter (Phase-4X Stage 1C onward).

Implements the generalized benchmark infrastructure rule: ALL code capable of changing
primary-sample membership — validity classification, transport-invalid classification, replacement
policy, attempt-to-slot assignment, and inclusion/exclusion logic — lives HERE, is tested, committed,
hashed, and included in the pre-run manifest before the first paid episode. No uncommitted helper may
determine whether a paid episode is valid, replaced, or excluded.

Two INDEPENDENT transport dimensions (an episode may be terminally valid while still having
experienced recovered failed attempts):
  terminal_transport_valid       — no logical request ended in an unrecovered transport failure
  recovered_transport_degradation — >=1 recovered failed attempt occurred

Membership rules (predeclared):
  measurement_valid = terminal_transport_valid AND workspace_gradeable
  - A replacement is permitted ONLY for a terminally measurement-invalid episode.
  - Recovered degradation in an otherwise gradeable episode NEVER triggers replacement.
  - A hard task-wall kill (timed_out) with no terminal transport failure is a TASK-level
    termination: measurement-valid.
  - A replacement occupies the same predeclared condition/block/position slot and does not alter
    subsequent ordering; the slot is filled by the FIRST measurement-valid attempt.
  - After MAX_REPLACEMENTS unsuccessful replacements the run STOPs (fail-closed).
  - Excluded attempts are preserved as sanitized operational evidence.

CLI: episode_arbiter.py <results_root> <model> <track> <task_id> [--attempt N] [--max-replacements K]
Prints a JSON verdict with decision ACCEPT | REPLACE | STOP; exit 0 for ACCEPT, 3 for REPLACE,
2 for STOP, 1 for errors.
"""
import argparse, json, sys
from pathlib import Path

MAX_REPLACEMENTS_DEFAULT = 2

# transport failure categories as emitted by the driver's isolated attempt path (also used for the
# legacy fallback scan of pre-telemetry agentlogs)
TERMINAL_MARKERS = ("socket_timeout", "hard_request_deadline", "incomplete_stream",
                     "malformed_stream", "worker_crash", "malformed_worker_result",
                     "retryable_http", "connection_reset", "connection")


def classify_episode(result: dict, agentlog: dict) -> dict:
    """Classify one graded-or-not episode. Telemetry-first (transport_summary written by the
    instrumented driver); legacy fallback = terminal-marker scan of the episode error only
    (recovered detail unobservable in legacy logs -> reported as None, never guessed)."""
    ts = agentlog.get("transport_summary")
    err = agentlog.get("error") or result.get("error")
    if ts:
        terminal_valid = bool(ts.get("terminal_transport_valid"))
        recovered = bool(ts.get("recovered_transport_degradation"))
        recovered_failed = ts.get("recovered_failed_attempts")
        recovered_hard = ts.get("recovered_hard_deadlines")
        source = "request_telemetry"
    else:
        terminal_valid = not (bool(err) and any(m in str(err) for m in TERMINAL_MARKERS))
        recovered = None
        recovered_failed = None
        recovered_hard = None
        source = "legacy_error_scan"
    gradeable = result.get("total_score") is not None
    timed_out = bool(result.get("agent", {}).get("timed_out", False))
    return {
        "terminal_transport_valid": terminal_valid,
        "recovered_transport_degradation": recovered,
        "recovered_failed_attempts": recovered_failed,
        "recovered_hard_deadlines": recovered_hard,
        "workspace_gradeable": gradeable,
        "task_wall_hard_kill": timed_out and terminal_valid,
        "measurement_valid": terminal_valid and gradeable,
        "classification_source": source,
        "error": err,
    }


def replacement_decision(classification: dict, attempt_number: int,
                         max_replacements: int = MAX_REPLACEMENTS_DEFAULT) -> str:
    """ACCEPT | REPLACE | STOP for the attempt at 1-based attempt_number in its slot.
    Recovered degradation NEVER causes REPLACE; only terminal measurement-invalidity does."""
    if classification["measurement_valid"]:
        return "ACCEPT"
    if attempt_number >= 1 + max_replacements:
        return "STOP"
    return "REPLACE"


def assign_slot(attempt_classifications, max_replacements: int = MAX_REPLACEMENTS_DEFAULT):
    """Given the ORDERED classifications of all attempts at one slot, return
    (slot_filling_index_or_None, decisions). The FIRST measurement-valid attempt fills the slot;
    later attempts (if any were run in error) are excluded evidence, never slot-fillers."""
    decisions = []
    fill = None
    for i, c in enumerate(attempt_classifications):
        d = replacement_decision(c, i + 1, max_replacements)
        decisions.append(d)
        if d == "ACCEPT" and fill is None:
            fill = i
    return fill, decisions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results_root")
    ap.add_argument("model")
    ap.add_argument("track")
    ap.add_argument("task_id")
    ap.add_argument("--attempt", type=int, default=1, help="1-based attempt number at this slot")
    ap.add_argument("--max-replacements", type=int, default=MAX_REPLACEMENTS_DEFAULT)
    a = ap.parse_args()
    base = Path(a.results_root) / a.model / a.track
    try:
        result = json.loads((base / f"{a.task_id}.json").read_text())
        agentlog = json.loads((base / f"{a.task_id}.agentlog.json").read_text())
    except Exception as e:  # missing/corrupt results = not gradeable
        result, agentlog = {}, {"error": f"missing_results:{type(e).__name__}"}
    c = classify_episode(result, agentlog)
    decision = replacement_decision(c, a.attempt, a.max_replacements)
    print(json.dumps({"decision": decision, "attempt": a.attempt, **c}))
    sys.exit({"ACCEPT": 0, "REPLACE": 3, "STOP": 2}[decision])


if __name__ == "__main__":
    main()
