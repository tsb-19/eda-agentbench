"""Optional OpenAI-compatible LLM provider.

Priority: MIMO_API_KEY > OPENAI_API_KEY > LLM_API_KEY
Loads from .env if not already in environment.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from eda_agentbench.llm.base import BaseLLMProvider, LLMResponse


# ---------------------------------------------------------------------------
# Structured provider errors (dependency-free; used for type-aware retry
# classification by callers' retry loops). These MUST stay RuntimeError-derived
# with an "HTTP <code>" message prefix so existing message-string retry
# classifiers (e.g. the retry predicate in scripts/llm_agent_driver.py) keep
# working unchanged. Network-layer exceptions (urllib.error.URLError,
# socket.timeout/TimeoutError, ConnectionError) are NOT wrapped -- callers
# classify them by type.
# ---------------------------------------------------------------------------
class ProviderError(RuntimeError):
    """Base class for provider HTTP failures."""


class ProviderHTTPError(ProviderError):
    """A non-2xx HTTP response from the API. Carries ``status_code`` so callers
    can classify retryability by status rather than by parsing the message."""

    def __init__(self, status_code: int, detail: str = "", api_base: str = ""):
        self.status_code = int(status_code)
        # keep the "HTTP <code> from <base>: <detail>" shape for back-compat
        super().__init__("HTTP %d from %s: %s" % (self.status_code, api_base, detail))


class StreamIncomplete(RuntimeError):
    """A streaming response ended WITHOUT a valid final answer (no SSE JSON chunk at all, a
    reasoning-only EOF, a usage-only EOF, or a partial answer with no finish_reason/[DONE]).

    Retryable. ``text`` is deliberately NOT exposed -- reasoning content must never be returned to
    the caller as the model answer. Carries no secrets (counts only in the message)."""


class StreamMalformed(RuntimeError):
    """A streaming SSE ``data:`` line could not be parsed as JSON. Retryable (a transient stream-layer
    glitch); bounded by the caller's single retry authority. Carries no secrets."""


# Default per-request timeout (seconds) for a single blocking socket operation in
# urlopen. Callers SHOULD pass an explicit ``timeout`` kwarg (the agentic driver
# resolves it from --request-timeout-sec / EDA_BENCH_LLM_REQUEST_TIMEOUT_SEC).
# NOTE: this is a per-blocking-operation urllib/socket timeout, NOT a guaranteed
# strict total-request wall-clock deadline.
DEFAULT_REQUEST_TIMEOUT_SEC = 300.0

# Default HARD total-request wall-clock deadline (seconds) the agentic driver enforces by killing the
# isolated request worker. This is INDEPENDENT of socket activity (covers slow-drip stalls that evade
# the per-operation timeout above). Resolved from --request-deadline-sec / EDA_BENCH_LLM_REQUEST_DEADLINE_SEC.
DEFAULT_REQUEST_DEADLINE_SEC = 300.0


def _load_dotenv() -> None:
    """Load .env file into environment if not already set."""
    for candidate in [Path(".env"), Path.home() / ".env"]:
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = value


# Provider configs: (env_key, default_api_base, default_model)
_PROVIDER_CONFIGS = [
    ("MIMO_API_KEY", "https://token-plan-sgp.xiaomimimo.com/v1", "mimo-v2.5-pro"),
    ("OPENAI_API_KEY", "https://api.openai.com/v1", "gpt-4o-mini"),
    ("LLM_API_KEY", "https://api.openai.com/v1", "gpt-4o-mini"),
]


def create_provider() -> BaseLLMProvider:
    """Create the best available LLM provider.

    Priority: MIMO > OPENAI > LLM. Falls back to MockLLMProvider.
    """
    _load_dotenv()

    for env_key, default_base, default_model in _PROVIDER_CONFIGS:
        api_key = os.environ.get(env_key, "")
        if api_key:
            api_base = os.environ.get("LLM_API_BASE", default_base).rstrip("/")
            model = os.environ.get("LLM_MODEL", default_model)
            return OpenAIProvider(api_key=api_key, api_base=api_base, model=model)

    from eda_agentbench.llm.mock import MockLLMProvider
    return MockLLMProvider()


