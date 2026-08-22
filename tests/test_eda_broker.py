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
