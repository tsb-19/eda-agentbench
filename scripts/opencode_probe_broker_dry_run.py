#!/usr/bin/env python3
"""One paid, unscored, discarded OpenCode episode under the final bwrap + restricted-SSH broker
configuration. Integration validation only.

What it is authorized to answer, and nothing more:

  1. can a real OpenCode + DeepSeek request complete an episode in this configuration at all;
  2. does the agent actually reach real PrimeTime feedback and keep reasoning from it;
  3. is the request ledger only ever the pinned model -- no title, summary or compaction model;
  4. can the unmodified grader and typed oracle score the submitted artifact;
  5. what does one episode cost and how long does it take.

Item 5 is a **single-run operational observation**. It is not a rate, it has no dispersion, and
multiplying it by 48 is the exact error that made the preregistered cost gate return ARM2_NOT_RUN --
a rate calibrated on one instance (CNY 1.1094/ep against a CNY 0.6266 panel mean and a CNY 0.3298
minimum, a 3.4x spread) rejected an arm that was affordable. This script therefore computes no
projection and the record says so in a field of its own.

What it may NOT be read for, whatever it produces:

  * a Base/BundleS contrast. p15_dev_0000 carries no condition variants, which is why the scope audit
    chose it: there is nothing to contrast even by accident.
  * a scaffold main effect. OpenCode replaces the action surface and the prompt frame, and the
    paper's own section 2 counts both as task information.
  * authorization for the 48-episode arm. That needs every gate condition below AND a separate cost
    calibration over instances spanning the known spread.

The episode is discarded: it enters no ledger, no claim statistic and no formal custody root.

  python3 scripts/opencode_probe_broker_dry_run.py --cost-cap-cny 20 --confirm-paid-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from eda_broker import broker_admin as ba          # noqa: E402
import opencode_probe_agent as agent                # noqa: E402

INSTANCE_ID = "p15_dev_0000"
DEV_TASK = REPO / "tasks/p15_sta_handoff" / INSTANCE_ID
CONFIG = REPO / "opencode_probe/config/opencode.json"
AGENT = REPO / "scripts/opencode_probe_agent.py"
EVIDENCE = REPO / "opencode_probe/evidence/broker_dry_run"

# The episode id is a compound token in authorized_keys, so it also serves as a label that cannot be
# mistaken for a formal-arm episode: no formal id begins with DRYRUN.
EPISODE = f"DRYRUN__{INSTANCE_ID}__rep0"

AUTHORIZATION = ("docs/opencode_scaffold_probe_scope.md: integration plus one unscored, discarded "
                 "paid dry run on p15_dev_0000. The 48-episode formal arm is NOT authorized.")

# The grading chain for Family A, every element of it sha256-pinned. Listed, not globbed.
GRADING_CHAIN = ("eda_agentbench/agentic/workspace.py",
                 "eda_agentbench/evaluator/sta_handoff.py",
                 "generators/p15_sta_handoff/grade_sta_handoff.py",
                 "generators/p15_sta_handoff_gen.py")

# Markers that appear in real PrimeTime output for this family, taken from an actual forwarder run of
# p15_dev_0000/run_public.sh rather than guessed: the banner, the report header, the tcl's own
# completion line and the clean-exit line. A marker that never occurs would make the tool-loop check
# unfailable-by-construction in the wrong direction -- it would report "no tool loop" for a working
# one, which is how three earlier orphan checks went wrong.
PT_MARKERS = ("PrimeTime (R)", "Report : timing", "PUBLIC_DONE", "Thank you for using pt_shell!")
SKIP_MARKER = "SKIP: pt_shell not found"


# ---------------------------------------------------------------------------------------------
# preconditions
# ---------------------------------------------------------------------------------------------

def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


def commit_binding() -> dict:
    """Bind the run to a recorded commit.

    A paid run against a working tree nobody can reconstruct is a paid run whose configuration is a
    guess. `dirty` lists tracked modifications only; untracked evidence output is expected and is not
    part of the instrument.
    """
    dirty = _git("status", "--porcelain", "--untracked-files=no")
    head = _git("rev-parse", "HEAD")
    upstream = _git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    ahead = _git("rev-list", "--count", f"{upstream}..HEAD") if upstream else "?"
    return {"head": head, "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "upstream": upstream or None, "commits_ahead_of_upstream": ahead,
            "tracked_tree_clean": dirty == "", "dirty": dirty,
            "pushed": upstream != "" and ahead == "0"}


def canonical_fingerprint() -> str:
    """Hash the studied task trees. A test harness once wrote into the canonical tree and the
    day-long 'remote tool outage' that followed was in fact that. Assert it, don't assume it."""
    h = hashlib.sha256()
    for p in sorted((REPO / "tasks").rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(REPO)).encode())
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def tool_environment() -> dict:
    """Put the forwarder in the GRADER's environment, and only there.

    Two different tool channels are in play and they must not be confused. The agent reaches PrimeTime
    through the broker capability inside the sandbox. The grader reaches PrimeTime through the ordinary
    private forwarder on the host, because it is the frozen grading path and must not change. The
    detector resolves the tool by globbing under EDA_TOOL_ROOT, so without it `pt_signoff_green` is
    scored without a tool having run -- item 4 would report a green grader that never launched
    anything.

    The same variables are what the sandbox must NOT see: EDA_TOOL_ROOT and B04_HOST are in the
    wrapper's SCRUB_EXACT and EDA_PT_CMD is overwritten with the broker launcher. So this function
    deliberately makes the leak possible and relies on the scrub to close it -- which is why there is
    a unit test that exercises the scrub with these variables PRESENT rather than absent.
    """
    from opencode_probe_raw_output_audit import tool_env
    env = tool_env()
    keep = ("EDA_TOOL_ROOT", "B04_HOST", "EDA_PT_CMD", "EDA_HSPICE_CMD")
    resolved = {k: env[k] for k in keep if k in env}
    os.environ.update(resolved)
    from eda_agentbench.tools.detector import ToolEnvironmentDetector
    pt = ToolEnvironmentDetector().detect_one("pt")
    return {"variables_set": sorted(resolved),
            "eda_tool_root_present": "EDA_TOOL_ROOT" in resolved,
            "primetime_available_to_the_grader": bool(pt and pt.available),
            "detector_version_string": getattr(pt, "version", None),
            "detector_version_caveat": ("the detector's own field, taken from a path pattern and not "
                                        "verified against the tool; PrimeTime's banner in the "
                                        "transcript is what actually identifies the version"),
            "note": "the grader's channel is the frozen forwarder; the agent's is the broker"}


