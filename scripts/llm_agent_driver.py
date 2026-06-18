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
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.generate_model_submissions import load_model_specs  # noqa: E402

# Commands that look like attempts to escape the workspace / read the oracle.
_DENY = re.compile(r"(EDA_TASK_PATH|/hidden\b|/solution\b|/oracle\b|run_hidden|\.\./)", re.I)
_ACTION_RE = re.compile(r"^\s*(RUN|WRITE|FINISH)\b[:\s]?(.*)$", re.I | re.M)
_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.S)


def _provider_for(model_name: str, models_cfg: Path):
    for name, provider, gen_kwargs in load_model_specs(models_cfg, allow_mock=False):
        if name == model_name:
            return provider, gen_kwargs
    raise SystemExit(f"model {model_name!r} not found in {models_cfg}")


def _chat_with_retry(provider, messages, gen_kwargs, retries=4):
    delay = 3.0
    for attempt in range(retries + 1):
        try:
            return provider.chat(messages, **gen_kwargs)
        except Exception as e:  # noqa: BLE001
            m = str(e).lower()
            transient = any(s in m for s in ("429", "http 5", "overloaded", "timeout",
                                             "timed out", "temporarily", "502", "503"))
            if attempt >= retries or not transient:
                raise
            time.sleep(min(delay * (2 ** attempt), 45.0))
    raise RuntimeError("unreachable")


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
    ap.add_argument("--log", default=None, help="sidecar transcript+usage JSON")
    args = ap.parse_args(argv)

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
        "      Stop — you are confident the fix is correct.\n\n"
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
                 "edited": [], "error": None}

    try:
        for step in range(args.max_actions):
            if time.time() > deadline:
                log["actions"].append({"type": "deadline"})
                break
            resp = _chat_with_retry(provider, messages, gen_kwargs)
            for k in log["usage"]:
                log["usage"][k] += (resp.usage or {}).get(k, 0)
            reply = resp.text or ""
            messages.append({"role": "assistant", "content": reply})

            kind, *payload = parse_action(reply)
            if kind == "finish":
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
                    try:
                        r = subprocess.run(cmd, shell=True, cwd=workspace, env=run_env,
                                           capture_output=True, text=True,
                                           timeout=min(180, max(10, int(deadline - time.time()))))
                        out = (r.stdout or "") + (("\n[stderr]\n" + r.stderr) if r.stderr else "")
                    except subprocess.TimeoutExpired:
                        out = "[command timed out]"
                    if len(out) > args.max_obs_bytes:
                        out = out[: args.max_obs_bytes] + "\n...[truncated]"
                    obs = f"$ {cmd}\n{out}"
                    log["actions"].append({"type": "run", "cmd": cmd})
            else:  # write
                name, content = payload[0], payload[1]
                base = Path(name).name
                if base not in editable_names:
                    obs = f"Refused: {name!r} is not editable. Editable: {sorted(editable_names)}"
                    log["actions"].append({"type": "write_refused", "file": name})
                else:
                    # Map basename back to the editable relpath, write into the workspace.
                    rel = next(e for e in editable if Path(e).name == base)
                    dest = workspace / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if not content.endswith("\n"):
                        content += "\n"
                    dest.write_text(content)
                    if rel not in log["edited"]:
                        log["edited"].append(rel)
                    obs = f"Wrote {len(content)} bytes to {rel}."
                    log["actions"].append({"type": "write", "file": rel, "bytes": len(content)})

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
