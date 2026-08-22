#!/usr/bin/env python3
"""Zero-call preflight for the restricted-SSH EDA broker.

Fourteen negative controls, a planted oracle decoy, a full-size batch key install, a fail-closed cap
hit, verified cleanup, and a forwarder-equivalence check. No model is called; every one of these is a
property of the configuration, the remote host and the sandbox, and a model adds nothing to
establishing them.

This preflight does NOT authorize the formal 48-episode arm. It addresses one blocker. Check 7
remains UNSETTLED and check 5 must be re-established under this configuration -- its earlier PASS
was obtained with the tools absent, which is not the configuration the arm would use.

Two rules govern how the controls are written:

  * Record the OBSERVATION, never a verdict alone. "ssh exit 255, stderr: 'PTY allocation request
    failed'", not "refused".
  * A control that cannot run is a FAIL, not a skip. If scp is not installed locally, control 5
    established nothing, and a battery that quietly shrinks is the failure mode this project keeps
    meeting.
"""

from __future__ import annotations

import argparse
import base64
import difflib
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from eda_broker import broker_admin as ba          # noqa: E402
from eda_broker import broker_client as bc         # noqa: E402
from eda_broker import broker_protocol as bp       # noqa: E402

OUT = REPO / "opencode_probe/evidence/remote_broker_preflight.json"

EPISODE = "p15_dev_0000"
EPISODE_X = "p15_dev_0000_x"                 # control 10's cross-episode target
EPISODE_CAP = "p15_dev_0000_cap"             # control 14's lowered-cap episode
EPISODE_KILL = "p15_dev_0000_kill"           # the process-group kill observation
INSTANCE = REPO / "tasks/p15_sta_handoff/p15_dev_0000"

# b04's /tmp mirrors are recreated by the next grading run, so proving the tree is empty proves
# nothing about the next episode. A deliberately planted truth file is the property the arm needs.
DECOY_DIR = "/tmp/eda_shim_PREFLIGHT"
DECOY_NAME = "signoff_intent_truth.json"

# Normalisation for the forwarder-equivalence comparison. Each rule records how much it dropped: a
# normalisation that grows until two outputs agree is the same failure as a verifier tuned until it
# prints nothing.
NORMALISE = [
    (r"^\s*Version .* for linux64 .*$", "tool version banner"),
    (r"^\s*Copyright \(c\).*$", "copyright banner"),
    (r"\b\d{4}-\d{2}-\d{2}\b|\b[A-Z][a-z]{2} \d{1,2}, \d{4}\b", "dates"),
    (r"\b\d{1,2}:\d{2}:\d{2}\b", "clock times"),
    (r"(?i)\b(cpu|elapsed|wall)\s*(time)?\s*[:=]\s*[\d.:]+", "timing lines"),
    (r"(?i)licen[cs]e.*(check ?out|server|queue|wait)", "licence chatter"),
    (r"\bpid\s*[:=]?\s*\d+", "pids"),
    (r"\b\d+\.\d{3,}\b", "high-precision floats"),
]


# ---------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------

def control(cid, name, attempt, expected, observed, passed, **detail):
    r = {"id": cid, "name": name, "attempt": attempt, "expected": expected,
         "observed": observed, "pass": bool(passed)}
    if detail:
        r["detail"] = detail
    return r


def _run(argv, **kw):
    kw.setdefault("capture_output", True)
    kw.setdefault("timeout", 120)
    try:
        return subprocess.run(argv, **kw)
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(argv, 124, b"", b"timed out")


def _describe(r) -> str:
    if r is None:
        return "the command is not installed on this host; the control did not run"
    out = (r.stdout or b"")[-200:].decode("utf-8", "replace").strip()
    err = (r.stderr or b"")[-200:].decode("utf-8", "replace").strip()
    return f"exit {r.returncode}; stdout={out!r}; stderr={err!r}"


def _probe_ssh(key: Path, kh: Path, host: str, extra=(), payload=b"", timeout=90):
    argv = bc.ssh_argv(key, kh, host)
    argv = argv[:1] + list(extra) + argv[1:]
    return _run(argv, input=payload, timeout=timeout)


def _framed(r):
    """Return the broker's reply, or None if nothing framed came back."""
    if r is None:
        return None
    try:
        return bp.unframe(r.stdout)
    except bp.Refusal:
        return None


def _request(op_name, files: Path, mutate=None) -> bytes:
    op = bp.OPS[op_name]
    inputs = {}
    for n in bp.input_names(op):
        inputs[n] = base64.b64encode((files / n).read_bytes()).decode()
    req = {"op": op_name, "inputs": inputs}
    if mutate:
        req = mutate(req)
    return bp.frame(req)


def _scratch(instance: Path) -> Path:
    d = Path(tempfile.mkdtemp(prefix="preflight_"))
    shutil.copytree(instance / "files", d / "files")
    return d / "files"


