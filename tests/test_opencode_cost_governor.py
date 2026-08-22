"""Guards on the paid dry run's two new instruments: the cost governor and the run's readers.

Every check here exists because the corresponding instrument could otherwise pass while measuring
nothing. That is not a hypothetical in this project: the preflight's launcher test read the
launcher's *source* and so accepted a wrapper that lost argv[0] and would have refused every
episode; its orphan check passed vacuously, then failed universally, then failed on a column header.
So each instrument below is exercised against a known-empty AND a known-nonempty case, and the
governor is additionally required to report honestly on whether it ran live.

No test here makes a model call. The fakes are small Python scripts that emit OpenCode's event-stream
shape, which is what lets the live-cap behaviour be settled before any money is spent.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import opencode_probe_agent as agent               # noqa: E402
import opencode_probe_broker_dry_run as dry        # noqa: E402

REPORT = REPO / "docs/opencode_probe_dry_run_report.md"
PREFLIGHT = REPO / "opencode_probe/evidence/remote_broker_preflight.json"
RUN_PUBLIC_TCL = REPO / "tasks/p15_sta_handoff/p15_dev_0000/files/run_public.tcl"


def _step(input_t=0, output=0, reasoning=0, cache_read=0, cache_write=0, reason="tool-calls"):
    return json.dumps({
        "type": "step_finish", "timestamp": 0,
        "part": {"type": "step-finish", "reason": reason, "cost": 0,
                 "tokens": {"total": input_t + output + reasoning + cache_read,
                            "input": input_t, "output": output, "reasoning": reasoning,
                            "cache": {"read": cache_read, "write": cache_write}}}})


def _governor(cap: float) -> agent.CostGovernor:
    return agent.CostGovernor(cap_cny=cap, rates=agent.Rates.from_arm2(), t0=time.time())


# ---------------------------------------------------------------------------------------------
# the arithmetic
# ---------------------------------------------------------------------------------------------

def test_the_cost_arithmetic_reproduces_the_published_dry_run_figures():
    """Bind the governor's arithmetic to the two figures already published in the dry-run report.

    Both sides are recomputed from committed artifacts: the tokens come out of the committed event
    streams, the target figures out of the committed report table. If either drifts the test fails,
    which is the point -- the report's CNY 6.41 and the governor's cap must be the same currency.
    """
    rates = agent.Rates.from_arm2()
    published = {}
    for line in REPORT.read_text().splitlines():
        if line.startswith("| episode ") and "`" in line:
            cells = [c.strip() for c in line.strip("|").split("|")]
            mode = cells[0].split("`")[1]
            lo, hi = (x.strip() for x in cells[-1].replace("**", "").split("–"))
            published[mode] = (float(lo.replace(" ", "")), float(hi.replace(" ", "")))
    assert set(published) == {"normal", "negctl"}, f"report table not parsed: {published}"

    for mode, want in published.items():
        stream = REPO / f"opencode_probe/evidence/dry_run/{mode}_eventstream.json"
        blob = json.loads(stream.read_text())["stdout"]
        inp = out = rea = 0
        for line in blob.splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if obj.get("type") != "step_finish":
                continue
            i, o, r = agent.billed((obj.get("part") or {}).get("tokens") or {})
            inp += i
            out += o
            rea += r
        assert agent.cost_range(inp, out, rea, rates) == want, mode


def test_cache_reads_are_billed_and_omitting_them_understates_by_an_order_of_magnitude():
    """The specific mistake this guard exists for.

    Summing only `input` and `output` gives CNY 0.58 for the episode the report prices at 6.41,
    because that episode re-read 485 888 cached tokens against 36 311 fresh ones -- an 11x
    understatement. A cap calibrated on the smaller figure would be 11x too loose and would still
    look principled.
    """
    tokens = {"input": 36311, "output": 5869, "reasoning": 3815, "cache": {"read": 485888}}
    inp, out, rea = agent.billed(tokens)
    assert inp == 36311 + 485888
    rates = agent.Rates.from_arm2()
    with_cache = agent.cost_range(inp, out, rea, rates)[0]
    without_cache = agent.cost_range(36311, out, rea, rates)[0]
    assert (with_cache, without_cache) == (6.4072, 0.5766)
    assert with_cache > 10 * without_cache


def test_the_cap_is_enforced_on_the_upper_figure():
    """The gateway reports cost 0 and does not say whether reasoning tokens are billed. A cap must
    assume they are; a spend PROJECTION must assume they are not. Enforcing the lower figure would
    make the cap quietly looser than it claims."""
    g = _governor(cap=1.0)
    g.observe(_step(input_t=0, output=0, reasoning=50_000), time.time())
    lo, hi = g.cost()
    assert lo < 1.0 < hi
    assert g.tripped_at_step == 1
    assert g.record()["enforced_on"] == "upper"


# ---------------------------------------------------------------------------------------------
# tripping and not tripping
# ---------------------------------------------------------------------------------------------

def test_the_governor_trips_on_the_step_that_crosses_the_cap():
    g = _governor(cap=20.0)
    trips = [g.observe(_step(input_t=500_000), time.time()) for _ in range(5)]
    assert trips == [False, False, False, True, False], trips
    assert g.tripped_at_step == 4
    assert g.record()["cap_exceeded"] is True


def test_the_governor_does_not_trip_below_the_cap():
    """The known-negative case. A governor that trips on everything is as useless as one that trips
    on nothing, and only one of the two is visible in a passing run."""
    g = _governor(cap=20.0)
    for _ in range(3):
        assert g.observe(_step(input_t=500_000), time.time()) is False
    assert g.tripped_at_step is None
    assert g.record()["cap_exceeded"] is False
    assert g.cost()[1] == pytest.approx(18.0)


def test_the_governor_ignores_lines_that_are_not_step_records():
    g = _governor(cap=0.001)
    for line in ("", "not json", "[]", json.dumps({"type": "tool_use", "part": {}}),
                 json.dumps({"type": "step_start"})):
        assert g.observe(line, time.time()) is False
    assert g.totals()["requests"] == 0


# ---------------------------------------------------------------------------------------------
# liveness: the governor must report on itself
# ---------------------------------------------------------------------------------------------

FAKE_STREAMING = """\
import json, subprocess, sys, time
sentinel, gap, n = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
subprocess.Popen([sys.executable, "-c",
                  "import time,sys;time.sleep(3);open(sys.argv[1],'w').write('grandchild')",
                  sentinel + ".grandchild"])
