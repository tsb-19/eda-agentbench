"""Phase-4V0: dependency-free SSE streaming support for the urllib LLM provider.

Verifies the opt-in streaming path (provider + driver + process-isolated worker) using ONLY local
fake servers / monkeypatched responses -- NO paid gateway is contacted. Covers the required fake-SSE
scenarios A-N and the unit/regression items from the Phase-4V0 spec:

* config resolution + malformed rejection
* request body carries stream=true + stream_options.include_usage ONLY when enabled
* reasoning/answer separation; only answer content reaches the caller
* usage capture incl. reasoning_tokens; finish_reason + [DONE] handling
* incomplete_stream / malformed_stream classification; bounded retry; no inner streaming retry loop
* NO raw reasoning text in logs or worker IPC output; no secrets in worker stdout
* hard deadline still kills an endless slow-drip stream; op-timeout still handles silence
* the non-streaming provider path is byte/field compatible with prior behavior
"""
from __future__ import annotations

import json
import os
import socket as _socket
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
from eda_agentbench.llm import openai_provider  # noqa: E402
from eda_agentbench.llm.openai_provider import (  # noqa: E402
    OpenAIProvider, ProviderHTTPError, StreamIncomplete, StreamMalformed,
)

# Real-worker tests spawn the POSIX process-isolated worker and validate the killpg/reap guarantee.
_skip_non_posix = pytest.mark.skipif(
    not (hasattr(os, "killpg") and hasattr(os, "getpgid")),
    reason="POSIX process-group termination (start_new_session/os.killpg) not available")


# --------------------------------------------------------------------------- SSE line builders
def _data(obj: dict) -> bytes:
    return ("data: " + json.dumps(obj) + "\n").encode()


def _done() -> bytes:
    return b"data: [DONE]\n"


def _comment(text: str = "keepalive") -> bytes:
    return (": " + text + "\n").encode()


def _blank() -> bytes:
    return b"\n"


def _delta(reason: str = "", answer: str = "", finish=None) -> dict:
    d = {}
    if reason:
        d["reasoning_content"] = reason
    if answer:
        d["content"] = answer
    return {"choices": [{"delta": d, "finish_reason": finish}]}


def _usage_obj() -> dict:
    return {"choices": [], "usage": {
        "prompt_tokens": 11, "completion_tokens": 9,
        "completion_tokens_details": {"reasoning_tokens": 6}}}


# --------------------------------------------------------------------------- monkeypatchable stream resp
class _FakeStreamResp:
    """Mimics http.client.HTTPResponse enough for _chat_stream: readline() yields scripted byte
    lines (one per call); close() is a no-op. Deterministic SSE-parser tests without sockets."""

    def __init__(self, lines: list[bytes]):
        self._lines = list(lines)
        self._i = 0

    def readline(self):
        if self._i >= len(self._lines):
            return b""  # EOF
        ln = self._lines[self._i]
        self._i += 1
        return ln

    def close(self):
        pass


class _FakeTimeoutResp:
    """readline() yields N scripted lines, then raises socket.timeout (network-layer timeout
    propagating raw out of _chat_stream)."""

    def __init__(self, lines: list[bytes], ok_lines: int):
        self._lines = list(lines)
        self._ok = ok_lines
        self._i = 0

    def readline(self):
        if self._i < self._ok:
            ln = self._lines[self._i]
            self._i += 1
            return ln
        raise _socket.timeout("stream went silent")

    def close(self):
        pass


class _FakeNonStreamResp:
    """For the non-streaming regression: .read() returns one JSON body; context manager."""

    def __init__(self, body: bytes):
        self._b = body

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


# --------------------------------------------------------------------------- local fake SSE server (sockets)
def _sse_frame_bytes(frame):
    kind = frame[0]
    if kind == "reason":
        return _data({"choices": [{"delta": {"reasoning_content": frame[1]}}]})
    if kind == "answer":
        return _data({"choices": [{"delta": {"content": frame[1]}}]})
    if kind == "finish":
        return _data({"choices": [{"delta": {}, "finish_reason": frame[1]}]})
    if kind == "usage":
        return _data(frame[1])  # {"choices":[],"usage":{...}}
    if kind == "done":
        return _done()
    if kind == "comment":
        return _comment(frame[1] if len(frame) > 1 else "keepalive")
    if kind == "blank":
        return _blank()
    if kind == "malformed":
        return ("data: " + frame[1] + "\n").encode()
    raise ValueError("unknown frame kind %r" % (kind,))