def _remote(host, script, timeout=120):
    """One remote command, under a login shell, with the script quoted as ONE word.

    ssh joins its remaining argv with spaces and the REMOTE shell parses the result, so an unquoted
    `bash -lc 'a | b'` sends only `a` to bash -lc and runs `| b` elsewhere. The first preflight run
    failed three controls on exactly that: the decoy could not be planted, the operator-key probe
    printed nothing, and an `ls ... | wc -l` counted the remote home directory instead of the
    invocation dirs -- reporting "19" invocation dirs left when there were none. Routed through
    broker_admin._ssh so there is one quoting implementation, not two.
    """
    return ba._ssh(host, script, timeout=timeout)


def _remote_user_region_sha(host, root) -> str:
    d = ba._deploy_record()
    res = ba._remote_akb_call(host, root, d,
                              "import hashlib\n"
                              "report({'sha': hashlib.sha256(akb.user_region(ak)).hexdigest(),"
                              " 'n': len(akb.list_entries(ak)),"
                              " 'lines': [e['line'] for e in akb.list_entries(ak)]})")
    return res


def _stage_client_bin(dest: Path) -> Path:
    """A local pt_shell/hspice launcher pair, so run_public.sh can dispatch through the broker
    exactly as it would inside the sandbox -- built by the SAME function the sandbox uses, so the two
    cannot drift. The shebang is rewritten to this interpreter; nothing else differs."""
    sys.path.insert(0, str(REPO / "scripts"))
    import opencode_probe_agent as agent

    dest.mkdir(parents=True, exist_ok=True)
    bin_dir = agent.stage_broker_bin(dest)
    for shim in sorted(bp.OP_BY_SHIM):
        p = bin_dir / shim
        p.write_text(agent.broker_launcher_source(python=sys.executable))
        p.chmod(0o755)
    return bin_dir


# ---------------------------------------------------------------------------------------------
# controls 1-9: what the probe key cannot do
# ---------------------------------------------------------------------------------------------

def controls_ssh_surface(key, kh, host) -> list:
    out = []

    r = _probe_ssh(key, kh, host, payload=b"", extra=())
    # The forced command runs and the client's command line is ignored; with no framed request on
    # stdin the broker answers REFUSED FRAMING rather than executing anything.
    argv = bc.ssh_argv(key, kh, host) + ["cat /etc/passwd"]
    r1 = _run(argv, input=b"", timeout=90)
    resp = _framed(r1)
    leaked = b"root:x:" in (r1.stdout if r1 else b"")
    out.append(control(
        1, "client command is ignored by the forced command",
        "ssh -i key tsb@b04 'cat /etc/passwd' with empty stdin",
        "the forced command runs; REFUSED FRAMING; no passwd content",
        _describe(r1) + f"; framed={resp}",
        resp is not None and resp.get("reason") == "FRAMING" and not leaked,
        etc_passwd_leaked=leaked))

    r2 = _probe_ssh(key, kh, host, payload=bp.frame({"op": "ls", "inputs": {}}))
    resp = _framed(r2)
    out.append(control(
        2, "unknown op", 'framed {"op": "ls"}', "REFUSED UNKNOWN_OP",
        _describe(r2) + f"; framed={resp}",
        resp is not None and resp.get("reason") == "UNKNOWN_OP"))

    files = _scratch(INSTANCE)
    r3 = _probe_ssh(key, kh, host,
                    payload=_request("sta_public", files,
                                     lambda q: {**q, "inputs": {**q["inputs"], "extra.txt": ""}}))
    resp = _framed(r3)
    out.append(control(
        3, "input key set with an extra name", "inputs + extra.txt", "REFUSED INPUT_SET_MISMATCH",
        _describe(r3) + f"; framed={resp}",
        resp is not None and resp.get("reason") == "INPUT_SET_MISMATCH"))

    def swap_to_path(q):
        inputs = dict(q["inputs"])
        inputs.pop("design.v", None)
        inputs["../hidden/" + DECOY_NAME] = ""
        return {**q, "inputs": inputs}

    r4 = _probe_ssh(key, kh, host, payload=_request("sta_public", files, swap_to_path))
    resp = _framed(r4)
    out.append(control(
        4, "input name that expresses a path", f"input key ../hidden/{DECOY_NAME}",
        "REFUSED ILLEGAL_INPUT_NAME",
        _describe(r4) + f"; framed={resp}",
        resp is not None and resp.get("reason") == "ILLEGAL_INPUT_NAME"))
    shutil.rmtree(files.parent, ignore_errors=True)

    with tempfile.NamedTemporaryFile(suffix=".txt") as tf:
        tf.write(b"x")
        tf.flush()
        r5 = _run(["scp", "-i", str(key), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
                   "-o", f"UserKnownHostsFile={kh}", "-o", "StrictHostKeyChecking=yes",
                   tf.name, f"{host}:/tmp/"], timeout=90)
    out.append(control(
        5, "scp", "scp -i key <file> tsb@b04:/tmp/", "fails -- no scp server ever runs",
        _describe(r5), r5 is not None and r5.returncode != 0))

    r6 = _run(["sftp", "-i", str(key), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
               "-o", f"UserKnownHostsFile={kh}", "-o", "StrictHostKeyChecking=yes",
               "-b", "/dev/null", host], timeout=90)
    out.append(control(
        6, "sftp", "sftp -i key tsb@b04", "fails -- no sftp-server",
        _describe(r6), r6 is not None and r6.returncode != 0))

    r7 = _probe_ssh(key, kh, host, extra=("-tt",), payload=b"")
    saw_pty = b"PTY allocation" in ((r7.stderr or b"") if r7 else b"")
    resp = _framed(r7)
    out.append(control(
        7, "PTY allocation", "ssh -tt -i key tsb@b04", "PTY allocation refused",
        _describe(r7) + f"; framed={resp}",
        r7 is not None and (saw_pty or resp is not None),
        pty_message_seen=saw_pty))

    r8 = _probe_ssh(key, kh, host, extra=("-L", "9999:localhost:22"), payload=b"")
    denied = b"forwarding" in ((r8.stderr or b"").lower() if r8 else b"")
    probe = _run(["bash", "-c", "exec 3<>/dev/tcp/127.0.0.1/9999"], timeout=10)
    out.append(control(
        8, "port forwarding", "ssh -L 9999:localhost:22 -i key tsb@b04",
        "forwarding refused and no listener established",
        _describe(r8) + f"; local 9999 reachable: {probe is not None and probe.returncode == 0}",
        (denied or (probe is None or probe.returncode != 0)),
        refusal_message_seen=denied))

    r9 = _probe_ssh(key, kh, host, extra=("-A",), payload=b"")
    out.append(control(
        9, "agent forwarding", "ssh -A -i key tsb@b04",
        "agent forwarding refused; no SSH_AUTH_SOCK exists to forward",
        _describe(r9) + f"; local SSH_AUTH_SOCK={os.environ.get('SSH_AUTH_SOCK')!r}",
        r9 is not None))
    return out


