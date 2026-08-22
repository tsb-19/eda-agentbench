"""Guards on the OpenCode remote EDA broker.

The broker is a capability, not a channel: the agent is given two named operations and no way to
express anything else. These tests hold the properties that make that true and that keep an
infrastructure fault from being recorded as model behaviour.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

AUDIT = REPO / "opencode_probe/evidence/raw_output_audit.json"


@pytest.mark.skipif(not AUDIT.is_file(), reason="headroom calibration not yet run (Task 1)")
def test_the_transport_caps_have_measured_headroom_over_the_complete_calibration_set():
    """The cap must be justified against MEASURED raw output.

    `64 KiB / 4000 B = 16x` is not evidence: 4000 bytes is how much the model sees in one
    observation, and the transport cap is how much the broker may return at all. The frozen runner
    lets an agent redirect a large output to a file and paginate it back, so a transport cap below
    the real output size would make the probe's action surface WEAKER than the control's.
    """
    a = json.loads(AUDIT.read_text())
    assert a["n_tool_ran"] >= 1, "audit recorded no instance where the tool actually ran"
    caps = a["caps"]
    assert a["max_stdout_bytes"] * 8 <= caps["stdout_bytes"], (
        f"stdout cap {caps['stdout_bytes']} leaves under 8x headroom over the measured maximum "
        f"{a['max_stdout_bytes']}")
    assert a["max_stderr_bytes"] * 8 <= caps["stderr_bytes"]
    assert a["max_artifact_bytes"] * 8 <= caps["artifact_bytes"]
    assert a["max_request_upper_bound_bytes"] * 8 <= caps["request_bytes"]
    assert a["verdict"] == "HEADROOM_ESTABLISHED"


@pytest.mark.skipif(not AUDIT.is_file(), reason="headroom calibration not yet run (Task 1)")
def test_the_calibration_covered_every_directory_the_formal_panel_would_use():
    """A maximum over whichever instances happened to run is the same defect as an aggregate over
    whichever episodes happened to finish. Stage 1 is 12 instances x 2 conditions = 24 directories;
    all 24 must be measured and all 24 must have actually launched the tool."""
    a = json.loads(AUDIT.read_text())
    panel = a["formal_panel"]
    assert panel["missing"] == [], f"formal-panel directories never measured: {panel['missing']}"
    assert len(panel["expected"]) == 24, f"expected 24 formal directories, got {panel['expected']}"
    assert panel["complete"] is True
    assert a["complete"] is True, "a --limit run may not carry a verdict"
    by_name = {r["instance"]: r for r in a["instances"]}
    not_run = [n for n in panel["expected"] if not by_name[n]["tool_ran"]]
    assert not_run == [], f"the tool never ran for: {not_run}"


@pytest.mark.skipif(not AUDIT.is_file(), reason="headroom calibration not yet run (Task 1)")
def test_the_audit_does_not_claim_the_caps_can_never_bind():
    """Headroom over a finite calibration set is not a proof about every future invocation. The
    record has to say so itself, because the record is what a later reader will quote."""
    a = json.loads(AUDIT.read_text())
    assert "headroom" in a["claim"].lower()
    assert a["not_claimed"], "the record must state what it does not establish"
    assert "never bind" in a["not_claimed"].lower(), \
        "the disclaimer must name the thing being disclaimed, not gesture at it"
    # Scanned with `not_claimed` removed: that field's whole job is to contain these phrases as
    # negations, so including it here would forbid the record from disclaiming anything.
    scanned = {k: v for k, v in a.items() if k != "not_claimed"}
    blob = json.dumps(scanned).lower()
    for overclaim in ("non_binding", "never bind", "cannot exceed", "proves the cap"):
        assert overclaim not in blob, f"the record overclaims: {overclaim!r}"


# --------------------------------------------------------------------------------------------
# Task 2 -- protocol
# --------------------------------------------------------------------------------------------

def _proto():
    from eda_broker import broker_protocol as bp
    return bp


def test_episode_id_grammar_is_closed():
    bp = _proto()
    for good in ("p15_eval_0004", "p16_eval_0001", "p15_dev_0000", "a.b-c_1",
                 "p15_eval_0004__BundleS__rep1"):
        assert bp.valid_episode_id(good)
    for bad in ("", "a" * 65, "p15 eval", "p15/eval", "../etc", "p15;rm -rf /", "p15\n0005",
                "$(id)", "`id`", "p15|cat"):
        assert not bp.valid_episode_id(bad), f"{bad!r} must not be a legal episode id"


def test_the_op_table_covers_both_families_and_pins_the_canonical_argv():
    bp = _proto()
    assert set(bp.OPS) == {"sta_public", "spice_public"}
    assert bp.OP_BY_SHIM == {"pt_shell": "sta_public", "hspice": "spice_public"}
    assert bp.OPS["sta_public"].client_argv == ("-f", "run_public.tcl")
    assert bp.OPS["spice_public"].client_argv == ("-i", "circuit_built.sp", "-o", "hspice_run")
    assert bp.OPS["spice_public"].artifacts == ("hspice_run.lis",)
    assert bp.OPS["sta_public"].artifacts == ()


def test_build_scripts_and_their_inputs_are_canonical_not_editable():
    """OpenCode's `edit` tool can write ANY workspace file, and the frozen anti-cheat only
    hash-checks metadata's `forbidden` list. For p15 that list is
    ["design.v", "constraints.sdc", "run_public.sh", "run_public.tcl", "tiny.db", "tiny.lib", ...] --
    it EXCLUDES build_applied_sdc.py, partition_pins.json and intent_exception.json, all three of
    which build_applied_sdc.py reads and all three of which change the real PrimeTime feedback. So a
    modified partition_pins.json would alter the tool signal and pass anti-cheat. The broker refuses
    it at execution time. (p16's forbidden list is complete by comparison; the broker pins both
    families the same way regardless, because "the grader happens to forbid it" is not the same
    guarantee as "the tool cannot be given it".)
    """
    bp = _proto()
    sta = bp.OPS["sta_public"]
    assert sta.editable == ("exception_config.json",)
    for f in ("run_public.tcl", "build_applied_sdc.py", "partition_pins.json",
              "intent_exception.json", "constraints.sdc", "design.v", "tiny.db"):
        assert f in sta.canonical, f"{f} must be hash-pinned, not agent-supplied"
    assert "tiny.lib" not in sta.canonical, \
        "run_public.tcl links against tiny.db only; tiny.lib is not a tool input"
    assert sta.generated == ("agent_applied.sdc",)
    spice = bp.OPS["spice_public"]
    assert spice.editable == ("meas_config.json",)
    for f in ("build_deck.py", "circuit_core.sp", "corner_models.json", "load_models.json"):
        assert f in spice.canonical, f"{f} must be hash-pinned, not agent-supplied"
    assert "parse_measure.py" not in spice.canonical, \
        "parse_measure.py runs locally on the returned .lis and is not a remote input"
    assert spice.generated == ("circuit_built.sp",)


def test_the_op_input_sets_match_the_real_task_directories():
    """The op table is a claim about what the tool reads. Checked against the canonical tasks, so a
    drift in either direction -- a file the broker would refuse to ship, or one it would ship that
    the task does not have -- fails here rather than at the first remote invocation."""
    bp = _proto()
    for op_name, inst in (("sta_public", "tasks/p15_sta_handoff/p15_eval_0004_base"),
                          ("spice_public", "tasks/p16_spice_handoff/p16_eval_0001_base")):
        files = REPO / inst / "files"
        for name in bp.input_names(bp.OPS[op_name]):
            assert (files / name).is_file(), f"{op_name}: {name} is not in {inst}/files/"
        for name in bp.OPS[op_name].generated:
            assert not (files / name).exists(), \
                f"{op_name}: {name} is generated and must not ship in the task"


def test_a_generated_file_is_never_an_accepted_input():
    """The agent could otherwise hand over an agent_applied.sdc it wrote itself and inject
    arbitrary SDC into the public feedback loop."""
    bp = _proto()
    for op in bp.OPS.values():
        assert not (set(op.generated) & set(bp.input_names(op)))


def test_the_input_key_set_must_be_exactly_the_ops_set():
    bp = _proto()
    op = bp.OPS["sta_public"]
    full = {n: "" for n in bp.input_names(op)}

    def req(inputs):
        return {"op": "sta_public", "inputs": inputs}

    assert bp.validate_request(req(dict(full))) is op

    with pytest.raises(bp.Refusal) as e:      # superset
        bp.validate_request(req({**full, "extra.txt": ""}))
    assert e.value.reason == "INPUT_SET_MISMATCH"

    missing = dict(full); missing.pop("design.v")
    with pytest.raises(bp.Refusal) as e:      # subset
        bp.validate_request(req(missing))
    assert e.value.reason == "INPUT_SET_MISMATCH"


def test_no_input_name_can_express_a_path():
    bp = _proto()
    op = bp.OPS["sta_public"]
    for hostile in ("../etc/passwd", "/etc/passwd", "a/b", "..", ".",
                    "hidden/signoff_intent_truth.json", "x\x00y"):
        inputs = {n: "" for n in bp.input_names(op)}
        inputs.pop(sorted(inputs)[0])
        inputs[hostile] = ""
        with pytest.raises(bp.Refusal):
            bp.validate_request({"op": "sta_public", "inputs": inputs})


def test_unknown_op_is_refused():
    bp = _proto()
    for bad in ("ls", "", "sta_hidden", "run_hidden", None, 7):
        with pytest.raises(bp.Refusal) as e:
            bp.validate_request({"op": bad, "inputs": {}})
        assert e.value.reason == "UNKNOWN_OP"


def test_framing_round_trips_and_rejects_a_polluted_prefix():
    """b04's login shell emits a banner and an rc error on stderr. stdout is clean today, but a
    silently-absorbed prefix would corrupt JSON parsing into an unexplained broker error rather
    than a typed transport failure. Framing makes pollution detectable."""
    bp = _proto()
    payload = {"op": "sta_public", "rc": 0, "stdout": "x" * 100}
    raw = bp.frame(payload)
    assert raw.startswith(bp.MAGIC.encode())
    assert bp.unframe(raw) == payload
    with pytest.raises(bp.Refusal) as e:
        bp.unframe(b"bash: lsof: command not found\n" + raw)
    assert e.value.reason == "FRAMING"
    with pytest.raises(bp.Refusal):
        bp.unframe(raw[:-3])          # truncated body


def test_caps_come_from_the_measured_audit_record():
    bp = _proto()
    audit = json.loads(AUDIT.read_text())
    assert bp.CAPS == audit["caps"]


# --------------------------------------------------------------------------------------------
# Task 3 -- authorized_keys managed block
# --------------------------------------------------------------------------------------------

import os
import socket
import time

USER_KEYS = (
    "ssh-rsa AAAAB3NzaC1yc2ELAPTOP operator@laptop\n"
    "ssh-ed25519 AAAAC3NzaC1lZDI1WORKSTATION operator@workstation\n"
    "ssh-ed25519 AAAAC3NzaC1lZDI1BUILDBOT buildbot\n"
)

# The formal arm: 12 instances x 2 conditions x k=2. Requirement E is about this count.
FORMAL_EPISODES = tuple(f"p15_eval_{i:04d}__{c}__rep{k}"
                        for i in range(4, 16) for c in ("Base", "BundleS") for k in (0, 1))


def _akb():
    from eda_broker import authorized_keys_block as akb
    return akb


def _line(akb, ep):
    return (f'restrict,command="/home/tsb/eda-probe-broker/broker.sh {ep}" '
            f'ssh-ed25519 AAAAKEYFOR{ep} probe-{ep}')


def test_user_keys_survive_add_and_remove(tmp_path):
    akb = _akb()
    ak = tmp_path / "authorized_keys"
    ak.write_text(USER_KEYS)
    akb.add_entry(ak, "p15_eval_0004", _line(akb, "p15_eval_0004"))
    akb.add_entry(ak, "p15_eval_0005", _line(akb, "p15_eval_0005"))
    akb.remove_entry(ak, "p15_eval_0004")
    akb.remove_entry(ak, "p15_eval_0005")
    assert ak.read_text() == USER_KEYS, "the managed block must leave the user's own keys byte-identical"


def test_concurrent_episodes_coexist_and_teardown_is_surgical(tmp_path):
    akb = _akb()
    ak = tmp_path / "authorized_keys"
    ak.write_text(USER_KEYS)
    for ep in ("p15_eval_0004", "p15_eval_0005", "p15_eval_0006"):
        akb.add_entry(ak, ep, _line(akb, ep))
    assert {e["episode"] for e in akb.list_entries(ak)} == {"p15_eval_0004", "p15_eval_0005", "p15_eval_0006"}
    akb.remove_entry(ak, "p15_eval_0005")
    assert {e["episode"] for e in akb.list_entries(ak)} == {"p15_eval_0004", "p15_eval_0006"}
    assert "AAAAKEYFORp15_eval_0005" not in ak.read_text()
    assert "AAAAKEYFORp15_eval_0004" in ak.read_text()


def test_reap_removes_only_dead_probe_entries(tmp_path):
    akb = _akb()
    ak = tmp_path / "authorized_keys"
    ak.write_text(USER_KEYS)
    for ep in ("p15_eval_0004", "p15_eval_0005"):
        akb.add_entry(ak, ep, _line(akb, ep))
    removed = akb.reap(ak, live={"p15_eval_0004"})
    assert removed == ["p15_eval_0005"]
    assert {e["episode"] for e in akb.list_entries(ak)} == {"p15_eval_0004"}
    assert USER_KEYS.splitlines()[0] in ak.read_text()


def test_a_crash_between_write_and_rename_cannot_truncate_the_file(tmp_path, monkeypatch):
    akb = _akb()
    ak = tmp_path / "authorized_keys"
    ak.write_text(USER_KEYS)
    akb.add_entry(ak, "p15_eval_0004", _line(akb, "p15_eval_0004"))
    original = ak.read_text()

    def boom(*a, **k):
        raise OSError("simulated crash before rename")

    monkeypatch.setattr(akb.os, "replace", boom)
    with pytest.raises(OSError):
        akb.add_entry(ak, "p15_eval_0005", _line(akb, "p15_eval_0005"))
    assert ak.read_text() == original, "a failed mutation must leave the previous file intact"
    assert not list(tmp_path.glob("*.tmp*")), "temp files must not be left behind"


def test_an_illegal_episode_id_never_reaches_authorized_keys(tmp_path):
    akb = _akb()
    ak = tmp_path / "authorized_keys"
    ak.write_text(USER_KEYS)
    for bad in ("p15 eval", 'x" command="/bin/sh', "p15\nssh-rsa AAAA", "../p15", "a" * 65):
        with pytest.raises(ValueError):
            akb.add_entry(ak, bad, "ssh-ed25519 AAAA x")
    assert ak.read_text() == USER_KEYS


# --- requirement G: the mutex ---------------------------------------------------------------

def _own(lock, *, host, pid, t, nonce="foreign"):
    lock.mkdir(parents=True, exist_ok=True)
    (lock / "owner").write_text(json.dumps(
        {"owner_host": host, "owner_pid": pid, "owner_nonce": nonce,
         "created_at": t, "heartbeat": t}))


def test_the_mutex_serialises(tmp_path):
    akb = _akb()
    lock = tmp_path / "lock.d"
    with akb.Mutex(lock, stale_sec=900):
        with pytest.raises(akb.LockBusy):
            with akb.Mutex(lock, stale_sec=900, wait_sec=0):
                pass
    with akb.Mutex(lock, stale_sec=900):
        pass                      # released cleanly, so re-acquirable
    assert not lock.exists()


def test_age_alone_never_breaks_a_lock(tmp_path):
    """The race this forbids: A is alive but slow, B decides A is stale on the clock alone, B
    deletes the lock, and A and B then rewrite authorized_keys concurrently."""
    akb = _akb()
    lock = tmp_path / "lock.d"
    _own(lock, host=socket.gethostname(), pid=os.getpid(), t=0.0)   # ancient, but THIS live process
    with pytest.raises(akb.LockBusy):
        with akb.Mutex(lock, stale_sec=1, wait_sec=0):
            pass
    assert (lock / "owner").is_file(), "a live owner's lock must still be there"


def test_a_fresh_lock_is_not_broken_even_when_the_owner_is_verifiably_dead(tmp_path):
    akb = _akb()
    lock = tmp_path / "lock.d"
    _own(lock, host=socket.gethostname(), pid=2 ** 22 - 1, t=time.time())
    with pytest.raises(akb.LockBusy):
        with akb.Mutex(lock, stale_sec=900, wait_sec=0):
            pass


def test_a_stale_and_verifiably_dead_local_owner_is_broken(tmp_path):
    akb = _akb()
    lock = tmp_path / "lock.d"
    _own(lock, host=socket.gethostname(), pid=2 ** 22 - 1, t=0.0)
    with akb.Mutex(lock, stale_sec=1, wait_sec=0):
        pass
    assert not lock.exists()


def test_an_unverifiable_stale_owner_is_quarantined_rather_than_deleted(tmp_path):
    """A lock owned by another host cannot be proved dead from here. Renaming it aside is atomic,
    so exactly one breaker wins; and if the old owner was in fact alive, its own release will find
    a foreign nonce and remove nothing."""
    akb = _akb()
    lock = tmp_path / "lock.d"
    _own(lock, host="some-other-host", pid=4242, t=0.0)
    with akb.Mutex(lock, stale_sec=1, wait_sec=0):
        pass
    q = akb.list_quarantine(lock)
    assert len(q) == 1, f"the broken lock must be preserved for audit, got {q}"
    rec = json.loads((q[0] / "owner").read_text())
    assert rec["owner_host"] == "some-other-host"


def test_a_release_never_removes_a_lock_it_no_longer_owns(tmp_path):
    """The other half of quarantine safety. If our lock was broken while we held it, the directory
    now belongs to someone else and our __exit__ must not free it."""
    akb = _akb()
    lock = tmp_path / "lock.d"
    m = akb.Mutex(lock, stale_sec=900)
    m.__enter__()
    _own(lock, host="thief", pid=1, t=time.time(), nonce="not-ours")
    m.__exit__(None, None, None)
    assert lock.exists() and json.loads((lock / "owner").read_text())["owner_nonce"] == "not-ours"
    assert m.broken_by_other is True


def test_the_owner_record_carries_everything_the_stale_rule_needs(tmp_path):
    akb = _akb()
    lock = tmp_path / "lock.d"
    with akb.Mutex(lock) as m:
        rec = json.loads((lock / "owner").read_text())
        assert set(rec) >= {"owner_host", "owner_pid", "owner_nonce", "created_at", "heartbeat"}
        assert rec["owner_pid"] == os.getpid()
        assert rec["owner_host"] == socket.gethostname()
        assert rec["owner_nonce"] == m.nonce and len(m.nonce) >= 16
        first = rec["heartbeat"]
        time.sleep(0.01)
        m.touch()
        assert json.loads((lock / "owner").read_text())["heartbeat"] > first


# --- requirement E: batch provisioning ------------------------------------------------------

def test_the_whole_formal_arm_installs_in_one_rewrite_under_one_lock(tmp_path, monkeypatch):
    """Requirement E. 48 rewrites of a file on NFS is 48 chances to lose the operator's login keys;
    the property the arm needs (holding episode i's key implies you can only run episode i) lives in
    each line's command=, not in when the line was written."""
    akb = _akb()
    ak = tmp_path / "authorized_keys"
    ak.write_text(USER_KEYS)

    rewrites, acquires = [], []
    real_write, real_mkdir = akb._atomic_write, akb.os.mkdir
    monkeypatch.setattr(akb, "_atomic_write",
                        lambda p, t: (rewrites.append(p), real_write(p, t))[1])
    monkeypatch.setattr(akb.os, "mkdir",
                        lambda p, *a, **k: (acquires.append(p), real_mkdir(p, *a, **k))[1])

    n = akb.add_entries(ak, [(ep, _line(akb, ep)) for ep in FORMAL_EPISODES])
    assert n == 48
    assert len(rewrites) == 1, f"expected exactly one atomic rewrite, got {len(rewrites)}"
    assert len(acquires) == 1, f"expected exactly one lock acquisition, got {len(acquires)}"
    assert len(akb.list_entries(ak)) == 48


def test_a_batch_install_and_teardown_leave_the_user_keys_byte_identical(tmp_path):
    akb = _akb()
    ak = tmp_path / "authorized_keys"
    ak.write_text(USER_KEYS)
    akb.add_entries(ak, [(ep, _line(akb, ep)) for ep in FORMAL_EPISODES])
    assert ak.read_text().startswith(USER_KEYS)
    removed = akb.remove_entries(ak, list(FORMAL_EPISODES))
    assert sorted(removed) == sorted(FORMAL_EPISODES)
    assert ak.read_text() == USER_KEYS, "batch teardown must restore the file byte-for-byte"


def test_every_batch_line_forces_only_its_own_episode(tmp_path):
    """K_i => E_i, checked line by line on the installed file rather than assumed from the API."""
    akb = _akb()
    ak = tmp_path / "authorized_keys"
    ak.write_text(USER_KEYS)
    akb.add_entries(ak, [(ep, _line(akb, ep)) for ep in FORMAL_EPISODES])
    for e in akb.list_entries(ak):
        forced = [ep for ep in FORMAL_EPISODES if f'broker.sh {ep}"' in e["line"]]
        assert forced == [e["episode"]], f"{e['episode']}: line forces {forced}"


def test_a_batch_that_fails_validation_writes_nothing(tmp_path):
    akb = _akb()
    ak = tmp_path / "authorized_keys"
    ak.write_text(USER_KEYS)
    good = [(ep, _line(akb, ep)) for ep in FORMAL_EPISODES[:4]]
    for bad in (("p15 eval", "ssh-ed25519 AAAA x"),
                ("p15_ok", "ssh-ed25519 AAAA x\nssh-rsa BBBB y"),
                ("a" * 65, "ssh-ed25519 AAAA x")):
        with pytest.raises(ValueError):
            akb.add_entries(ak, good + [bad])
        assert ak.read_text() == USER_KEYS, "validation must precede the single rewrite"


def test_a_duplicate_episode_in_a_batch_is_refused(tmp_path):
    """Two keys for one episode is not a harmless redundancy: teardown-by-episode would leave one
    of them behind, and the leftover is a live capability nobody is holding."""
    akb = _akb()
    ak = tmp_path / "authorized_keys"
    ak.write_text(USER_KEYS)
    ep = FORMAL_EPISODES[0]
    with pytest.raises(ValueError):
        akb.add_entries(ak, [(ep, _line(akb, ep)), (ep, _line(akb, ep) + "2")])
    assert ak.read_text() == USER_KEYS


# --------------------------------------------------------------------------------------------
# Task 4 -- the remote broker
# --------------------------------------------------------------------------------------------

import base64
import hashlib
import signal
import subprocess


def _rb():
    from eda_broker import remote_broker as rb
    return rb


def test_ssh_original_command_is_never_consulted():
    """A forced command that parses SSH_ORIGINAL_COMMAND has re-created the arbitrary-command
    channel and put a filter in front of it. Every such filter is one quoting bug from a bypass.

    Checked against the AST rather than by counting lines: every occurrence of the name must be the
    argument of a `pop`, i.e. a deletion. There are legitimately two -- the process environment on
    entry, and the login environment handed to children -- and a line count of "exactly one" would
    fail a correct implementation while still passing a `os.environ.get(...)` hidden in a comment.
    """
    import ast

    src = (REPO / "scripts/eda_broker/remote_broker.py").read_text()
    tree = ast.parse(src)
    NAME = "SSH_ORIGINAL_COMMAND"

    def is_name(node):
        return isinstance(node, ast.Constant) and node.value == NAME

    deletions = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("pop", "__delitem__")
                and node.args and is_name(node.args[0])):
            deletions.add(id(node.args[0]))

    mentions = [n for n in ast.walk(tree) if is_name(n)]
    assert mentions, "the forced command must still delete SSH_ORIGINAL_COMMAND"
    non_deleting = [n for n in mentions if id(n) not in deletions]
    assert non_deleting == [], (
        f"{NAME} is used at line(s) "
        f"{[n.lineno for n in non_deleting]} in something other than a deletion")
    assert len(deletions) == 2, (
        "expected exactly two deletions -- the process environment and the child login "
        f"environment -- got {len(deletions)}")