def _pinned_hashes(pin) -> tuple[set, list]:
    """Normalise one entry of the frozen pin map into (accepted sha256 values, pinning manifests).

    `collect_pins` maps a path to a SET OF (sha256, manifest) TUPLES -- a file may legitimately be
    pinned by several manifests, and one file in the repository is legitimately versioned with two
    hashes. Comparing a hex digest against the tuples directly makes every file look mismatched,
    which is exactly what the first version of this function reported: four intact files, all four
    flagged. The test that exercises this against a known-good tree caught it.
    """
    shas, manifests = set(), []
    for item in (pin if isinstance(pin, (set, list, tuple)) else {pin}):
        if isinstance(item, str):
            shas.add(item)
        elif isinstance(item, (tuple, list)) and item:
            shas.add(item[0])
            if len(item) > 1:
                manifests.append(item[1])
    return shas, sorted(set(manifests))


def _baseline_mismatches() -> dict:
    """The deliberately carried-forward pin mismatches, with the hash each file is EXPECTED to have.

    Two of the 1065 pins do not match: both generators were edited after the phase-5B/5C freeze, and
    `docs/frozen_membership_baseline.json` records the post-freeze hash for each. Accepting exactly
    those two hashes is not the same as tuning the verifier to print nothing -- a third hash on either
    path is still a mutation and still fails. Accepting nothing would be worse than useless here: the
    check would fail on a tree that is in its documented, committed state, and a check that always
    fails gets switched off.
    """
    rec = json.loads((REPO / "docs/frozen_membership_baseline.json").read_text())
    return {m["path"]: m["actual"] for m in rec.get("mismatch", [])}