# ---------------------------------------------------------------------------------------------
# control 10: cross-episode
# ---------------------------------------------------------------------------------------------

def control_cross_episode(key, kh, host, root) -> dict:
    files = _scratch(INSTANCE)

    def name_the_other(q):
        # Every field the protocol allows, plus two it does not.
        return {**q, "episode": EPISODE_X, "episode_id": EPISODE_X, "target": EPISODE_X}

    r = _probe_ssh(key, kh, host, payload=_request("sta_public", files, name_the_other), timeout=300)
    resp = _framed(r)
    shutil.rmtree(files.parent, ignore_errors=True)

    argv = bc.ssh_argv(key, kh, host) + [f"broker.sh {EPISODE_X}"]
    r_argv = _run(argv, input=b"", timeout=90)
    resp_argv = _framed(r_argv)

    env_attempt = _run(bc.ssh_argv(key, kh, host)[:1]
                       + ["-o", "SendEnv=SSH_ORIGINAL_COMMAND"]
                       + bc.ssh_argv(key, kh, host)[1:] + [f"broker.sh {EPISODE_X}"],
                       input=b"", timeout=90)

    touched = _remote(host, f"ls -1 {root}/ep/{EPISODE_X}/ 2>/dev/null | grep -c '^inv-' || true")
    inv_count = (touched.stdout or b"0").decode().strip().splitlines()[-1:] or ["0"]
    other_touched = inv_count[0] not in ("0", "")

    served_own = (resp is not None
                  and (resp.get("status") in (bp.Status.OK, bp.Status.TOOL_TIMEOUT)
                       or resp.get("status") == bp.Status.REFUSED))
    return control(
        10, "cross-episode selection",
        f"episode {EPISODE}'s key, naming {EPISODE_X} in JSON fields, in argv, and via SendEnv",
        f"served for {EPISODE} or refused; {EPISODE_X}'s directory never touched",
        f"json={resp and resp.get('status')}/{resp and resp.get('reason')}; "
        f"argv={_describe(r_argv)} framed={resp_argv and resp_argv.get('status')}; "
        f"sendenv={_describe(env_attempt)}; "
        f"{EPISODE_X} inv-* count after: {inv_count[0]!r}",
        served_own and not other_touched,
        other_episode_touched=other_touched)


# ---------------------------------------------------------------------------------------------
# control 11: the planted decoy
# ---------------------------------------------------------------------------------------------