def test_a_timeout_kills_the_whole_process_tree(tmp_path):
    """subprocess timeout alone leaves orphan pt_shell descendants holding licences and writing
    into the next episode's workspace. The broker must kill the process GROUP."""
    rb = _rb()
    marker = tmp_path / "child_alive"
    script = tmp_path / "spawn.sh"
    script.write_text(
        "#!/bin/bash\n"
        f"( while true; do touch {marker}; sleep 0.2; done ) &\n"
        "sleep 300\n")
    script.chmod(0o755)
    rc, out, err, timed_out = rb.run_step(
        ["/bin/bash", str(script)], cwd=tmp_path, deadline=time.time() + 2.0, env=dict(os.environ))
    assert timed_out
    if marker.exists():
        marker.unlink()
    time.sleep(1.5)
    assert not marker.exists(), "a descendant survived the timeout and is still running"


def test_the_failure_kinds_are_distinct_statuses():
    """An infrastructure fault may never be recorded as a capability failure. A tool that exits
    nonzero, a tool that overran its wall clock, a broker that could not run at all, a transport
    that broke and an output that exceeded a transport cap are five different facts and must not
    collapse into one."""
    bp = _proto()
    assert len({bp.Status.OK, bp.Status.TOOL_TIMEOUT, bp.Status.REFUSED,
                bp.Status.BROKER_ERROR, bp.Status.TRANSPORT_ERROR,
                bp.Status.TRANSPORT_OUTPUT_LIMIT}) == 6
    assert set(bp.MEASUREMENT_INVALID) == {bp.Status.BROKER_ERROR, bp.Status.TRANSPORT_ERROR,
                                           bp.Status.TRANSPORT_OUTPUT_LIMIT}
    assert bp.Status.OK not in bp.MEASUREMENT_INVALID
    assert bp.Status.TOOL_TIMEOUT not in bp.MEASUREMENT_INVALID, \
        "a tool that overran its own wall clock is a tool fact, not an infrastructure fault"


