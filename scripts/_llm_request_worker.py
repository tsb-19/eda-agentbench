#!/usr/bin/env python3
"""Process-isolated LLM request worker (Phase-4U0b).

Runs ONE provider.chat() call in a separate child process so the parent driver can enforce a HARD
total wall-clock deadline by killing the whole process (a per-operation urllib/socket timeout does
NOT interrupt a peer that slow-drips bytes within each operation window). Dependency-free (stdlib +
the repo's urllib provider); no httpx.

SECRET SAFETY: the API key is NEVER passed via argv, stdin, or logs. The child resolves it from the
INHERITED environment (API_KEY / MIMO_API_KEY / OPENAI_API_KEY / LLM_API_KEY), exactly as the parent
process already has it after _load_dotenv. The stdin payload carries only NON-secret data: the
endpoint URL (no credentials), the model id, the messages, and gen_kwargs.

PROTOCOL (one JSON object on stdin, one JSON object on stdout):
  stdin  -> {"api_base": <url>, "model": <id>, "messages": [...], "gen_kwargs": {...}}
  stdout -> {"ok": true,  "text": ..., "model": ..., "usage": {...}, "metadata": {...}}
         |  {"ok": false, "error_class": ..., "status_code": <int|None>, "message_len": <int>}
The stdout result NEVER includes the API key, the Authorization header, the raw request body, or the
full error message text (only its length, so the parent can log diagnostics without leaking content).
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from eda_agentbench.llm.openai_provider import OpenAIProvider, ProviderHTTPError  # noqa: E402

# candidate env vars holding the API key, in priority order (matches create_provider convention +
# the gateway's API_KEY). The child reads whichever is set in its INHERITED environment.
_KEY_ENV_CANDIDATES = ("API_KEY", "MIMO_API_KEY", "OPENAI_API_KEY", "LLM_API_KEY")


def _resolve_api_key() -> str:
    # the parent already ran _load_dotenv; the child inherits os.environ. Re-run defensively so a
    # directly-invoked worker still works, but never print the key or the full environment.
    try:
        from eda_agentbench.llm.openai_provider import _load_dotenv
        _load_dotenv()
    except Exception:  # noqa: BLE001
        pass
    for env_var in _KEY_ENV_CANDIDATES:
        val = os.environ.get(env_var, "")
        if val:
            return val
    return ""


def _emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj))
    sys.stdout.flush()


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        api_base = payload["api_base"]
        model = payload["model"]
        messages = payload["messages"]
        gen_kwargs = payload.get("gen_kwargs", {}) or {}
    except Exception as e:  # noqa: BLE001 -- malformed IPC input
        _emit({"ok": False, "error_class": "WorkerInputError",
               "status_code": None, "message_len": len(str(e))})
        return 0

    api_key = _resolve_api_key()
    if not api_key:
        _emit({"ok": False, "error_class": "MissingApiKey", "status_code": None, "message_len": 0})
        return 0

    provider = OpenAIProvider(api_key=api_key, api_base=api_base, model=model)
    try:
        resp = provider.chat(messages, **gen_kwargs)
    except Exception as e:  # noqa: BLE001 -- structured, sanitized error (no key / no full message)
        _emit({
            "ok": False,
            "error_class": type(e).__name__,
            "status_code": getattr(e, "status_code", None),
            "message_len": len(str(e)),
        })
        return 0

    # success -- mirror exactly the fields the driver consumes (resp.text / resp.usage). Never echo
    # the key, the Authorization header, or the request payload.
    _emit({
        "ok": True,
        "text": resp.text or "",
        "model": resp.model or model,
        "usage": dict(resp.usage or {}),
        "metadata": dict(resp.metadata or {}),
    })
    return 0


if __name__ == "__main__":
    # never let an uncaught exception escape without a structured result line
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as e:  # noqa: BLE001 -- last-resort structured crash report
        try:
            _emit({"ok": False, "error_class": "WorkerCrash:%s" % type(e).__name__,
                   "status_code": None, "message_len": len(str(e))})
        except Exception:  # noqa: BLE001
            pass
        traceback.print_exc(file=sys.stderr)
        raise SystemExit(1)
