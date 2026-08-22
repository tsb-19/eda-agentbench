#!/usr/bin/env python3
"""The forced command. Runs ON the remote EDA host, as the only thing a probe key can do.

Selected by the SERVER, not the client: the episode id arrives in argv from the authorized_keys
line, so an agent holding episode 0004's key cannot request episode 0005 -- there is no field in
which to name one. SSH_ORIGINAL_COMMAND is deleted on entry and never consulted; see the test.

Every exit path cleans up: success, refusal, tool failure, wall-clock timeout and signal. A flow
that overruns is killed by process group, because subprocess timeout alone leaves pt_shell
descendants holding licences and writing into whatever runs next.

An output over its transport cap is fail-closed, never truncated. The headroom calibration in
opencode_probe/evidence/raw_output_audit.json covers a finite calibration set, so a future
invocation may exceed a cap; when one does, the episode is discarded rather than measured against a
silently shortened observation.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eda_broker import broker_protocol as bp   # noqa: E402

# The client's original command line still exists in the environment and is deliberately destroyed
# here. It plays no part in any authorisation decision and no child process sees it.
os.environ.pop("SSH_ORIGINAL_COMMAND", None)

ROOT = Path(os.environ.get("EDA_BROKER_ROOT", str(Path.home() / "eda-probe-broker")))
DEPLOY = ROOT / "deploy.json"


def _deploy() -> dict:
    return json.loads(DEPLOY.read_text()) if DEPLOY.is_file() else {}


def bump_invocation(episode_dir) -> int:
    """Server-side rate bound. The agent holds the key by design, so the number of remote tool
    launches it can trigger has to be bounded somewhere other than its own good behaviour."""
    counter = Path(episode_dir) / "invocations"
    n = int(counter.read_text().strip() or 0) if counter.is_file() else 0
    n += 1
    if n > bp.MAX_INVOCATIONS_PER_EPISODE:
        raise bp.Refusal("INVOCATION_CAP", limit=bp.MAX_INVOCATIONS_PER_EPISODE)
    counter.write_text(str(n))
    return n


def materialise(op, inputs: dict, workdir, manifest: dict) -> None:
    """Write the accepted inputs under names from the broker's OWN table.

    No client string is used as a path. Canonical files are hash-checked against the manifest the
    host installed and refused on divergence -- stricter than the frozen runner, which shipped
    whatever was in $PWD and caught tampering at scoring time. Post-hoc detection is enough when
    the consequence is a bad score; it is not enough when the consequence is a leaked oracle,
    because detecting the read afterwards does not un-read it.
    """
    workdir = Path(workdir)
    decoded: dict = {}
    for name in bp.input_names(op):
        try:
            blob = base64.b64decode(inputs[name], validate=True)
        except Exception:
            raise bp.Refusal("MALFORMED_INPUT", file=name)
        if name in op.canonical:
            want = manifest.get(name)
            got = hashlib.sha256(blob).hexdigest()
            if want is None:
                raise bp.Refusal("MANIFEST_INCOMPLETE", file=name)
            if got != want:
                raise bp.Refusal("NON_EDITABLE_DIVERGENCE", file=name,
                                 canonical=f"sha256:{want[:12]}", supplied=f"sha256:{got[:12]}")
        decoded[name] = blob
    # Only after every check: nothing is written when a request is refused.
    for name, blob in decoded.items():
        (workdir / name).write_bytes(blob)


def run_step(argv, cwd, deadline: float, env: dict):
    """Run one step in its own session, and kill the whole group if it overruns."""
    remaining = max(1.0, deadline - time.time())
    p = subprocess.Popen(argv, cwd=str(cwd), env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                         start_new_session=True)
    try:
        out, err = p.communicate(timeout=remaining)
        return p.returncode, out, err, False
    except subprocess.TimeoutExpired:
        _kill_group(p.pid)
        try:
            out, err = p.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            out, err = b"", b""
        return -1, out, err, True


def _kill_group(pid: int) -> None:
    try:
        pgid = os.getpgid(pid)
    except OSError:
        return
    for sig, wait in ((signal.SIGTERM, bp.KILL_GRACE_SEC), (signal.SIGKILL, 2)):
        try:
            os.killpg(pgid, sig)
        except OSError:
            return
        end = time.time() + wait
        while time.time() < end:
            try:
                os.killpg(pgid, 0)
            except OSError:
                return
            time.sleep(0.1)


def sanitise(text: str, workdir, home) -> str:
    """Rewrite remote paths out of anything the agent will see.

    The frozen forwarder did the same (bin/forwarder step 5: sed s|$REMOTE|$CWD|g). Skipping it
    would both depart from the frozen observation and print /home/<user> into an agent transcript
    on a branch that is not anonymised.
    """
    return text.replace(str(workdir), bp.WORKDIR_TOKEN).replace(str(home), bp.HOME_TOKEN)


def enforce_output_caps(out: bytes, err: bytes, artifacts: dict, caps=None) -> None:
    """Raise if any output exceeds its transport cap. There is deliberately no truncating path.

    The raw-output audit establishes headroom over a finite calibration set, which is not a proof
    that a cap can never bind. So this has to be safe when one does. Truncating would create a
    second observation cap -- invisible to the agent, absent from the frozen arm, and
    indistinguishable in a log from real tool output. Failing closed costs one episode, marked
    measurement-invalid.
    """
    caps = caps or bp.CAPS
    if len(out) > caps["stdout_bytes"]:
        raise bp.TransportOutputLimit(kind="stdout", bytes=len(out), limit=caps["stdout_bytes"])
    if len(err) > caps["stderr_bytes"]:
        raise bp.TransportOutputLimit(kind="stderr", bytes=len(err), limit=caps["stderr_bytes"])
    for name, blob in sorted(artifacts.items()):
        if len(blob) > caps["artifact_bytes"]:
            raise bp.TransportOutputLimit(kind="artifact", name=name, bytes=len(blob),
                                          limit=caps["artifact_bytes"])


def limit_response(exc) -> dict:
    """The response for a cap hit. It carries the measurement, not the output: no stdout, no stderr,
    no artifacts, so there is nothing for a caller to mistake for a tool result."""
    return {"status": bp.Status.TRANSPORT_OUTPUT_LIMIT,
            "reason": "output exceeded a transport cap",
            "detail": dict(exc.detail), "rc": 125}


def _resolve(step, deploy) -> list:
    """PY and TOOL are placeholders in the op table; they are resolved from the deploy record and
    the login-shell PATH, never from the request."""
    argv = list(step)
    if argv[0] == "PY":
        argv[0] = deploy.get("python3", "python3")
    return argv


def _login_env() -> dict:
    """The tool environment the frozen forwarder produced: `ssh host bash -lc '...'`. Reproduced
    here so the broker resolves the same pt_shell / hspice the frozen arm used."""
    r = subprocess.run(["bash", "-lc", "env -0"], capture_output=True, timeout=60)
    env = dict(os.environ)
    for chunk in r.stdout.split(b"\0"):
        if b"=" in chunk:
            k, _, v = chunk.partition(b"=")
            env[k.decode("utf-8", "replace")] = v.decode("utf-8", "replace")
    env.pop("SSH_ORIGINAL_COMMAND", None)
    return env


def _episode_caps(manifest: dict) -> dict:
    """Caps for this episode. Normally the calibrated ones; a provisioned override exists solely so
    the zero-model preflight can exercise the fail-closed path on real tool output without waiting
    for a genuinely oversized PrimeTime log. The override can only ever LOWER a cap -- a manifest
    cannot widen the transport bound."""
    caps = dict(bp.CAPS)
    override = manifest.get("caps_override") or {}
    for k, v in override.items():
        if k in caps and isinstance(v, int) and 0 < v < caps[k]:
            caps[k] = v
    return caps


def _serve(episode_id: str) -> dict:
    deploy = _deploy()
    episode_dir = ROOT / "ep" / episode_id
    if not episode_dir.is_dir():
        raise bp.Refusal("NO_SUCH_EPISODE")
    manifest = json.loads((episode_dir / "manifest.json").read_text())

    raw = sys.stdin.buffer.read(bp.CAPS["request_bytes"] + 1)
    if len(raw) > bp.CAPS["request_bytes"]:
        raise bp.Refusal("REQUEST_TOO_LARGE", limit=bp.CAPS["request_bytes"])
    req = bp.unframe(raw)
    op = bp.validate_request(req)
    if op.name not in manifest["ops"]:
        raise bp.Refusal("OP_NOT_PROVISIONED", op=op.name)

    n = bump_invocation(episode_dir)
    workdir = episode_dir / f"inv-{n}"
    workdir.mkdir(mode=0o700)
    try:
        materialise(op, req["inputs"], workdir, manifest["sha256"])
        env = _login_env()
        deadline = time.time() + bp.OP_WALL_CLOCK_SEC
        home = Path.home()
        rc, out, err, timed_out = 0, b"", b"", False
        for step in op.steps:
            argv = _resolve(step, deploy)
            if argv[0] == "TOOL":
                argv[0] = op.shim_name          # resolved from the login-shell PATH, as the forwarder does
            rc, o, e, timed_out = run_step(argv, workdir, deadline, env)
            out += o
            err += e
            if rc != 0 or timed_out:
                break
        arts_raw = {}
        for name in op.artifacts:
            f = workdir / name
            if f.is_file():
                arts_raw[name] = f.read_bytes()
        # Fail-closed, before anything is encoded or returned. An over-cap output raises out of
        # _serve and becomes a typed transport_output_limit response with no output in it at all.
        enforce_output_caps(out, err, arts_raw, caps=_episode_caps(manifest))
        arts = {n2: base64.b64encode(b).decode() for n2, b in arts_raw.items()}
        return {"op": op.name, "status": bp.Status.TOOL_TIMEOUT if timed_out else bp.Status.OK,
                "rc": rc,
                "stdout": sanitise(out.decode("utf-8", "replace"), workdir, home),
                "stderr": sanitise(err.decode("utf-8", "replace"), workdir, home),
                "artifacts": arts,
                "invocation": n,
                "elapsed_s": round(bp.OP_WALL_CLOCK_SEC - max(0.0, deadline - time.time()), 2)}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main(argv=None) -> int:
    argv = list(sys.argv if argv is None else argv)
    resp = None
    try:
        if len(argv) != 2 or not bp.valid_episode_id(argv[1]):
            raise bp.Refusal("ILLEGAL_EPISODE_ID")
        resp = _serve(argv[1])
    except bp.TransportOutputLimit as t:
        resp = limit_response(t)
    except bp.Refusal as r:
        resp = {"status": bp.Status.REFUSED, "reason": r.reason, "detail": r.detail, "rc": 126}
    except Exception as e:                       # never leak a traceback path to the client
        resp = {"status": bp.Status.BROKER_ERROR, "reason": type(e).__name__, "rc": 125}
    sys.stdout.buffer.write(bp.frame(resp))
    sys.stdout.buffer.flush()
    return 0 if resp.get("status") in (bp.Status.OK, bp.Status.TOOL_TIMEOUT) else 1


def _on_signal(signum, frame):
    raise SystemExit(128 + signum)


for _s in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
    signal.signal(_s, _on_signal)

if __name__ == "__main__":
    raise SystemExit(main())