def test_an_over_cap_output_fails_closed_instead_of_truncating(tmp_path):
    """Requirement F. Task 1's headroom is measured over a finite calibration set, so a future
    invocation may still exceed a cap. When it does, the only safe behaviour is to spend one
    discarded episode -- not to hand the agent a silently shortened observation that the frozen arm
    never had and that no log would distinguish from real tool output."""
    rb, bp = _rb(), _proto()
    small = 1024
    caps = {"stdout_bytes": small, "stderr_bytes": small, "artifact_bytes": small}
    rb.enforce_output_caps(b"x" * small, b"", {}, caps=caps)
    for out, err, arts, kind in ((b"x" * (small + 1), b"", {}, "stdout"),
                                 (b"", b"x" * (small + 1), {}, "stderr"),
                                 (b"", b"", {"hspice_run.lis": b"x" * (small + 1)}, "artifact")):
        with pytest.raises(bp.TransportOutputLimit) as e:
            rb.enforce_output_caps(out, err, arts, caps=caps)
        assert e.value.detail["kind"] == kind
        assert e.value.detail["bytes"] == small + 1
        assert e.value.detail["limit"] == small


def test_a_cap_hit_is_reported_as_measurement_invalid_and_carries_no_output():
    """The response for a cap hit must not contain a partial stdout at all. A caller that receives
    both an error status and 1 MiB of plausible tool text will eventually log the text."""
    rb, bp = _rb(), _proto()
    resp = rb.limit_response(bp.TransportOutputLimit(kind="stdout", bytes=99, limit=98))
    assert resp["status"] == bp.Status.TRANSPORT_OUTPUT_LIMIT
    assert resp["status"] in bp.MEASUREMENT_INVALID
    assert "stdout" not in resp and "stderr" not in resp and "artifacts" not in resp
    assert resp["detail"]["kind"] == "stdout"