for i in range(n):
    time.sleep(gap)
    print(json.dumps({"type": "step_finish",
                      "part": {"type": "step-finish", "reason": "tool-calls", "cost": 0,
                               "tokens": {"input": 500000, "output": 0, "reasoning": 0,
                                          "cache": {"read": 0, "write": 0}}}}), flush=True)
open(sentinel, "w").write("completed")
"""

FAKE_BUFFERED = """\
import json, sys, time
sentinel, n = sys.argv[1], int(sys.argv[2])
lines = [json.dumps({"type": "step_finish",
                     "part": {"type": "step-finish", "reason": "tool-calls", "cost": 0,
                              "tokens": {"input": 500000, "output": 0, "reasoning": 0,
                                         "cache": {"read": 0, "write": 0}}}}) for _ in range(n)]
time.sleep(1.5)
sys.stdout.write("\\n".join(lines) + "\\n")
sys.stdout.flush()
open(sentinel, "w").write("completed")
"""

FAKE_SILENT = """\
import sys, time
time.sleep(120)
open(sys.argv[1], "w").write("completed")
"""


def _fake(tmp_path: Path, source: str, name: str) -> Path:
    p = tmp_path / name
    p.write_text(source)
    return p


def test_the_governor_kills_a_streaming_child_and_says_it_was_live(tmp_path):
    """The case the cap exists for: events arrive one at a time and the run is interrupted.

    Three things are asserted, and the third is what makes this a live cap rather than an audit: the
    child never reached its completion sentinel, the termination reason is the governor, and the
    governor's own liveness record says the token records arrived spread out over the run.
    """
    sentinel = tmp_path / "done"
    fake = _fake(tmp_path, FAKE_STREAMING, "fake_streaming.py")
    g = _governor(cap=20.0)
    run = agent.run_governed([sys.executable, str(fake), str(sentinel), "0.6", "8"],
                             dict(os.environ), 60, g)
    assert not sentinel.exists(), "the child ran to completion, so the cap did not interrupt it"
    assert run["terminated_by"] == "cost_cap_exceeded"
    assert g.tripped_at_step == 4
    live = g.liveness()
    assert live["live"] is True, live
    assert live["arrival_spread_s"] >= 1.0


def test_the_kill_reaches_the_whole_process_group(tmp_path):
    """A tool channel is a chain: bwrap, opencode, bash, run_public.sh, the broker client, an ssh to a
    remote PrimeTime holding a licence. Killing only the top of it leaves the licence checked out, so
    the governor kills the group -- proved by a grandchild that would write a file if it survived."""
    sentinel = tmp_path / "done"
    fake = _fake(tmp_path, FAKE_STREAMING, "fake_streaming.py")
    agent.run_governed([sys.executable, str(fake), str(sentinel), "0.2", "8"],
                       dict(os.environ), 60, _governor(cap=20.0))
    time.sleep(4)
    assert not Path(str(sentinel) + ".grandchild").exists(), "a grandchild survived the group kill"


def test_the_governor_admits_when_it_was_not_live(tmp_path):
    """If OpenCode ever buffers its stdout the cap degenerates into a post-hoc audit. That must be
    reported rather than absorbed: `live` false is the signal that the wall clock was the only real
    bound, and it is the difference between a cap and a claim about one."""
    sentinel = tmp_path / "done"
    fake = _fake(tmp_path, FAKE_BUFFERED, "fake_buffered.py")
    g = _governor(cap=20.0)
    run = agent.run_governed([sys.executable, str(fake), str(sentinel), "8"],
                             dict(os.environ), 60, g)
    assert g.tripped_at_step == 4, "the totals must still be right when the stream is buffered"
    assert g.liveness()["live"] is False, g.liveness()
    assert run["terminated_by"] == "cost_cap_exceeded"


def test_the_wall_clock_bounds_a_child_that_emits_nothing(tmp_path):
    """The second bound, and the one that needs nothing from OpenCode at all. A model that stops
    responding mid-request produces no events, so the governor cannot see it; the watchdog can."""
    sentinel = tmp_path / "done"
    fake = _fake(tmp_path, FAKE_SILENT, "fake_silent.py")
    t0 = time.time()
    run = agent.run_governed([sys.executable, str(fake), str(sentinel)],
                             dict(os.environ), 2, _governor(cap=20.0))
    assert run["terminated_by"] == "wall_clock"
    assert time.time() - t0 < 60
    assert not sentinel.exists()


def test_a_cap_breach_is_measurement_invalid_not_a_short_episode(tmp_path):
    """Fail-closed, in the same sense as the broker's transport_output_limit: the wrapper reports a
    distinct exit code and a MEASUREMENT_INVALID marker, so a killed episode cannot be read as a model
    that finished early."""
    src = (REPO / "scripts/opencode_probe_agent.py").read_text()
    assert "EXIT_COST_CAP = 121" in src
    assert 'MEASUREMENT_INVALID cost_cap_exceeded' in src
    assert 'MEASUREMENT_INVALID wall_clock' in src
    assert "return EXIT_COST_CAP" in src and "return EXIT_WALL_CLOCK" in src


# ---------------------------------------------------------------------------------------------
# the request ledger
# ---------------------------------------------------------------------------------------------

def test_the_ledger_distinguishes_an_empty_scan_from_a_clean_one(tmp_path):
    """A scan that finds no session storage must not read as "only the pinned model". The driver's
    gate therefore carries `ledger_actually_read_something` as a condition of its own."""
    empty = agent.session_ledger(tmp_path)
    assert empty["json_files_scanned"] == 0
    assert empty["model_ids_anywhere"] == {}
    src = (REPO / "scripts/opencode_probe_broker_dry_run.py").read_text()
    assert "ledger_actually_read_something" in src
    assert "ledger_read_something" in src


def test_the_ledger_finds_a_hidden_model_that_is_not_an_assistant_message(tmp_path):
    """The known-nonempty case, and the one the previous scan would have missed: a title or summary
    agent's record need not be an assistant message in the session it summarised."""
    (tmp_path / "a.json").write_text(json.dumps(
        {"role": "assistant", "modelID": "deepseek-v4-pro",
         "tokens": {"input": 10, "output": 2, "reasoning": 1, "cache": {"read": 5}}}))
    (tmp_path / "b.json").write_text(json.dumps(
        {"role": "session", "title": {"modelID": "cheap-title-model"}}))
    led = agent.session_ledger(tmp_path)
    assert led["json_files_scanned"] == 2
    assert led["assistant_messages"] == 1
    assert led["assistant_models"] == {"deepseek-v4-pro": 1}
    assert set(led["model_ids_anywhere"]) == {"deepseek-v4-pro", "cheap-title-model"}
    assert led["assistant_tokens"] == {"input_billed": 15, "output": 2, "reasoning": 1}