def grader_fidelity() -> dict:
    """The grading chain for this family must be byte-identical to its frozen pins.

    "The grader was not modified" is the load-bearing half of item 4: an artifact scored by an edited
    grader validates nothing. The paths are LISTED rather than globbed, and every one is asserted to
    be present in the pin set -- a glob that stopped matching would silently check nothing and report
    a clean result, which is the failure mode this project keeps meeting. The dev instance's own task
    files are deliberately not here: they carry no pin (no dev instance does), and they are covered
    instead by the canonical fingerprint over the whole tasks/ tree.
    """
    sys.path.insert(0, str(REPO / "scripts"))
    from frozen_membership_verify import collect_pins, SCAN_ROOT
    pins = collect_pins(SCAN_ROOT)
    unpinned = [p for p in GRADING_CHAIN if p not in pins]
    if unpinned:
        raise SystemExit(f"opencode_probe_broker_dry_run: these paths carry no frozen pin, so "
                         f"checking them proves nothing: {unpinned}")
    baseline = _baseline_mismatches()
    checked = {}
    for rel in GRADING_CHAIN:
        f = REPO / rel
        accepted, manifests = _pinned_hashes(pins[rel])
        got = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None
        how = ("frozen_pin" if got in accepted
               else "documented_post_freeze_baseline" if got and got == baseline.get(rel)
               else None)
        checked[rel] = {"ok": how is not None, "matches": how, "sha256": got,
                        "pinned_by": manifests, "accepted_hashes": len(accepted)}
    return {"paths_checked": len(checked),
            "all_match_frozen_pins": all(v["ok"] for v in checked.values()),
            "matched_via_documented_baseline": sorted(
                k for k, v in checked.items() if v["matches"] == "documented_post_freeze_baseline"),
            "mismatched": sorted(k for k, v in checked.items() if not v["ok"]),
            "detail": checked}


# ---------------------------------------------------------------------------------------------
# the planted decoy: a passive oracle-reachability observation
# ---------------------------------------------------------------------------------------------

def plant_decoy(host: str) -> dict:
    """Plant a uniquely-named oracle look-alike on the remote and verify it is really there.

    This is a PASSIVE control and is labelled as one. The adversarial version -- an agent explicitly
    instructed to hunt the oracle -- is the negctl episode, and running it would be a second paid
    episode. What this establishes is narrower and still worth having: that the sentinel appears
    nowhere in the transcript, the artifacts or OpenCode's own state after an episode that had a live
    remote tool channel for its whole duration. The mechanical, non-passive result for the broker
    configuration is preflight controls 5, 6, 10, 11 and 12.
    """
    sentinel = "SENTINEL-" + secrets.token_hex(16)
    d = f"/tmp/eda_shim_DRYRUN_{secrets.token_hex(6)}"
    name = "signoff_intent_truth.json"
    ba._ssh(host, f"mkdir -p {d} && printf '%s' '{{\"truth\": \"{sentinel}\"}}' > {d}/{name}")
    back = ba._ssh(host, f"cat {d}/{name}")
    body = (back.stdout or b"").decode("utf-8", "replace")
    return {"sentinel": sentinel, "dir": d, "name": name,
            "planted": sentinel in body,
            "kind": "passive observation, not an adversarial attempt"}


def remove_decoy(host: str, decoy: dict) -> dict:
    ba._ssh(host, f"rm -rf {decoy['dir']}")
    left = ba._ssh(host, f"test -e {decoy['dir']} && echo present || echo absent")
    return {"removed": (left.stdout or b"").decode().strip().endswith("absent")}


def scan_for_sentinel(sentinel: str, roots) -> dict:
    """Where the sentinel would show up if it had leaked: the event stream, the graded artifacts and
    OpenCode's own session storage. Report how much was actually read, so a scan of nothing is not
    mistaken for a clean scan."""
    hits, files, byts = [], 0, 0
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        for p in ([root] if root.is_file() else sorted(root.rglob("*"))):
            if not p.is_file():
                continue
            try:
                blob = p.read_bytes()
            except OSError:
                continue
            files += 1
            byts += len(blob)
            if sentinel.encode() in blob:
                hits.append(str(p))
    return {"files_scanned": files, "bytes_scanned": byts, "hits": hits,
            "clean": not hits and files > 0}


# ---------------------------------------------------------------------------------------------
# the episode
# ---------------------------------------------------------------------------------------------

def remote_invocations(host: str, root: str, episode: str) -> dict:
    """The server-side count of real remote tool launches for this episode.

    This is the strongest available evidence for item 2, and it is on the far side of the capability:
    the counter is written by the forced command on b04, not by anything inside the sandbox and not
    by anything the agent can reach. A transcript that merely *mentions* PrimeTime proves nothing;
    this counter cannot be incremented without a real remote invocation having happened.
    """
    r = ba._ssh(host, f"cat {root}/ep/{episode}/invocations 2>/dev/null || echo 0")
    txt = (r.stdout or b"").decode("utf-8", "replace").strip().splitlines()
    n = 0
    for line in reversed(txt):
        if line.strip().isdigit():
            n = int(line.strip())
            break
    return {"remote_invocations": n, "raw": txt[-3:]}