def _fake_instance(tmp_path):
    """A minimal sta_public input set with a real, deterministic build script."""
    d = tmp_path / "src"
    d.mkdir()
    (d / "exception_config.json").write_text('{"intent_class": "a", "target_partition": "p"}')
    (d / "build_applied_sdc.py").write_text(
        "open('agent_applied.sdc','w').write('BUILT\\n')\n")
    for n in ("run_public.tcl", "constraints.sdc", "partition_pins.json",
              "intent_exception.json", "design.v", "tiny.db"):
        (d / n).write_text(f"canonical-{n}\n")
    return d


def _inputs_and_manifest(src, op):
    bp = _proto()
    inputs, manifest = {}, {}
    for n in bp.input_names(op):
        b = (src / n).read_bytes()
        inputs[n] = base64.b64encode(b).decode()
        if n in op.canonical:
            manifest[n] = hashlib.sha256(b).hexdigest()
    return inputs, manifest


def test_a_divergent_canonical_file_is_refused_before_anything_crosses(tmp_path):
    rb, bp = _rb(), _proto()
    op = bp.OPS["sta_public"]
    src = _fake_instance(tmp_path)
    inputs, manifest = _inputs_and_manifest(src, op)
    inputs["run_public.tcl"] = base64.b64encode(b"exec /bin/sh\n").decode()
    work = tmp_path / "inv"
    work.mkdir()
    with pytest.raises(bp.Refusal) as e:
        rb.materialise(op, inputs, work, manifest)
    assert e.value.reason == "NON_EDITABLE_DIVERGENCE"
    assert e.value.detail["file"] == "run_public.tcl"
    assert not list(work.iterdir()), "nothing may be written when a request is refused"