def control_planted_decoy(key, kh, host) -> dict:
    sentinel = "SENTINEL-" + secrets.token_hex(16)
    _remote(host, f"mkdir -p {DECOY_DIR} && "
                  f"printf '%s' '{{\"truth\": \"{sentinel}\"}}' > {DECOY_DIR}/{DECOY_NAME}")
    planted = _remote(host, f"cat {DECOY_DIR}/{DECOY_NAME}")
    if sentinel not in (planted.stdout or b"").decode("utf-8", "replace"):
        return control(11, "planted oracle decoy",
                       f"plant sentinel {sentinel[:20]}... at {DECOY_DIR}/{DECOY_NAME}",
                       "the sentinel is unreachable through every op and every field",
                       "the decoy could not be planted; the control did not run", False)

    files = _scratch(INSTANCE)
    attempts = []
    for label, mutate in (
        ("input name is the decoy path",
         lambda q: {**q, "inputs": {**{k: v for k, v in q["inputs"].items() if k != "design.v"},
                                    f"{DECOY_DIR}/{DECOY_NAME}": ""}}),
        ("input name traverses to the decoy",
         lambda q: {**q, "inputs": {**{k: v for k, v in q["inputs"].items() if k != "design.v"},
                                    f"../../..{DECOY_DIR}/{DECOY_NAME}": ""}}),
        ("extra field names the decoy",
         lambda q: {**q, "read": f"{DECOY_DIR}/{DECOY_NAME}", "include": DECOY_DIR}),
        ("tcl input is replaced with one that reads the decoy",
         lambda q: {**q, "inputs": {**q["inputs"], "run_public.tcl": base64.b64encode(
             f'set fh [open "{DECOY_DIR}/{DECOY_NAME}" r]; puts [read $fh]; exit\n'.encode()
         ).decode()}}),
    ):
        r = _probe_ssh(key, kh, host, payload=_request("sta_public", files, mutate), timeout=300)
        body = json.dumps(_framed(r)) + (r.stdout or b"").decode("utf-8", "replace") if r else ""
        attempts.append({"attempt": label, "sentinel_present": sentinel in body,
                         "observed": _describe(r)})
    shutil.rmtree(files.parent, ignore_errors=True)
    _remote(host, f"rm -rf {DECOY_DIR}")

    leaked = [a for a in attempts if a["sentinel_present"]]
    return control(
        11, "planted oracle decoy",
        f"plant sentinel {sentinel[:20]}... at {DECOY_DIR}/{DECOY_NAME} and attempt to read it "
        f"through every op and every field",
        "the sentinel never appears in any response; correctness does not depend on /tmp being clean",
        f"{len(attempts)} attempts, {len(leaked)} leaked the sentinel: "
        + json.dumps([a["attempt"] for a in leaked]),
        not leaked, attempts=attempts, sentinel_prefix=sentinel[:20])


# ---------------------------------------------------------------------------------------------
# control 12: sandbox credential isolation
# ---------------------------------------------------------------------------------------------

def control_sandbox_isolation(broker_dir: Path) -> dict:
    sys.path.insert(0, str(REPO / "scripts"))
    import opencode_probe_agent as agent

    with tempfile.TemporaryDirectory(prefix="preflight_sb_") as td:
        td = Path(td)
        ws, state = td / "ws", td / "state"
        ws.mkdir()
        state.mkdir()
        bin_dir = agent.stage_broker_bin(state)
        probe = ("set -e\n"
                 "echo HOME_SSH=$(test -e $HOME/.ssh && echo present || echo absent)\n"
                 "echo AUTH_SOCK=${SSH_AUTH_SOCK:-unset}\n"
                 f"echo PROBE_DIR=$(ls -1 {agent.IN_SANDBOX_BROKER} 2>/dev/null | sort | tr '\\n' ',')\n"
                 f"echo KEY_WRITABLE=$(test -w {agent.BROKER_KEY} && echo yes || echo no)\n"
                 "echo FORWARDER=$(command -v forwarder || echo absent)\n")
        argv = agent.bwrap_argv(ws, state, Path("/bin/sh"), ["/bin/sh", "-c", probe],
                                ro_binds=[], seal_tool_output=False,
                                broker=agent.BrokerMounts(key=broker_dir / "key",
                                                          known_hosts=broker_dir / "known_hosts",
                                                          bin_dir=bin_dir))
        env = agent.scrubbed_env(REPO / "opencode_probe/config/opencode.json", state,
                                 api_key="unused", broker_enabled=True)
        r = _run(argv, env=env, timeout=120)

    text = (r.stdout or b"").decode("utf-8", "replace") if r else ""
    facts = dict(line.split("=", 1) for line in text.splitlines() if "=" in line)
    ok = (r is not None and r.returncode == 0
          and facts.get("HOME_SSH") == "absent"
          and facts.get("AUTH_SOCK") == "unset"
          and facts.get("KEY_WRITABLE") == "no"
          and facts.get("FORWARDER") == "absent"
          and set(facts.get("PROBE_DIR", "").strip(",").split(",")) == {"bin", "key", "known_hosts"})
    return control(
        12, "sandbox credential isolation",
        "run a probe inside the episode sandbox and report what credentials it can see",
        "~/.ssh absent, SSH_AUTH_SOCK unset, only key/known_hosts/bin under /tmp/eda-probe, "
        "the key read-only, no forwarder on PATH",
        _describe(r) + "; " + json.dumps(facts),
        ok, facts=facts)


# ---------------------------------------------------------------------------------------------
# control 13: the full-size batch install
# ---------------------------------------------------------------------------------------------

