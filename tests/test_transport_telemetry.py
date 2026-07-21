"""Regression tests: request-level transport telemetry + episode aggregates (Phase-4X Stage 1C).

Proves that a retry-success sequence is visible BOTH at request level (per-attempt records with
category/timestamps/pids) AND at episode level (aggregates + the pre-existing retries counter), that
terminal failures are recorded, that the two transport dimensions are independent, and that no
prompt/response content or credentials leak into the telemetry."""
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import llm_agent_driver as drv  # noqa: E402


class _Resp:
    def __init__(self):
        self.text = "ANSWER"
        self.model = "DeepSeek-V4-Pro"
        self.usage = {"prompt_tokens": 10, "completion_tokens": 5, "reasoning_tokens": 3}
        self.metadata = {"finish_reason": "stop",
                          "stream": {"time_to_first_chunk_s": 0.12, "time_to_first_answer_s": 0.5,
                                     "total_duration_s": 2.5, "chunk_count": 9}}


def _fake_attempts(seq):
    """Return an _attempt_isolated replacement yielding the given _AttemptResult sequence."""
    it = iter(seq)

    def fake(provider, messages, gen_kwargs, request_deadline, op_timeout):
        return next(it)
    return fake


def _fail(category, pid=111):
    return drv._AttemptResult(category=category, retryable=True, status=None,
                              termination="normal_exit", worker_pid=pid,
                              diag={"body_sha256": "abc123def456"})


def _ok(pid=222):
    return drv._AttemptResult(success=True, resp=_Resp(), termination="normal_exit",
                              worker_pid=pid, diag={"body_sha256": "abc123def456"})


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda *_: None)


SECRET = "sk-CANARY-KEY"
PROMPT_CANARY = "UNIQUE-PROMPT-CANARY-42"
MSGS = [{"role": "user", "content": PROMPT_CANARY}]
KW = {"max_tokens": 64, "timeout": 5}


def test_retry_success_visible_at_request_and_episode_level(monkeypatch):
    monkeypatch.setattr(drv, "_attempt_isolated", _fake_attempts([_fail("socket_timeout"), _ok()]))
    telemetry = []
    resp, n_retry = drv._chat_with_retry_deadline(None, MSGS, KW, 300.0, 120.0, 1,
                                                  telemetry=telemetry)
    # episode-level counter (pre-existing field) sees the retry
    assert n_retry == 1
    # request level: one logical request, two physical attempts, categories in order
    assert len(telemetry) == 1
    rec = telemetry[0]
    assert rec["total_attempts"] == 2
    assert [a["category"] for a in rec["attempts"]] == ["socket_timeout", "success"]
    assert rec["recovered_failed_attempts"] == 1
    assert rec["recovered_categories"] == ["socket_timeout"]
    assert rec["recovered_hard_deadlines"] == 0
    assert rec["terminal_failure_category"] is None
    assert rec["retry_wall_s"] >= 0
    # attempt records carry timestamps + pids + sanitized hash
    for a in rec["attempts"]:
        assert a["start_ts"] is not None and a["end_ts"] is not None
        assert a["worker_pid"] in (111, 222)
        assert a["body_sha256"] == "abc123def456"
    # stream metrics + served model propagated on success
    assert rec["time_to_first_chunk_s"] == 0.12
    assert rec["time_to_first_answer_s"] == 0.5
    assert rec["stream_duration_s"] == 2.5
    assert rec["finish_reason"] == "stop"
    assert rec["served_model"] == "DeepSeek-V4-Pro"
    # episode aggregate: recovered degradation visible, terminally valid
    s = drv._episode_transport_summary(telemetry)
    assert s["logical_requests"] == 1
    assert s["total_physical_attempts"] == 2
    assert s["recovered_failed_attempts"] == 1
    assert s["recovered_hard_deadlines"] == 0
    assert s["terminal_transport_valid"] is True
    assert s["recovered_transport_degradation"] is True


def test_recovered_hard_deadline_counted(monkeypatch):
    monkeypatch.setattr(drv, "_attempt_isolated",
                        _fake_attempts([_fail("hard_request_deadline"), _ok()]))
    telemetry = []
    drv._chat_with_retry_deadline(None, MSGS, KW, 300.0, 120.0, 1, telemetry=telemetry)
    s = drv._episode_transport_summary(telemetry)
    assert s["recovered_hard_deadlines"] == 1
    assert s["terminal_transport_valid"] is True


def test_terminal_failure_recorded_and_flags_independent(monkeypatch):
    monkeypatch.setattr(drv, "_attempt_isolated",
                        _fake_attempts([_fail("socket_timeout"), _fail("socket_timeout")]))
    telemetry = []
    with pytest.raises(Exception):
        drv._chat_with_retry_deadline(None, MSGS, KW, 300.0, 120.0, 1, telemetry=telemetry)
    assert len(telemetry) == 1
    rec = telemetry[0]
    assert rec["terminal_failure_category"] == "socket_timeout"
    assert rec["total_attempts"] == 2
    # the FIRST failure was recovered-then-retried; the terminal one is not "recovered"
    assert rec["recovered_failed_attempts"] == 1
    s = drv._episode_transport_summary(telemetry)
    assert s["terminal_transport_valid"] is False
    assert s["recovered_transport_degradation"] is True  # independent dimensions


def test_clean_request_no_degradation(monkeypatch):
    monkeypatch.setattr(drv, "_attempt_isolated", _fake_attempts([_ok()]))
    telemetry = []
    drv._chat_with_retry_deadline(None, MSGS, KW, 300.0, 120.0, 1, telemetry=telemetry)
    s = drv._episode_transport_summary(telemetry)
    assert s["total_physical_attempts"] == 1
    assert s["recovered_failed_attempts"] == 0
    assert s["terminal_transport_valid"] is True
    assert s["recovered_transport_degradation"] is False


def test_telemetry_is_sanitized(monkeypatch):
    monkeypatch.setattr(drv, "_attempt_isolated", _fake_attempts([_fail("socket_timeout"), _ok()]))
    telemetry = []
    drv._chat_with_retry_deadline(None, MSGS, KW, 300.0, 120.0, 1, telemetry=telemetry)
    blob = json.dumps(telemetry)
    assert PROMPT_CANARY not in blob          # no prompt content
    assert SECRET not in blob                 # no credentials
    assert "Authorization" not in blob and "Bearer" not in blob
    assert "reasoning_content" not in blob    # no raw reasoning
    assert "ANSWER" not in blob               # no response content


def test_telemetry_none_keeps_legacy_behavior(monkeypatch):
    monkeypatch.setattr(drv, "_attempt_isolated", _fake_attempts([_fail("socket_timeout"), _ok()]))
    resp, n_retry = drv._chat_with_retry_deadline(None, MSGS, KW, 300.0, 120.0, 1)
    assert n_retry == 1 and resp.text == "ANSWER"