def _make_sse_server(scripts):
    """scripts = [ [frame, ...], ... ] one frame-list per request (index clamped). Frames:
    ('reason',t)|('answer',t)|('finish',fr)|('usage',obj)|('done',)|('comment',t)|('blank',)|
    ('malformed',s)|('sleep',secs)|('drip_forever',interval)|('respond',status,json_obj).
    Returns (base_url, server). Caller must .shutdown()+.server_close()."""
    lock = threading.Lock()
    state = {"i": 0, "b": list(scripts)}

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, *a):
            pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length:
                self.rfile.read(length)
            with lock:
                idx = min(state["i"], len(state["b"]) - 1)
                state["i"] += 1
                script = list(state["b"][idx])
            # a leading 'respond' frame sends a non-SSE status response (error scenarios)
            if script and script[0][0] == "respond":
                _, status, body_obj = script[0]
                payload = json.dumps(body_obj).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                try:
                    self.wfile.write(payload)
                except Exception:
                    pass
                return
            # SSE response: headers first, then frames streamed with flush per frame. No
            # Content-Length + Connection: close -> the client reads until EOF.
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            for frame in script:
                kind = frame[0]
                if kind == "sleep":
                    threading.Event().wait(frame[1])  # Event().wait survives the time.sleep patch
                    continue
                if kind == "drip_forever":
                    interval = frame[1]
                    while True:
                        try:
                            self.wfile.write(_sse_frame_bytes(("reason", "drip")))
                            self.wfile.flush()
                        except Exception:
                            return
                        threading.Event().wait(interval)
                try:
                    self.wfile.write(_sse_frame_bytes(frame))
                    self.wfile.flush()
                except Exception:
                    return
            # script exhausted -> handler returns -> Connection: close -> client sees EOF

    class Server(http.server.ThreadingHTTPServer):
        allow_reuse_address = True
        daemon_threads = True

    srv = Server(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}", srv


