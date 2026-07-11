"""Phase-4U0: dependency-free request-timeout / retry hardening for the LLM driver.

The active model-call path is stdlib urllib (eda_agentbench.llm.openai_provider.OpenAIProvider),
NOT the OpenAI SDK. These tests verify the new configurable per-request timeout, type-aware retry
classification, single retry authority (_chat_with_retry), bounded attempts, fresh urlopen per retry,
sanitized logging, and unchanged response parsing. Local stdlib fake-server scenarios (stall / 503 /
400) validate behavior WITHOUT contacting any paid gateway.
"""
from __future__ import annotations

import json
import socket as _socket
import sys
import threading
import time
import http.server
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import llm_agent_driver as drv  # noqa: E402
from eda_agentbench.llm import openai_provider  # noqa: E402
from eda_agentbench.llm.openai_provider import (  # noqa: E402
    DEFAULT_REQUEST_TIMEOUT_SEC, OpenAIProvider, ProviderHTTPError,
)

import urllib.error  # noqa: E402

OK_BODY = {"model": "m", "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
           "usage": {"prompt_tokens": 7, "completion_tokens": 3}}


# --------------------------------------------------------------------------- helpers
class _FakeResp:
    def __init__(self, body: bytes):
        self._b = body

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeProvider:
    """Scripted provider: each .chat() call pops the next item (Exception to raise, else a value)."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def chat(self, messages, **kw):
        self.calls += 1
        item = self.script.pop(0) if self.script else None
        if isinstance(item, BaseException):
            raise item
        return item


def _make_fake_server(behaviors):
    """Start a local ThreadingHTTPServer; behaviors = [(delay_s, status, body_json|None), ...] consumed
    one per request (index clamped). Returns base_url. Caller must .shutdown()+.server_close()."""
    lock = threading.Lock()
    state = {"i": 0, "behaviors": list(behaviors)}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass  # silence test-server logging

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length:
                self.rfile.read(length)
            with lock:
                idx = min(state["i"], len(state["behaviors"]) - 1)
                state["i"] += 1
                delay, status, body = state["behaviors"][idx]
            if delay:
                # use Event().wait (NOT time.sleep) so the autouse monkeypatch of time.sleep
                # (which patches the shared time module) does not null the server-side delay
                threading.Event().wait(delay)  # client urlopen(timeout=...) interrupts this read
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
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return f"http://127.0.0.1:{port}", srv


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """Make _chat_with_retry's backoff instant so retry tests are fast."""
    monkeypatch.setattr(drv.time, "sleep", lambda *_a, **_k: None)


# --------------------------------------------------------------- 1-4: timeout resolution
def test_resolve_default_is_300(monkeypatch):
    monkeypatch.delenv("EDA_BENCH_LLM_REQUEST_TIMEOUT_SEC", raising=False)
    assert drv._resolve_request_timeout(None, None) == DEFAULT_REQUEST_TIMEOUT_SEC == 300.0


def test_resolve_env_overrides_default(monkeypatch):
    assert drv._resolve_request_timeout(None, "120") == 120.0


def test_resolve_cli_overrides_env():
    assert drv._resolve_request_timeout("42", "120") == 42.0


@pytest.mark.parametrize("bad", ["0", "-5", "0.0", "-0.1", "abc", "", "nan", "inf", "-inf", "1e400"])
def test_resolve_rejects_invalid(bad):
    # float("nan")/float("inf") parse but are non-finite -> rejected; 1e400 overflows to inf
    with pytest.raises(SystemExit):
        drv._resolve_request_timeout(bad, None)


# --------------------------------------------------------------- 5,13,17: provider integration
def test_resolved_timeout_reaches_urlopen(monkeypatch):
    seen = []

    def fake_urlopen(req, timeout=None):
        seen.append(timeout)
        return _FakeResp(json.dumps(OK_BODY).encode())

    monkeypatch.setattr(openai_provider, "urlopen", fake_urlopen)
    p = OpenAIProvider("test-key", "http://example.test", "m")
    p.chat([{"role": "user", "content": "hi"}], timeout=42.0)
    assert seen == [42.0]


def test_each_retry_makes_a_new_urlopen_call(monkeypatch):
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(1)
        if len(calls) < 3:
            raise TimeoutError("timed out")
        return _FakeResp(json.dumps(OK_BODY).encode())

    monkeypatch.setattr(openai_provider, "urlopen", fake_urlopen)
    p = OpenAIProvider("test-key", "http://example.test", "m")
    resp, n = drv._chat_with_retry(p, [{"role": "user", "content": "hi"}],
                                   {"timeout": 1.0, "max_tokens": 5}, retries=4)
    assert len(calls) == 3          # two timeouts (new urlopen each) + one success
    assert n == 2


def test_provider_response_parsing_unchanged(monkeypatch):
    monkeypatch.setattr(openai_provider, "urlopen",
                        lambda req, timeout=None: _FakeResp(json.dumps(OK_BODY).encode()))
    p = OpenAIProvider("test-key", "http://example.test", "m")
    r = p.chat([{"role": "user", "content": "hi"}], timeout=10.0)
    assert r.text == "OK"
    assert r.usage["prompt_tokens"] == 7 and r.usage["completion_tokens"] == 3
    assert r.model == "m"


# --------------------------------------------------------------- 6-9,10,11: classification
def test_classify_socket_timeout():
    assert drv._classify_retryable(_socket.timeout("timed out")) == ("timeout", True)


def test_classify_timeout_error():
    assert drv._classify_retryable(TimeoutError("timed out")) == ("timeout", True)


def test_classify_urlerror_socket_timeout():
    assert drv._classify_retryable(urllib.error.URLError(_socket.timeout("timed out"))) == ("timeout", True)