# ---------------------------------------------------------------------------------------------
# the tool-loop reader
# ---------------------------------------------------------------------------------------------

def _tool_use(cmd: str, output: str) -> str:
    return json.dumps({"type": "tool_use",
                       "part": {"type": "tool", "tool": "bash",
                                "state": {"status": "completed",
                                          "input": {"command": cmd}, "output": output}}})


def _stream(*lines: str) -> dict:
    return {"stdout": "\n".join(lines) + "\n"}


REAL_PT = ("PrimeTime (R)\nInformation: There are 22 leaf cells\n"
           "****************************************\nReport : timing\n"
           "No paths with slack less than 0.00.\nPUBLIC_DONE\n"
           "Thank you for using pt_shell!\n")


def test_the_tool_loop_reader_passes_on_a_real_looking_loop():
    """The known-nonempty case. Without it the reader could be permanently stuck at "no loop" and a
    passing gate would be unreachable rather than merely unmet."""
    log = _stream(_step(input_t=10), _tool_use("bash run_public.sh", REAL_PT),
                  _step(input_t=10), _tool_use("cat exception_config.json", "{}"),
                  _step(input_t=10))
    ev = dry.tool_loop_evidence(log, invocations=2)
    assert ev["loop"] is True, ev
    assert ev["run_public_calls"] == 1
    assert ev["steps_after_first_tool_call"] >= 1
    assert set(ev["primetime_markers_seen"]) == set(dry.PT_MARKERS)