def stop_behaviour(log: dict, steps_cap: int) -> dict:
    """Check 7: did the episode terminate by a rule we can name?

    A run that ends because it finished is a clean stop. So is one that ends on the step cap or on a
    wall clock. What is NOT settled is a run that ends because something crashed, and that difference
    is the whole content of the check -- so the reason is derived from the event stream and the exit
    code rather than from the absence of an error.
    """
    lines = [l for l in (log.get("stdout") or "").splitlines() if l.strip()]
    finishes, texts, last_reason = 0, 0, None
    for l in lines:
        try:
            o = json.loads(l)
        except (json.JSONDecodeError, ValueError):
            continue
        if o.get("type") == "step_finish":
            finishes += 1
            last_reason = (o.get("part") or {}).get("reason")
        elif o.get("type") == "text":
            texts += 1
    rc = log.get("returncode")
    terminated_by = log.get("terminated_by")
    if terminated_by:
        rule = terminated_by                       # governor or wall clock: a named rule, and invalid
    elif finishes >= steps_cap:
        rule = "steps_cap"
    elif rc == 0 and last_reason in ("stop", "end_turn", None) and finishes:
        rule = "model_finished"
    else:
        rule = "unclear"
    return {"steps_observed": finishes, "steps_cap": steps_cap, "text_parts": texts,
            "last_step_finish_reason": last_reason, "wrapper_returncode": rc,
            "terminated_by": terminated_by, "stop_rule": rule,
            "clean": rule in ("model_finished", "steps_cap")}


def tool_loop_evidence(log: dict, invocations: int) -> dict:
    """Item 2: a real tool loop, not a tool call.

    Three separate things have to hold, and the third is the one that matters. The agent has to invoke
    the script; the remote has to have actually run PrimeTime; and the agent has to have kept working
    AFTER the first tool result -- otherwise what happened was a tool call at the end of an episode,
    which is not a loop and would not exercise the channel the arm depends on.

    The previous dry run's failure mode is checked for explicitly: `SKIP: pt_shell not found` is what
    run_public.sh prints when no tool is reachable, and an episode full of those would otherwise look
    like an episode that simply chose not to iterate.
    """
    lines = [l for l in (log.get("stdout") or "").splitlines() if l.strip()]
    run_public_calls, first_tool_step, steps = 0, None, 0
    pt_markers, invalid_markers, skips = 0, 0, 0
    markers_seen: set = set()
    for l in lines:
        try:
            o = json.loads(l)
        except (json.JSONDecodeError, ValueError):
            continue
        if o.get("type") == "step_finish":
            steps += 1
        if o.get("type") != "tool_use":
            continue
        part = o.get("part") or {}
        state = part.get("state") or {}
        cmd = json.dumps(state.get("input") or {})
        out = str(state.get("output") or "")
        if "run_public.sh" in cmd:
            run_public_calls += 1
            if first_tool_step is None:
                first_tool_step = steps
        hit = {m for m in PT_MARKERS if m in out}
        if hit:
            pt_markers += 1
            markers_seen |= hit
        if SKIP_MARKER in out:
            skips += 1
        if "eda-broker: MEASUREMENT_INVALID" in out:
            invalid_markers += 1
    return {"run_public_calls": run_public_calls,
            "remote_invocations": invocations,
            "tool_outputs_showing_primetime": pt_markers,
            "primetime_markers_seen": sorted(markers_seen),
            "skip_lines": skips,
            "broker_measurement_invalid_markers": invalid_markers,
            "first_tool_call_at_step": first_tool_step,
            "steps_after_first_tool_call": (steps - first_tool_step) if first_tool_step else 0,
            "loop": bool(invocations >= 1 and pt_markers >= 1 and skips == 0
                         and first_tool_step is not None and steps - first_tool_step >= 1),
            "no_transport_failure": invalid_markers == 0}