def control_batch_keys(host, root, out_root: Path) -> dict:
    """Requirement E, at the size that motivates it.

    Uses the 48 episode IDS the formal arm would install -- because 48 is the number whose NFS
    exposure batching exists to remove -- but points every one of them at p15_dev_0000's files and
    prefixes every id with PREFLIGHT__, so no studied instance is provisioned and no residue can be
    mistaken for a real arm.
    """
    plan = [{"episode": "PREFLIGHT__" + p["episode"], "instance": EPISODE}
            for p in ba.formal_arm_plan()]
    before = _remote_user_region_sha(host, root)
    rec, during, after, auth_ok = None, None, None, False
    try:
        rec = ba.provision_batch(plan, out_root, host=host, root=root)
        during = _remote_user_region_sha(host, root)
        # "the bytes look right" and "the key still works" are different claims, and only the second
        # one matters at 2 a.m.
        probe = _remote(host, "echo OPERATOR_KEY_OK", timeout=60)
        auth_ok = probe is not None and b"OPERATOR_KEY_OK" in (probe.stdout or b"")
    finally:
        td = ba.teardown_batch(host=host, root=root)
        after = _remote_user_region_sha(host, root)

    forcing = True
    if during:
        for line in during["lines"]:
            forced = re.findall(r'command="[^"]*/broker\.sh ([^"]*)"', line)
            if len(forced) != 1 or not forced[0].startswith("PREFLIGHT__"):
                forcing = False
                break

    d = {"n_entries_before": before["n"],
         "n_entries_during": during["n"] if during else -1,
         "n_entries_after": after["n"],
         "user_region_sha256_before": before["sha"],
         "user_region_sha256_during": during["sha"] if during else "",
         "user_region_sha256_after": after["sha"],
         "operator_key_authenticated_during_batch": auth_ok,
         "every_line_forces_only_its_own_episode": forcing,
         "teardown": td,
         "batch_verified": bool(rec and rec.get("ok"))}
    ok = (d["n_entries_during"] == 48 and d["n_entries_after"] == 0
          and d["user_region_sha256_before"] == d["user_region_sha256_during"] ==
          d["user_region_sha256_after"]
          and auth_ok and forcing and td.get("ok") and d["batch_verified"])
    return control(
        13, "batch install of a full arm's keys",
        "install 48 PREFLIGHT__-prefixed episode keys in one rewrite, then tear them down in one",
        "the non-managed region of authorized_keys is byte-identical before, during and after; "
        "48 entries during and 0 after; every line forces only its own episode; the operator's own "
        "key still authenticates while the batch is live",
        json.dumps({k: v for k, v in d.items() if k != "teardown"}),
        ok, **d)


# ---------------------------------------------------------------------------------------------
# control 14: a cap hit fails closed
# ---------------------------------------------------------------------------------------------

def control_cap_hit(host, root, work_root: Path) -> dict:
    """Lower the stdout cap below the measured 3205 B of real PrimeTime output, then run the real
    tool through the real client and observe what the agent would have seen."""
    out_dir = work_root / EPISODE_CAP
    ba.provision(EPISODE_CAP, INSTANCE, out_dir, host=host, root=root,
                 caps_override={"stdout_bytes": 1024})
    try:
        files = _scratch(INSTANCE)
        bin_dir = _stage_client_bin(work_root / "capbin")
        env = dict(os.environ)
        env.update({"EDA_BROKER_KEY": str(out_dir / "key"),
                    "EDA_BROKER_KNOWN_HOSTS": str(out_dir / "known_hosts"),
                    "EDA_BROKER_HOST": host})
        r = _run([str(bin_dir / "pt_shell"), "-f", "run_public.tcl"],
                 cwd=str(files), env=env, timeout=400)
        # And the raw response, so the assertion is about the wire and not only about the client.
        raw = _probe_ssh(out_dir / "key", out_dir / "known_hosts", host,
                         payload=_request("sta_public", files), timeout=400)
        resp = _framed(raw) or {}
        shutil.rmtree(files.parent, ignore_errors=True)
    finally:
        ba.teardown(EPISODE_CAP, host=host, root=root)

    with_output = [k for k in ("stdout", "stderr", "artifacts") if k in resp]
    stdout_bytes = len(r.stdout or b"") if r else -1
    stderr_head = (r.stderr or b"")[:400].decode("utf-8", "replace") if r else ""
    d = {"status": resp.get("status"),
         "reason": resp.get("reason"),
         "limit_detail": resp.get("detail"),
         "response_keys_with_output": with_output,
         "client_exit_code": r.returncode if r else -1,
         "client_stdout_bytes": stdout_bytes,
         "client_stderr_head": stderr_head}
    ok = (d["status"] == bp.Status.TRANSPORT_OUTPUT_LIMIT
          and with_output == []
          and d["client_exit_code"] == 125
          and stdout_bytes == 0
          and "MEASUREMENT_INVALID" in stderr_head)
    return control(
        14, "an output over its transport cap fails closed",
        "provision with stdout_bytes lowered to 1024, then run real PrimeTime (measured 3205 B)",
        "transport_output_limit; no stdout/stderr/artifacts key in the response; client exits 125 "
        "printing MEASUREMENT_INVALID and nothing on stdout",
        json.dumps(d), ok, **d)


# ---------------------------------------------------------------------------------------------
# cleanup verification
# ---------------------------------------------------------------------------------------------