@pytest.fixture(autouse=True)
def _fast_backoff_and_key(monkeypatch):
    # make the retry-loop backoff instant; the WORKER subprocess keeps its own real clock (server
    # delays use Event().wait, unaffected). Ensure a key is present so the worker reports success.
    monkeypatch.setattr(drv.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setenv("API_KEY", "test-key-not-a-real-secret")


def _provider(base):
    return OpenAIProvider("test-key", base, "m")


def _stream_chat(monkeypatch, lines):
    """provider.chat(stream=True) against a scripted fake stream response (no sockets)."""
    monkeypatch.setattr(openai_provider, "urlopen",
                        lambda req, timeout=None: _FakeStreamResp(lines))
    p = OpenAIProvider("test-key", "http://example.test", "m")
    return p.chat([{"role": "user", "content": "hi"}], stream=True, timeout=10.0, max_tokens=5)


# ============================================================ config resolution (items 1-3)
def test_stream_default_false(monkeypatch):
    monkeypatch.delenv("EDA_BENCH_STREAM_RESPONSES", raising=False)
    assert drv._resolve_stream_flag(None, None) is False


@pytest.mark.parametrize("cli,env,want", [
    ("1", None, True), (None, "on", True), (None, "TRUE", True), ("yes", "0", True),
    ("0", "1", False), (None, "off", False), ("no", None, False), (None, "False", False),
])
def test_stream_precedence_and_values(cli, env, want):
    assert drv._resolve_stream_flag(cli, env) is want


@pytest.mark.parametrize("bad", ["maybe", "2", "yep", " ", "stream", "t"])
def test_stream_malformed_rejected(bad):
    with pytest.raises(SystemExit):
        drv._resolve_stream_flag(bad, None)


# ============================================================ request body (items 4-5)
def test_body_has_stream_only_when_enabled(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["body"] = json.loads(req.data.decode())
        # return a minimal valid stream so the call succeeds
        return _FakeStreamResp([_data(_delta(answer="ok", finish="stop")), _done()])

    monkeypatch.setattr(openai_provider, "urlopen", fake_urlopen)
    p = OpenAIProvider("test-key", "http://example.test", "m")
    p.chat([{"role": "user", "content": "hi"}], stream=True, timeout=10.0)
    assert captured["body"]["stream"] is True
    assert captured["body"]["stream_options"] == {"include_usage": True}
    # other fields untouched
    assert captured["body"]["model"] == "m" and captured["body"]["max_tokens"] == 2000


def test_body_has_no_stream_when_disabled(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["body"] = json.loads(req.data.decode())
        return _FakeNonStreamResp(json.dumps(
            {"model": "m", "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
             "usage": {"prompt_tokens": 1, "completion_tokens": 1}}).encode())

    monkeypatch.setattr(openai_provider, "urlopen", fake_urlopen)
    p = OpenAIProvider("test-key", "http://example.test", "m")
    p.chat([{"role": "user", "content": "hi"}], timeout=10.0)  # no stream
    assert "stream" not in captured["body"]
    assert "stream_options" not in captured["body"]


# ============================================================ SSE parser (provider-level, no sockets)
# Scenario A: reasoning then answer then finish then usage then [DONE]
def test_scenario_A_reasoning_then_answer(monkeypatch):
    lines = [
        _comment(), _blank(),
        _data(_delta(reason="thinking 1")), _blank(),
        _data(_delta(reason="thinking 2")), _blank(),
        _data(_delta(answer="Hello")), _blank(),
        _data(_delta(answer=" world")), _blank(),
        _data(_delta(finish="stop")), _blank(),
        _data(_usage_obj()), _blank(),
        _done(), _blank(),
    ]
    r = _stream_chat(monkeypatch, lines)
    assert r.text == "Hello world"                       # item 7: only answer content returned
    assert "thinking" not in r.text                      # item 6: reasoning NOT in the answer
    assert r.metadata["reasoning_content"] == "thinking 1thinking 2"  # kept separate in metadata
    assert r.usage["prompt_tokens"] == 11 and r.usage["completion_tokens"] == 9
    assert r.usage["reasoning_tokens"] == 6              # item 9: reasoning-token usage capture
    assert r.metadata["finish_reason"] == "stop"         # item 10
    st = r.metadata["stream"]
    assert st["done_seen"] is True and st["chunk_count"] >= 6   # item 11
    assert st["reasoning_chars"] == len("thinking 1thinking 2")
    assert st["answer_chars"] == len("Hello world")


# Scenario E: usage-only final chunk (empty choices + usage) is parsed
def test_scenario_E_usage_only_final_chunk(monkeypatch):
    lines = [
        _data(_delta(answer="done")), _blank(),
        _data(_delta(finish="stop")), _blank(),
        _data(_usage_obj()), _blank(),                   # empty choices, usage present
        _done(), _blank(),
    ]
    r = _stream_chat(monkeypatch, lines)
    assert r.text == "done"
    assert r.usage["reasoning_tokens"] == 6 and r.usage["prompt_tokens"] == 11  # item 8


# Scenario F: missing [DONE] but finish_reason present -> accepted, done_seen False
def test_scenario_F_no_done_finish_present(monkeypatch):
    lines = [_data(_delta(answer="ok")), _blank(), _data(_delta(finish="stop")), _blank()]
    r = _stream_chat(monkeypatch, lines)
    assert r.text == "ok"
    assert r.metadata["finish_reason"] == "stop"
    assert r.metadata["stream"]["done_seen"] is False    # item 11: [DONE] absent recorded


# Scenario G: premature EOF (partial answer, no finish/[DONE]) -> incomplete_stream
def test_scenario_G_premature_eof(monkeypatch):
    lines = [_data(_delta(answer="partia")), _blank()]   # no finish, no DONE, then EOF
    with pytest.raises(StreamIncomplete):
        _stream_chat(monkeypatch, lines)


# Scenario H: reasoning-only EOF -> incomplete_stream, reasoning never returned as answer
def test_scenario_H_reasoning_only_eof(monkeypatch):
    lines = [_data(_delta(reason="only thinking")), _blank()]
    with pytest.raises(StreamIncomplete) as ei:
        _stream_chat(monkeypatch, lines)
    assert "SECRET" not in str(ei.value) and "only thinking" not in str(ei.value)


# Scenario I: malformed SSE JSON -> malformed_stream
def test_scenario_I_malformed_json(monkeypatch):
    lines = [("data: {not valid json\n").encode()]
    with pytest.raises(StreamMalformed):
        _stream_chat(monkeypatch, lines)


# Scenario J: SSE comments and blank separators are ignored
def test_scenario_J_comments_and_blanks_ignored(monkeypatch):
    lines = [
        _comment("keep1"), _blank(),
        _data(_delta(answer="a")), _blank(), _blank(),
        _comment("keep2"),
        _data(_delta(answer="b")), _blank(),
        _data(_delta(finish="stop")), _blank(),
        _done(),
    ]
    r = _stream_chat(monkeypatch, lines)
    assert r.text == "ab"


# Scenario K: UTF-8 / non-ASCII content assembles correctly across deltas
def test_scenario_K_utf8_boundaries(monkeypatch):
    lines = [
        _data(_delta(answer="你好")), _blank(),
        _data(_delta(answer="世界")), _blank(),
        _data(_delta(answer="🎉")), _blank(),
        _data(_delta(finish="stop")), _blank(),
        _done(),
    ]
    r = _stream_chat(monkeypatch, lines)
    assert r.text == "你好世界🎉"


# --------------------------------------------------------------------------- SSE framing edge cases
# The parser is tuned for the OpenAI-compatible wire format (one `data:` line per event). These lock
# in safe handling of CRLF line endings, `data:` with/without a following space, multiple leading
# spaces, a no-space `[DONE]`, and two back-to-back `data:` JSON lines (parsed independently, never
# corrupted). (Phase-4V0 review note 2.)
def test_framing_crlf_line_endings(monkeypatch):
    # full CRLF framing: data line + blank separator both \r\n-terminated
    lines = [
        b"data: " + json.dumps(_delta(answer="hi")).encode() + b"\r\n",
        b"\r\n",
        b"data: " + json.dumps(_delta(finish="stop")).encode() + b"\r\n",
        b"\r\n",
        b"data: [DONE]\r\n",
        b"\r\n",
    ]
    r = _stream_chat(monkeypatch, lines)
    assert r.text == "hi" and r.metadata["stream"]["done_seen"] is True


def test_framing_data_no_space(monkeypatch):
    # "data:{...}" with NO space after the colon
    lines = [
        ("data:" + json.dumps(_delta(answer="x")) + "\n").encode(),
        ("data:" + json.dumps(_delta(finish="stop")) + "\n").encode(),
        b"data:[DONE]\n",
    ]
    r = _stream_chat(monkeypatch, lines)
    assert r.text == "x" and r.metadata["stream"]["done_seen"] is True


def test_framing_data_multiple_spaces(monkeypatch):
    # "data:  {...}" with TWO spaces (lenient lstrip; JSON tolerates leading whitespace)
    lines = [
        ("data:  " + json.dumps(_delta(answer="y")) + "\n").encode(),
        ("data: " + json.dumps(_delta(finish="stop")) + "\n").encode(),
        b"data: [DONE]\n",
    ]
    r = _stream_chat(monkeypatch, lines)
    assert r.text == "y"


def test_framing_two_data_lines_parsed_independently(monkeypatch):
    # two valid `data:` JSON lines with NO blank separator between them are parsed as two chunks,
    # never concatenated/corrupted (OpenAI sends one data line per event; this confirms graceful
    # handling if two ever appear back-to-back).
    lines = [
        _data(_delta(answer="a")),
        _data(_delta(answer="b")),
        _data(_delta(finish="stop")),
        _done(),
    ]
    r = _stream_chat(monkeypatch, lines)
    assert r.text == "ab"
    assert r.metadata["stream"]["chunk_count"] == 3   # three JSON chunks parsed


def test_framing_uppercase_field_names_ignored_safely(monkeypatch):
    # non-`data:` SSE fields (e.g. uppercase or event:/id:) are ignored, not misparsed as data
    lines = [
        b"event: message\n",
        b"id: 42\n",
        _data(_delta(answer="z")),
        _data(_delta(finish="stop")),
        _done(),
    ]
    r = _stream_chat(monkeypatch, lines)
    assert r.text == "z"


def test_no_chunks_at_all_is_incomplete(monkeypatch):
    # [DONE] with zero JSON chunks -> got_chunk False -> incomplete_stream
    monkeypatch.setattr(openai_provider, "urlopen",
                        lambda req, timeout=None: _FakeStreamResp([_done()]))
    p = OpenAIProvider("test-key", "http://example.test", "m")
    with pytest.raises(StreamIncomplete):
        p.chat([{"role": "user", "content": "hi"}], stream=True, timeout=10.0)


def test_network_timeout_propagates_raw(monkeypatch):
    # a readline that raises socket.timeout must propagate (callers classify by type)
    monkeypatch.setattr(openai_provider, "urlopen",
                        lambda req, timeout=None: _FakeTimeoutResp(
                            [_data(_delta(reason="x")), _blank()], ok_lines=1))
    p = OpenAIProvider("test-key", "http://example.test", "m")
    with pytest.raises((_socket.timeout, TimeoutError)):
        p.chat([{"role": "user", "content": "hi"}], stream=True, timeout=10.0)
    # and it is classified retryable as a timeout
    cat, retry = drv._classify_retryable(StreamIncomplete("x"))  # sanity for the new classes
    assert cat == "incomplete_stream" and retry


# ============================================================ classification wiring
def test_classify_streaming_exceptions():
    assert drv._classify_retryable(StreamIncomplete("x")) == ("incomplete_stream", True)
    assert drv._classify_retryable(StreamMalformed("x")) == ("malformed_stream", True)
    assert drv._classify_worker_error("StreamIncomplete", None) == ("incomplete_stream", True)
    assert drv._classify_worker_error("StreamMalformed", None) == ("malformed_stream", True)


# ============================================================ local fake-server scenarios (real worker)
@_skip_non_posix
def test_scenario_B_long_reasoning_keeps_stream_alive():
    """B: reasoning chunks arrive periodically for longer than the op-timeout window; the stream
    stays alive (each underlying recv() returns within the inactivity window) so NO socket timeout
    fires. (The strict total-duration bound is the hard deadline, exercised in scenario C.)"""
    script = []
    for i in range(5):
        script += [("reason", "think %d" % i), ("sleep", 0.2)]   # ~1.0s of periodic reasoning
    script += [("answer", "final"), ("finish", "stop"), ("done")]
    base, srv = _make_sse_server([script])
    try:
        res = drv._attempt_isolated(_provider(base), [{"role": "user", "content": "hi"}],
                                    {"stream": True, "max_tokens": 5}, request_deadline=5.0,
                                    op_timeout=0.4)
        assert res.success, "category=%s term=%s" % (res.category, res.termination)
        assert res.resp.text == "final"
        assert res.category is None                                    # no timeout fired
    finally:
        srv.shutdown(); srv.server_close()


@_skip_non_posix
def test_scenario_C_endless_drip_hard_deadline_kills_worker():
    """C (DECISIVE): server drips a reasoning chunk every 0.2s (< op_timeout) so the per-op timeout
    does NOT fire; the HARD process deadline DOES fire and kills+reaps the worker. (item 15)"""
    base, srv = _make_sse_server([[("drip_forever", 0.2)]])
    try:
        res = drv._attempt_isolated(_provider(base), [{"role": "user", "content": "hi"}],
                                    {"stream": True, "max_tokens": 5}, request_deadline=1.5,
                                    op_timeout=1.0)
        assert res.category == "hard_request_deadline"                # NOT socket_timeout
        assert res.termination in ("terminate", "kill")
        assert res.worker_pid is not None
        try:
            os.kill(res.worker_pid, 0)
            alive = True
        except (ProcessLookupError, PermissionError):
            alive = False
        assert not alive, "worker %d still alive after deadline" % res.worker_pid
        assert res.elapsed < 5.0
    finally:
        srv.shutdown(); srv.server_close()


@_skip_non_posix
def test_scenario_D_silent_connection_op_timeout():
    """D: server accepts, sends headers, then sleeps (no chunks) -> per-op timeout fires. (item 16)"""
    base, srv = _make_sse_server([[("sleep", 30)]])
    try:
        res = drv._attempt_isolated(_provider(base), [{"role": "user", "content": "hi"}],
                                    {"stream": True, "max_tokens": 5}, request_deadline=5.0,
                                    op_timeout=0.5)
        assert res.category == "socket_timeout"
        assert res.termination == "normal_exit"                       # worker exited on its own
        assert res.elapsed < 3.0
    finally:
        srv.shutdown(); srv.server_close()


@_skip_non_posix
def test_scenario_M_stream_unsupported_400_no_fallback_no_retry():
    """M: a deterministic 400 when streaming -> ProviderHTTPError(400), no silent non-streaming
    fallback, no repeated retry."""
    base, srv = _make_sse_server([[("respond", 400, {"error": "streaming not supported"})]])
    try:
        res = drv._attempt_isolated(_provider(base), [{"role": "user", "content": "hi"}],
                                    {"stream": True, "max_tokens": 5}, request_deadline=8.0,
                                    op_timeout=5.0)
        assert res.category == "non_retryable_http" and res.status == 400 and res.retryable is False
        # via the retry loop: raises promptly, exactly ONE attempt
        with pytest.raises(RuntimeError) as ei:
            drv._chat_with_retry_deadline(_provider(base), [{"role": "user", "content": "hi"}],
                                          {"stream": True, "max_tokens": 5}, 8.0, 5.0, retries=2)
        assert "non_retryable_http" in str(ei.value) and "400" in str(ei.value)
    finally:
        srv.shutdown(); srv.server_close()


@_skip_non_posix
def test_scenario_N_retryable_503_then_streamed_success():
    """N: first request 503 (retryable), second fresh request streams a valid answer. (item 17)"""
    bad = [("respond", 503, {"error": "busy"})]
    good = [("answer", "RECOVERED"), ("finish", "stop"), ("done")]
    base, srv = _make_sse_server([bad, good])
    try:
        resp, n = drv._chat_with_retry_deadline(_provider(base), [{"role": "user", "content": "hi"}],
                                                {"stream": True, "max_tokens": 5},
                                                request_deadline=8.0, op_timeout=5.0, retries=2)
        assert resp.text == "RECOVERED" and n == 1                     # exactly one retry
    finally:
        srv.shutdown(); srv.server_close()


@_skip_non_posix
def test_incomplete_stream_is_retryable_then_raises_bounded():
    """Persistent premature-EOF stream -> bounded attempts, then raises incomplete_stream."""
    eof = [("answer", "partial")]   # answer but no finish/[DONE], then close -> incomplete
    base, srv = _make_sse_server([eof] * 5)
    t0 = time.time()
    try:
        with pytest.raises(RuntimeError) as ei:
            drv._chat_with_retry_deadline(_provider(base), [{"role": "user", "content": "hi"}],
                                          {"stream": True, "max_tokens": 5}, 8.0, 5.0, retries=1)
        assert "incomplete_stream" in str(ei.value)
        assert time.time() - t0 < 10.0                               # bounded (2 attempts)
    finally:
        srv.shutdown(); srv.server_close()


def test_retry_loop_no_overlapping_streaming_attempts():
    """Structural no-overlap proof (item 18): _retry_loop awaits each attempt_fn before the next,
    so two streaming-style attempts never run concurrently."""
    active = {"now": 0, "max": 0}

    def attempt_fn():
        active["now"] += 1
        active["max"] = max(active["max"], active["now"])
        time.sleep(0.05)            # instant under the autouse patch
        active["now"] -= 1
        return drv._AttemptResult(category="incomplete_stream", retryable=True)

    with pytest.raises(RuntimeError):
        drv._retry_loop(attempt_fn, retries=2, on_attempt=lambda *a: None)
    assert active["max"] == 1


# ============================================================ reasoning / secret safety
@_skip_non_posix
def test_worker_output_has_no_raw_reasoning():
    """item 14: spawn the REAL worker against a fake SSE server that emits reasoning + answer;
    the worker's stdout JSON must NOT carry reasoning_content or the reasoning text."""
    script = [("reason", "TOPSECRET-CHAIN-OF-THOUGHT"), ("answer", "ok"),
              ("finish", "stop"), ("done")]
    base, srv = _make_sse_server([script])
    try:
        payload = json.dumps({"api_base": base, "model": "m",
                              "messages": [{"role": "user", "content": "hi"}],
                              "gen_kwargs": {"stream": True, "timeout": 5.0, "max_tokens": 5}})
        proc = subprocess.run([sys.executable, str(REPO / "scripts" / "_llm_request_worker.py")],
                              input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, env={**os.environ}, timeout=20)
        obj = json.loads(proc.stdout)
        assert obj["ok"] is True and obj["text"] == "ok"
        assert "reasoning_content" not in obj["metadata"]            # raw reasoning stripped
        assert "TOPSECRET-CHAIN-OF-THOUGHT" not in proc.stdout       # reasoning text absent
        assert "TOPSECRET-CHAIN-OF-THOUGHT" not in proc.stderr
        assert "reasoning_chars" in obj["metadata"]                  # safe aggregate kept
        assert "test-key" not in proc.stdout and "test-key" not in proc.stderr
    finally:
        srv.shutdown(); srv.server_close()


def test_no_reasoning_text_in_isolated_log_capsys(capsys):
    """item 13 (capsys): streaming retry log carries category/counts but not the reasoning text."""
    monkeypatch_patch = None
    # build a fake worker that emits sanitized metadata with reasoning present server-side
    class _P:
        def __init__(self, cmd, **kw):
            self.pid = 4242
            self.returncode = 0

        def communicate(self, stdin=None, timeout=None):
            return (json.dumps({"ok": True, "text": "ans", "model": "m",
                                "usage": {"prompt_tokens": 1, "completion_tokens": 1,
                                          "reasoning_tokens": 3},
                                "metadata": {"finish_reason": "stop",
                                             "reasoning_chars": 31,
                                             "reasoning_sha256": "abcdef012345",
                                             "stream": {"chunk_count": 4, "reasoning_chars": 31,
                                                        "answer_chars": 3, "done_seen": True}}}
                                ).encode(), b"")

        def wait(self, timeout=None):
            return 0

    import llm_agent_driver as _drv
    orig_popen = _drv.subprocess.Popen
    _drv.subprocess.Popen = lambda *a, **k: _P(*a, **k)
    try:
        _drv._chat_with_retry_deadline(
            OpenAIProvider("real-secret-key", "http://gateway.example.test/v1", "DeepSeek-V4-Pro"),
            [{"role": "system", "content": "CONFIDENTIAL-PROMPT"},
             {"role": "user", "content": "hi"}], {"stream": True, "max_tokens": 4096},
            5.0, 2.0, retries=0)
    finally:
        _drv.subprocess.Popen = orig_popen
    err = capsys.readouterr().err
    assert "[llm_deadline]" in err and "category=success" in err
    assert "real-secret-key" not in err
    assert "CONFIDENTIAL-PROMPT" not in err
    assert "Authorization" not in err and "Bearer" not in err


# ============================================================ non-streaming regression (L / item 19)
def test_non_streaming_provider_path_unchanged(monkeypatch):
    """L: the non-streaming provider path returns the SAME fields as before (incl. reasoning_content
    in metadata), and the request body has no stream keys."""
    body_obj = {"model": "m",
                "choices": [{"message": {"content": "OK", "reasoning_content": "rtext"},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 3,
                          "completion_tokens_details": {"reasoning_tokens": 2}}}
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["body"] = json.loads(req.data.decode())
        return _FakeNonStreamResp(json.dumps(body_obj).encode())

    monkeypatch.setattr(openai_provider, "urlopen", fake_urlopen)
    p = OpenAIProvider("test-key", "http://example.test", "m")
    r = p.chat([{"role": "user", "content": "hi"}], timeout=10.0)
    assert r.text == "OK"
    assert r.model == "m"
    assert r.usage == {"prompt_tokens": 7, "completion_tokens": 3, "reasoning_tokens": 2}
    assert r.metadata["finish_reason"] == "stop"
    assert r.metadata["reasoning_content"] == "rtext"        # non-stream still carries it
    assert "stream" not in r.metadata                         # no stream diagnostics on non-stream
    assert "stream" not in captured["body"]                   # body unchanged
