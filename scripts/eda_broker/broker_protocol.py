#!/usr/bin/env python3
"""Wire protocol and op table for the restricted-SSH EDA broker.

Pure data and pure functions: no network, no subprocess, no filesystem writes. Everything that
decides whether a request is legal lives here, so it can be tested exhaustively without a remote
host.

Two properties are structural rather than defended:

  * The client never names a path. Input keys are matched against a fixed per-op set and the broker
    writes each accepted value under a name from its own table. Traversal is not sanitised away, it
    is unrepresentable.
  * The client never names an episode. The episode is burned into the server-side forced command,
    so it is not a field of this protocol at all.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

MAGIC = "EDABROKER1"
WORKDIR_TOKEN = "@WORKDIR@"
HOME_TOKEN = "@HOME@"

EPISODE_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")

# A name is a bare basename or it is not a name. `.` and `..` are excluded explicitly because they
# are legal basenames and are not files.
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")

MAX_INVOCATIONS_PER_EPISODE = 200
OP_WALL_CLOCK_SEC = 180          # parity with the frozen per-command timeout
KILL_GRACE_SEC = 10


class Status:
    OK = "ok"
    TOOL_TIMEOUT = "tool_timeout"        # the tool ran and exceeded the wall clock
    REFUSED = "refused"                  # the request was illegal; nothing crossed to the remote
    BROKER_ERROR = "broker_error"        # the broker itself failed
    TRANSPORT_ERROR = "transport_error"  # client-side: ssh/framing failed; NOT a tool result
    # An output exceeded a transport cap. Fail-closed and deliberately NOT a truncation: the
    # headroom calibration in the raw-output audit covers a finite calibration set, so a future
    # invocation may still exceed a cap, and the only safe behaviour then is to spend one discarded
    # episode rather than hand the agent a silently shortened observation. Measurement-invalid.
    TRANSPORT_OUTPUT_LIMIT = "transport_output_limit"


# The statuses that mean "this episode measured infrastructure, not a model". No aggregate may
# include an episode whose tool channel reported one of these.
MEASUREMENT_INVALID = (Status.BROKER_ERROR, Status.TRANSPORT_ERROR, Status.TRANSPORT_OUTPUT_LIMIT)


class Refusal(Exception):
    def __init__(self, reason: str, **detail):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


class TransportOutputLimit(Exception):
    """An output exceeded a transport cap.

    Deliberately a distinct exception rather than a `truncated: true` flag on an otherwise-normal
    response. A flag invites the caller to carry on with a shortened observation, which would make
    the cap a silent second truncation channel on top of the frozen runner's 4000-byte one -- and
    unlike that one, it would be invisible to the agent and absent from the frozen arm. The cost of
    failing closed is one discarded episode; the cost of truncating is a contaminated measurement
    that looks clean.
    """

    def __init__(self, **detail):
        super().__init__(detail.get("kind", "output_limit"))
        self.detail = detail


@dataclass(frozen=True)
class Op:
    name: str
    shim_name: str
    client_argv: tuple[str, ...]
    editable: tuple[str, ...]
    canonical: tuple[str, ...]
    generated: tuple[str, ...]
    steps: tuple[tuple[str, ...], ...]
    artifacts: tuple[str, ...] = field(default=())


# `PY` and `TOOL` are placeholders resolved by the broker from its deploy record and the login-shell
# PATH respectively. They are never taken from the request.
OPS: dict[str, Op] = {
    "sta_public": Op(
        name="sta_public",
        shim_name="pt_shell",
        client_argv=("-f", "run_public.tcl"),
        editable=("exception_config.json",),
        canonical=("run_public.tcl", "build_applied_sdc.py", "constraints.sdc",
                   "partition_pins.json", "intent_exception.json", "design.v", "tiny.db"),
        generated=("agent_applied.sdc",),
        steps=(("PY", "build_applied_sdc.py"),
               ("TOOL", "-f", "run_public.tcl")),
    ),
    "spice_public": Op(
        name="spice_public",
        shim_name="hspice",
        client_argv=("-i", "circuit_built.sp", "-o", "hspice_run"),
        editable=("meas_config.json",),
        canonical=("build_deck.py", "circuit_core.sp", "corner_models.json", "load_models.json"),
        generated=("circuit_built.sp",),
        steps=(("PY", "build_deck.py"),
               ("TOOL", "-i", "circuit_built.sp", "-o", "hspice_run")),
        artifacts=("hspice_run.lis",),
    ),
}

OP_BY_SHIM = {op.shim_name: op.name for op in OPS.values()}


def _load_caps() -> dict[str, int]:
    """Caps are DERIVED from the measured raw-output audit, not chosen against the 4000-byte
    observation truncation. See docs/opencode_probe_remote_broker_design.md section 4.1."""
    rec = Path(__file__).resolve().parents[2] / "opencode_probe/evidence/raw_output_audit.json"
    if rec.is_file():
        caps = json.loads(rec.read_text()).get("caps")
        if caps:
            return dict(caps)
    return {"request_bytes": 2 * 1024 * 1024, "stdout_bytes": 1024 * 1024,
            "stderr_bytes": 1024 * 1024, "artifact_bytes": 8 * 1024 * 1024}


CAPS = _load_caps()


def valid_episode_id(s) -> bool:
    return isinstance(s, str) and bool(EPISODE_RE.match(s))


def input_names(op: Op) -> tuple[str, ...]:
    return tuple(op.editable) + tuple(op.canonical)


def frame(payload: dict) -> bytes:
    body = json.dumps(payload, ensure_ascii=False).encode()
    return f"{MAGIC} {len(body)}\n".encode() + body + b"\n"


def unframe(raw: bytes) -> dict:
    head = MAGIC.encode() + b" "
    if not raw.startswith(head):
        raise Refusal("FRAMING", got=raw[:80].decode("utf-8", "replace"))
    nl = raw.find(b"\n")
    if nl < 0:
        raise Refusal("FRAMING", got="no length terminator")
    try:
        n = int(raw[len(head):nl])
    except ValueError:
        raise Refusal("FRAMING", got=raw[:80].decode("utf-8", "replace"))
    body = raw[nl + 1: nl + 1 + n]
    if len(body) != n:
        raise Refusal("FRAMING", expected=n, got=len(body))
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise Refusal("FRAMING", got=str(e))


def validate_request(req) -> Op:
    """Return the Op, or raise Refusal. Nothing here touches the filesystem."""
    if not isinstance(req, dict):
        raise Refusal("MALFORMED_REQUEST")
    op = OPS.get(req.get("op")) if isinstance(req.get("op"), str) else None
    if op is None:
        raise Refusal("UNKNOWN_OP", op=repr(req.get("op")))
    inputs = req.get("inputs")
    if not isinstance(inputs, dict):
        raise Refusal("MALFORMED_REQUEST", field="inputs")
    for k in inputs:
        if not isinstance(k, str) or not NAME_RE.match(k) or k in (".", ".."):
            raise Refusal("ILLEGAL_INPUT_NAME", name=repr(k))
    if set(inputs) != set(input_names(op)):
        raise Refusal("INPUT_SET_MISMATCH",
                      expected=sorted(input_names(op)), got=sorted(inputs))
    return op