def test_the_tool_loop_reader_fails_when_the_tool_was_never_reached():
    """The previous dry run's exact outcome: run_public.sh printed SKIP because no tool was
    reachable. An episode of those must not read as an episode that chose not to iterate."""
    log = _stream(_step(input_t=10),
                  _tool_use("bash run_public.sh", "SKIP: pt_shell not found (EDA_PT_CMD=pt_shell)"),
                  _step(input_t=10))
    ev = dry.tool_loop_evidence(log, invocations=0)
    assert ev["loop"] is False
    assert ev["skip_lines"] == 1
    assert ev["tool_outputs_showing_primetime"] == 0


def test_the_tool_loop_reader_fails_without_a_server_side_invocation():
    """A transcript that shows PrimeTime output is not proof PrimeTime ran: the text could come from
    anywhere the agent can write. The server-side counter is on the far side of the capability."""
    log = _stream(_step(input_t=10), _tool_use("bash run_public.sh", REAL_PT), _step(input_t=10))
    assert dry.tool_loop_evidence(log, invocations=0)["loop"] is False


def test_the_tool_loop_reader_fails_when_nothing_followed_the_tool_call():
    """A tool call in the final step is a tool call, not a loop; the arm depends on the agent reading
    real feedback and then acting on it."""
    log = _stream(_step(input_t=10), _step(input_t=10),
                  _tool_use("bash run_public.sh", REAL_PT))
    ev = dry.tool_loop_evidence(log, invocations=1)
    assert ev["steps_after_first_tool_call"] == 0
    assert ev["loop"] is False


def test_a_broker_transport_failure_is_detected_rather_than_read_as_tool_output():
    log = _stream(_step(input_t=10),
                  _tool_use("bash run_public.sh",
                            "eda-broker: MEASUREMENT_INVALID transport_output_limit: "
                            "output exceeded a transport cap"),
                  _step(input_t=10))
    ev = dry.tool_loop_evidence(log, invocations=1)
    assert ev["no_transport_failure"] is False
    assert ev["broker_measurement_invalid_markers"] == 1


def test_the_primetime_markers_come_from_recorded_output_not_from_memory():
    """Markers are only useful if they actually occur. Two of the four are checked against committed
    artifacts -- the banner against the preflight's captured broker output, the completion line
    against the task's own canonical tcl -- and the loop condition needs only one to fire."""
    assert "PrimeTime (R)" in json.loads(PREFLIGHT.read_text())["equivalence"]["broker_normalised_head"]
    assert "PUBLIC_DONE" in RUN_PUBLIC_TCL.read_text()
    assert dry.SKIP_MARKER in (REPO / "tasks/p15_sta_handoff/p15_dev_0000/files/run_public.sh").read_text()


# ---------------------------------------------------------------------------------------------
# stop behaviour, and the run's own discipline
# ---------------------------------------------------------------------------------------------