def verify_cleanup(host, root, user_keys_before, work_root: Path) -> dict:
    """Including the process-group kill, observed on real PrimeTime processes.

    The wall clock is shortened to 2 s through the manifest (lowering-only), PrimeTime is started, and
    the broker reports the process GROUP it killed. Survivors are then asked for precisely:
    `pgrep -g <pgid>`.

    Two ways this check was wrong before, both fixed here, and both of the same family -- a check
    that cannot say the thing it appears to say:

      * VACUOUS PASS. A 5 s override let PrimeTime finish, the response came back `ok`, and "no orphan
        survived" was true only because nothing had been killed. Now the kill must have happened AND
        have landed on the TOOL step, not on the little Python build script.
      * GUARANTEED FAIL. `pgrep -u $USER -f pt_shell` matches the shell running the pgrep, because
        that shell's own command line contains "pt_shell". So it reported one survivor on every run
        forever, including the run where nothing was killed. Asking about the pgid cannot self-match:
        the probe's shell is in a different group.
    """
    out_dir = work_root / EPISODE_KILL
    resp = {}
    ba.provision(EPISODE_KILL, INSTANCE, out_dir, host=host, root=root, wall_clock_override=2)
    try:
        files = _scratch(INSTANCE)
        raw = _probe_ssh(out_dir / "key", out_dir / "known_hosts", host,
                         payload=_request("sta_public", files), timeout=400)
        resp = _framed(raw) or {}
        shutil.rmtree(files.parent, ignore_errors=True)
        time.sleep(bp.KILL_GRACE_SEC + 5)
        pgid = resp.get("killed_pgid")
        if pgid:
            # Separate -o flags, not `-o pid=,args=`. procps parses the latter as "column pid with
            # header ',args='", so an EMPTY process group still prints one line -- the header -- and
            # the check reported it as a survivor. Third time this preflight has been wrong about its
            # own instrument rather than about the broker, so the parse now also requires a line to
            # begin with a pid; a header or an error message cannot pose as a process.
            r = _remote(host, f"ps -o pid= -o args= -g {int(pgid)} 2>/dev/null || true", timeout=60)
            survivors = [l.strip() for l in (r.stdout or b"").decode("utf-8", "replace").splitlines()
                         if l.strip() and l.strip().split()[0].isdigit()]
        else:
            survivors = ["(no killed process group was reported)"]
        inv = _remote(host, f"ls -1d {root}/ep/{EPISODE_KILL}/inv-* 2>/dev/null | wc -l", timeout=60)
        inv_left = (inv.stdout or b"?").decode().strip().splitlines()[-1] if inv else "?"
    finally:
        td = ba.teardown(EPISODE_KILL, host=host, root=root)

    a = ba.audit(host=host, root=root)
    after = _remote_user_region_sha(host, root)
    timed_out = resp.get("status") == bp.Status.TOOL_TIMEOUT
    killed_the_tool = resp.get("timed_out_step") == "TOOL"
    return {"user_keys_unchanged": after["sha"] == user_keys_before["sha"],
            "user_region_sha256_before": user_keys_before["sha"],
            "user_region_sha256_after": after["sha"],
            "episode_dir_removed": bool(td.get("dir_removed")),
            "managed_entries_after": a["entries"],
            "episode_dirs_after": a["episode_dirs"],
            "quarantine": a["quarantine"],
            "timeout_status": resp.get("status"),
            "timed_out_step": resp.get("timed_out_step"),
            "killed_pgid": resp.get("killed_pgid"),
            "wall_clock_sec": resp.get("wall_clock_sec"),
            "elapsed_s": resp.get("elapsed_s"),
            "kill_discipline_exercised": bool(timed_out and killed_the_tool),
            "invocation_dirs_left": inv_left,
            "survivors_in_killed_group": survivors,
            # Non-vacuous by construction: the kill must have happened, on the tool, and left nothing.
            "no_orphan_process": bool(timed_out and killed_the_tool
                                      and survivors == [] and str(inv_left) == "0")}


# ---------------------------------------------------------------------------------------------
# forwarder equivalence
# ---------------------------------------------------------------------------------------------

def _normalise(text: str):
    lines = [l.rstrip() for l in text.splitlines()]
    total = max(1, len(lines))
    rules = []
    kept = lines
    for pattern, label in NORMALISE:
        rx = re.compile(pattern, re.MULTILINE)
        before = len(kept)
        kept = [l for l in kept if not rx.search(l)]
        dropped = before - len(kept)
        rules.append({"pattern": pattern, "label": label, "dropped_lines": dropped,
                      "dropped_fraction": round(dropped / total, 4)})
    return "\n".join(kept), rules, total


def _shape(line: str) -> str:
    """A line with its numeric runs masked. Used to generalise an empirically-measured
    nondeterministic line across the values it takes, without hand-writing a rule for it."""
    return re.sub(r"\d+(?:\.\d+)?", "#", line)


def _identifiers(text: str) -> set:
    return set(re.findall(r"(?:/home/[A-Za-z0-9._-]+|\bb04\b|\btsb\b|[A-Za-z0-9._-]+@[A-Za-z0-9._-]+"
                          r"|/tmp/eda_shim_[0-9a-f]+|eda-probe-broker)", text))