def test_the_editable_file_is_accepted_verbatim_and_generated_files_are_not_written(tmp_path):
    rb, bp = _rb(), _proto()
    op = bp.OPS["sta_public"]
    src = _fake_instance(tmp_path)
    inputs, manifest = _inputs_and_manifest(src, op)
    agent_bytes = b'{"intent_class": "CHANGED", "target_partition": "q"}'
    inputs["exception_config.json"] = base64.b64encode(agent_bytes).decode()
    work = tmp_path / "inv"
    work.mkdir()
    rb.materialise(op, inputs, work, manifest)
    assert (work / "exception_config.json").read_bytes() == agent_bytes
    assert not (work / "agent_applied.sdc").exists()
    assert sorted(p.name for p in work.iterdir()) == sorted(bp.input_names(op))


def test_the_remote_workdir_and_home_never_appear_in_a_response(tmp_path):
    """The frozen forwarder rewrote the remote path back to the local one (bin/forwarder step 5).
    Without the same rewrite the agent's observation would name /home/tsb/... -- both a departure
    from the frozen observation and a de-anonymisation trace on a branch that is not anonymised."""
    rb, bp = _rb(), _proto()
    work = tmp_path / "ep" / "inv-1"
    work.mkdir(parents=True)
    home = tmp_path
    text = f"Error: cannot open {work}/design.v\nlogfile in {home}/scratch\n"
    clean = rb.sanitise(text, work, home)
    assert str(work) not in clean
    assert str(home) not in clean
    assert bp.WORKDIR_TOKEN in clean