def test_the_stop_rule_is_named_and_a_crash_is_not_a_clean_stop():
    finished = {"stdout": "\n".join([_step(input_t=1), _step(input_t=1, reason="stop")]) + "\n",
                "returncode": 0, "terminated_by": None}
    assert dry.stop_behaviour(finished, steps_cap=60)["stop_rule"] == "model_finished"

    capped = {"stdout": "\n".join([_step(input_t=1)] * 3) + "\n",
              "returncode": 0, "terminated_by": None}
    assert dry.stop_behaviour(capped, steps_cap=3)["stop_rule"] == "steps_cap"

    crashed = {"stdout": _step(input_t=1) + "\n", "returncode": 1, "terminated_by": None}
    out = dry.stop_behaviour(crashed, steps_cap=60)
    assert out["stop_rule"] == "unclear" and out["clean"] is False

    governed = {"stdout": "", "returncode": 121, "terminated_by": "cost_cap_exceeded"}
    out = dry.stop_behaviour(governed, steps_cap=60)
    assert out["stop_rule"] == "cost_cap_exceeded" and out["clean"] is False


def test_the_grading_chain_is_pinned_so_checking_it_means_something():
    sys.path.insert(0, str(REPO / "scripts"))
    from frozen_membership_verify import collect_pins, SCAN_ROOT
    pins = collect_pins(SCAN_ROOT)
    assert dry.GRADING_CHAIN, "the grading chain must not be empty"
    for rel in dry.GRADING_CHAIN:
        assert rel in pins, f"{rel} carries no frozen pin, so comparing it proves nothing"
    assert dry.grader_fidelity()["all_match_frozen_pins"] is True


def test_the_pin_reader_understands_the_shape_the_pin_map_actually_has():
    """The bug the test above caught. `collect_pins` maps a path to a set of (sha256, manifest)
    TUPLES, so comparing a hex digest to the entries directly makes every intact file look modified:
    the first version of the fidelity check reported four mismatches on a clean tree. A reader that
    flags everything is as broken as one that flags nothing, and only one of the two is loud."""
    shas, manifests = dry._pinned_hashes({("abc", "MANIFEST_A")})
    assert shas == {"abc"}
    assert manifests == ["MANIFEST_A"]
    assert dry._pinned_hashes("abc") == ({"abc"}, [])
    assert "def" not in dry._pinned_hashes({("abc", "m")})[0], (
        "a wrong digest must still be a mismatch")
    multi, ms = dry._pinned_hashes({("abc", "m1"), ("abc", "m2"), ("xyz", "m1")})
    assert multi == {"abc", "xyz"} and ms == ["m1", "m2"], (
        "a legitimately multi-hash or multi-manifest pin must not collapse")


def test_the_key_slots_are_listed_because_the_names_are_off_by_one():
    """.env holds TR_API_KEY, TR_API_KEY_1, TR_API_KEY_2, so slot 2 is TR_API_KEY_1. A formula would
    have selected the wrong balance, and a wrong balance is indistinguishable from an empty one."""
    assert agent.KEY_SLOTS == ("TR_API_KEY", "TR_API_KEY_1", "TR_API_KEY_2")
    assert agent.KEY_SLOTS[1] == "TR_API_KEY_1"