def test_classify_connection_reset():
    assert drv._classify_retryable(ConnectionResetError("reset")) == ("connection", True)


def test_classify_urlerror_connection():
    assert drv._classify_retryable(urllib.error.URLError(ConnectionRefusedError("refused"))) == ("connection", True)


def test_classify_retryable_http_503_429():
    assert drv._classify_retryable(ProviderHTTPError(503, "d", "b")) == ("retryable_http", True)
    assert drv._classify_retryable(ProviderHTTPError(429, "d", "b")) == ("retryable_http", True)


def test_classify_non_retryable_http_400_401_404():
    for code in (400, 401, 403, 404):
        cat, retry = drv._classify_retryable(ProviderHTTPError(code, "d", "b"))
        assert (cat, retry) == ("non_retryable_http", False), code


def test_classify_does_not_retry_arbitrary_oserror():
    # FileNotFoundError is an OSError but NOT a transient connection failure -> not retried
    cat, retry = drv._classify_retryable(FileNotFoundError("nope"))
    assert retry is False


# --------------------------------------------------------------- _chat_with_retry behavior
def test_retryable_503_then_success():
    p = _FakeProvider([ProviderHTTPError(503, "d", "b"), "OK"])
    resp, n = drv._chat_with_retry(p, [{}], {}, retries=4)
    assert resp == "OK" and n == 1 and p.calls == 2


def test_non_retryable_400_not_retried():
    p = _FakeProvider([ProviderHTTPError(400, "bad model", "b")])
    with pytest.raises(ProviderHTTPError):
        drv._chat_with_retry(p, [{}], {}, retries=4)
    assert p.calls == 1           # no retry


def test_attempt_count_bounded_by_outer_loop():
    p = _FakeProvider([ProviderHTTPError(503, "d", "b")] * 10)
    with pytest.raises(ProviderHTTPError):
        drv._chat_with_retry(p, [{}], {}, retries=2)
    assert p.calls == 3           # retries=2 -> 3 total attempts, NOT 10


def test_persistent_stall_is_bounded():
    p = _FakeProvider([TimeoutError("timed out")] * 10)
    t0 = time.time()
    with pytest.raises(TimeoutError):
        drv._chat_with_retry(p, [{}], {"timeout": 0.2}, retries=2)
    assert p.calls == 3
    assert time.time() - t0 < 5.0   # terminates promptly (backoff is no-op here)


# --------------------------------------------------------------- 16: sanitized logging
def test_retry_log_has_category_class_attempt_but_no_secrets(capsys, monkeypatch):
    # ProviderHTTPError whose detail mentions a URL -- the message must NOT be logged
    p = _FakeProvider([ProviderHTTPError(503, "see https://user:secret@gateway/x", "b"), "OK"])
    drv._chat_with_retry(p, [{}], {}, retries=4)
    err = capsys.readouterr().err
    assert "[llm_retry]" in err
    assert "attempt=" in err and "category=retryable_http" in err and "exc=ProviderHTTPError" in err
    # no secret material: no api key, no Authorization, no credential-bearing URL/detail
    assert "secret" not in err
    assert "Authorization" not in err and "Bearer" not in err and "test-key" not in err


# --------------------------------------------------------------- local fake-server scenarios
def test_server_stall_then_success():
    """Scenario A: first request delays past the timeout (raises), retry succeeds."""
    base, srv = _make_fake_server([(2.0, 200, OK_BODY), (0.0, 200, OK_BODY)])
    try:
        p = OpenAIProvider("test-key", base, "m")
        t0 = time.time()
        resp, n = drv._chat_with_retry(p, [{"role": "user", "content": "hi"}],
                                       {"timeout": 0.5, "max_tokens": 5}, retries=4)
        assert resp.text == "OK" and n == 1
        assert time.time() - t0 < 6.0   # bounded (timeout 0.5 + backoff no-op)
    finally:
        srv.shutdown(); srv.server_close()


def test_server_retryable_503_then_success():
    """Scenario D: first request 503, retry succeeds."""
    base, srv = _make_fake_server([(0.0, 503, {"error": "busy"}), (0.0, 200, OK_BODY)])
    try:
        p = OpenAIProvider("test-key", base, "m")
        resp, n = drv._chat_with_retry(p, [{"role": "user", "content": "hi"}],
                                       {"timeout": 2.0, "max_tokens": 5}, retries=4)
        assert resp.text == "OK" and n == 1
    finally:
        srv.shutdown(); srv.server_close()


def test_server_non_retryable_400():
    """Scenario C: deterministic 400 -> no retry."""
    base, srv = _make_fake_server([(0.0, 400, {"error": "invalid model"})])
    try:
        p = OpenAIProvider("test-key", base, "m")
        with pytest.raises(ProviderHTTPError) as ei:
            drv._chat_with_retry(p, [{"role": "user", "content": "hi"}],
                                 {"timeout": 2.0, "max_tokens": 5}, retries=4)
        assert ei.value.status_code == 400
    finally:
        srv.shutdown(); srv.server_close()


def test_server_persistent_stall_terminates():
    """Scenario B: every attempt stalls -> bounded retries -> clear final error, promptly."""
    base, srv = _make_fake_server([(5.0, 200, OK_BODY)] * 99)  # always delay 5s >> timeout
    try:
        p = OpenAIProvider("test-key", base, "m")
        t0 = time.time()
        with pytest.raises((TimeoutError, urllib.error.URLError)):
            drv._chat_with_retry(p, [{"role": "user", "content": "hi"}],
                                 {"timeout": 0.3, "max_tokens": 5}, retries=2)
        # 3 attempts * 0.3s timeout + no-op backoff -> well under the per-attempt server delay
        assert time.time() - t0 < 5.0
    finally:
        srv.shutdown(); srv.server_close()