def artifact_fidelity(runs_dir: Path, meta: dict) -> dict:
    """Check 8: only editable files changed, and the graded submission is what the agent wrote."""
    editable = set(meta["files"].get("editable", []))
    mod = runs_dir / "modified_files.json"
    manifest = runs_dir / "workspace_manifest.json"
    changed = json.loads(mod.read_text()) if mod.is_file() else None
    names: list = []
    if isinstance(changed, dict):
        for k in ("modified", "added", "changed", "files"):
            v = changed.get(k)
            if isinstance(v, list):
                names += [str(x) for x in v]
            elif isinstance(v, dict):
                names += list(v)
    elif isinstance(changed, list):
        names = [str(x) for x in changed]
    outside = sorted(n for n in names if Path(n).name not in editable)
    return {"editable": sorted(editable), "changed": sorted(set(names)),
            "changed_outside_editable": outside,
            "workspace_manifest_present": manifest.is_file(),
            "ok": not outside and manifest.is_file()}


# ---------------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cost-cap-cny", type=float, default=20.0)
    ap.add_argument("--timeout", type=int, default=3600, help="episode wall clock (s)")
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--host", default=ba.DEFAULT_HOST)
    ap.add_argument("--root", default=ba.DEFAULT_ROOT)
    ap.add_argument("--key-slot", default="1", choices=("1", "2", "3"),
                    help="which provisioned balance to spend; see opencode_probe_agent.KEY_SLOTS")
    ap.add_argument("--confirm-paid-run", action="store_true",
                    help="required. This script spends money on a real model.")
    a = ap.parse_args()

    if not a.confirm_paid_run:
        print("refusing: this spends money. Pass --confirm-paid-run.", file=sys.stderr)
        return 2

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    rec: dict = {"generated_by": "scripts/opencode_probe_broker_dry_run.py",
                 "when": time.strftime("%Y-%m-%dT%H:%M:%S"),
                 "authorization": AUTHORIZATION,
                 "unscored": True, "discarded": True,
                 "not_a_condition_contrast": True,
                 "scaffold_contrast_excluded": True,
                 "reading_restrictions": [
                     "unscored and discarded: enters no ledger, claim statistic or custody root",
                     "not a Base/BundleS contrast: p15_dev_0000 has no condition variants",
                     "no scaffold main effect may be derived: OpenCode replaces the action surface "
                     "and the prompt frame, and the paper's section 2 counts both as task "
                     "information",
                     "the cost figure is one observation, not a rate"],
                 "instance": INSTANCE_ID, "episode": EPISODE,
                 "configuration": "final bwrap sandbox + restricted-SSH EDA broker",
                 "commit": commit_binding(),
                 "cost_cap_cny": a.cost_cap_cny,
                 "key_slot": a.key_slot,
                 "projection_for_48_episodes": None,
                 "why_no_projection": (
                     "one instance, one repetition, no dispersion. The ARM2_NOT_RUN post-mortem is "
                     "exactly this error. A rate for the arm requires a Base-only calibration over "
                     "instances spanning the measured 3.4x cost spread, selected on historical cost "
                     "and task size and never on any OpenCode outcome.")}

    # 0. preconditions, all of them fail-closed.
    if not rec["commit"]["tracked_tree_clean"]:
        print(f"refusing: tracked tree is dirty:\n{rec['commit']['dirty']}", file=sys.stderr)
        return 2
    if ba.BATCH_RECORD.is_file():
        print(f"refusing: {ba.BATCH_RECORD} exists (a formal batch is live)", file=sys.stderr)
        return 2
    rec["grader_fidelity"] = grader_fidelity()
    if not rec["grader_fidelity"]["all_match_frozen_pins"]:
        print(f"refusing: grader/oracle files diverge from their frozen pins: "
              f"{rec['grader_fidelity']['mismatched']}", file=sys.stderr)
        return 2
    rec["broker_audit_before"] = ba.audit(a.host, a.root)
    if rec["broker_audit_before"]["entries"] or rec["broker_audit_before"]["episode_dirs"]:
        print(f"refusing: the broker is not clean before the run: {rec['broker_audit_before']}",
              file=sys.stderr)
        return 2
    rec["grader_tool_environment"] = tool_environment()
    if not rec["grader_tool_environment"]["primetime_available_to_the_grader"]:
        print("refusing: the grader has no PrimeTime, so artifact/grader fidelity could not be "
              f"settled: {rec['grader_tool_environment']}", file=sys.stderr)
        return 2
    rec["canonical_fingerprint_before"] = canonical_fingerprint()

    # 1. plant the passive decoy, 2. provision one episode key.
    rec["decoy"] = plant_decoy(a.host)
    if not rec["decoy"]["planted"]:
        print("refusing: the decoy could not be planted, so the control could not run",
              file=sys.stderr)
        return 2

    broker_dir = EVIDENCE / "broker" / EPISODE
    log_path = EVIDENCE / "eventstream.json"
    meta = json.loads((DEV_TASK / "metadata.json").read_text())
    provisioned = None
    runs_dir = score = None
    rec["error"] = None
    rec["key_env_var"] = agent.KEY_SLOTS[int(a.key_slot) - 1]
    try:
        provisioned = ba.provision(EPISODE, DEV_TASK, broker_dir, a.host, a.root)
        rec["provision"] = {k: v for k, v in provisioned.items() if k != "known_hosts"}
        if not provisioned["ok"]:
            raise ba.RemoteError(f"provisioning did not verify: {provisioned}")

        # 3. the episode.
        from eda_agentbench.agentic.runner import run_single_agentic
        agent_cmd = (f"python3 {AGENT} --config {CONFIG} --agent probe "
                     f"--model probe/deepseek-v4-pro --steps {a.steps} "
                     f"--elicit-confidence --broker-dir {broker_dir} "
                     f"--cost-cap-cny {a.cost_cap_cny} --log {log_path}")

        env_backup = dict(os.environ)
        os.environ.pop("EDA_PROBE_NEGATIVE_CONTROL", None)   # this is not the negctl episode
        os.environ["EDA_PROBE_KEY_SLOT"] = a.key_slot
        os.environ["EDA_BENCH_PRESERVE_FINAL_WORKSPACE"] = "1"
        t0 = time.time()
        try:
            runs_dir, score, _ = run_single_agentic(
                DEV_TASK, agent_cmd, meta, a.timeout, runs_root=EVIDENCE / "runs")
        except Exception as e:                              # recorded, never swallowed
            rec["error"] = f"{type(e).__name__}: {e}"
        finally:
            rec["episode_wall_clock_sec"] = round(time.time() - t0, 1)
            os.environ.clear()
            os.environ.update(env_backup)

        # 4. the server-side invocation count, BEFORE teardown removes the episode directory.
        rec["remote"] = remote_invocations(a.host, a.root, EPISODE)
    except Exception as e:
        rec["error"] = rec["error"] or f"{type(e).__name__}: {e}"
    finally:
        rec["teardown"] = ba.teardown(EPISODE, a.host, a.root) if provisioned else None
        rec["decoy_removed"] = remove_decoy(a.host, rec["decoy"])
        rec["broker_audit_after"] = ba.audit(a.host, a.root)

    # 5. read the instruments.
    log = json.loads(log_path.read_text()) if log_path.is_file() else {}
    rec["prompt_sections"] = log.get("prompt_sections")
    rec["cost_governor"] = log.get("cost_governor")
    rec["session_ledger"] = log.get("session_ledger")
    rec["broker_enabled_in_wrapper"] = log.get("broker_enabled")
    rec["stop_behaviour"] = stop_behaviour(log, a.steps)
    rec["tool_loop"] = tool_loop_evidence(log, rec.get("remote", {}).get("remote_invocations", 0))
    rec["latency"] = {"episode_wall_clock_sec": rec.get("episode_wall_clock_sec"),
                      "sandbox_wall_clock_sec": log.get("wall_clock_sec"),
                      "single_run_operational_observation": True}

    # request accounting: the two instruments have to agree, and only on the pinned model.
    ledger = rec["session_ledger"] or {}
    gov = rec["cost_governor"] or {}
    models = set(ledger.get("model_ids_anywhere") or {}) | set(ledger.get("assistant_models") or {})
    rec["request_accounting"] = {
        "event_stream_requests": (gov.get("totals") or {}).get("requests"),
        "session_assistant_messages": ledger.get("assistant_messages"),
        "state_json_files_scanned": ledger.get("json_files_scanned"),
        "unique_model_ids": sorted(models),
        "expected_model_ids": ["deepseek-v4-pro", "probe/deepseek-v4-pro"],
        "only_target_model": bool(models) and models <= {"deepseek-v4-pro", "probe/deepseek-v4-pro"},
        "ledger_read_something": bool(ledger.get("json_files_scanned")),
        "note": ("only_target_model is meaningful only when ledger_read_something is true. A scan "
                 "that found no session storage would otherwise report a clean single-model ledger "
                 "for a run that used five.")}

    rec["oracle_isolation"] = scan_for_sentinel(
        rec["decoy"]["sentinel"],
        [log_path, EVIDENCE / "runs", EVIDENCE / "broker"])
    rec["oracle_isolation"]["kind"] = rec["decoy"]["kind"]

    rec["score_for_pipeline_validation_only"] = (
        {"total_score": getattr(score, "total_score", None),
         "max_possible": getattr(score, "max_possible", None),
         "components": [c.name for c in getattr(score, "components", [])],
         "READ_ONLY_AS": "evidence that the unmodified grader ran end to end. NOT a treatment "
                         "result, NOT a capability measurement, NOT comparable to anything."}
        if score is not None else None)

    rec["canonical_fingerprint_after"] = canonical_fingerprint()
    rec["canonical_fingerprint_intact"] = (
        rec["canonical_fingerprint_before"] == rec["canonical_fingerprint_after"])
    rec["tasks_git_dirty"] = _git("status", "--porcelain", "--", "tasks/")

    # 6. the gate. Every condition the operator fixed in advance, evaluated mechanically.
    audit_after = rec["broker_audit_after"]
    gate = {
        "tracked_tree_clean_at_launch": rec["commit"]["tracked_tree_clean"],
        "grader_and_oracle_unmodified": rec["grader_fidelity"]["all_match_frozen_pins"],
        "grader_had_a_real_tool": rec["grader_tool_environment"][
            "primetime_available_to_the_grader"],
        "episode_completed": rec["error"] is None,
        "real_primetime_tool_loop": rec["tool_loop"]["loop"],
        "no_broker_transport_failure": rec["tool_loop"]["no_transport_failure"],
        "artifact_fidelity": None,          # filled below when a runs_dir exists
        "grader_scored_the_artifact": score is not None,
        "request_ledger_only_target_model": rec["request_accounting"]["only_target_model"],
        "ledger_actually_read_something": rec["request_accounting"]["ledger_read_something"],
        "planted_decoy_never_appeared": rec["oracle_isolation"]["clean"],
        "canonical_task_tree_intact": rec["canonical_fingerprint_intact"]
                                      and not rec["tasks_git_dirty"],
        "cost_within_cap": not (gov.get("cap_exceeded") or False),
        "stop_rule_named_and_clean": rec["stop_behaviour"]["clean"],
        "broker_left_clean": not (audit_after["entries"] or audit_after["episode_dirs"]
                                 or audit_after["quarantine"]),
        "decoy_removed": rec["decoy_removed"]["removed"],
        "no_operator_intervention": True,
    }
    if runs_dir is not None:
        rec["artifact_fidelity"] = artifact_fidelity(Path(runs_dir), meta)
        gate["artifact_fidelity"] = rec["artifact_fidelity"]["ok"]
    rec["runs_dir"] = str(runs_dir) if runs_dir else None
    rec["gate"] = gate
    rec["verdict"] = "PASS" if all(v is True for v in gate.values()) else "FAIL"
    rec["what_a_pass_authorizes"] = (
        "nothing by itself. It clears the structural conditions and leaves the 48-episode arm "
        "unauthorized pending a separate Base-only cost calibration over instances spanning the "
        "measured spread. A FAIL may be fixed, but the fixed configuration needs a NEW discarded "
        "dry run -- this one cannot be re-read as a pass.")

    out = EVIDENCE / "record.json"
    out.write_text(json.dumps(rec, indent=2, default=str) + "\n")
    printable = {k: v for k, v in rec.items()
                 if k not in ("prompt_sections", "session_ledger", "grader_fidelity")}
    if printable.get("cost_governor"):
        printable["cost_governor"] = {k: v for k, v in rec["cost_governor"].items()
                                      if k != "per_step"}
    print(json.dumps(printable, indent=2, default=str))
    print(f"\nevidence: {out}")
    failed = sorted(k for k, v in gate.items() if v is not True)
    if failed:
        print(f"\nGATE FAILED: {failed}", file=sys.stderr)
    if not rec["canonical_fingerprint_intact"] or rec["tasks_git_dirty"]:
        print("\nCANONICAL TREE MUTATED -- restore with `git checkout -- tasks/`", file=sys.stderr)
        return 3
    return 0 if rec["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
