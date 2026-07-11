"""Phase-4U0b: process-isolated HARD total-request deadline for the LLM driver.

Each provider.chat() runs in a separate child process; the parent enforces a wall-clock deadline by
killing the whole worker (independent of socket activity -- covers slow-drip stalls that evade the
per-operation urllib timeout). The API key is NEVER in argv/stdin/logs (the child reads it from the
inherited environment). All diagnostics use local fake servers or monkeypatched workers -- no paid
gateway is contacted.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import http.server
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import llm_agent_driver as drv  # noqa: E402
from eda_agentbench.llm.openai_provider import OpenAIProvider, ProviderHTTPError  # noqa: E402

# Tests that spawn a REAL worker subprocess and validate the POSIX process-group kill/reap guarantee
# (start_new_session + os.killpg) are skipped on platforms without killpg, rather than silently
# assuming it exists. Pure-logic / fake-Popen tests below run on all platforms.
_skip_non_posix = pytest.mark.skipif(
    not (hasattr(os, "killpg") and hasattr(os, "getpgid")),
    reason="POSIX process-group termination (start_new_session/os.killpg) not available")

OK_BODY = {"model": "m", "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
           "usage": {"prompt_tokens": 7, "completion_tokens": 3}}


# --------------------------------------------------------------------------- fake server
def _make_server(behaviors):
    """behaviors = [(mode, status, body, drip, delay), ...] one per request (index clamped).
    mode: 'ok'|'status'|'noreply'|'drip'. Returns base_url; caller shuts down."""
    lock = threading.Lock()
    state = {"i": 0, "b": list(behaviors)}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length:
                self.rfile.read(length)
            with lock:
                idx = min(state["i"], len(state["b"]) - 1)
                state["i"] += 1
                mode, status, body, drip, delay = state["b"][idx]
            if mode == "noreply":
                threading.Event().wait(delay)  # never respond within the test -> op timeout fires
                return
            if mode == "drip":
                # send headers (huge body) then drip bytes forever; each recv < op_timeout so the
                # per-op timeout does NOT fire -- only the hard deadline kills the worker.
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", "100000000")
                self.end_headers()
                while True:
                    try:
                        self.wfile.write(b"x")
                        self.wfile.flush()
                    except Exception:
                        return
                    threading.Event().wait(drip)
            # ok / status
            body_bytes = json.dumps(body).encode() if body is not None else b"{}"
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body_bytes)))
            self.end_headers()
            try:
                self.wfile.write(body_bytes)
            except Exception:
                pass

    class Server(http.server.ThreadingHTTPServer):
        allow_reuse_address = True
        daemon_threads = True

    srv = Server(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}", srv


@pytest.fixture(autouse=True)
def _fast_backoff(monkeypatch):
    # make the retry-loop backoff instant; the WORKER subprocess keeps its own real clock (drip uses
    # Event().wait, unaffected). Also ensure a key is present so the worker doesn't report MissingApiKey.
    monkeypatch.setattr(drv.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setenv("API_KEY", "test-key-not-a-real-secret")


# --------------------------------------------------------------- config resolution
def test_deadline_default(monkeypatch):
    monkeypatch.delenv("EDA_BENCH_LLM_REQUEST_DEADLINE_SEC", raising=False)
    assert drv._resolve_request_deadline(None, None) == 300.0


def test_deadline_env_overrides_default():
    assert drv._resolve_request_deadline(None, "250") == 250.0


def test_deadline_cli_overrides_env():
    assert drv._resolve_request_deadline("180", "250") == 180.0


@pytest.mark.parametrize("bad", ["0", "-5", "abc", "", "nan", "inf", "-inf"])
def test_deadline_rejects_invalid(bad):
    with pytest.raises(SystemExit):
        drv._resolve_request_deadline(bad, None)


def test_timeout_and_deadline_are_distinct():
    # different defaults, different env vars, independently resolved
    assert drv._resolve_request_timeout(None, None) == 300.0
    assert drv._resolve_request_deadline(None, None) == 300.0
    assert drv._resolve_request_timeout("120", None) == 120.0
    assert drv._resolve_request_deadline("180", None) == 180.0


def test_max_chat_retries_default_and_override():
    assert drv._resolve_max_chat_retries(None, None) == 4
    assert drv._resolve_max_chat_retries("1", None) == 1
    assert drv._resolve_max_chat_retries(None, "0") == 0
    with pytest.raises(SystemExit):
        drv._resolve_max_chat_retries("-1", None)
    with pytest.raises(SystemExit):
        drv._resolve_max_chat_retries("abc", None)


# --------------------------------------------------------------- worker-error classification
def test_classify_worker_errors():
    assert drv._classify_worker_error("ProviderHTTPError", 503) == ("retryable_http", True)
    assert drv._classify_worker_error("ProviderHTTPError", 400) == ("non_retryable_http", False)
    assert drv._classify_worker_error("TimeoutError", None) == ("socket_timeout", True)
    assert drv._classify_worker_error("ConnectionResetError", None) == ("connection", True)
    assert drv._classify_worker_error("URLError", None) == ("connection", True)
    assert drv._classify_worker_error("MissingApiKey", None) == ("non_retryable_http", False)


# --------------------------------------------------------------- safe diagnostics (no secrets)
def test_safe_diagnostics_have_no_key_or_content():
    spec = {"api_base": "https://gateway.example.test/v1", "model": "DeepSeek-V4-Pro",
            "messages": [{"role": "system", "content": "SECRET-PROMPT-TEXT"},
                         {"role": "user", "content": "hi"}],
            "gen_kwargs": {"max_tokens": 4096, "timeout": 120}}
    d = drv._safe_request_diagnostics(spec)
    blob = json.dumps(d)
    assert d["host"] == "gateway.example.test"
    assert d["msg_count"] == 2 and d["system_chars"] == len("SECRET-PROMPT-TEXT")
    assert d["max_tokens"] == 4096 and len(d["body_sha256"]) == 12
    assert "SECRET-PROMPT-TEXT" not in blob and "test-key" not in blob
    assert "Authorization" not in blob and "Bearer" not in blob


# --------------------------------------------------------------- fake-Popen worker (crash/malformed/argv/secrets/overlap)
class _FakeProc:
    """Simulates subprocess.Popen for crash/malformed/secrets tests (no real server)."""

    def __init__(self, stdout=b"", stderr=b"", returncode=0, pid=99999, delay=0.0):
        self._out = stdout
        self._err = stderr
        self.returncode = returncode
        self.pid = pid
        self._delay = delay
        self.communicate_calls = 0

    def communicate(self, stdin=None, timeout=None):
        self.communicate_calls += 1
        if self._delay:
            # honor the deadline: raise TimeoutExpired if delay > timeout
            if timeout is not None and self._delay > timeout:
                raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout)
            time.sleep(self._delay)
        return self._out, self._err

    def wait(self, timeout=None):
        return self.returncode

    def terminate(self):
        pass

    def kill(self):
        pass


def test_secrets_not_in_argv_nor_stdin(monkeypatch):
    captured = {}

    class _P:
        def __init__(self, cmd, **kw):
            captured["argv"] = cmd
            captured["kwargs"] = kw
            self.pid = 123
            self.returncode = 0

        def communicate(self, stdin=None, timeout=None):
            captured["stdin"] = stdin
            return json.dumps({"ok": True, "text": "OK", "model": "m",
                               "usage": {}, "metadata": {}}).encode(), b""

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(drv.subprocess, "Popen", lambda *a, **k: _P(*a, **k))
    p = OpenAIProvider("real-secret-key-value", "http://example.test", "m")
    res = drv._attempt_isolated(p, [{"role": "user", "content": "hi"}], {"max_tokens": 5}, 5.0, 2.0)
    assert res.success
    # argv is exactly [python, worker_script] -- NO key
    assert captured["argv"][0] == sys.executable
    assert captured["argv"][-1].endswith("_llm_request_worker.py")
    assert "real-secret-key-value" not in json.dumps(captured["argv"])
    # stdin payload has no key / Authorization / Bearer
    stdin_str = captured["stdin"].decode() if isinstance(captured["stdin"], bytes) else str(captured["stdin"])
    assert "real-secret-key-value" not in stdin_str
    assert "Authorization" not in stdin_str and "Bearer" not in stdin_str
    assert "api_key" not in stdin_str


def test_worker_crash_classified(monkeypatch):
    monkeypatch.setattr(drv.subprocess, "Popen",
                        lambda *a, **k: _FakeProc(stdout=b"", stderr=b"boom", returncode=1))
    p = OpenAIProvider("k", "http://example.test", "m")
    res = drv._attempt_isolated(p, [{"role": "user", "content": "hi"}], {"max_tokens": 5}, 5.0, 2.0)
    assert res.category == "worker_crash" and res.retryable is True


def test_malformed_worker_output_classified(monkeypatch):
    monkeypatch.setattr(drv.subprocess, "Popen",
                        lambda *a, **k: _FakeProc(stdout=b"not-json", returncode=0))
    p = OpenAIProvider("k", "http://example.test", "m")
    res = drv._attempt_isolated(p, [{"role": "user", "content": "hi"}], {"max_tokens": 5}, 5.0, 2.0)
    assert res.category == "malformed_worker_result" and res.retryable is True


def test_retry_loop_has_no_overlapping_attempts():
    """Structural no-overlap proof: _retry_loop awaits each attempt_fn before the next."""
    active = {"now": 0, "max": 0}

    def attempt_fn():
        active["now"] += 1
        active["max"] = max(active["max"], active["now"])
        time.sleep(0.05)  # instant (autouse no-op sleep)
        active["now"] -= 1
        return drv._AttemptResult(category="hard_request_deadline", retryable=True)

    with pytest.raises(RuntimeError):
        drv._retry_loop(attempt_fn, retries=2, on_attempt=lambda *a: None)
    assert active["max"] == 1   # never two attempts active at once


def test_hard_deadline_retry_count_bounded():
    calls = [0]

    def attempt_fn():
        calls[0] += 1
        return drv._AttemptResult(category="hard_request_deadline", retryable=True)

    with pytest.raises(RuntimeError):
        drv._retry_loop(attempt_fn, retries=1, on_attempt=lambda *a: None)
    assert calls[0] == 2   # retries=1 -> exactly 2 total attempts (initial + 1 retry), not more


# --------------------------------------------------------------- local fake-server scenarios (real worker)
def _provider(base):
    return OpenAIProvider("test-key", base, "m")


@_skip_non_posix
def test_server_success_parsing_unchanged():
    base, srv = _make_server([("ok", 200, OK_BODY, 0, 0)])
    try:
        res = drv._attempt_isolated(_provider(base), [{"role": "user", "content": "hi"}],
                                    {"max_tokens": 5}, 10.0, 5.0)
        assert res.success and res.resp.text == "OK"
        assert res.resp.usage["prompt_tokens"] == 7 and res.resp.usage["completion_tokens"] == 3
        assert res.termination == "normal_exit"
    finally:
        srv.shutdown(); srv.server_close()


@_skip_non_posix
def test_scenario_A_no_response_op_timeout_fires():
    """A: server accepts, never responds -> per-op timeout fires (worker exits with socket_timeout)."""
    base, srv = _make_server([("noreply", None, None, 0, 30)])
    try:
        res = drv._attempt_isolated(_provider(base), [{"role": "user", "content": "hi"}],
                                    {"max_tokens": 5}, 8.0, 0.5)
        assert res.category == "socket_timeout"      # op timeout fired before the deadline
        assert res.termination == "normal_exit"      # worker exited on its own (not killed)
        assert res.elapsed < 4.0
    finally:
        srv.shutdown(); srv.server_close()


@_skip_non_posix
def test_scenario_B_slow_drip_hard_deadline_fires():
    """B (DECISIVE): server drips a byte every 0.2s (< op_timeout 1.0) so the per-op timeout does NOT
    fire; the hard process deadline DOES fire and kills the worker."""
    base, srv = _make_server([("drip", 200, None, 0.2, 0)])
    try:
        res = drv._attempt_isolated(_provider(base), [{"role": "user", "content": "hi"}],
                                    {"max_tokens": 5}, 1.5, 1.0)
        assert res.category == "hard_request_deadline"   # NOT socket_timeout -> deadline, not op
        assert res.termination in ("terminate", "kill")
        assert res.worker_pid is not None
        # child must be dead/reaped (os.kill(pid,0) raises ProcessLookupError when gone)
        import os as _os
        try:
            _os.kill(res.worker_pid, 0)
            alive = True
        except (ProcessLookupError, PermissionError):
            alive = False
        assert not alive, "worker %d still alive after deadline" % res.worker_pid
        assert res.elapsed < 5.0
    finally:
        srv.shutdown(); srv.server_close()


@_skip_non_posix
def test_scenario_C_slow_drip_then_success():
    """C: first request slow-drips past the deadline (killed); second fresh request succeeds."""
    base, srv = _make_server([("drip", 200, None, 0.2, 0), ("ok", 200, OK_BODY, 0, 0)])
    try:
        resp, n = drv._chat_with_retry_deadline(_provider(base), [{"role": "user", "content": "hi"}],
                                                {"max_tokens": 5}, request_deadline=1.5,
                                                op_timeout=1.0, retries=1)
        assert resp.text == "OK" and n == 1   # exactly one retry, then success
    finally:
        srv.shutdown(); srv.server_close()


@_skip_non_posix
def test_scenario_D_persistent_slow_drip_bounded():
    """D: both allowed attempts slow-drip -> two total attempts, both killed, bounded time, clear error."""
    base, srv = _make_server([("drip", 200, None, 0.2, 0)] * 5)
    t0 = time.time()
    try:
        with pytest.raises(RuntimeError) as ei:
            drv._chat_with_retry_deadline(_provider(base), [{"role": "user", "content": "hi"}],
                                          {"max_tokens": 5}, request_deadline=1.2,
                                          op_timeout=1.0, retries=1)
        assert "hard_request_deadline" in str(ei.value)
        assert time.time() - t0 < 8.0   # bounded (2 attempts * ~1.2s deadline + instant backoff)
    finally:
        srv.shutdown(); srv.server_close()


@_skip_non_posix
def test_scenario_E_non_retryable_400():
    """E: structured 400 -> no retry, no termination, raises promptly."""
    base, srv = _make_server([("status", 400, {"error": "bad model"}, 0, 0)])
    try:
        with pytest.raises(RuntimeError) as ei:
            drv._chat_with_retry_deadline(_provider(base), [{"role": "user", "content": "hi"}],
                                          {"max_tokens": 5}, request_deadline=8.0,
                                          op_timeout=5.0, retries=2)
        assert "non_retryable_http" in str(ei.value) and "400" in str(ei.value)
    finally:
        srv.shutdown(); srv.server_close()


@_skip_non_posix
def test_scenario_F_retryable_503_then_success():
    """F: first request 503 (retryable), second fresh request succeeds."""
    base, srv = _make_server([("status", 503, {"error": "busy"}, 0, 0), ("ok", 200, OK_BODY, 0, 0)])
    try:
        resp, n = drv._chat_with_retry_deadline(_provider(base), [{"role": "user", "content": "hi"}],
                                                {"max_tokens": 5}, request_deadline=8.0,
                                                op_timeout=5.0, retries=2)
        assert resp.text == "OK" and n == 1
    finally:
        srv.shutdown(); srv.server_close()


def test_scenario_G_worker_crash_detected(monkeypatch):
    """G: worker crash (nonzero exit, no JSON) -> classified worker_crash, no indefinite wait."""
    monkeypatch.setattr(drv.subprocess, "Popen",
                        lambda *a, **k: _FakeProc(stdout=b"", stderr=b"ImportError: boom", returncode=1))
    base = "http://example.test"
    res = drv._attempt_isolated(_provider(base), [{"role": "user", "content": "hi"}],
                                {"max_tokens": 5}, 5.0, 2.0)
    assert res.category == "worker_crash"
    # bounded retry: one retry after a crash, then raises
    with pytest.raises(RuntimeError):
        drv._retry_loop(lambda: res, retries=1, on_attempt=lambda *a: None)


# --------------------------------------------------------------- sanitized logging
def test_isolated_log_safe(capsys, monkeypatch):
    monkeypatch.setattr(drv.subprocess, "Popen",
                        lambda *a, **k: _FakeProc(stdout=b"not-json", returncode=1))
    p = OpenAIProvider("real-secret-key-value", "http://gateway.example.test/v1", "DeepSeek-V4-Pro")
    # logging happens in the retry loop (on_attempt), so drive it through _chat_with_retry_deadline.
    with pytest.raises(RuntimeError):
        drv._chat_with_retry_deadline(
            p, [{"role": "system", "content": "CONFIDENTIAL-PROMPT"},
                {"role": "user", "content": "hi"}], {"max_tokens": 4096}, 5.0, 2.0, retries=0)
    err = capsys.readouterr().err
    assert "[llm_deadline]" in err
    assert "category=" in err and "termination=" in err and "deadline=" in err and "host=" in err
    # no secrets / no prompt content
    assert "real-secret-key-value" not in err
    assert "CONFIDENTIAL-PROMPT" not in err
    assert "Authorization" not in err and "Bearer" not in err
    assert "test-key" not in err


def test_in_process_path_still_logs_llm_retry_format(capsys):
    """Phase-4U0 in-process path (unchanged) still emits the [llm_retry] format its tests expect."""
    base, srv = _make_server([("status", 503, {"error": "busy"}, 0, 0), ("ok", 200, OK_BODY, 0, 0)])
    try:
        drv._chat_with_retry(_provider(base), [{"role": "user", "content": "hi"}],
                             {"max_tokens": 5}, retries=2)
        err = capsys.readouterr().err
        assert "[llm_retry]" in err and "category=" in err
    except Exception:
        srv.shutdown(); srv.server_close(); raise
    srv.shutdown(); srv.server_close()
