#!/usr/bin/env python3
"""In-sandbox client. Installed as `pt_shell` and `hspice`, which is how run_public.sh already
dispatches (EDA_PT_CMD / EDA_HSPICE_CMD), so no hash-pinned canonical file changes.

The client holds a per-episode key and can reach exactly one forced command. It cannot name an
episode: the episode is in the authorized_keys line, not in this protocol. It cannot name a path:
input keys are matched against a fixed per-op set on the far side.

The failure kinds are kept apart on purpose, because collapsing them would let an infrastructure
fault be recorded as model behaviour -- the measurement-validity rule this project exists to defend.

One limitation is inherited rather than chosen: both run_public.sh scripts are sha256-pinned task
files that end in `exit 0` and merge stderr into stdout with 2>&1. So this client's exit code does
not survive to whatever invoked run_public.sh. The `eda-broker: MEASUREMENT_INVALID <status>:`
marker in the merged text is the only carrier that does, which is why it is worded to match the
frozen forwarder's own `eda-shim: remote execution ... failed` line.
"""

from __future__ import annotations

import base64
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eda_broker import broker_protocol as bp   # noqa: E402

KEY = Path(os.environ.get("EDA_BROKER_KEY", "/tmp/eda-probe/key"))
KNOWN_HOSTS = Path(os.environ.get("EDA_BROKER_KNOWN_HOSTS", "/tmp/eda-probe/known_hosts"))
HOST = os.environ.get("EDA_BROKER_HOST", "tsb@b04")
CONNECT_TIMEOUT = 30
CLIENT_DEADLINE = bp.OP_WALL_CLOCK_SEC + 90     # remote wall clock plus transfer headroom

EXIT_TIMEOUT, EXIT_TRANSPORT, EXIT_REFUSED = 124, 125, 126


def op_for_argv0(argv0: str) -> str:
    name = bp.OP_BY_SHIM.get(Path(argv0).name)
    if name is None:
        raise bp.Refusal("UNKNOWN_SHIM", argv0=Path(argv0).name)
    return name


def check_argv(op, argv) -> None:
    if tuple(argv) != op.client_argv:
        raise bp.Refusal("UNEXPECTED_ARGV", expected=list(op.client_argv), got=list(argv))


def build_request(op, cwd) -> dict:
    inputs = {}
    for name in bp.input_names(op):
        f = Path(cwd) / name
        if not f.is_file():
            raise bp.Refusal("MISSING_INPUT", file=name)
        inputs[name] = base64.b64encode(f.read_bytes()).decode()
    return {"op": op.name, "inputs": inputs}


def ssh_argv(key, known_hosts, host: str) -> list:
    return ["ssh", "-T", "-q",
            "-i", str(key),
            "-o", "IdentitiesOnly=yes",
            "-o", "IdentityAgent=none",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=yes",
            "-o", f"UserKnownHostsFile={known_hosts}",
            "-o", "ControlMaster=no",
            "-o", "ControlPath=none",
            "-o", f"ConnectTimeout={CONNECT_TIMEOUT}",
            host]


def emit(resp: dict, cwd, out, err) -> int:
    status = resp.get("status")
    if status in bp.MEASUREMENT_INVALID:
        # Named the way the frozen forwarder named its own failure, so the runner's log heuristics
        # see an infrastructure fault rather than tool text. No stdout is produced at all: a
        # plausible-looking partial tool log is worse than none, and for transport_output_limit it
        # would be exactly the silent truncation this design refuses to have.
        detail = resp.get("detail") or ""
        err.write(f"eda-broker: MEASUREMENT_INVALID {status}: "
                  f"{resp.get('reason')} {detail}".rstrip() + "\n")
        return EXIT_TRANSPORT
    if status == bp.Status.REFUSED:
        err.write(f"eda-broker: REFUSED {resp.get('reason')} {resp.get('detail')}\n")
        return EXIT_REFUSED

    local = str(Path(cwd).resolve())
    out.write((resp.get("stdout") or "").replace(bp.WORKDIR_TOKEN, local))
    err.write((resp.get("stderr") or "").replace(bp.WORKDIR_TOKEN, local))
    allowed = bp.OPS[resp["op"]].artifacts if resp.get("op") in bp.OPS else ()
    for name, blob in (resp.get("artifacts") or {}).items():
        if name in allowed:                            # whitelisted by the client too
            (Path(cwd) / name).write_bytes(base64.b64decode(blob))
    if status == bp.Status.TOOL_TIMEOUT:
        err.write(f"eda-broker: tool exceeded the {bp.OP_WALL_CLOCK_SEC}s wall clock\n")
        return EXIT_TIMEOUT
    return int(resp.get("rc", 0))


def main(argv=None) -> int:
    argv = list(sys.argv if argv is None else argv)
    try:
        op = bp.OPS[op_for_argv0(argv[0])]
        check_argv(op, argv[1:])
        req = build_request(op, Path.cwd())
    except bp.Refusal as r:
        return emit({"status": bp.Status.REFUSED, "reason": r.reason, "detail": r.detail},
                    Path.cwd(), sys.stdout, sys.stderr)

    raw = bp.frame(req)
    if len(raw) > bp.CAPS["request_bytes"]:
        return emit({"status": bp.Status.REFUSED, "reason": "REQUEST_TOO_LARGE",
                     "detail": {"bytes": len(raw)}}, Path.cwd(), sys.stdout, sys.stderr)
    try:
        p = subprocess.run(ssh_argv(KEY, KNOWN_HOSTS, HOST), input=raw,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=CLIENT_DEADLINE)
    except subprocess.TimeoutExpired:
        return emit({"status": bp.Status.TRANSPORT_ERROR,
                     "reason": f"no response within {CLIENT_DEADLINE}s"},
                    Path.cwd(), sys.stdout, sys.stderr)
    try:
        resp = bp.unframe(p.stdout)
    except bp.Refusal as r:
        return emit({"status": bp.Status.TRANSPORT_ERROR,
                     "reason": f"ssh rc={p.returncode} framing={r.reason} {r.detail}"},
                    Path.cwd(), sys.stdout, sys.stderr)
    return emit(resp, Path.cwd(), sys.stdout, sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
