"""Tests for the authoritative paid-episode validity/replacement arbiter (scripts/episode_arbiter.py).

Covers the predeclared membership rules: measurement validity, recovered-degradation-never-replaces,
task-wall hard-kill validity, replacement caps (fail-closed STOP), first-valid-fills-slot assignment,
and the legacy (pre-telemetry) fallback path."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import episode_arbiter as arb  # noqa: E402


def _res(score=1.0, timed_out=False, error=None):
    return {"total_score": score, "agent": {"timed_out": timed_out}, "error": error}


def _lg(terminal_valid=True, recovered=False, failed=0, hard=0, error=None):
    return {"error": error,
            "transport_summary": {"logical_requests": 10, "total_physical_attempts": 10 + failed,
                                   "recovered_failed_attempts": failed,
                                   "recovered_hard_deadlines": hard,
                                   "cumulative_retry_wall_s": 1.0,
                                   "terminal_transport_valid": terminal_valid,
                                   "recovered_transport_degradation": recovered}}


def test_clean_valid_episode_accepts():
    c = arb.classify_episode(_res(), _lg())
    assert c["measurement_valid"] and c["terminal_transport_valid"]
    assert arb.replacement_decision(c, 1) == "ACCEPT"


def test_recovered_degradation_does_NOT_trigger_replacement():
    c = arb.classify_episode(_res(score=0.2), _lg(recovered=True, failed=3, hard=1))
    assert c["measurement_valid"] is True
    assert c["recovered_transport_degradation"] is True
    assert arb.replacement_decision(c, 1) == "ACCEPT"  # gradeable + terminally valid -> counts


def test_task_wall_hard_kill_is_measurement_valid():
    c = arb.classify_episode(_res(score=1.0, timed_out=True), _lg())
    assert c["task_wall_hard_kill"] is True
    assert c["measurement_valid"] is True
    assert arb.replacement_decision(c, 1) == "ACCEPT"


def test_terminal_transport_failure_replaces_then_stops():
    c = arb.classify_episode(_res(score=None), _lg(terminal_valid=False))
    assert c["measurement_valid"] is False
    assert arb.replacement_decision(c, 1) == "REPLACE"
    assert arb.replacement_decision(c, 2) == "REPLACE"
    assert arb.replacement_decision(c, 3) == "STOP"  # 1 + MAX_REPLACEMENTS(2) reached


def test_ungradeable_workspace_replaces():
    c = arb.classify_episode(_res(score=None), _lg())
    assert c["workspace_gradeable"] is False
    assert c["measurement_valid"] is False
    assert arb.replacement_decision(c, 1) == "REPLACE"


def test_slot_filled_by_first_valid_attempt_only():
    invalid = arb.classify_episode(_res(score=None), _lg(terminal_valid=False))
    valid1 = arb.classify_episode(_res(score=0.2), _lg())
    valid2 = arb.classify_episode(_res(score=1.0), _lg())
    fill, decisions = arb.assign_slot([invalid, valid1, valid2])
    assert fill == 1                       # first measurement-valid attempt fills the slot
    assert decisions[0] == "REPLACE" and decisions[1] == "ACCEPT"
    # an over-collected later attempt never displaces the slot-filler
    fill2, _ = arb.assign_slot([valid1, valid2])
    assert fill2 == 0


def test_slot_stops_fail_closed_after_cap():
    invalid = arb.classify_episode(_res(score=None), _lg(terminal_valid=False))
    fill, decisions = arb.assign_slot([invalid, invalid, invalid])
    assert fill is None
    assert decisions[-1] == "STOP"


def test_legacy_fallback_terminal_scan():
    res = _res(score=0.2)
    lg = {"error": None}  # pre-telemetry agentlog
    c = arb.classify_episode(res, lg)
    assert c["classification_source"] == "legacy_error_scan"
    assert c["terminal_transport_valid"] is True
    assert c["recovered_transport_degradation"] is None  # unobservable, never guessed
    lg_bad = {"error": "RuntimeError: chat attempt failed: category=socket_timeout"}
    c2 = arb.classify_episode(_res(score=None, error=lg_bad["error"]), lg_bad)
    assert c2["terminal_transport_valid"] is False
    assert arb.replacement_decision(c2, 1) == "REPLACE"