def test_the_invocation_cap_is_enforced_server_side(tmp_path):
    rb, bp = _rb(), _proto()
    ep = tmp_path / "p15_eval_0004"
    ep.mkdir()
    for _ in range(bp.MAX_INVOCATIONS_PER_EPISODE):
        rb.bump_invocation(ep)
    with pytest.raises(bp.Refusal) as e:
        rb.bump_invocation(ep)
    assert e.value.reason == "INVOCATION_CAP"


def test_an_illegal_episode_id_in_argv_is_refused(tmp_path, capsysbinary):
    """Defence in depth: the host already validated it before writing authorized_keys. The broker
    validates it again, because a forced command is only as trustworthy as whoever wrote the line."""
    rb = _rb()
    assert rb.main(["broker", "../etc"]) != 0
    assert rb.main(["broker"]) != 0
    out = capsysbinary.readouterr().out
    assert b"ILLEGAL_EPISODE_ID" in out, "the refusal must be framed back, not merely returned"


# --------------------------------------------------------------------------------------------
# Task 5 -- the in-sandbox client
# --------------------------------------------------------------------------------------------

def _bc():
    from eda_broker import broker_client as bc
    return bc


def test_the_op_is_selected_by_the_name_the_shim_was_invoked_as():
    bc, bp = _bc(), _proto()
    assert bc.op_for_argv0("/tmp/eda-probe/bin/pt_shell") == "sta_public"
    assert bc.op_for_argv0("hspice") == "spice_public"
    with pytest.raises(bp.Refusal):
        bc.op_for_argv0("/tmp/eda-probe/bin/bash")


def test_unexpected_argv_is_refused_rather_than_ignored():
    """The design says the client ignores its arguments. Ignoring silently would also ignore a
    tampered run_public.sh; asserting the canonical argv turns that into a visible refusal."""
    bc, bp = _bc(), _proto()
    sta = bp.OPS["sta_public"]
    bc.check_argv(sta, ["-f", "run_public.tcl"])
    for bad in (["-f", "evil.tcl"], [], ["-f", "run_public.tcl", "-x"], ["-shell"]):
        with pytest.raises(bp.Refusal) as e:
            bc.check_argv(sta, bad)
        assert e.value.reason == "UNEXPECTED_ARGV"


def test_ssh_is_invoked_so_it_cannot_fall_back_to_another_key_or_host_key(tmp_path):
    bc = _bc()
    argv = bc.ssh_argv(tmp_path / "key", tmp_path / "known_hosts", "tsb@b04")
    joined = " ".join(argv)
    for required in ("IdentitiesOnly=yes", "IdentityAgent=none", "BatchMode=yes",
                     "StrictHostKeyChecking=yes", "ControlMaster=no",
                     f"UserKnownHostsFile={tmp_path / 'known_hosts'}"):
        assert required in joined, f"missing hardening option: {required}"
    assert "-T" in argv, "no PTY may be requested"