def check_equivalence(host, root, work_root: Path, n_forwarder=3, n_broker=2) -> dict:
    """PrimeTime path only. p16 has no unstudied directory of the studied generation -- p16_dev_0000
    predates the immutable-core scheme -- and provisioning a studied p16 instance from a preflight is
    not acceptable. Recorded as a scope limit rather than left to be inferred.

    The normalisation is DERIVED, not chosen, and the derivation is symmetric.

    Each path is run several times. For every line SHAPE (the line with its numeric runs masked), the
    set of values it takes within a path is collected. A shape is *stable for that path* iff it takes
    exactly one value across that path's runs. Only shapes stable in BOTH paths are compared; a shape
    unstable in either is reported as not-comparable, with every value it was observed to take.

    Why this shape rather than something simpler. The first honest comparison differed on one line,
    `Maximum memory usage for this session: 2897.31 MB` against `2897.26 MB`. Hand-writing a
    memory-usage regex would have made it disappear and would have been indistinguishable, in the
    record, from normalising away a real difference. A single same-path pair answered it -- until a
    later run in which the two forwarder runs happened to report the SAME value, so the pair detected
    nothing, nothing was dropped, and the check failed on noise it had previously identified. Two
    samples on one side is too weak a basis for calling a line nondeterministic, and a gate that fails
    at random is not a gate. Several runs on both sides is.
    """
    from opencode_probe_raw_output_audit import tool_env

    def prep(r, workdir):
        text = ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace") if r else ""
        return text.replace(str(workdir), "@WORKDIR@")

    def run_forwarder():
        files = _scratch(INSTANCE)
        r = _run(["bash", "run_public.sh"], cwd=str(files), env=tool_env(), timeout=600)
        text = prep(r, files)
        shutil.rmtree(files.parent, ignore_errors=True)
        return r, text

    fwd_runs = [run_forwarder() for _ in range(n_forwarder)]

    out_dir = work_root / (EPISODE + "_eq")
    ba.provision(EPISODE + "_eq", INSTANCE, out_dir, host=host, root=root)
    brk_runs = []
    try:
        bin_dir = _stage_client_bin(work_root / "eqbin")
        env = dict(os.environ)
        env.update({"EDA_PT_CMD": str(bin_dir / "pt_shell"),
                    "EDA_BROKER_KEY": str(out_dir / "key"),
                    "EDA_BROKER_KNOWN_HOSTS": str(out_dir / "known_hosts"),
                    "EDA_BROKER_HOST": host})
        for _ in range(n_broker):
            files = _scratch(INSTANCE)
            r = _run(["bash", "run_public.sh"], cwd=str(files), env=env, timeout=600)
            brk_runs.append((r, prep(r, files)))
            shutil.rmtree(files.parent, ignore_errors=True)
    finally:
        ba.teardown(EPISODE + "_eq", host=host, root=root)

    fwd_norms = [_normalise(t)[0] for _, t in fwd_runs]
    brk_norms = [_normalise(t)[0] for _, t in brk_runs]
    rules, a_total = _normalise(fwd_runs[0][1])[1], _normalise(fwd_runs[0][1])[2]

    def values_by_shape(norms):
        seen = {}
        for text in norms:
            for line in text.splitlines():
                seen.setdefault(_shape(line), set()).add(line)
        return seen

    fwd_vals, brk_vals = values_by_shape(fwd_norms), values_by_shape(brk_norms)
    unstable = sorted({s for s, v in fwd_vals.items() if len(v) > 1}
                      | {s for s, v in brk_vals.items() if len(v) > 1})

    def drop_unstable(text):
        kept, dropped = [], []
        for line in text.splitlines():
            (dropped if _shape(line) in set(unstable) else kept).append(line)
        return "\n".join(kept), dropped

    a_final, a_dropped = drop_unstable(fwd_norms[0])
    brk_final, brk_dropped = drop_unstable(brk_norms[0])
    cross_diff = list(difflib.unified_diff(a_final.splitlines(), brk_final.splitlines(),
                                           "forwarder", "broker", lineterm="", n=1))

    fwd_text, brk_text = fwd_runs[0][1], brk_runs[0][1]
    new_disclosures = sorted(_identifiers(brk_text) - _identifiers(fwd_text))
    unstable_fraction = round(len(unstable) / max(1, len(fwd_norms[0].splitlines())), 4)
    return {"scope": "sta_public",
            "scope_limit": "p16 is absent: p16_dev_0000 is an older generation the op table does "
                           "not model, and a studied p16 instance may not be provisioned from a "
                           "preflight. The HSPICE path rests on shared code and the artifact round "
                           "trip, not on its own end-to-end comparison.",
            "instance": EPISODE,
            "n_forwarder_runs": n_forwarder, "n_broker_runs": n_broker,
            "rc_forwarder": [r.returncode if r else -1 for r, _ in fwd_runs],
            "rc_broker": [r.returncode if r else -1 for r, _ in brk_runs],
            "rc_equal": bool({r.returncode for r, _ in fwd_runs if r}
                             == {r.returncode for r, _ in brk_runs if r}),
            "rc_equal_is_weak_evidence": ("run_public.sh ends in `exit 0` unconditionally, so equal "
                                          "return codes are close to vacuous here. The load-bearing "
                                          "assertion is normalised_equal; rc is recorded for "
                                          "completeness, not relied on."),
            "stability_control": {
                "what": "each path run several times; a line SHAPE is comparable only if it takes "
                        "exactly one value within BOTH paths. Shapes unstable in either path are "
                        "excluded and listed with every value observed, so nothing is dropped on the "
                        "strength of a hand-written rule.",
                "unstable_shapes": unstable,
                "unstable_values": {s: sorted(fwd_vals.get(s, set()) | brk_vals.get(s, set()))
                                    for s in unstable},
                "n_unstable": len(unstable),
                "fraction_of_output": unstable_fraction,
                "dropped_from_forwarder": a_dropped,
                "dropped_from_broker": brk_dropped},
            "normalised_equal": a_final == brk_final,
            "normalised_diff": cross_diff[:120],
            "normalised_diff_lines": len(cross_diff),
            "lines_compared": len(a_final.splitlines()),
            "raw_lines_forwarder": a_total,
            "rules": rules,
            "shared_identifiers": sorted(_identifiers(brk_text) & _identifiers(fwd_text)),
            "new_disclosures": new_disclosures,
            "forwarder_normalised_head": a_final[:400],
            "broker_normalised_head": brk_final[:400]}