def test_the_driver_refuses_to_spend_money_without_explicit_confirmation():
    r = subprocess.run([sys.executable, str(REPO / "scripts/opencode_probe_broker_dry_run.py")],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 2
    assert "--confirm-paid-run" in r.stderr


def test_the_driver_refuses_to_project_the_arm_from_one_episode():
    """The ARM2_NOT_RUN failure, forbidden mechanically. One dev instance at one repetition has no
    dispersion, and the gate that rejected an affordable arm was fed exactly such a rate."""
    src = (REPO / "scripts/opencode_probe_broker_dry_run.py").read_text()
    assert '"projection_for_48_episodes": None' in src
    assert "why_no_projection" in src
    assert "single_run_operational_observation" in src
    for forbidden in ("* 48", "*48", "48 *", "48*"):
        assert forbidden not in src, f"the driver computes a 48-episode projection via {forbidden!r}"


def test_the_scrub_removes_the_forwarder_pointers_when_they_are_actually_set(tmp_path, monkeypatch):
    """The case preflight control 12 could not reach.

    Control 12 built the sandbox environment from the preflight's own environment, where
    EDA_TOOL_ROOT and B04_HOST were unset -- so it confirmed they were absent without ever testing
    the code that removes them. The paid dry run sets both deliberately, because the GRADER needs the
    forwarder, so the scrub is now load-bearing on a present value rather than a missing one.

    EDA_PT_CMD is the sharper half: it is not scrubbed but redirected. If it survived pointing at the
    forwarder shim, run_public.sh inside the sandbox would dispatch to the forwarder and the episode
    would silently be measuring the wrong tool channel.
    """
    monkeypatch.setenv("EDA_TOOL_ROOT", "/some/private/shim/root")
    monkeypatch.setenv("B04_HOST", "user@remote-eda-host")
    monkeypatch.setenv("EDA_PT_CMD", "/some/private/shim/root/bin/pt_shell")
    monkeypatch.setenv("EDA_HSPICE_CMD", "/some/private/shim/root/bin/hspice")

    env = agent.scrubbed_env(REPO / "opencode_probe/config/opencode.json", tmp_path,
                             api_key="unused", broker_enabled=True)
    assert "EDA_TOOL_ROOT" not in env
    assert "B04_HOST" not in env
    assert env["EDA_PT_CMD"] == f"{agent.BROKER_BIN}/pt_shell"
    assert env["EDA_HSPICE_CMD"] == f"{agent.BROKER_BIN}/hspice"
    joined = "\n".join(f"{k}={v}" for k, v in env.items())
    assert "remote-eda-host" not in joined
    assert "/some/private/shim/root" not in joined


def test_without_the_broker_the_tool_pointer_is_a_dead_path_and_that_is_recorded(tmp_path, monkeypatch):
    """The no-broker configuration is deliberately left as it was recorded, not tightened here.

    EDA_TOOL_ROOT and B04_HOST go in both configurations. EDA_PT_CMD does not: with no broker it
    survives pointing at the forwarder shim, which inside the sandbox is an unmounted absolute path,
    so `command -v` fails and run_public.sh prints SKIP -- exactly the previous dry run's recorded
    behaviour. It is a de-anonymisation trace and no capability, and the dry-run report already
    carries it as a residue to neutralise before any export. Asserting the true behaviour here keeps
    that row honest; asserting the pointer were absent would be asserting something false.
    """
    monkeypatch.setenv("EDA_TOOL_ROOT", "/some/private/shim/root")
    monkeypatch.setenv("B04_HOST", "user@remote-eda-host")
    monkeypatch.setenv("EDA_PT_CMD", "/some/private/shim/root/bin/pt_shell")
    env = agent.scrubbed_env(REPO / "opencode_probe/config/opencode.json", tmp_path,
                             api_key="unused", broker_enabled=False)
    assert "EDA_TOOL_ROOT" not in env and "B04_HOST" not in env
    assert "EDA_BROKER_KEY" not in env
    assert env["EDA_PT_CMD"] == "/some/private/shim/root/bin/pt_shell"
    assert "EDA_PT_CMD" in (REPO / "docs/opencode_probe_dry_run_report.md").read_text(), (
        "the residue must stay documented where a reader will find it")


def test_the_dry_run_is_marked_unscored_discarded_and_not_a_contrast():
    src = (REPO / "scripts/opencode_probe_broker_dry_run.py").read_text()
    for flag in ('"unscored": True', '"discarded": True',
                 '"not_a_condition_contrast": True', '"scaffold_contrast_excluded": True'):
        assert flag in src
    assert "no scaffold main effect may be derived" in src, (
        "the record must carry the exclusion in words, not only as a flag")
    assert "READ_ONLY_AS" in src, "the score must carry its own reading restriction"
    assert "cannot be re-read as a pass" in src, (
        "a failed dry run must require a new one, not a fix plus a re-read")


def test_the_documented_pin_mismatches_are_accepted_by_hash_and_nothing_else():
    """Two of the 1065 pins legitimately do not match: both generators were edited after the
    phase-5B/5C freeze and the baseline records the post-freeze hash. Accepting exactly those hashes
    is not tuning the verifier to silence -- a third hash on either path still fails -- and refusing
    them would make the check fail on the tree's documented, committed state."""
    baseline = dry._baseline_mismatches()
    assert set(baseline) == {"generators/p15_sta_handoff_gen.py",
                             "generators/p16_spice_handoff_gen.py"}
    fid = dry.grader_fidelity()
    assert fid["matched_via_documented_baseline"] == ["generators/p15_sta_handoff_gen.py"]
    assert fid["detail"]["generators/p15_sta_handoff_gen.py"]["sha256"] == \
        baseline["generators/p15_sta_handoff_gen.py"]
    for rel, v in fid["detail"].items():
        assert v["matches"] in ("frozen_pin", "documented_post_freeze_baseline"), (rel, v)