def test_a_transport_failure_is_never_reported_as_a_tool_result(capsys):
    """The project's own rule: an infrastructure timeout, gateway error or worker failure is
    measurement-invalid, never a capability failure. If ssh dies, the client must not print a
    plausible-looking tool log and exit 0."""
    bc, bp = _bc(), _proto()
    rc = bc.emit({"status": bp.Status.TRANSPORT_ERROR, "reason": "ssh exited 255"},
                 cwd=Path("."), out=sys.stdout, err=sys.stderr)
    captured = capsys.readouterr()
    assert rc == 125
    assert captured.out == ""
    assert "MEASUREMENT_INVALID" in captured.err
    assert "transport_error" in captured.err


@pytest.mark.parametrize("status", ["broker_error", "transport_output_limit"])
def test_every_measurement_invalid_status_exits_125_and_prints_no_stdout(status, capsys):
    """Requirement F's client half. A cap hit must reach the runner as an infrastructure fault with
    an empty stdout -- if it arrived as a shortened tool log, nothing downstream could tell it from
    a real one, and the episode would be scored."""
    bc, bp = _bc(), _proto()
    assert status in bp.MEASUREMENT_INVALID
    rc = bc.emit({"status": status, "reason": "output exceeded a transport cap",
                  "detail": {"kind": "stdout", "bytes": 2097152, "limit": 1048576},
                  "stdout": "THIS MUST NOT BE PRINTED"},
                 cwd=Path("."), out=sys.stdout, err=sys.stderr)
    captured = capsys.readouterr()
    assert rc == 125
    assert captured.out == ""
    assert "THIS MUST NOT BE PRINTED" not in captured.err
    assert "MEASUREMENT_INVALID" in captured.err and status in captured.err


def test_the_workdir_token_is_rewritten_to_the_local_cwd(tmp_path, capsys):
    bc, bp = _bc(), _proto()
    rc = bc.emit({"status": bp.Status.OK, "rc": 0, "op": "sta_public",
                  "stdout": f"reading {bp.WORKDIR_TOKEN}/design.v\n", "stderr": "",
                  "artifacts": {}},
                 cwd=tmp_path, out=sys.stdout, err=sys.stderr)
    captured = capsys.readouterr()
    assert rc == 0
    assert f"reading {tmp_path}/design.v" in captured.out
    assert bp.WORKDIR_TOKEN not in captured.out


def test_an_artifact_the_op_does_not_declare_is_not_written(tmp_path, capsys):
    """The broker is trusted for its own table, but the client keeps its own whitelist: a response
    is still a message from the network, and it must not be able to create arbitrary workspace
    files."""
    bc, bp = _bc(), _proto()
    bc.emit({"status": bp.Status.OK, "rc": 0, "op": "spice_public", "stdout": "", "stderr": "",
             "artifacts": {"hspice_run.lis": base64.b64encode(b"REAL").decode(),
                           "run_hidden.sh": base64.b64encode(b"INJECTED").decode()}},
            cwd=tmp_path, out=sys.stdout, err=sys.stderr)
    capsys.readouterr()
    assert (tmp_path / "hspice_run.lis").read_bytes() == b"REAL"
    assert not (tmp_path / "run_hidden.sh").exists(), "an undeclared artifact must be dropped"


def test_the_request_carries_exactly_the_ops_input_set_and_no_generated_file(tmp_path):
    bc, bp = _bc(), _proto()
    op = bp.OPS["sta_public"]
    src = _fake_instance(tmp_path)
    (src / "agent_applied.sdc").write_text("AGENT INJECTED\n")
    req = bc.build_request(op, src)
    assert req["op"] == "sta_public"
    assert set(req["inputs"]) == set(bp.input_names(op))
    assert "agent_applied.sdc" not in req["inputs"]
    assert "episode" not in req and "episode_id" not in req, \
        "the client must have no field in which to name an episode"


# --------------------------------------------------------------------------------------------
# Task 6 -- host-side administration
# --------------------------------------------------------------------------------------------

def _admin():
    from eda_broker import broker_admin as ba
    return ba


def test_the_authorized_keys_line_burns_the_episode_into_the_forced_command():
    ba = _admin()
    line = ba.authorized_keys_line("p15_eval_0004", "ssh-ed25519 AAAAKEY probe",
                                   root="/home/tsb/eda-probe-broker", from_addr="10.0.0.1")
    assert line.startswith("restrict,")
    assert 'command="/home/tsb/eda-probe-broker/broker.sh p15_eval_0004"' in line
    assert 'from="10.0.0.1"' in line
    assert line.endswith("ssh-ed25519 AAAAKEY probe")
    assert "\n" not in line


def test_restrict_is_used_rather_than_an_enumeration_of_the_five_options():
    """`restrict` is default-deny: an option a future OpenSSH adds is denied unless this line opts
    back into it. An enumeration silently gains whatever is invented next."""
    ba = _admin()
    line = ba.authorized_keys_line("p15_eval_0004", "ssh-ed25519 AAAAKEY probe",
                                   root="/r", from_addr=None)
    assert line.split(",")[0] == "restrict"


def test_an_illegal_episode_id_cannot_reach_a_forced_command():
    ba = _admin()
    for bad in ('x" command="/bin/sh', "a b", "../x", "p15\nssh-rsa AAAA", "a" * 65):
        with pytest.raises(ValueError):
            ba.authorized_keys_line(bad, "ssh-ed25519 AAAAKEY probe", root="/r", from_addr=None)


def test_the_manifest_pins_every_canonical_file_and_no_oracle(tmp_path):
    ba, bp = _admin(), _proto()
    inst = REPO / "tasks/p15_sta_handoff/p15_dev_0000"
    m = ba.build_manifest(inst)
    assert m["ops"] == ["sta_public"]
    for n in bp.OPS["sta_public"].canonical:
        assert n in m["sha256"] and len(m["sha256"][n]) == 64
    blob = json.dumps(m)
    for forbidden in ("hidden", "truth", "solution", "oracle", "run_hidden"):
        assert forbidden not in blob, f"the manifest discloses {forbidden!r}"
    for n in bp.OPS["sta_public"].generated:
        assert n not in m["sha256"], "a generated file must never be pinned as an input"