class OpenAIProvider(BaseLLMProvider):
    """OpenAI-compatible API provider."""

    def __init__(self, api_key: str, api_base: str = "", model: str = ""):
        self._api_key = api_key
        self._api_base = (api_base or "https://api.openai.com/v1").rstrip("/")
        self._model = model or "gpt-4o-mini"

    @property
    def name(self) -> str:
        return "mimo" if "mimo" in self._api_base.lower() or "mimo" in self._model.lower() else "openai"

    @property
    def model(self) -> str:
        return self._model

    @property
    def api_base(self) -> str:
        # read-only endpoint URL (no credentials) -- used to hand the non-secret endpoint to a
        # process-isolated request worker without passing the API key.
        return self._api_base

    def generate(self, prompt: str, system: str = "", **kwargs: Any) -> LLMResponse:
        """Generate text via OpenAI-compatible API.

        Recognized kwargs: temperature, max_tokens, timeout, and ``extra_body``
        (a dict merged into the request body — used to enable provider-specific
        reasoning/thinking modes). If the API returns a separate
        ``reasoning_content`` it is preserved in ``metadata`` but the answer
        ``content`` is what's returned as ``text``.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, **kwargs)

    def chat(self, messages: list[dict], **kwargs: Any) -> LLMResponse:
        """Multi-turn variant of :meth:`generate`: takes a full OpenAI-style
        ``messages`` list ([{role, content}, ...]) instead of a single
        prompt+system, so callers can preserve assistant/user turn structure
        across iterations (the agentic ReAct loop needs this). Same recognized
        kwargs and same ``LLMResponse`` contract as :meth:`generate`.
        """
        if not self._api_key:
            raise RuntimeError("No API key set. Use MockLLMProvider for testing.")

        # Streaming is an EXPLICIT opt-in (default False). The provider NEVER enables streaming from
        # the model name. When on, the request carries "stream": true + stream_options.include_usage,
        # and _chat_stream reads the SSE body incrementally so a long-thinking response is observed
        # token-by-token (defeating the per-operation socket-inactivity timeout). On a stream-
        # unsupported 4xx the provider RAISES ProviderHTTPError -- it does NOT silently fall back to
        # the non-streaming path.
        stream = bool(kwargs.get("stream", False))

        body = {
            "model": self._model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2000),
        }
        extra_body = kwargs.get("extra_body") or {}
        if isinstance(extra_body, dict):
            body.update(extra_body)
        if stream:
            body["stream"] = True
            body["stream_options"] = {"include_usage": True}

        req = Request(
            f"{self._api_base}/chat/completions",
            data=json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )

        # per-blocking-operation timeout (connect/read/write each bounded). NOT a strict
        # total-request deadline. Callers' retry loop (_chat_with_retry) is the sole retry
        # authority; this provider performs exactly ONE urlopen attempt per chat() call.
        timeout = kwargs.get("timeout", DEFAULT_REQUEST_TIMEOUT_SEC)
        if stream:
            return self._chat_stream(req, timeout)
        try:
            with urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
        except HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:500]
            # structured error carrying status_code for type-aware retry classification;
            # network-layer exceptions (URLError/socket.timeout/ConnectionError) propagate raw.
            raise ProviderHTTPError(e.code, detail, self._api_base) from e

        choice = data["choices"][0]
        msg = choice.get("message", {})
        text = msg.get("content") or ""
        usage = data.get("usage", {})

        return LLMResponse(
            text=text,
            model=data.get("model", self._model),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "reasoning_tokens": (usage.get("completion_tokens_details", {}) or {}).get("reasoning_tokens", 0),
            },
            metadata={
                "api_base": self._api_base,
                "finish_reason": choice.get("finish_reason"),
                "reasoning_content": msg.get("reasoning_content") or "",
            },
        )

    # ------------------------------------------------------------------ streaming (SSE)
    def _chat_stream(self, req: Request, timeout: float) -> LLMResponse:
        """Dependency-free OpenAI-compatible SSE streaming read.

        Reads the HTTP body line-by-line. ``timeout`` is a per-blocking-operation INACTIVITY (read)
        timeout: each underlying socket ``recv()`` within a ``readline`` must make progress within
        ``timeout``, so periodic SSE chunks reset that inactivity window and a live stream does not
        trip it -- while a silent connection still raises ``socket.timeout``. ``timeout`` is NOT a
        strict bound on any single ``readline`` (a line assembled from several recvs can take longer
        in total), and NOT a total-request bound; the STRICT total-duration bound is the caller's hard
        process deadline, which also covers an endless slow-drip (this method does not sleep or bound
        total wall-clock; that is the driver/worker's job).

        Reasoning vs answer are accumulated in SEPARATE buffers; only the assembled ANSWER content is
        returned as ``LLMResponse.text``. Raw reasoning is kept solely in ``metadata`` (callers / the
        worker strip it before any IPC or artifact). Network-layer errors (``socket.timeout`` /
        ``URLError`` / ``ConnectionError``) propagate RAW so callers classify them by type; HTTP 4xx/5xx
        -> ``ProviderHTTPError(status_code)`` (no silent non-streaming fallback); logical stream
        failures -> ``StreamIncomplete`` (no valid final answer) / ``StreamMalformed`` (bad SSE JSON).

        Completion rules (see Phase-4V0 spec sec.5): success requires (a) >=1 valid SSE JSON chunk,
        (b) non-empty answer content, and (c) at least one of ``finish_reason`` or ``[DONE]``. A
        reasoning-only EOF, a usage-only EOF, a partial answer with no completion indicator, or no
        chunks at all -> ``StreamIncomplete``. A close after ``finish_reason`` + non-empty answer but
        before ``[DONE]`` is ACCEPTED as complete (``done_seen=False`` recorded).
        """
        try:
            resp = urlopen(req, timeout=timeout)
        except HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:500]
            raise ProviderHTTPError(e.code, detail, self._api_base) from e
        # urlopen() network errors (URLError / socket.timeout / ConnectionError) propagate raw here;
        # ``resp`` is undefined on that path so the try/finally below is not entered.

        reasoning_parts: list[str] = []
        answer_parts: list[str] = []
        finish_reason = None
        seen_done = False
        got_chunk = False
        usage: dict[str, Any] = {}
        model_id = self._model
        chunk_count = 0
        reasoning_chunks = 0
        t0 = time.monotonic()
        ttfc = None  # time to first valid SSE JSON chunk
        ttfa = None  # time to first ANSWER-content chunk
        try:
            while True:
                raw = resp.readline()
                if not raw:
                    break  # EOF (server closed the stream)
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if not line or line.startswith(":"):
                    continue  # blank separator or SSE comment/keepalive line -> ignore
                if not line.startswith("data:"):
                    continue  # ignore other SSE fields (event: / id: / retry:)
                payload = line[len("data:"):].lstrip()
                if payload == "[DONE]":
                    seen_done = True
                    break
                chunk_count += 1
                try:
                    obj = json.loads(payload)
                except (json.JSONDecodeError, ValueError) as e:
                    raise StreamMalformed("SSE chunk %d is not valid JSON: %s" % (chunk_count, e)) from e
                got_chunk = True
                if ttfc is None:
                    ttfc = time.monotonic() - t0
                m = obj.get("model")
                if m:
                    model_id = m
                u = obj.get("usage")
                if isinstance(u, dict) and u:
                    usage = u  # the include_usage final chunk (may arrive with empty choices)
                choices = obj.get("choices") or []
                if choices and isinstance(choices[0], dict):
                    delta = choices[0].get("delta") or {}
                    rc = delta.get("reasoning_content")
                    if rc:
                        reasoning_parts.append(rc)
                        reasoning_chunks += 1
                    cc = delta.get("content")
                    if cc:
                        answer_parts.append(cc)
                        if ttfa is None:
                            ttfa = time.monotonic() - t0
                    fr = choices[0].get("finish_reason")
                    if fr:
                        finish_reason = fr
        finally:
            try:
                resp.close()
            except Exception:  # noqa: BLE001 -- cleanup must never mask the real outcome
                pass

        answer = "".join(answer_parts)
        reasoning = "".join(reasoning_parts)
        total_duration = time.monotonic() - t0

        if not got_chunk:
            raise StreamIncomplete("stream ended before any valid SSE JSON chunk arrived")
        if not answer:
            # reasoning-only EOF or usage-only EOF -> reasoning MUST NOT be returned as the answer
            raise StreamIncomplete("stream ended with no answer content (reasoning-only or usage-only)")
        if finish_reason is None and not seen_done:
            raise StreamIncomplete("stream ended with partial answer and no finish_reason/[DONE]")

        ctd = usage.get("completion_tokens_details") or {}
        reasoning_tokens = ctd.get("reasoning_tokens", 0) if isinstance(ctd, dict) else 0
        return LLMResponse(
            text=answer,
            model=model_id,
            # usage shape is INTENTIONALLY identical to the non-streaming path (prompt/completion/
            # reasoning_tokens) so streaming and non-streaming result objects stay compatible.
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "reasoning_tokens": reasoning_tokens or 0,
            },
            metadata={
                "api_base": self._api_base,
                "finish_reason": finish_reason,
                # raw reasoning kept ONLY in metadata; the worker strips it before IPC/artifact.
                "reasoning_content": reasoning,
                "stream": {
                    "chunk_count": chunk_count,
                    "reasoning_chunk_count": reasoning_chunks,
                    "reasoning_chars": len(reasoning),
                    "reasoning_sha256": hashlib.sha256(
                        reasoning.encode("utf-8", "ignore")).hexdigest()[:12],
                    "answer_chars": len(answer),
                    "done_seen": seen_done,
                    "time_to_first_chunk_s": round(ttfc, 4) if ttfc is not None else None,
                    "time_to_first_answer_s": round(ttfa, 4) if ttfa is not None else None,
                    "total_duration_s": round(total_duration, 4),
                },
            },
        )

