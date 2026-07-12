#!/usr/bin/env python3
"""LLM agentic driver — the `agent_cmd` for eda_agentbench's run_single_agentic.

Runs ONE model through a bounded ReAct loop inside the agent workspace
($EDA_WORKSPACE, == cwd). Each turn the model emits exactly one action:

    RUN: <shell command>     run a command in the workspace, observe its output
    WRITE: <filename>        overwrite an editable file (content in a ``` block)
    ```
    <full new file content>
    ```
    FINISH                   stop; the edited files are the submission

This gives the model real tools (it can `bash run_public.sh` to see live sg_shell/
pt_shell output) and real symptom-level feedback, while the runner keeps hidden/
solution out of the workspace and withholds the acceptance verdict until grading.

ISOLATION (critical): the runner exports EDA_TASK_PATH (the real task dir, which
contains hidden/ and solution/) into our env. We MUST NOT reveal it to the model,
and we scrub it from the env of every RUN subprocess, plus refuse commands that
look like attempts to read the oracle. Without this an agent could just
`cat $EDA_TASK_PATH/solution/*`.

Invoked (by scripts/run_agentic_baseline.py) as:
    python3 scripts/llm_agent_driver.py --model GLM-5.1 --models configs/baseline_models.json \
        --max-actions 12 --log <path>.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.error
from pathlib import Path
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.generate_model_submissions import load_model_specs  # noqa: E402
from eda_agentbench.llm.base import LLMResponse  # noqa: E402
from eda_agentbench.llm.openai_provider import (  # noqa: E402
    DEFAULT_REQUEST_DEADLINE_SEC, DEFAULT_REQUEST_TIMEOUT_SEC, ProviderHTTPError, StreamIncomplete,
    StreamMalformed,
)
from eda_agentbench.reliability import parse_confidence  # noqa: E402

# process-isolated request worker (one provider.chat() call per child; killed at the hard deadline)
_REQUEST_WORKER = REPO / "scripts" / "_llm_request_worker.py"

# Agentic confidence elicitation (reliability pivot): asked on the FINISH message, parsed there.
_CONF_FINISH = (
    "      When you FINISH, on the SAME message add one final line outside any code block:\n"
    "      CONFIDENCE: <HIGH | MEDIUM | LOW | ABSTAIN>\n"
    "      stating how sure you are the fix is correct (ABSTAIN = 'needs human review'). Report "
    "honestly — a wrong fix declared HIGH is the worst outcome.\n")

# Commands that look like attempts to escape the workspace / read the oracle.
_DENY = re.compile(r"(EDA_TASK_PATH|/hidden\b|/solution\b|/oracle\b|run_hidden|\.\./)", re.I)
_ACTION_RE = re.compile(r"^\s*(RUN|WRITE|FINISH)\b[:\s]?(.*)$", re.I | re.M)
_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.S)


def _provider_for(model_name: str, models_cfg: Path):
    for name, provider, gen_kwargs in load_model_specs(models_cfg, allow_mock=False):
        if name == model_name:
            return provider, gen_kwargs
    raise SystemExit(f"model {model_name!r} not found in {models_cfg}")


def _resolve_request_timeout(cli_val, env_val):
    """Resolve the per-request timeout (seconds). Precedence: CLI > env > default.
    Rejects zero/negative/non-numeric/non-finite with a clear error (before launch)."""
    if cli_val is not None:
        raw = cli_val
    elif env_val:
        raw = env_val
    else:
        return DEFAULT_REQUEST_TIMEOUT_SEC
    try:
        val = float(raw)
    except (TypeError, ValueError):
        raise SystemExit("--request-timeout-sec / EDA_BENCH_LLM_REQUEST_TIMEOUT_SEC must be numeric, "
                         "got %r" % (raw,))
    if not math.isfinite(val) or val <= 0:
        raise SystemExit("--request-timeout-sec / EDA_BENCH_LLM_REQUEST_TIMEOUT_SEC must be a positive "
                         "finite number, got %r" % (raw,))
    return val


# HTTP statuses that are conventionally transient and safe to retry. 409 (Conflict) is
# NOT included -- it is usually deterministic rather than transient.
_RETRYABLE_HTTP = frozenset({408, 429, 500, 502, 503, 504})


def _classify_retryable(exc):
    """Return (category, retryable) for a provider/network exception. Type-and-status based;
    message-string matching is only a defensive fallback. Does not retry every OSError blindly."""
    # timeout (socket.timeout is an alias of TimeoutError on 3.10+)
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return "timeout", True
    # urllib wraps network errors in URLError(.reason)
    if isinstance(exc, urllib.error.URLError):
        reason = getattr(exc, "reason", None)
        if isinstance(reason, (socket.timeout, TimeoutError)):
            return "timeout", True
        if isinstance(reason, ConnectionError):  # ConnectionReset/Refused/Aborted/BrokenPipe
            return "connection", True
        return "other", False
    # bare connection-layer failures (not wrapped by urllib)
    if isinstance(exc, ConnectionError):
        return "connection", True
    # structured HTTP status from the provider
    if isinstance(exc, ProviderHTTPError):
        if exc.status_code in _RETRYABLE_HTTP:
            return "retryable_http", True
        return "non_retryable_http", False
    # streaming logical failures (no inner streaming retry loop; the single _retry_loop retries by
    # issuing a fresh process worker + fresh HTTP request). incomplete_stream = the stream ended
    # without a valid final answer (reasoning-only EOF, premature EOF, no finish/[DONE]);
    # malformed_stream = an SSE data line was not valid JSON. Both are bounded by max_chat_retries.
    if isinstance(exc, StreamIncomplete):
        return "incomplete_stream", True
    if isinstance(exc, StreamMalformed):
        return "malformed_stream", True
    # defensive message-string fallback (e.g. providers raising plain RuntimeErrors)
    m = str(exc).lower()
    if any(s in m for s in ("429", "overloaded", "timeout", "timed out", "502", "503", "504",
                            "temporarily")):
        return "other", True
    return "other", False


def _log_retry_attempt(attempt, elapsed, category, exc_class, status, next_delay, out=None):
    """Sanitized per-attempt diagnostic. Logs NO secrets: only attempt index, elapsed seconds,
    category, exception CLASS NAME (not the message -- it may carry a credential-bearing URL),
    HTTP status where applicable, and the planned next retry delay. ``out`` resolves to sys.stderr
    at call time so tests (capsys) can capture it."""
    if out is None:
        out = sys.stderr
    try:
        out.write("[llm_retry] attempt=%d elapsed=%.2fs category=%s exc=%s status=%s next_delay=%s\n"
                  % (attempt, elapsed, category, exc_class,
                     status if status is not None else "none",
                     "%.2fs" % next_delay if next_delay is not None else "none"))
        out.flush()
    except Exception:  # noqa: BLE001 -- logging must never break the episode
        pass


def _resolve_request_deadline(cli_val, env_val):
    """Resolve the HARD total-request wall-clock deadline (seconds). Precedence: CLI > env > default.
    Rejects zero/negative/non-numeric/non-finite with a clear error (before launch)."""
    if cli_val is not None:
        raw = cli_val
    elif env_val:
        raw = env_val
    else:
        return DEFAULT_REQUEST_DEADLINE_SEC
    try:
        val = float(raw)
    except (TypeError, ValueError):
        raise SystemExit("--request-deadline-sec / EDA_BENCH_LLM_REQUEST_DEADLINE_SEC must be numeric, "
                         "got %r" % (raw,))
    if not math.isfinite(val) or val <= 0:
        raise SystemExit("--request-deadline-sec / EDA_BENCH_LLM_REQUEST_DEADLINE_SEC must be a positive "
                         "finite number, got %r" % (raw,))
    return val


def _resolve_max_chat_retries(cli_val, env_val, default=4):
    """Resolve the max retry count (>= 0 integer). Precedence: CLI > env > default (4)."""
    if cli_val is not None:
        raw = cli_val
    elif env_val:
        raw = env_val
    else:
        return default
    try:
        val = int(raw)
    except (TypeError, ValueError):
        raise SystemExit("--max-chat-retries / EDA_BENCH_MAX_CHAT_RETRIES must be an integer, got %r" % (raw,))
    if val < 0:
        raise SystemExit("--max-chat-retries / EDA_BENCH_MAX_CHAT_RETRIES must be >= 0, got %r" % (raw,))
    return val


# Accepted opt-in values for the streaming flag (case-insensitive). Streaming is an EXPLICIT opt-in;
# the driver NEVER enables it from the model name.
_STREAM_TRUE = frozenset({"1", "true", "yes", "on"})
_STREAM_FALSE = frozenset({"0", "false", "no", "off"})


def _resolve_stream_flag(cli_val, env_val):
    """Resolve the SSE streaming opt-in (default False). Precedence: CLI > env > default.
    Accepts 1/true/yes/on (True) and 0/false/no/off (False), case-insensitive; any other value is
    rejected before launch with a clear error. Streaming is never auto-enabled from the model name."""
    if cli_val is not None:
        raw = cli_val
    elif env_val not in (None, ""):
        raw = env_val
    else:
        return False
    r = str(raw).strip().lower()
    if r in _STREAM_TRUE:
        return True
    if r in _STREAM_FALSE:
        return False
    raise SystemExit("--stream-responses / EDA_BENCH_STREAM_RESPONSES must be one of "
                     "1/true/yes/on or 0/false/no/off, got %r" % (raw,))


class _AttemptResult:
    """Uniform per-attempt outcome for the single retry authority. Carries EITHER a success response
    OR a structured error (category/retryable/status/original-exception-for-reraise). No secrets."""

    __slots__ = ("success", "resp", "category", "retryable", "status", "exc", "exc_class",
                 "termination", "worker_pid", "diag", "elapsed")

    def __init__(self, *, success=False, resp=None, category=None, retryable=False, status=None,
                 exc=None, exc_class=None, termination="normal_exit", worker_pid=None, diag=None,
                 elapsed=0.0):
        self.success = success
        self.resp = resp
        self.category = category
        self.retryable = retryable
        self.status = status
        self.exc = exc            # original exception (for in-process reraise); None for isolated
        self.exc_class = exc_class
        self.termination = termination
        self.worker_pid = worker_pid
        self.diag = diag or {}
        self.elapsed = elapsed


def _backoff_delay(attempt):
    return min(3.0 * (2 ** attempt), 45.0)


def _retry_loop(attempt_fn, retries, on_attempt):
    """THE single retry authority. attempt_fn() -> _AttemptResult per attempt (each a fresh request).
    on_attempt(attempt, result, elapsed, next_delay) logs. Returns (resp, n_retries) or raises."""
    for attempt in range(retries + 1):
        t0 = time.monotonic()
        res = attempt_fn()
        elapsed = time.monotonic() - t0
        last = attempt >= retries
        next_delay = None if (last or res.success or not res.retryable) else _backoff_delay(attempt)
        try:
            on_attempt(attempt, res, elapsed, next_delay)
        except Exception:  # noqa: BLE001 -- logging must never break the episode
            pass
        if res.success:
            return res.resp, attempt
        if last or not res.retryable:
            if res.exc is not None:
                raise res.exc
            raise RuntimeError("chat attempt failed: category=%s exc=%s status=%s"
                               % (res.category, res.exc_class, res.status))
        time.sleep(next_delay)
    raise RuntimeError("unreachable")


# ---------------- in-process attempt path (Phase-4U0 behavior; used by the in-process _chat_with_retry
# and its unit tests; the production driver uses the isolated path below)
def _attempt_in_process(provider, messages, gen_kwargs):
    try:
        resp = provider.chat(messages, **gen_kwargs)
        return _AttemptResult(success=True, resp=resp)
    except Exception as e:  # noqa: BLE001
        category, retryable = _classify_retryable(e)
        return _AttemptResult(category=category, retryable=retryable, status=getattr(e, "status_code", None),
                              exc=e, exc_class=type(e).__name__)


def _log_in_process(attempt, res, elapsed, next_delay, out=None):
    cat = "success" if res.success else (res.category or "other")
    _log_retry_attempt(attempt=attempt, elapsed=elapsed, category=cat,
                       exc_class=res.exc_class or "none", status=res.status, next_delay=next_delay, out=out)


def _chat_with_retry(provider, messages, gen_kwargs, retries=4):
    """In-process retry (Phase-4U0 path): each attempt calls provider.chat directly with the
    per-operation urlopen timeout. Kept for compatibility and unit tests; the production driver uses
    _chat_with_retry_deadline (process-isolated hard deadline). _retry_loop is the single authority."""
    return _retry_loop(lambda: _attempt_in_process(provider, messages, gen_kwargs), retries, _log_in_process)


# ---------------- process-isolated attempt path with a HARD wall-clock deadline
def _classify_worker_error(error_class, status):
    """Classify a structured error reported by the isolated worker (by class name + HTTP status)."""
    if error_class == "ProviderHTTPError" and status is not None:
        return ("retryable_http" if status in _RETRYABLE_HTTP else "non_retryable_http",
                status in _RETRYABLE_HTTP)
    if error_class == "StreamIncomplete":
        return "incomplete_stream", True
    if error_class == "StreamMalformed":
        return "malformed_stream", True
    if error_class in ("TimeoutError", "socket.timeout"):
        return "socket_timeout", True
    if error_class in ("ConnectionResetError", "ConnectionAbortedError", "ConnectionRefusedError",
                       "BrokenPipeError", "ConnectionError"):
        return "connection", True
    if error_class == "URLError":
        return "connection", True
    if error_class == "MissingApiKey":
        return "non_retryable_http", False  # configuration error -- fail promptly
    return "other", False


def _safe_request_diagnostics(spec):
    """Non-secret request diagnostics (help compare a healthy ping vs a stalled full request without
    exposing content). Includes endpoint HOSTNAME (no credentials), message counts/lengths, max_tokens,
    and a SHA-256 of the canonical request spec."""
    msgs = spec.get("messages", []) or []
    sys_chars = len(msgs[0].get("content", "")) if msgs and msgs[0].get("role") == "system" else 0
    user_chars = sum(len(m.get("content", "")) for m in msgs if m.get("role") == "user")
    host = urlsplit(spec.get("api_base", "")).hostname or ""
    body = json.dumps(spec, sort_keys=True).encode()
    return {"msg_count": len(msgs), "system_chars": sys_chars, "user_chars": user_chars,
            "max_tokens": spec.get("gen_kwargs", {}).get("max_tokens"),
            "body_bytes": len(body), "body_sha256": hashlib.sha256(body).hexdigest()[:12], "host": host}


def _terminate_and_reap(proc, grace=2.0):
    """Terminate the worker, then reap. Returns 'normal_exit' | 'terminate' | 'kill'.

    PLATFORM: on POSIX the worker is started with start_new_session=True (so proc.pid is its process-
    group leader); we kill the WHOLE group via os.killpg so no descendant can survive. On a non-POSIX
    platform os.killpg/os.getpgid do not exist -- we fall back to terminating the worker process
    directly (the dependency-free worker spawns no subprocess descendants of its own). This path is
    therefore guarded (hasattr check) rather than silently assuming killpg is present."""
    if hasattr(os, "killpg") and hasattr(os, "getpgid"):
        try:
            pgid = os.getpgid(proc.pid)
        except ProcessLookupError:
            return "normal_exit"
        sig_action = "terminate"
        try:
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            try:
                proc.terminate()
            except ProcessLookupError:
                pass
        try:
            proc.wait(timeout=grace)
            return sig_action
        except subprocess.TimeoutExpired:
            try:
                os.killpg(pgid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
            try:
                proc.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                pass  # best-effort; extremely unlikely after SIGKILL
            return "kill"
    # non-POSIX fallback: terminate the worker process directly (no process groups available)
    try:
        proc.terminate()
    except ProcessLookupError:
        return "normal_exit"
    try:
        proc.wait(timeout=grace)
        return "terminate"
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            pass
        return "kill"


def _log_isolated_attempt(attempt, res, elapsed, next_delay, op_timeout, deadline, out=None):
    """Sanitized per-attempt log for the isolated path. NO key/Authorization/prompt/body content.
    Includes the safe diagnostics + termination action + deadlines."""
    out = sys.stderr if out is None else out
    cat = "success" if res.success else (res.category or "other")
    d = res.diag or {}
    line = (
        "[llm_deadline] attempt=%d pid=%s elapsed=%.2fs op_timeout=%s deadline=%s category=%s "
        "termination=%s status=%s msg_count=%s body_bytes=%s max_tokens=%s host=%s sha=%s next_delay=%s\n"
        % (attempt, res.worker_pid if res.worker_pid is not None else "none", elapsed,
           op_timeout, deadline, cat, res.termination,
           res.status if res.status is not None else "none",
           d.get("msg_count", "none"), d.get("body_bytes", "none"), d.get("max_tokens", "none"),
           d.get("host", "none"), d.get("body_sha256", "none"),
           "%.2fs" % next_delay if next_delay is not None else "none"))
    try:
        out.write(line)
        out.flush()
    except Exception:  # noqa: BLE001
        pass


def _attempt_isolated(provider, messages, gen_kwargs, request_deadline, op_timeout):
    """Run ONE provider.chat in a separate child process, enforcing a HARD wall-clock deadline.
    The API key is NEVER in argv/stdin/logs (the child reads it from inherited env). Each call is a
    fresh worker + fresh urllib request."""
    spec = {"api_base": provider.api_base, "model": provider.model,
            "messages": messages, "gen_kwargs": {**gen_kwargs, "timeout": op_timeout}}
    stdin_payload = (json.dumps(spec) + "\n").encode()
    diag = _safe_request_diagnostics(spec)
    # start_new_session puts the worker in its own POSIX session/process group so _terminate_and_reap
    # can kill the whole group. It is a POSIX-only option; on non-POSIX we omit it (the worker has no
    # subprocess descendants, so direct terminate/kill suffices there).
    proc = subprocess.Popen([sys.executable, str(_REQUEST_WORKER)], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=(os.name == "posix"), close_fds=True)
    pid = proc.pid
    t0 = time.monotonic()
    try:
        out, _err = proc.communicate(stdin_payload, timeout=request_deadline)
    except subprocess.TimeoutExpired:
        term = _terminate_and_reap(proc)
        return _AttemptResult(category="hard_request_deadline", retryable=True, status=None,
                              termination=term, worker_pid=pid, diag=diag,
                              elapsed=time.monotonic() - t0)
    # worker exited within the deadline -> parse its structured stdout
    elapsed = time.monotonic() - t0
    term = "normal_exit"
    try:
        obj = json.loads(out.decode("utf-8", errors="replace"))
    except Exception:  # noqa: BLE001 -- no/invalid JSON -> crash or malformed
        cat = "worker_crash" if proc.returncode != 0 else "malformed_worker_result"
        return _AttemptResult(category=cat, retryable=True, status=None, termination=term,
                              worker_pid=pid, diag=diag, elapsed=elapsed)
    if obj.get("ok"):
        resp = LLMResponse(text=obj.get("text", ""), model=obj.get("model", provider.model),
                           usage=obj.get("usage", {}), metadata=obj.get("metadata", {}))
        return _AttemptResult(success=True, resp=resp, termination=term, worker_pid=pid, diag=diag,
                              elapsed=elapsed)
    error_class = obj.get("error_class") or "Unknown"
    status = obj.get("status_code")
    category, retryable = _classify_worker_error(error_class, status)
    return _AttemptResult(category=category, retryable=retryable, status=status,
                          exc_class=error_class, termination=term, worker_pid=pid, diag=diag,
                          elapsed=elapsed)


def _chat_with_retry_deadline(provider, messages, gen_kwargs, request_deadline, op_timeout, retries):
    """Production retry path: each attempt runs in a fresh isolated worker killed at the HARD deadline.
    _retry_loop is the single retry authority; on_attempt logs the isolated-format diagnostics."""
    def on_attempt(attempt, res, elapsed, next_delay):
        _log_isolated_attempt(attempt, res, elapsed, next_delay, op_timeout, request_deadline)
    return _retry_loop(
        lambda: _attempt_isolated(provider, messages, gen_kwargs, request_deadline, op_timeout),
        retries, on_attempt)


def parse_action(text: str):
    """Return ('run', cmd) | ('write', name, content) | ('finish', None) | ('none', None).

    Takes the FIRST recognized action marker (models often explain, then act)."""
    m = _ACTION_RE.search(text)
    if not m:
        return ("none", None)
    verb = m.group(1).upper()
    rest = m.group(2).strip()
    if verb == "FINISH":
        return ("finish", None)
    if verb == "RUN":
        cmd = rest
        if not cmd:  # command may be in a following fenced block
            fb = _FENCE_RE.search(text[m.end():])
            cmd = fb.group(1).strip() if fb else ""
        return ("run", cmd)
    # WRITE: <name> then a fenced block with the file body
    name = rest.split()[0] if rest else ""
    fb = _FENCE_RE.search(text[m.end():])
    content = fb.group(1) if fb else ""
    return ("write", name, content)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="LLM ReAct agent driver (agent_cmd).")
    ap.add_argument("--model", required=True)
    ap.add_argument("--models", required=True, help="baseline_models.json")
    ap.add_argument("--max-actions", type=int, default=12)
    ap.add_argument("--max-obs-bytes", type=int, default=4000)
    ap.add_argument("--elicit-confidence", action="store_true",
                    help="Ask the agent to declare CONFIDENCE on FINISH; parse + log it "
                         "(reliability/calibration layer). Off by default — capability runs unchanged.")
    ap.add_argument("--temperature", type=float, default=None,
                    help="Override the model's configured sampling temperature. Use temperature>0 "
                         "for reliability k-trials so identical inputs yield run-to-run variance.")
    ap.add_argument("--log", default=None, help="sidecar transcript+usage JSON")
    ap.add_argument("--request-timeout-sec", default=None,
                    help="Per-request blocking-socket timeout (seconds) for one model HTTP call. "
                         "Precedence: this flag > EDA_BENCH_LLM_REQUEST_TIMEOUT_SEC > default 300. "
                         "Per-operation inactivity; NOT the whole-episode wall (EDA_TIMEOUT) and NOT "
                         "the hard total deadline (--request-deadline-sec). Must be positive+finite.")
    ap.add_argument("--request-deadline-sec", default=None,
                    help="HARD total wall-clock deadline (seconds) for one model HTTP call, enforced "
                         "by killing an isolated request worker. INDEPENDENT of socket activity (covers "
                         "slow-drip stalls the per-operation timeout cannot interrupt). Precedence: "
                         "this flag > EDA_BENCH_LLM_REQUEST_DEADLINE_SEC > default 300. Must be >= the "
                         "operation timeout, positive, and finite.")
    ap.add_argument("--max-chat-retries", default=None,
                    help="Max retried chat attempts after the first (>= 0). Precedence: this flag > "
                         "EDA_BENCH_MAX_CHAT_RETRIES > default 4. Phase-4U uses 1 (one initial + one retry).")
    ap.add_argument("--stream-responses", nargs="?", const="1", default=None,
                    help="Enable dependency-free SSE streaming for model responses (opt-in). With no "
                         "value or a true value (1/true/yes/on) streaming is enabled; a false value "
                         "(0/false/no/off) disables it. Precedence: this flag > "
                         "EDA_BENCH_STREAM_RESPONSES > default off. Streaming receives incremental "
                         "tokens during long reasoning so a long-thinking response is not censored by "
                         "the per-operation socket timeout. Never auto-enabled from the model name.")
    args = ap.parse_args(argv)

    # Resolve the per-request timeout (CLI > env > default); fail fast on bad values.
    request_timeout = _resolve_request_timeout(
        args.request_timeout_sec, os.environ.get("EDA_BENCH_LLM_REQUEST_TIMEOUT_SEC"))
    # Resolve the HARD total-request deadline (CLI > env > default); fail fast on bad values.
    request_deadline = _resolve_request_deadline(
        args.request_deadline_sec, os.environ.get("EDA_BENCH_LLM_REQUEST_DEADLINE_SEC"))
    if request_deadline < request_timeout:
        raise SystemExit("--request-deadline-sec (%.1f) must be >= --request-timeout-sec (%.1f)"
                         % (request_deadline, request_timeout))
    max_chat_retries = _resolve_max_chat_retries(
        args.max_chat_retries, os.environ.get("EDA_BENCH_MAX_CHAT_RETRIES"))
    # SSE streaming opt-in (CLI > env > default False). When enabled, gen_kwargs["stream"]=True is
    # threaded through the isolated worker into provider.chat, which adds "stream":true +
    # stream_options.include_usage to the request body and reads the SSE body incrementally.
    stream = _resolve_stream_flag(args.stream_responses, os.environ.get("EDA_BENCH_STREAM_RESPONSES"))

    workspace = Path(os.environ["EDA_WORKSPACE"]).resolve()
    task_path = Path(os.environ["EDA_TASK_PATH"])          # used HERE only, never shown
    deadline = time.time() + int(os.environ.get("EDA_TIMEOUT", "900")) - 30

    # Read ONLY prompt.md + metadata.json from the task dir (never hidden/solution).
    meta = json.loads((task_path / "metadata.json").read_text())
    prompt_md = (task_path / "prompt.md").read_text() if (task_path / "prompt.md").is_file() else ""
    editable = list(meta["files"].get("editable", []))
    visible = list(meta["files"].get("visible", []))
    editable_names = {Path(e).name for e in editable}

    provider, gen_kwargs = _provider_for(args.model, Path(args.models))
    # Per-call cap is fine for ReAct turns; the loop provides the iteration.
    gen_kwargs = dict(gen_kwargs)
    gen_kwargs.setdefault("max_tokens", 4096)
    if args.temperature is not None:
        gen_kwargs["temperature"] = args.temperature
    # per-request blocking-socket timeout, threaded into provider.chat -> urlopen(timeout=...).
    # NOT a process-global socket.setdefaulttimeout; scoped to this provider call only.
    gen_kwargs["timeout"] = request_timeout
    if stream:
        # opt-in SSE streaming; threaded through the isolated worker into provider.chat.
        gen_kwargs["stream"] = True

    system = (
        "You are an expert IC design engineer fixing a bug in a sandboxed workspace, "
        "using a commercial EDA flow. Work iteratively, like a real engineer.\n\n"
        f"# TASK\n{prompt_md}\n\n"
        f"# WORKSPACE\nVisible files: {', '.join(visible)}\n"
        f"Editable files (only these may be changed): {', '.join(editable)}\n\n"
        "# HOW TO ACT\n"
        "Each message, reply with EXACTLY ONE action and nothing else:\n"
        "  RUN: <shell command>\n"
        "      Run a command in the workspace and see its output. Use this to read files "
        "(e.g. `cat design.v`) and to run the provided test script to get real tool "
        "feedback (e.g. `bash run_public.sh`).\n"
        "  WRITE: <filename>\n"
        "  ```\n  <full new file content>\n  ```\n"
        "      Replace an editable file with the given full content.\n"
        "  FINISH\n"
        "      Stop — you are confident the fix is correct.\n"
        + (_CONF_FINISH if args.elicit_confidence else "")
        + "\n"
        "# ENVIRONMENT\n"
        "- The commercial EDA tools are already installed and on PATH. Just run the "
        "provided script (e.g. `bash run_public.sh`) directly; do NOT search for tool "
        "binaries or export PATH — that only wastes actions.\n"
        "- WRITE only accepts the editable file(s) listed above. For scratch math, use "
        "RUN with python (e.g. `python3 -c \"...\"`); writing any other filename is refused.\n"
        "- Spend your limited actions on design iterations (run the script, read the "
        "measured numbers, change the editable file, re-run), not on exploring the setup.\n\n"
        f"You have at most {args.max_actions} actions. The final hidden acceptance test is "
        "NOT shown to you and there is no answer key — reason about correctness yourself, "
        "the way an engineer does before signoff. Do not attempt to read hidden tests, "
        "solutions, or anything outside the workspace."
    )
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": "Begin. What is your first action?"}]

    # RUN subprocesses inherit our env MINUS the task-path pointers (oracle isolation),
    # but KEEP PATH + the EDA tool shim vars so `bash run_public.sh` reaches the tools.
    run_env = {k: v for k, v in os.environ.items() if k not in ("EDA_TASK_PATH", "EDA_TASK_ID")}

    log: dict = {"model": args.model, "task_id": meta["task_id"], "track": meta["track"],
                 "actions": [], "usage": {"prompt_tokens": 0, "completion_tokens": 0,
                                          "reasoning_tokens": 0}, "finished": False,
                 "edited": [], "error": None, "confidence": "", "confidence_format_ok": None,
                 "retries": 0}

    try:
        for step in range(args.max_actions):
            if time.time() > deadline:
                log["actions"].append({"type": "deadline"})
                break
            resp, n_retry = _chat_with_retry_deadline(provider, messages, gen_kwargs,
                                                      request_deadline, request_timeout, max_chat_retries)
            log["retries"] += n_retry
            for k in log["usage"]:
                log["usage"][k] += (resp.usage or {}).get(k, 0)
            reply = resp.text or ""
            messages.append({"role": "assistant", "content": reply})

            kind, *payload = parse_action(reply)
            if kind == "finish":
                if args.elicit_confidence:
                    log["confidence"], log["confidence_format_ok"] = parse_confidence(reply)
                log["actions"].append({"type": "finish"})
                log["finished"] = True
                break
            if kind == "none":
                obs = ("No action recognized. Reply with exactly one of RUN: <cmd>, "
                       "WRITE: <file> (+ ``` block), or FINISH.")
                log["actions"].append({"type": "none"})
            elif kind == "run":
                cmd = payload[0]
                if not cmd or _DENY.search(cmd):
                    obs = "Refused: command is empty or not allowed (do not read outside the workspace)."
                    log["actions"].append({"type": "run_refused", "cmd": cmd})
                else:
                    rc = None
                    try:
                        r = subprocess.run(cmd, shell=True, cwd=workspace, env=run_env,
                                           capture_output=True, text=True,
                                           timeout=min(180, max(10, int(deadline - time.time()))))
                        out = (r.stdout or "") + (("\n[stderr]\n" + r.stderr) if r.stderr else "")
                        rc = r.returncode
                    except subprocess.TimeoutExpired:
                        out = "[command timed out]"
                    if len(out) > args.max_obs_bytes:
                        out = out[: args.max_obs_bytes] + "\n...[truncated]"
                    obs = f"$ {cmd}\n{out}"
                    # Record rc + a truncated tail of the output. The model SEES `out`;
                    # without storing it the transcript is undiagnosable post-hoc (we
                    # could not tell WHY episodes failed in the 30-task damping run).
                    log["actions"].append({"type": "run", "cmd": cmd, "rc": rc,
                                           "out": out[:1500]})
            else:  # write
                name, content = payload[0], payload[1]
                base = Path(name).name
                if base not in editable_names:
                    obs = f"Refused: {name!r} is not editable. Editable: {sorted(editable_names)}"
                    log["actions"].append({"type": "write_refused", "file": name})
                else:
                    # Write to the editable file's ACTUAL seeded location. The runner's
                    # create_agent_workspace flattens the task's visible/ (P5) or files/
                    # (other tracks) dir INTO the workspace root, so an editable listed as
                    # "visible/foo.sp" actually lives at "foo.sp", while other tracks keep
                    # their relpath. The grader reads that same seeded path, so writing to
                    # the editable relpath blindly (e.g. creating a fresh visible/foo.sp)
                    # would land the fix where the grader never looks -> every edit silently
                    # discarded. Pick the path that was actually seeded.
                    rel = next(e for e in editable if Path(e).name == base)
                    if (workspace / rel).exists():
                        target = rel
                    elif (workspace / base).exists():
                        target = base
                    else:
                        target = rel  # not seeded (agent creating a new file): use relpath
                    dest = workspace / target
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if not content.endswith("\n"):
                        content += "\n"
                    dest.write_text(content)
                    if target not in log["edited"]:
                        log["edited"].append(target)
                    obs = f"Wrote {len(content)} bytes to {target}."
                    log["actions"].append({"type": "write", "file": target, "bytes": len(content)})

            messages.append({"role": "user", "content": obs})
    except Exception as e:  # noqa: BLE001 — record, let runner grade whatever edits exist
        log["error"] = f"{type(e).__name__}: {e}"

    # Brief stdout summary (captured by the runner into stdout.log).
    print(f"[agent {args.model}] {meta['task_id']}: {len(log['actions'])} actions, "
          f"edited={log['edited']}, finished={log['finished']}, "
          f"tok in/out={log['usage']['prompt_tokens']}/{log['usage']['completion_tokens']}"
          + (f", error={log['error']}" if log["error"] else ""))
    if args.log:
        Path(args.log).parent.mkdir(parents=True, exist_ok=True)
        Path(args.log).write_text(json.dumps(log, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