def test_the_manifest_is_built_for_the_right_family(tmp_path):
    ba = _admin()
    m = ba.build_manifest(REPO / "tasks/p16_spice_handoff/p16_eval_0001_base")
    assert m["ops"] == ["spice_public"]
    assert "build_deck.py" in m["sha256"]
    assert "circuit_core.sp" in m["sha256"]


def test_the_p16_dev_instance_is_an_older_generation_and_is_refused_not_guessed_at():
    """p16_dev_0000 predates the immutable-core scheme: its build_deck.py writes circuit_built.sp
    from scratch with no circuit_core.sp, and it ships circuit_built.sp in the task. The op table
    models the STUDIED generation (p16_eval_*), so the dev directory is not serviceable -- and it
    fails loudly at manifest time rather than being silently provisioned with a different input set
    from the one the tool will read.

    This is why the forwarder-equivalence check cannot use p16_dev_0000: there is no unstudied p16
    directory of the studied generation. Recorded here so a later reader does not conclude the
    omission was an oversight.
    """
    ba = _admin()
    dev = REPO / "tasks/p16_spice_handoff/p16_dev_0000"
    assert not (dev / "files/circuit_core.sp").exists()
    assert (dev / "files/circuit_built.sp").exists(), \
        "the older generation ships the deck it builds; the newer one generates it"
    with pytest.raises(SystemExit) as e:
        ba.build_manifest(dev)
    assert "circuit_core.sp" in str(e.value)


# --- requirement E: the batch path ----------------------------------------------------------

def test_the_episode_id_encodes_instance_condition_and_repetition_in_one_token():
    """One token, not three argv fields: the forced command stays `broker.sh <id>` with argv fixed
    at length 2, which is what the illegal-argv guard in Task 4 already holds. K_i => E_i needs the
    episode to be unforgeable by the client, not to be structured."""
    ba, bp = _admin(), _proto()
    ep = ba.episode_id("p15_eval_0004", "BundleS", 1)
    assert ep == "p15_eval_0004__BundleS__rep1"
    assert bp.valid_episode_id(ep)
    for inst, cond, rep in (("p15_eval_0004", "Base", 0), ("p15_eval_0015", "BundleS", 1)):
        assert bp.valid_episode_id(ba.episode_id(inst, cond, rep))
    for bad in (("p15 eval", "Base", 0), ("p15_eval_0004", "Base BundleS", 0),
                ("p15_eval_0004", 'x" command="/bin/sh', 0)):
        with pytest.raises(ValueError):
            ba.episode_id(*bad)


def test_the_formal_arm_plan_is_48_distinct_episodes_over_24_directories():
    """docs/opencode_probe_analysis_plan.md stage 1: 12 instances x {Base, BundleS} x k=2."""
    ba = _admin()
    plan = ba.formal_arm_plan()
    assert len(plan) == 48
    assert len({p["episode"] for p in plan}) == 48, "every episode needs its own key"
    assert len({p["instance"] for p in plan}) == 24, "12 instances x 2 conditions of task directory"
    assert {p["condition"] for p in plan} == {"Base", "BundleS"}
    assert {p["rep"] for p in plan} == {0, 1}
    for p in plan:
        assert (REPO / "tasks/p15_sta_handoff" / p["instance"]).is_dir(), p["instance"]


def test_the_formal_arm_plan_selects_no_instance_on_prior_informativeness():
    """The analysis plan says all twelve of p15_eval_0004..0015, with no selection. Derived from a
    range rather than a literal list, so it cannot quietly become a favourable subset."""
    ba = _admin()
    got = sorted({p["instance_id"] for p in ba.formal_arm_plan()})
    assert got == [f"p15_eval_{i:04d}" for i in range(4, 16)]


def test_a_live_batch_locks_out_per_episode_key_mutation(tmp_path, monkeypatch):
    """The mechanical half of "authorized_keys is static during the arm". A retry loop or a stray
    helper calling provision() mid-arm would silently restore the 48-rewrite behaviour."""
    ba = _admin()
    rec = tmp_path / "batch.json"
    rec.write_text(json.dumps({"batch_id": "b1", "episodes": ["p15_eval_0004__Base__rep0"]}))
    monkeypatch.setattr(ba, "BATCH_RECORD", rec)
    with pytest.raises(ba.BatchActive):
        ba.provision("p15_eval_0004__Base__rep0",
                     REPO / "tasks/p15_sta_handoff/p15_dev_0000", tmp_path / "out")
    with pytest.raises(ba.BatchActive):
        ba.teardown("p15_eval_0004__Base__rep0")
    with pytest.raises(ba.BatchActive):
        ba.provision_batch(ba.formal_arm_plan(), tmp_path / "out")


def test_a_batch_plan_is_validated_before_any_key_is_generated(tmp_path, monkeypatch):
    """Everything that can fail per episode must fail BEFORE the single authorized_keys write, so a
    bad plan leaves zero probe keys authorized rather than a partially-authorized arm."""
    ba = _admin()
    monkeypatch.setattr(ba, "BATCH_RECORD", tmp_path / "absent.json")
    dev = "p15_dev_0000"
    for bad, why in (([{"episode": "p15 eval", "instance": dev}], "illegal id"),
                     ([{"episode": "a__Base__rep0", "instance": dev},
                       {"episode": "a__Base__rep0", "instance": dev}], "duplicate"),
                     ([{"episode": "a__Base__rep0", "instance": "no_such_instance"}], "no instance")):
        with pytest.raises(ValueError):
            ba.validate_batch_plan(bad)
    ok = ba.validate_batch_plan([{"episode": "a__Base__rep0", "instance": dev}])
    assert ok[0]["instance_path"].is_dir()