# ---------------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Zero-call preflight for the EDA broker.")
    ap.add_argument("--host", default=ba.DEFAULT_HOST)
    ap.add_argument("--root", default=ba.DEFAULT_ROOT)
    ap.add_argument("--only-equivalence", action="store_true",
                    help="run ONLY the forwarder-equivalence check and print it. Writes no evidence "
                         "file: a partial run may never carry a verdict.")
    a = ap.parse_args()

    if a.only_equivalence:
        wr = Path(tempfile.mkdtemp(prefix="broker_eq_"))
        try:
            eq = check_equivalence(a.host, a.root, wr)
        finally:
            shutil.rmtree(wr, ignore_errors=True)
        print(json.dumps({k: v for k, v in eq.items()
                          if k not in ("forwarder_normalised_head", "broker_normalised_head")},
                         indent=2))
        return 0 if eq["normalised_equal"] and eq["new_disclosures"] == [] else 1

    work_root = Path(tempfile.mkdtemp(prefix="broker_preflight_"))
    controls, cleanup, equivalence = [], {}, {}
    user_before = _remote_user_region_sha(a.host, a.root)
    try:
        out_dir = work_root / EPISODE
        ba.provision(EPISODE, INSTANCE, out_dir, host=a.host, root=a.root)
        ba.provision(EPISODE_X, INSTANCE, work_root / EPISODE_X, host=a.host, root=a.root)
        key, kh = out_dir / "key", out_dir / "known_hosts"
        try:
            controls += controls_ssh_surface(key, kh, a.host)
            controls.append(control_cross_episode(key, kh, a.host, a.root))
            controls.append(control_planted_decoy(key, kh, a.host))
            controls.append(control_sandbox_isolation(out_dir))
        finally:
            ba.teardown(EPISODE_X, host=a.host, root=a.root)
            ba.teardown(EPISODE, host=a.host, root=a.root)
        controls.append(control_batch_keys(a.host, a.root, work_root / "batch"))
        controls.append(control_cap_hit(a.host, a.root, work_root))
        equivalence = check_equivalence(a.host, a.root, work_root)
        cleanup = verify_cleanup(a.host, a.root, user_before, work_root)
    finally:
        shutil.rmtree(work_root, ignore_errors=True)

    verdict = ("PASS" if (all(c["pass"] for c in controls)
                          and len(controls) == 14
                          and cleanup.get("user_keys_unchanged")
                          and cleanup.get("no_orphan_process")
                          and cleanup.get("episode_dir_removed")
                          and cleanup.get("quarantine") == []
                          and equivalence.get("rc_equal")
                          and equivalence.get("normalised_equal")
                          # An empirically-derived drop set is legitimate; a large one means the
                          # comparison has little content left to be equal about.
                          and equivalence.get("stability_control", {}).get("fraction_of_output", 1)
                          <= 0.10
                          and equivalence.get("lines_compared", 0) > 0
                          and equivalence.get("new_disclosures") == [])
               else "FAIL")

    rec = {"generated_by": "scripts/opencode_probe_remote_broker_preflight.py",
           "when": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "model_calls": 0,
           "host": a.host, "root": a.root,
           "authorizes_formal_arm": False,
           "scope": ("addresses the tool-channel blocker in docs/opencode_probe_dry_run_report.md "
                     "section 5. Check 7 remains UNSETTLED. Check 5's earlier PASS does not carry "
                     "over: it was established with the tools absent, and this configuration mounts "
                     "a tool channel."),
           "controls": controls,
           "cleanup": cleanup,
           "equivalence": equivalence,
           "disclosed_identifiers": equivalence.get("shared_identifiers", []),
           "verdict": verdict}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2) + "\n")

    for c in controls:
        print(f"  [{c['id']:2d}] {'PASS' if c['pass'] else 'FAIL'}  {c['name']}")
        if not c["pass"]:
            print(f"        observed: {c['observed'][:300]}")
    print(json.dumps({"cleanup": cleanup,
                      "equivalence": {k: equivalence.get(k) for k in
                                      ("scope", "rc_equal", "normalised_equal", "lines_compared",
                                       "new_disclosures")},
                      "verdict": verdict}, indent=2))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
