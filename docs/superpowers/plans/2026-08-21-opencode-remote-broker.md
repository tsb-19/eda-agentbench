# OpenCode remote EDA broker — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the sandboxed OpenCode agent a real PrimeTime/HSPICE feedback channel that is a
*named two-operation capability* rather than an SSH account, so that check 2 (tool feedback) and
check 5 (oracle isolation) can hold in the same configuration — without spending a single model call
to build or verify it.

**Architecture:** A per-episode ed25519 key on b04 whose `authorized_keys` line is
`restrict,command="…broker.sh <episode_id>"`, so the episode is burned into the server-side forced
command and the client has no field in which to name a different one. For the formal arm all 48 such
lines are installed in **one** atomic rewrite before the arm and removed in one after, so
`authorized_keys` never changes while episodes are running and each sandbox mounts only its own
private key. The agent-side client is installed as the `pt_shell` / `hspice` shim that
`run_public.sh` already dispatches through (`EDA_PT_CMD` / `EDA_HSPICE_CMD`), so no hash-pinned
canonical file changes. The wire protocol is a length-framed JSON request on stdin with a fixed
per-op key set; no client string ever reaches the remote filesystem as a path.

**Revision history of this plan:** round-1 review (A–D) folded in on 2026-08-21; round-2 review
(E–G: batch key provisioning, headroom-not-proof plus fail-closed caps, conservative mutex
stale-breaking) folded in on 2026-08-22 before any implementation began.

**Tech Stack:** Python 3 (host + remote; remote interpreter resolved at deploy time, currently
Python 3.9.0 on b04), OpenSSH 7.4p1 on b04 (`restrict` requires ≥ 7.2 — available), `bwrap` for the
existing sandbox, pytest.

---

## Global Constraints

Copied from `CLAUDE.md`, `docs/opencode_scaffold_probe_scope.md` and
`docs/opencode_probe_analysis_plan.md`. Every task's requirements implicitly include this section.

- **Zero model calls.** Nothing in this plan may call a paid model. The dry run is already spent and
  is not re-run. If a task cannot be verified without a model call, it is not done — it is recorded
  as unsettled.
- **This does not authorize the formal 48-episode arm.** It addresses the blocker in
  `docs/opencode_probe_dry_run_report.md` §5 and nothing else. Check 7 stays UNSETTLED. Check 5's
  earlier PASS does **not** carry over: it was established with the tools absent, and this changes
  that configuration.
- **The scaffold main effect may not be estimated.** No script, table, key or summary produced here
  may express `OpenCode − controlled runner`. `test_no_scaffold_main_effect_claim` must keep passing.
- **Nothing is written under `reports/`.** All new artifacts go under `opencode_probe/`. An early
  Phase-8A draft that wrote to `reports/` drove the pin count 1065 → 1979.
- **`reports/evidence/` is read-only** and no sha256-pinned file may change. Before editing anything
  under `scripts/`, run:
  ```bash
  python3 -c "import sys; sys.path.insert(0,'scripts'); \
    from frozen_membership_verify import collect_pins, SCAN_ROOT; \
    print('<path>' in collect_pins(SCAN_ROOT))"
  ```
  Expected `False` for every path this plan touches. `scripts/opencode_probe_agent.py` is **not**
  pinned (verify anyway); `scripts/llm_agent_driver.py` **is** and must not be touched.
- **Never write into `tasks/`.** `test_canonical_golden_fingerprint_intact` fires if anything does.
  Every tool execution in this plan runs in a scratch copy. This is the `docs/incident_golden_corruption.md`
  failure mode and it costs a day when it recurs.
- **Infrastructure fault ≠ capability failure.** Every new error path must be *typed* so a transport
  failure can never be recorded as tool behaviour or model behaviour.
- **Verify that the verification ran.** No number in an evidence record may be inferred; each is
  measured, and the measurement's own execution is asserted.
- **Bilingual docs.** Every reader-facing doc changed here ships `x.md` and `x.zh.md` with the
  `**English | [中文](x.zh.md)**` header. This plan file itself is English-only, matching the
  existing `docs/superpowers/` precedent.
- **Design doc and implementation land in the same commit.** `scripts/slim_link_check.py` scans only
  *tracked* files, so an uncommitted design doc referencing future paths is not a violation; a
  committed one would be. No `slim_link_check` exemption may be added to make this green.
- **Do not push the branch and do not create tags.**

### Fixed values this plan pins

| Name | Value | Source |
|---|---|---|
| remote host | `tsb@b04`, OpenSSH 7.4p1, CentOS 7 | measured |
| remote broker root | `/home/tsb/eda-probe-broker/` | this plan; deliberately **not** `/tmp` |
| remote python3 | resolved at deploy from `bash -lc 'command -v python3'` (currently `/share_x86/soft/anaconda3/envs/py390/bin/python3`) | measured; recorded in the deploy record |
| remote `pt_shell` | resolved from the login-shell PATH, as the forwarder does (`S-2021.06-SP5`) | measured; parity with the frozen arm |
| remote `hspice` | resolved from the login-shell PATH (`S-2021.09-SP1`) | measured; parity |
| op wall clock | 180 s total per invocation | parity with the frozen per-command timeout |
| request cap | 2 MiB | Task 1 must show ≥ 8× headroom over the measured maximum |
| stdout / stderr transport cap | 1 MiB each | Task 1 must show ≥ 8× headroom over the measured maximum |
| `hspice_run.lis` artifact cap | 8 MiB | Task 1 must show ≥ 8× headroom over the measured maximum |
| invocations per episode | 200 | ≥ 3× the 60-action frozen budget |
| episode id grammar | `^[A-Za-z0-9_.-]{1,64}$` | validated by host **and** by broker |
| episode id form | one compound token, `<instance>__<condition>__rep<k>` | so `argv` stays length-2 and `K_i ⇒ E_i` needs no protocol field |
| wire magic | `EDABROKER1` | framing, so remote rc noise is detected not absorbed |
| formal-arm key lifecycle | **batch**: 48 keys installed in one rewrite before the arm, removed in one rewrite after | `authorized_keys` is static for the whole arm |

### The reviewer-required changes, and where each lands

Round 1 (A–D) and round 2 (E–G, 2026-08-22). Every one of these is a requirement, not a preference.

| | Requirement | Task |
|---|---|---|
| **A** | `authorized_keys` lifecycle: managed block, lock, atomic rewrite, never clobber user keys, stale reap, concurrent episodes coexist | Task 3, used by Task 6 |
| **B** | The transport caps must rest on measured raw output, not on `64K/4K = 16` | Task 1; caps consumed in Task 2; wording fixed in Task 9 |
| **C** | Timeout kills the whole remote process tree; timeout / tool failure / transport failure are distinct types | Task 4 (kill + classify), Task 5 (client-side taxonomy) |
| **D** | Fixed schema, fixed server-side filenames, no client paths, no archive extraction | Task 2 (schema), Task 4 (materialisation) |
| **E** | The formal arm does **not** rewrite `authorized_keys` 48 times. All 48 public keys are installed in one atomic rewrite before the arm and removed in one after; each sandbox mounts only its own private key. Per-episode add/remove survives for preflight and dry-run use only. | Task 3 (`add_entries`/`remove_entries`), Task 6 (`provision_batch`/`teardown_batch` + batch lock-out), Task 8 (control 13) |
| **F** | Task 1 establishes **empirical headroom over the complete calibration set** — it does not prove a cap can never bind. A runtime cap hit is **fail-closed**: typed `transport_output_limit`, measurement-invalid, never a silent truncation the agent reads as tool output. | Task 1 (claim + calibration set), Task 2 (6th status), Task 4 (fail-closed), Task 5 (exit 125), Task 8 (control 14) |
| **G** | The `mkdir` mutex carries `owner_host`, `owner_pid`, `owner_nonce`, `created_at`, `heartbeat`. Age alone never breaks a lock: breaking requires verified local death, otherwise the lock is atomically renamed to quarantine and the lock is re-contested. Release verifies its own nonce. | Task 3 |

### Why E is not merely a simplification

`$HOME` on b04 is NFS. `nfs(5)` states plainly that NFS provides no cluster-coherent caching and
that a network partition can lose locks; `mkdir(2)` records protocol-level infelicities of its own on
NFS. A design that needs 96 correct mutual-exclusion episodes (48 installs + 48 removals) against
that substrate is betting the operator's three real login keys on a primitive whose own manual page
disclaims the guarantee. Batch provisioning reduces the bet to **two** acquisitions per arm, at the
boundaries, where a failure is visible before any episode runs and after all of them have.

It costs nothing that matters. The property the arm needs is `K_i ⇒ E_i` — holding episode *i*'s key
implies you can only run episode *i* — and that property lives in the `command=` of each individual
line, not in when the line was written. Cross-episode selection stays unrepresentable, concurrency
still works, and `authorized_keys` is byte-static for the entire arm.

---

## File Structure

| Path | Responsibility |
|---|---|
| `scripts/eda_broker/__init__.py` | package marker so `scripts/` modules can `from eda_broker import …` |
| `scripts/eda_broker/broker_protocol.py` | pure data: op table, input classes, caps, framing, episode-id grammar, error taxonomy. No I/O, no subprocess. Imported by client, broker, admin and tests. |
| `scripts/eda_broker/authorized_keys_block.py` | the managed-block editor: NFS-conservative mutex (owner/nonce/heartbeat, quarantine rather than unlink), atomic rewrite, add/remove/**add_entries**/**remove_entries**/list/reap. Operates on a *file path*, so it is unit-testable locally and shipped to b04 unchanged. |
| `scripts/eda_broker/remote_broker.py` | the forced command. Reads a framed request, validates, materialises a private invocation workspace, runs the op under its own process group with a hard deadline, frames the response, cleans up on every exit path. |
| `scripts/eda_broker/broker_client.py` | in-sandbox shim, invoked as `pt_shell` or `hspice`. Builds the request from the cwd, calls `ssh` with pinned identity/known-hosts, rewrites `@WORKDIR@`, emits stdout/stderr/rc exactly as the forwarder does. |
| `scripts/eda_broker/broker_admin.py` | host-side: `deploy`, `provision`, `teardown`, `provision-batch`, `teardown-batch`, `audit`. Holds the only credential that can write `authorized_keys`. |
| `scripts/opencode_probe_raw_output_audit.py` | zero-call transport-headroom calibration over the complete calibration set (requirement B/F). |
| `scripts/opencode_probe_remote_broker_preflight.py` | zero-call preflight: 14 negative controls, planted decoy, cleanup verification, forwarder-equivalence check. Writes the evidence record. |
| `scripts/opencode_probe_agent.py` | **modify**: bind the probe key, `known_hosts` and the two shims at neutral in-sandbox paths; export `EDA_PT_CMD` / `EDA_HSPICE_CMD`. |
| `tests/test_eda_broker.py` | protocol, classification, refusal, key-block concurrency, kill semantics, source-level `SSH_ORIGINAL_COMMAND` assertion. |
| `tests/test_opencode_probe.py` | **modify**: add `test_check6_is_parity_not_absolute`. |
| `opencode_probe/evidence/raw_output_audit.json` | Task 1's record. |
| `opencode_probe/evidence/remote_broker_preflight.json` | Task 8's record. |
| `opencode_probe/broker/deploy.json` | Task 6's deploy record (remote interpreter, hashes, host key). |
| `opencode_probe/broker/batch.json` | Task 6's batch record: the episode → key-fingerprint map for a live batch. Its presence locks out per-episode `authorized_keys` mutation. |
| `docs/opencode_probe_remote_broker_design.md` + `.zh.md` | **modify** (currently untracked): fold in A–D, then commit with the implementation. |
| `docs/opencode_scaffold_probe_scope.md` + `.zh.md` | **modify**: the dated check-6 parity amendment. |

---

## Task 1: Empirical transport-headroom calibration

Requirement **B**/**F**. The repository contains **no** untruncated public-tool output: the frozen
driver stores `out[:1500]` *after* a 4000-byte truncation (`scripts/llm_agent_driver.py:742`), and
`agentlog.sanitized.json` is the only committed carrier. So the measurement has to be made, not
mined. It can be: running `run_public.sh` is a local tool invocation, not a model call and not an
episode.

**What this task claims, exactly.** It establishes **empirical transport headroom over the complete
calibration set** — every instance directory either family could serve, with the 24 directories of
the formal panel required to be present and to have actually run the tool. It does **not** prove the
caps can never bind. It cannot: 1 MiB > 8 × 100 KiB is a statement about the instances that were
measured, not about every future PrimeTime invocation, and no finite audit upgrades it into one.

The claim is therefore paired with a runtime property that does not depend on the audit being
exhaustive, implemented in Tasks 2, 4 and 5 and verified in Task 8 control 14:

> A cap hit at runtime is **fail-closed**. The broker emits `transport_output_limit`, the client exits
> 125 with `MEASUREMENT_INVALID`, and **no truncated output is delivered as an agent observation**.
> The episode is infrastructure-invalid. A future 2 MiB `.lis` therefore costs one discarded episode;
> it never becomes a silent new truncation channel contaminating a capability measurement.

Together those two are sufficient. The audit alone is not, and the plan may not be summarised as
though it were.

**Files:**
- Create: `scripts/opencode_probe_raw_output_audit.py`
- Create: `opencode_probe/evidence/raw_output_audit.json` (generated)
- Test: `tests/test_eda_broker.py` (first test lives here)

**The calibration set.** Every directory under `tasks/p15_sta_handoff/` and
`tasks/p16_spice_handoff/` holding `files/run_public.sh` — currently 45 + 10 = 55. Within it, the
**formal panel** is the 24 directories `p15_eval_{0004..0015}_{base,bundles}`, which is exactly what
`docs/opencode_probe_analysis_plan.md` stage 1 would run (12 instances × 2 conditions, *k*=2 → 48
episodes over 24 distinct task directories). Coverage of those 24 is a **precondition of the
verdict**, not a summary statistic: a maximum taken over whichever instances happened to run is the
same failure as an aggregate taken over whichever episodes happened to finish, which this branch
already has a rule against.

`--limit` exists for development and is recorded in the output. A record with `complete: false` may
not carry a `HEADROOM_ESTABLISHED` verdict.

**Interfaces:**
- Consumes: nothing.
- Produces: `opencode_probe/evidence/raw_output_audit.json` with keys
  `{"instances": [{"instance": str, "family": str, "op": str, "stdout_bytes": int,
  "stderr_bytes": int, "artifact_bytes": {name: int}, "rc": int, "elapsed_s": float,
  "tool_ran": bool, "in_formal_panel": bool}],
  "max_stdout_bytes": int, "max_stderr_bytes": int, "max_artifact_bytes": int,
  "p95_stdout_bytes": int, "p99_stdout_bytes": int, "p95_stderr_bytes": int,
  "p99_stderr_bytes": int, "n_instances": int, "n_tool_ran": int,
  "formal_panel": {"expected": [str], "measured": [str], "missing": [str], "complete": bool},
  "complete": bool, "caps": {...}, "headroom": {...},
  "verdict": "HEADROOM_ESTABLISHED"|"INSUFFICIENT_HEADROOM"|"INCOMPLETE",
  "claim": str, "not_claimed": str}`.
  Task 2 reads `caps` from this file.

- [ ] **Step 1: Write the failing test**

Create `tests/test_eda_broker.py` with this content:

```python
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
```

- [ ] **Step 2: Run it to confirm it skips, not passes**

```bash
python3 -m pytest tests/test_eda_broker.py -q -rs
```

Expected: `3 skipped`, with the reason `headroom calibration not yet run (Task 1)`. A *pass* here
would mean the evidence file already exists and the tests are not measuring what they claim.

- [ ] **Step 3: Write the audit script**

Create `scripts/opencode_probe_raw_output_audit.py`:

```python
#!/usr/bin/env python3
"""Measure the RAW byte size of public-tool output, so the broker's transport caps are derived from
evidence rather than from the observation cap.

What this establishes: empirical transport headroom over the complete calibration set. What it does
NOT establish: that a cap can never bind. 1 MiB > 8 x the largest output on 55 measured directories
is a fact about those directories. The property that does not depend on this audit being exhaustive
is the runtime one -- a cap hit is fail-closed, typed transport_output_limit, measurement-invalid,
and never delivered to the agent as truncated tool output.

Zero model calls. This runs `run_public.sh` -- the same script the evaluator runs -- in a scratch
copy of each instance's `files/`, and records how many bytes the tool actually produced before any
truncation. The committed records cannot answer this: the frozen driver stores out[:1500] after a
4000-byte truncation (llm_agent_driver.py:742), so the untruncated size was never persisted.

NOTHING is written into tasks/. Each instance is copied to a scratch directory first; the canonical
fingerprint is asserted before and after, because a test harness writing into the canonical tree
once cost a day and was misattributed to a remote tool outage (docs/incident_golden_corruption.md).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "opencode_probe/evidence/raw_output_audit.json"

# Caps proposed for the broker. The audit's job is to measure the headroom each one has, and to
# refuse a verdict when that headroom is under 8x.
CAPS = {"request_bytes": 2 * 1024 * 1024,
        "stdout_bytes": 1024 * 1024,
        "stderr_bytes": 1024 * 1024,
        "artifact_bytes": 8 * 1024 * 1024}

HEADROOM_FACTOR = 8

ARTIFACTS = {"p15_sta_handoff": [], "p16_spice_handoff": ["hspice_run.lis"]}
FAMILY_OP = {"p15_sta_handoff": "sta_public", "p16_spice_handoff": "spice_public"}

CLAIM = ("empirical transport headroom over the complete calibration set: every measured directory "
         f"left at least {HEADROOM_FACTOR}x headroom under each proposed cap")
NOT_CLAIMED = ("that a cap can never bind. Headroom over a finite calibration set says nothing "
               "about a future invocation. The runtime guarantee is separate and does not depend on "
               "this audit: an over-cap output is typed transport_output_limit, the episode is "
               "measurement-invalid, and no truncated output is delivered as an agent observation.")

# docs/opencode_probe_analysis_plan.md stage 1: all 12 of p15_eval_0004..0015, Base and BundleS.
FORMAL_PANEL = tuple(f"p15_eval_{i:04d}_{c}"
                     for i in range(4, 16) for c in ("base", "bundles"))


def canonical_fingerprint() -> str:
    h = hashlib.sha256()
    for p in sorted((REPO / "tasks").rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(REPO)).encode())
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def _find_tool(root: Path, name: str) -> str | None:
    """Locate a forwarder symlink under the shim mirror without hardcoding a tool version.

    The mirror is EDA_TOOL_ROOT/soft2/synopsys/<tool>/<VERSION>/.../bin/<name>, and the version is
    not this repository's business -- CLAUDE.md's rule is that nothing here hardcodes an EDA path.
    """
    hits = sorted(p for p in Path(root).rglob(f"bin/{name}")
                  if p.is_file() or p.is_symlink())
    return str(hits[0]) if hits else None


def tool_env() -> dict:
    """The frozen tool environment, read from the operator's private shim env.sh.

    `run_public.sh` resolves the tool as `${EDA_PT_CMD:-pt_shell}` and skips when `command -v` fails.
    The shim mirror is NOT on PATH -- env.sh sets only EDA_TOOL_ROOT and B04_HOST -- so the absolute
    shim path has to be supplied here or every instance records SKIP. It is discovered by glob, never
    hardcoded; if env.sh or the mirror is absent the audit records tool_ran=False rather than
    inventing a path.
    """
    env = dict(os.environ)
    shim = os.environ.get("EDA_SHIM_ENV", str(Path.home() / "eda-remote-shim/env.sh"))
    p = Path(shim)
    if not p.is_file():
        p = Path("/data1/tongsb/eda-remote-shim/env.sh")
    if p.is_file():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line.startswith("export ") and "=" in line:
                k, _, v = line[len("export "):].partition("=")
                env.setdefault(k.strip(), v.strip().strip("'\""))
    root = env.get("EDA_TOOL_ROOT")
    if root and Path(root).is_dir():
        for var, name in (("EDA_PT_CMD", "pt_shell"), ("EDA_HSPICE_CMD", "hspice")):
            if var not in env:
                found = _find_tool(Path(root), name)
                if found:
                    env[var] = found
    return env


def measure(instance: Path, env: dict, timeout: int) -> dict:
    family = instance.parent.name
    # An upper bound on any request this instance can produce: the request carries a base64 copy of
    # a SUBSET of files/ (editable + canonical, never the generated file), so the whole directory
    # inflated by 4/3 bounds it from above. Bounding from above is what a cap needs.
    files_total = sum(p.stat().st_size for p in (instance / "files").rglob("*") if p.is_file())
    request_bound = -(-files_total * 4 // 3) + 4096       # base64 + JSON/framing slack
    with tempfile.TemporaryDirectory(prefix="rawaudit_") as td:
        work = Path(td) / "files"
        shutil.copytree(instance / "files", work)
        t0 = time.time()
        try:
            r = subprocess.run(["bash", "run_public.sh"], cwd=work, env=env,
                               capture_output=True, timeout=timeout)
            rc, out, err = r.returncode, r.stdout, r.stderr
            timed_out = False
        except subprocess.TimeoutExpired as e:
            rc, out, err = -1, e.stdout or b"", e.stderr or b""
            timed_out = True
        elapsed = time.time() - t0
        arts = {}
        for name in ARTIFACTS.get(family, []):
            f = work / name
            arts[name] = f.stat().st_size if f.is_file() else 0
    # "SKIP: <tool> not found" is what run_public.sh prints when the tool is unreachable. That is a
    # measurement of nothing, and is recorded as such rather than folded into a maximum.
    tool_ran = not out.startswith(b"SKIP:") and not timed_out
    return {"instance": instance.name, "family": family, "op": FAMILY_OP[family], "rc": rc,
            "stdout_bytes": len(out), "stderr_bytes": len(err),
            "artifact_bytes": arts, "elapsed_s": round(elapsed, 2),
            "files_total_bytes": files_total, "request_upper_bound_bytes": request_bound,
            "timed_out": timed_out, "tool_ran": tool_ran,
            "in_formal_panel": instance.name in FORMAL_PANEL,
            "stdout_head": out[:200].decode("utf-8", "replace")}


def _pct(values: list[int], q: float) -> int:
    if not values:
        return 0
    s = sorted(values)
    return s[min(len(s) - 1, int(q * len(s)))]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Measure raw public-tool output size across the complete calibration set. "
                    "Zero model calls.")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--limit", type=int, default=0,
                    help="0 = every instance. A non-zero value marks the record incomplete and "
                         "forfeits the verdict.")
    a = ap.parse_args()

    before = canonical_fingerprint()
    env = tool_env()
    instances = sorted(
        [p for p in (REPO / "tasks/p15_sta_handoff").iterdir() if (p / "files/run_public.sh").is_file()]
        + [p for p in (REPO / "tasks/p16_spice_handoff").iterdir() if (p / "files/run_public.sh").is_file()],
        key=lambda p: (p.parent.name, p.name))
    if a.limit:
        instances = instances[: a.limit]

    rows = []
    for i, p in enumerate(instances, 1):
        print(f"[{i}/{len(instances)}] {p.parent.name}/{p.name}", flush=True)
        rows.append(measure(p, env, a.timeout))
    after = canonical_fingerprint()
    if before != after:
        raise SystemExit("FATAL: the canonical task tree changed during the audit. "
                         "Restore with `git checkout -- tasks/` and find the writer.")

    ran = [r for r in rows if r["tool_ran"]]
    def mx(key):
        return max([r[key] for r in ran], default=0)
    art_max = max([v for r in ran for v in r["artifact_bytes"].values()], default=0)
    # The request bound does not depend on the tool having run, so it is taken over every measured
    # directory rather than only the ones that reached PrimeTime.
    req_max = max([r["request_upper_bound_bytes"] for r in rows], default=0)

    measured = {r["instance"] for r in rows}
    ran_names = {r["instance"] for r in ran}
    missing = [n for n in FORMAL_PANEL if n not in measured or n not in ran_names]
    panel_complete = not missing
    complete = (a.limit == 0) and panel_complete

    record = {
        "generated_by": "scripts/opencode_probe_raw_output_audit.py",
        "model_calls": 0,
        "claim": CLAIM,
        "not_claimed": NOT_CLAIMED,
        "headroom_factor": HEADROOM_FACTOR,
        "canonical_fingerprint": before,
        "n_instances": len(rows), "n_tool_ran": len(ran),
        "limit": a.limit, "complete": complete,
        "formal_panel": {"expected": list(FORMAL_PANEL),
                         "measured": sorted(n for n in FORMAL_PANEL if n in measured),
                         "missing": missing, "complete": panel_complete},
        "instances": rows,
        "max_stdout_bytes": mx("stdout_bytes"),
        "max_stderr_bytes": mx("stderr_bytes"),
        "max_artifact_bytes": art_max,
        "max_request_upper_bound_bytes": req_max,
        "p95_stdout_bytes": _pct([r["stdout_bytes"] for r in ran], 0.95),
        "p99_stdout_bytes": _pct([r["stdout_bytes"] for r in ran], 0.99),
        "p95_stderr_bytes": _pct([r["stderr_bytes"] for r in ran], 0.95),
        "p99_stderr_bytes": _pct([r["stderr_bytes"] for r in ran], 0.99),
        "caps": CAPS,
        "headroom": {
            "stdout_x": round(CAPS["stdout_bytes"] / mx("stdout_bytes"), 1) if mx("stdout_bytes") else None,
            "stderr_x": round(CAPS["stderr_bytes"] / mx("stderr_bytes"), 1) if mx("stderr_bytes") else None,
            "artifact_x": round(CAPS["artifact_bytes"] / art_max, 1) if art_max else None,
            "request_x": round(CAPS["request_bytes"] / req_max, 1) if req_max else None,
        },
    }
    enough = (len(ran) >= 1
              and mx("stdout_bytes") * HEADROOM_FACTOR <= CAPS["stdout_bytes"]
              and mx("stderr_bytes") * HEADROOM_FACTOR <= CAPS["stderr_bytes"]
              and art_max * HEADROOM_FACTOR <= CAPS["artifact_bytes"]
              and req_max * HEADROOM_FACTOR <= CAPS["request_bytes"])
    record["verdict"] = ("HEADROOM_ESTABLISHED" if (enough and complete)
                        else "INSUFFICIENT_HEADROOM" if not enough
                        else "INCOMPLETE")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({k: record[k] for k in
                      ("n_instances", "n_tool_ran", "complete", "max_stdout_bytes",
                       "max_stderr_bytes", "max_artifact_bytes", "max_request_upper_bound_bytes",
                       "p95_stdout_bytes", "p99_stdout_bytes", "headroom", "verdict")}, indent=2))
    if missing:
        print(f"formal-panel directories missing or tool-absent: {missing}")
    return 0 if record["verdict"] == "HEADROOM_ESTABLISHED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the calibration over the complete set**

```bash
source /data1/tongsb/eda-remote-shim/env.sh
python3 scripts/opencode_probe_raw_output_audit.py
```

Expected: `"verdict": "HEADROOM_ESTABLISHED"`, `complete: true`, exit 0. This runs the real tool on
55 directories and is the slowest step in the plan; do not shorten it with `--limit` and then commit
the record.

If the verdict is `INSUFFICIENT_HEADROOM`, **stop**. Do not raise the caps to make it green — record
the measured maximum, raise the cap to ≥ 8× it, re-run, and note the change in the design doc. A cap
tuned until the check passes is the same failure as a verifier tuned until it prints nothing.

If the verdict is `INCOMPLETE`, some formal-panel directory never ran the tool. That is an
infrastructure fault, not a result. Fix the tool channel and re-run.

- [ ] **Step 5: Run the tests to verify they now pass**

```bash
python3 -m pytest tests/test_eda_broker.py -q
```

Expected: `3 passed`.

- [ ] **Step 6: Confirm the canonical tree is untouched**

```bash
git status --porcelain -- tasks/
python3 -m pytest tests/test_fullpath_check.py -q -k canonical_golden_fingerprint
```

Expected: empty output from `git status`, and the fingerprint test passing.

- [ ] **Step 7: Commit**

```bash
git add scripts/opencode_probe_raw_output_audit.py tests/test_eda_broker.py \
        opencode_probe/evidence/raw_output_audit.json
git commit -m "calibrate transport headroom on measured output, and record what the measurement does not establish"
```

---

## Task 2: The protocol module

Requirement **D**'s schema half. Pure data and pure functions, so every classification and refusal
rule is unit-testable without a network, a sandbox or a tool.

**Files:**
- Create: `scripts/eda_broker/__init__.py`
- Create: `scripts/eda_broker/broker_protocol.py`
- Test: `tests/test_eda_broker.py` (append)

**Interfaces:**
- Consumes: `opencode_probe/evidence/raw_output_audit.json` → `caps` (Task 1).
- Produces:
  - `MAGIC: str = "EDABROKER1"`
  - `EPISODE_RE: re.Pattern` — `^[A-Za-z0-9_.-]{1,64}$`
  - `valid_episode_id(s: str) -> bool`
  - `Op` dataclass with fields
    `name, shim_name, client_argv: tuple[str,...], editable: tuple[str,...],
     canonical: tuple[str,...], generated: tuple[str,...], steps: tuple[tuple[str,...],...],
     artifacts: tuple[str,...]`
  - `OPS: dict[str, Op]` with keys `"sta_public"`, `"spice_public"`
  - `OP_BY_SHIM: dict[str, str]` — `{"pt_shell": "sta_public", "hspice": "spice_public"}`
  - `CAPS: dict[str, int]` — loaded from the audit record, falling back to the literals in it
  - `WORKDIR_TOKEN: str = "@WORKDIR@"`
  - `Status` string constants: `OK`, `TOOL_TIMEOUT`, `REFUSED`, `BROKER_ERROR`, `TRANSPORT_ERROR`,
    `TRANSPORT_OUTPUT_LIMIT`
  - `Refusal(Exception)` with `.reason: str` and `.detail: dict`
  - `TransportOutputLimit(Exception)` with `.detail: dict` — raised when an output exceeds a cap;
    mapped to `Status.TRANSPORT_OUTPUT_LIMIT`, never to a truncation
  - `MEASUREMENT_INVALID: tuple[str, ...]` — the statuses that mean the episode measured
    infrastructure rather than a model
  - `frame(payload: dict) -> bytes` and `unframe(raw: bytes) -> dict`
  - `validate_request(req: dict) -> Op` — raises `Refusal`
  - `input_names(op: Op) -> tuple[str, ...]` — the exact required key set, `editable + canonical`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_eda_broker.py`:

```python
# --------------------------------------------------------------------------------------------
# Task 2 -- protocol
# --------------------------------------------------------------------------------------------

def _proto():
    from eda_broker import broker_protocol as bp
    return bp


def test_episode_id_grammar_is_closed():
    bp = _proto()
    for good in ("p15_eval_0004", "p16_eval_0001", "p15_dev_0000", "a.b-c_1"):
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
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/test_eda_broker.py -q
```

Expected: `ModuleNotFoundError: No module named 'eda_broker'` on the new tests.

- [ ] **Step 3: Implement**

Create `scripts/eda_broker/__init__.py` (empty file, one line):

```python
"""Restricted-SSH EDA broker for the OpenCode external-scaffold probe."""
```

Create `scripts/eda_broker/broker_protocol.py`:

```python
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
    # headroom calibration in Task 1 covers a finite calibration set, so a future invocation may
    # still exceed a cap, and the only safe behaviour then is to spend one discarded episode rather
    # than hand the agent a silently shortened observation. Measurement-invalid, like the two above.
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
```

- [ ] **Step 4: Run the tests**

```bash
python3 -m pytest tests/test_eda_broker.py -q
```

Expected: all Task 1 + Task 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/eda_broker/__init__.py scripts/eda_broker/broker_protocol.py tests/test_eda_broker.py
git commit -m "define the broker op table and wire protocol, with paths unrepresentable by construction"
```

---

## Task 3: The `authorized_keys` managed block

Requirements **A**, **E** and **G**. Never read-modify-write the whole file unguarded.
`~/.ssh/authorized_keys` on b04 currently holds **3 real user keys in 687 bytes**; clobbering them
would lock the operator out of the host that runs every EDA tool.

`$HOME` on b04 is NFS (`qhdx.inspurnfs.com:/data/home/b04`). `flock(2)` there is emulated through the
lock manager, and `nfs(5)` states that NFS offers no cluster-coherent caching and that a partition
can lose locks; `mkdir(2)` documents NFS infelicities of its own. So the mutex is a `mkdir` —
atomic in the create step — but it is **not** described as a correct distributed lock, and its
stale-breaking is deliberately conservative:

| Situation | Action |
|---|---|
| age ≤ `stale_sec` | wait. Never broken, even if the owner is verifiably dead. |
| age > `stale_sec`, owner on **this** host, pid alive | wait. A slow operation is not a dead one. |
| age > `stale_sec`, owner on **this** host, pid gone | **verified death** — quarantine, then re-contest. |
| age > `stale_sec`, owner on another host, or owner record unreadable | liveness **unverifiable** — quarantine by atomic `rename`, then re-contest. Never `rm` in place. |

Quarantine rather than deletion is what makes the unverifiable branch safe. If the old owner is in
fact alive, its lock directory has moved out from under it; when it finishes, its release reads the
owner record, sees a nonce that is not its own, and **removes nothing**. The worst case is two
concurrent rewrites of the managed block, which the atomic-rename write already makes
last-writer-wins on whole-file content rather than a torn file — and requirement **E** removes even
that exposure from the formal arm by making the number of acquisitions two instead of ninety-six.

**Requirement E: the formal arm installs all 48 keys at once.** Per-episode `add_entry` /
`remove_entry` stay in the API and are used by the preflight and any dry run, where there is one
episode and an operator watching. The formal arm uses `add_entries` / `remove_entries`: one mutex
acquisition, one atomic rewrite, 48 lines. During the arm `authorized_keys` is byte-static.

**Files:**
- Create: `scripts/eda_broker/authorized_keys_block.py`
- Test: `tests/test_eda_broker.py` (append)

**Interfaces:**
- Consumes: `broker_protocol.valid_episode_id`.
- Produces:
  - `BEGIN = "# BEGIN EDA-OPENCODE-PROBE"`, `END = "# END EDA-OPENCODE-PROBE"`
  - `class Mutex` — context manager,
    `Mutex(lock_dir: Path, stale_sec: int = 900, wait_sec: float = 30.0, poll_sec: float = 0.25)`,
    with `.nonce`, `.touch()` and `.broken_by_other` set on a release that found a foreign nonce
  - `class LockBusy(RuntimeError)`
  - `list_quarantine(lock_dir: Path) -> list[Path]` — leftover quarantined locks, for `audit`
  - `read_block(path: Path) -> list[str]` — the managed lines only
  - `add_entry(path, episode_id: str, line: str) -> None` — one entry, one rewrite
  - `remove_entry(path, episode_id: str) -> bool`
  - `add_entries(path, entries: list[tuple[str, str]]) -> int` — **batch**: validates every id and
    every line, refuses duplicates, then performs exactly **one** rewrite under **one** mutex
  - `remove_entries(path, episode_ids: list[str]) -> list[str]` — batch removal, one rewrite
  - `list_entries(path) -> list[dict]` — `{"episode": str, "added": str, "line": str}`
  - `reap(path, live: set[str]) -> list[str]` — remove managed entries not in `live`
  - Every mutation is: acquire mutex → read → write temp in the same directory → `fsync` →
    `os.replace` → `fsync` the directory → release.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_eda_broker.py`:

```python
# --------------------------------------------------------------------------------------------
# Task 3 -- authorized_keys managed block
# --------------------------------------------------------------------------------------------

import os
import socket

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
```

`import time` is already needed by Task 4's block; add it to the module imports at the top of the
file when this task lands so the mutex tests can use it.

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/test_eda_broker.py -q
```

Expected: the new tests fail with
`ModuleNotFoundError: No module named 'eda_broker.authorized_keys_block'`.

- [ ] **Step 3: Implement**

Create `scripts/eda_broker/authorized_keys_block.py`:

```python
#!/usr/bin/env python3
"""Manage exactly one delimited region of ~/.ssh/authorized_keys on the remote host.

Four properties, each of which a naive read-modify-write of the whole file would lose:

  * The operator's own keys are never rewritten. b04's authorized_keys holds real login keys; a
    partial write there locks the operator out of the host that runs every EDA tool.
  * Concurrent episodes coexist. The state is not "one probe key at a time" -- it is a set, and
    teardown of episode A may not remove episode B.
  * A crash cannot truncate the file. Mutations write a sibling temp, fsync it, then os.replace.
    A failed mutation leaves the previous file byte-identical and removes its own temp.
  * A whole batch is one mutation. The formal arm installs 48 lines in a single rewrite under a
    single lock, so authorized_keys is byte-static for the duration of the arm.

The mutex is a directory, not flock: $HOME on b04 is NFS, where flock(2) is emulated through the
lock manager and nfs(5) disclaims both cluster-coherent caching and lock survival across a
partition. mkdir(2) is atomic in its create step, which is what a mutex needs -- but it is not a
correct distributed lock, so the stale rule below never breaks a lock on age alone and never
deletes a lock whose owner it cannot prove dead.

This module is shipped to the remote host unchanged and is also unit-tested locally, because it
operates on a path rather than on "the" authorized_keys.
"""

from __future__ import annotations

import errno
import json
import os
import secrets
import socket
import time
from pathlib import Path

from . import broker_protocol as bp

BEGIN = "# BEGIN EDA-OPENCODE-PROBE"
END = "# END EDA-OPENCODE-PROBE"
TAG = "# probe-entry "          # followed by a JSON object: {"episode":..., "added":...}
QUARANTINE_PREFIX = ".quarantine."


class LockBusy(RuntimeError):
    pass


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True            # exists, owned by someone else
    except (OverflowError, ValueError, TypeError):
        return False


class Mutex:
    """Directory mutex with a conservative stale rule.

    Breaking a lock requires BOTH that it is older than `stale_sec` AND that its owner is provably
    gone. "Provably" means: the owner recorded this host and its pid no longer exists. A lock owned
    by another host cannot be proved dead from here, so it is not deleted -- it is renamed aside
    into a quarantine directory and the lock is re-contested. The rename is atomic, so exactly one
    breaker wins, and an owner that was alive after all will find a foreign nonce at release time
    and free nothing.
    """

    def __init__(self, lock_dir, stale_sec: int = 900, wait_sec: float = 30.0,
                 poll_sec: float = 0.25):
        self.dir = Path(lock_dir)
        self.stale_sec = stale_sec
        self.wait_sec = wait_sec
        self.poll_sec = poll_sec
        self.nonce = None
        self.broken_by_other = False

    # -- acquisition ------------------------------------------------------------------------
    def __enter__(self):
        deadline = time.time() + self.wait_sec
        while True:
            self.dir.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.mkdir(str(self.dir), 0o700)      # the atomic step, and the only one
            except OSError as e:
                if e.errno not in (errno.EEXIST,):
                    raise
                if self._try_break():
                    continue
                if time.time() >= deadline:
                    raise LockBusy(f"{self.dir} held by another process")
                time.sleep(self.poll_sec)
                continue
            self.nonce = secrets.token_hex(16)
            self._write_owner()
            return self

    def _write_owner(self) -> None:
        now = time.time()
        (self.dir / "owner").write_text(json.dumps(
            {"owner_host": socket.gethostname(), "owner_pid": os.getpid(),
             "owner_nonce": self.nonce, "created_at": now, "heartbeat": now}))

    def touch(self) -> None:
        """Refresh the heartbeat. Staleness is measured from the heartbeat, so a legitimately long
        operation is never mistaken for a dead one."""
        rec = self._owner()
        if rec.get("owner_nonce") != self.nonce:
            self.broken_by_other = True
            return
        rec["heartbeat"] = time.time()
        (self.dir / "owner").write_text(json.dumps(rec))

    def _owner(self) -> dict:
        try:
            return json.loads((self.dir / "owner").read_text())
        except Exception:
            return {}

    def _try_break(self) -> bool:
        """Return True if the lock was cleared and acquisition should be retried."""
        rec = self._owner()
        last = rec.get("heartbeat") or rec.get("created_at")
        if last is None:
            try:                                    # no readable record: fall back to the mtime
                last = (self.dir / "owner").stat().st_mtime
            except OSError:
                try:
                    last = self.dir.stat().st_mtime
                except OSError:
                    return False                    # gone already; the retry will find out
        if (time.time() - float(last)) <= self.stale_sec:
            return False                            # rule 1: age alone is never enough, and youth
                                                    # is always enough to be left alone
        host, pid = rec.get("owner_host"), rec.get("owner_pid")
        if host == socket.gethostname() and pid is not None:
            if _pid_alive(pid):
                return False                        # slow, not dead
            return self._quarantine()               # verified death
        return self._quarantine()                   # unverifiable: move aside, never rm in place

    def _quarantine(self) -> bool:
        dest = self.dir.parent / (self.dir.name + QUARANTINE_PREFIX
                                  + f"{int(time.time())}." + secrets.token_hex(4))
        try:
            os.rename(str(self.dir), str(dest))
        except OSError:
            pass                # someone else won the race; either way the lock is no longer here
        return True

    # -- release ----------------------------------------------------------------------------
    def __exit__(self, *exc):
        self.release()
        return False

    def release(self) -> None:
        if self.nonce is not None and self._owner().get("owner_nonce") != self.nonce:
            # Our lock was broken while we held it. The directory belongs to someone else now and
            # removing it would free THEIR lock.
            self.broken_by_other = True
            return
        try:
            (self.dir / "owner").unlink()
        except OSError:
            pass
        try:
            self.dir.rmdir()
        except OSError:
            pass


def list_quarantine(lock_dir) -> list[Path]:
    """Quarantined locks left behind by a break. Reported by `audit`: each one is a record that
    somebody's lock was taken from them, which is worth seeing rather than silently cleaning."""
    lock_dir = Path(lock_dir)
    return sorted(p for p in lock_dir.parent.glob(lock_dir.name + QUARANTINE_PREFIX + "*")
                  if p.is_dir())


def _lock_dir(path: Path) -> Path:
    return Path(path).parent / ".eda-probe-akb.lock.d"


def _split(text: str) -> tuple[list[str], list[str], list[str]]:
    """Return (before, managed, after). A file with no block yields (all, [], [])."""
    lines = text.splitlines(keepends=True)
    try:
        b = next(i for i, l in enumerate(lines) if l.strip() == BEGIN)
        e = next(i for i, l in enumerate(lines) if l.strip() == END)
    except StopIteration:
        return lines, [], []
    return lines[:b], lines[b + 1:e], lines[e + 1:]


def _atomic_write(path: Path, text: str) -> None:
    path = Path(path)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    try:
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, text.encode())
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(str(tmp), str(path))
        dfd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if tmp.exists():
            tmp.unlink()


def _render(before, managed, after) -> str:
    body = "".join(before)
    if body and not body.endswith("\n"):
        body += "\n"
    if managed:
        body += BEGIN + "\n" + "".join(managed) + END + "\n"
    return body + "".join(after)


def list_entries(path) -> list[dict]:
    text = Path(path).read_text() if Path(path).is_file() else ""
    _, managed, _ = _split(text)
    out, pending = [], None
    for line in managed:
        if line.startswith(TAG):
            try:
                pending = json.loads(line[len(TAG):])
            except Exception:
                pending = None
        elif line.strip() and pending:
            out.append({"episode": pending.get("episode"), "added": pending.get("added"),
                        "line": line.rstrip("\n")})
            pending = None
    return out


def read_block(path) -> list[str]:
    text = Path(path).read_text() if Path(path).is_file() else ""
    return _split(text)[1]


def _rewrite(path, entries: list[dict]) -> None:
    text = Path(path).read_text() if Path(path).is_file() else ""
    before, _, after = _split(text)
    managed = []
    for e in entries:
        managed.append(TAG + json.dumps({"episode": e["episode"], "added": e["added"]}) + "\n")
        managed.append(e["line"].rstrip("\n") + "\n")
    _atomic_write(Path(path), _render(before, managed, after))


def _check(episode_id: str, line: str) -> None:
    if not bp.valid_episode_id(episode_id):
        raise ValueError(f"illegal episode id: {episode_id!r}")
    if "\n" in line or "\r" in line:
        raise ValueError("an authorized_keys entry may not span lines")


def add_entries(path, entries) -> int:
    """Install several probe keys in ONE rewrite under ONE lock (requirement E).

    Every id and every line is validated before the mutex is taken, so a bad batch cannot leave a
    partially-installed block behind. Duplicate episode ids are refused rather than deduplicated:
    two keys for one episode would survive a teardown keyed on the episode, and the survivor is a
    live capability with no owner.
    """
    entries = [(str(ep), str(line)) for ep, line in entries]
    for ep, line in entries:
        _check(ep, line)
    ids = [ep for ep, _ in entries]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ValueError(f"duplicate episode ids in one batch: {dupes}")
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    with Mutex(_lock_dir(path)):
        keep = [e for e in list_entries(path) if e["episode"] not in set(ids)]
        keep += [{"episode": ep, "added": now, "line": line} for ep, line in entries]
        _rewrite(path, keep)
    return len(entries)


def remove_entries(path, episode_ids) -> list[str]:
    """Remove several probe keys in ONE rewrite under ONE lock. Returns those actually present."""
    wanted = set()
    for ep in episode_ids:
        if not bp.valid_episode_id(ep):
            raise ValueError(f"illegal episode id: {ep!r}")
        wanted.add(ep)
    with Mutex(_lock_dir(path)):
        entries = list_entries(path)
        present = [e["episode"] for e in entries if e["episode"] in wanted]
        if present:
            _rewrite(path, [e for e in entries if e["episode"] not in wanted])
        return present


def add_entry(path, episode_id: str, line: str) -> None:
    """One entry, one rewrite. Kept for the preflight and any single-episode dry run; the formal
    arm uses add_entries so that authorized_keys is not rewritten 48 times."""
    _check(episode_id, line)
    with Mutex(_lock_dir(path)):
        entries = [e for e in list_entries(path) if e["episode"] != episode_id]
        entries.append({"episode": episode_id, "added": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "line": line})
        _rewrite(path, entries)


def remove_entry(path, episode_id: str) -> bool:
    if not bp.valid_episode_id(episode_id):
        raise ValueError(f"illegal episode id: {episode_id!r}")
    with Mutex(_lock_dir(path)):
        entries = list_entries(path)
        keep = [e for e in entries if e["episode"] != episode_id]
        if len(keep) == len(entries):
            return False
        _rewrite(path, keep)
        return True


def reap(path, live: set) -> list[str]:
    """Remove managed entries for episodes that are no longer live. Crash residue is a custody
    problem, not only a race: a probe key outliving its episode is a capability nobody is holding."""
    with Mutex(_lock_dir(path)):
        entries = list_entries(path)
        dead = [e["episode"] for e in entries if e["episode"] not in live]
        if dead:
            _rewrite(path, [e for e in entries if e["episode"] in live])
        return dead
```

- [ ] **Step 4: Run the tests**

```bash
python3 -m pytest tests/test_eda_broker.py -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/eda_broker/authorized_keys_block.py tests/test_eda_broker.py
git commit -m "manage probe keys as one delimited block, installed in one rewrite and never broken on age alone"
```

---

## Task 4: The remote broker (the forced command)

Requirements **C** and **D**'s materialisation half.

**Files:**
- Create: `scripts/eda_broker/remote_broker.py`
- Create: `scripts/eda_broker/broker_sh.template`
- Test: `tests/test_eda_broker.py` (append)

**Interfaces:**
- Consumes: `broker_protocol` (`OPS`, `validate_request`, `frame`, `unframe`, `CAPS`, `Status`,
  `Refusal`, `OP_WALL_CLOCK_SEC`, `KILL_GRACE_SEC`, `MAX_INVOCATIONS_PER_EPISODE`,
  `WORKDIR_TOKEN`).
- Produces:
  - `main(argv) -> int` — the forced-command entry point; `argv[1]` is the episode id
  - `run_step(argv: list[str], cwd: Path, deadline: float, env: dict) -> tuple[int, bytes, bytes, bool]`
    — returns `(rc, stdout, stderr, timed_out)`; runs in its own session and kills the whole group
  - `materialise(op, inputs: dict, workdir: Path, manifest: dict) -> None` — raises `Refusal`
  - `enforce_output_caps(out: bytes, err: bytes, artifacts: dict[str, bytes], caps=None) -> None`
    — raises `TransportOutputLimit`; **never truncates**
  - `limit_response(exc: TransportOutputLimit) -> dict` — the typed, output-free response
  - `_episode_caps(manifest) -> dict` — the calibrated caps, optionally **lowered** by a manifest
    `caps_override`. Lowering only: a manifest can never widen a transport bound. This exists so
    Task 8's control 14 can exercise the fail-closed path on real tool output in one round trip
    instead of manufacturing a genuinely oversized PrimeTime log.
  - `sanitise(text: str, workdir: Path, home: Path) -> str`
  - `SSH_ORIGINAL_COMMAND` appears exactly once in this file, in the deletion line.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_eda_broker.py`:

```python
# --------------------------------------------------------------------------------------------
# Task 4 -- the remote broker
# --------------------------------------------------------------------------------------------

import base64
import hashlib
import os
import signal
import subprocess
import time


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
    rb.enforce_output_caps(b"x" * small, b"", {}, caps={"stdout_bytes": small,
                                                       "stderr_bytes": small,
                                                       "artifact_bytes": small})
    for out, err, arts, kind in ((b"x" * (small + 1), b"", {}, "stdout"),
                                 (b"", b"x" * (small + 1), {}, "stderr"),
                                 (b"", b"", {"hspice_run.lis": b"x" * (small + 1)}, "artifact")):
        with pytest.raises(bp.TransportOutputLimit) as e:
            rb.enforce_output_caps(out, err, arts, caps={"stdout_bytes": small,
                                                        "stderr_bytes": small,
                                                        "artifact_bytes": small})
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


def test_an_illegal_episode_id_in_argv_is_refused(tmp_path):
    """Defence in depth: the host already validated it before writing authorized_keys. The broker
    validates it again, because a forced command is only as trustworthy as whoever wrote the line."""
    rb = _rb()
    assert rb.main(["broker", "../etc"]) != 0
    assert rb.main(["broker"]) != 0
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/test_eda_broker.py -q
```

Expected: the eight new tests fail with `ModuleNotFoundError: No module named 'eda_broker.remote_broker'`.

- [ ] **Step 3: Implement the broker**

Create `scripts/eda_broker/remote_broker.py`:

```python
#!/usr/bin/env python3
"""The forced command. Runs ON the remote EDA host, as the only thing a probe key can do.

Selected by the SERVER, not the client: the episode id arrives in argv from the authorized_keys
line, so an agent holding episode 0004's key cannot request episode 0005 -- there is no field in
which to name one. SSH_ORIGINAL_COMMAND is deleted on entry and never consulted; see the test.

Every exit path cleans up: success, refusal, tool failure, wall-clock timeout and signal. A flow
that overruns is killed by process group, because subprocess timeout alone leaves pt_shell
descendants holding licences and writing into whatever runs next.
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


def bump_invocation(episode_dir: Path) -> int:
    """Server-side rate bound. The agent holds the key by design, so the number of remote tool
    launches it can trigger has to be bounded somewhere other than its own good behaviour."""
    counter = Path(episode_dir) / "invocations"
    n = int(counter.read_text().strip() or 0) if counter.is_file() else 0
    n += 1
    if n > bp.MAX_INVOCATIONS_PER_EPISODE:
        raise bp.Refusal("INVOCATION_CAP", limit=bp.MAX_INVOCATIONS_PER_EPISODE)
    counter.write_text(str(n))
    return n


def materialise(op, inputs: dict, workdir: Path, manifest: dict) -> None:
    """Write the accepted inputs under names from the broker's OWN table.

    No client string is used as a path. Canonical files are hash-checked against the manifest the
    host installed and refused on divergence -- stricter than the frozen runner, which shipped
    whatever was in $PWD and caught tampering at scoring time. Post-hoc detection is enough when
    the consequence is a bad score; it is not enough when the consequence is a leaked oracle,
    because detecting the read afterwards does not un-read it.
    """
    workdir = Path(workdir)
    decoded: dict[str, bytes] = {}
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


def run_step(argv, cwd: Path, deadline: float, env: dict):
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


def sanitise(text: str, workdir: Path, home: Path) -> str:
    """Rewrite remote paths out of anything the agent will see.

    The frozen forwarder did the same (bin/forwarder step 5: sed s|$REMOTE|$CWD|g). Skipping it
    would both depart from the frozen observation and print /home/<user> into an agent transcript
    on a branch that is not anonymised.
    """
    return text.replace(str(workdir), bp.WORKDIR_TOKEN).replace(str(home), bp.HOME_TOKEN)


def _resolve(step, deploy) -> list[str]:
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


def enforce_output_caps(out: bytes, err: bytes, artifacts: dict, caps=None) -> None:
    """Raise if any output exceeds its transport cap. There is deliberately no truncating path.

    Task 1 establishes headroom over a finite calibration set, which is not a proof that a cap can
    never bind. So this has to be safe when one does. Truncating would create a second observation
    cap -- invisible to the agent, absent from the frozen arm, and indistinguishable in a log from
    real tool output. Failing closed costs one episode, marked measurement-invalid.
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
```

- [ ] **Step 4: Write the forced-command wrapper template**

Create `scripts/eda_broker/broker_sh.template`. `broker_admin.py deploy` substitutes `@PYTHON3@`
and `@ROOT@` and installs the result as `<root>/broker.sh`.

```bash
#!/bin/bash
# Forced command for a probe key. The episode id arrives as "$1" from the authorized_keys line and
# is passed through as a single argv element -- there is no eval, no re-parsing and no use of
# SSH_ORIGINAL_COMMAND anywhere in this path.
set -u
export EDA_BROKER_ROOT="@ROOT@"
exec "@PYTHON3@" "@ROOT@/lib/eda_broker/remote_broker.py" "$1"
```

- [ ] **Step 5: Run the tests**

```bash
python3 -m pytest tests/test_eda_broker.py -q
```

Expected: all pass, including the process-tree kill test.

- [ ] **Step 6: Commit**

```bash
git add scripts/eda_broker/remote_broker.py scripts/eda_broker/broker_sh.template tests/test_eda_broker.py
git commit -m "add the forced command: two ops, no client paths, process-group kill, typed refusals"
```

---

## Task 5: The in-sandbox client shim

**Files:**
- Create: `scripts/eda_broker/broker_client.py`
- Test: `tests/test_eda_broker.py` (append)

**Interfaces:**
- Consumes: `broker_protocol`.
- Produces:
  - `op_for_argv0(argv0: str) -> str` — raises `Refusal("UNKNOWN_SHIM")`
  - `check_argv(op, argv: list[str]) -> None` — raises `Refusal("UNEXPECTED_ARGV")`
  - `build_request(op, cwd: Path) -> dict`
  - `ssh_argv(key: Path, known_hosts: Path, host: str) -> list[str]`
  - `emit(resp: dict, cwd: Path, out, err) -> int` — writes artifacts, prints stdout/stderr,
    returns the exit code
  - `main(argv) -> int`
- Exit codes: the tool's own `rc` on `ok`; `124` on `tool_timeout`; `126` on `refused`;
  **`125` on `transport_error`, `broker_error` and `transport_output_limit`** — each of those three
  prints `eda-broker: MEASUREMENT_INVALID <status>: <reason>` on stderr and **no stdout at all**,
  matching the forwarder's `eda-shim: remote execution ... failed` convention so the runner's
  existing log heuristics see a named infrastructure fault rather than tool text.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_eda_broker.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/test_eda_broker.py -q
```

Expected: the new client tests fail on the missing module.

- [ ] **Step 3: Implement**

Create `scripts/eda_broker/broker_client.py`:

```python
#!/usr/bin/env python3
"""In-sandbox client. Installed as `pt_shell` and `hspice`, which is how run_public.sh already
dispatches (EDA_PT_CMD / EDA_HSPICE_CMD), so no hash-pinned canonical file changes.

The client holds a per-episode key and can reach exactly one forced command. It cannot name an
episode: the episode is in the authorized_keys line, not in this protocol. It cannot name a path:
input keys are matched against a fixed per-op set on the far side.

Three failure kinds are kept apart on purpose, because collapsing them would let an infrastructure
fault be recorded as model behaviour -- the measurement-validity rule this project exists to defend.
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


def build_request(op, cwd: Path) -> dict:
    inputs = {}
    for name in bp.input_names(op):
        f = Path(cwd) / name
        if not f.is_file():
            raise bp.Refusal("MISSING_INPUT", file=name)
        inputs[name] = base64.b64encode(f.read_bytes()).decode()
    return {"op": op.name, "inputs": inputs}


def ssh_argv(key: Path, known_hosts: Path, host: str) -> list[str]:
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


def emit(resp: dict, cwd: Path, out, err) -> int:
    status = resp.get("status")
    if status in bp.MEASUREMENT_INVALID:
        # Named the way the frozen forwarder named its own failure, so the runner's log heuristics
        # see an infrastructure fault rather than tool text. No stdout is produced at all: a
        # plausible-looking partial tool log is worse than none, and for transport_output_limit it
        # would be exactly the silent truncation this design refuses to have.
        err.write(f"eda-broker: MEASUREMENT_INVALID {status}: "
                  f"{resp.get('reason')} {resp.get('detail') or ''}\n".rstrip() + "\n")
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
```

- [ ] **Step 4: Run the tests**

```bash
python3 -m pytest tests/test_eda_broker.py -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/eda_broker/broker_client.py tests/test_eda_broker.py
git commit -m "add the pt_shell/hspice client shim, with transport faults typed as measurement-invalid"
```

---

## Task 6: Host-side administration

The only component holding a credential that can write `authorized_keys`. It runs **outside** the
sandbox, before and after each episode.

**Files:**
- Create: `scripts/eda_broker/broker_admin.py`
- Create: `opencode_probe/broker/deploy.json` (generated)
- Create: `opencode_probe/broker/batch.json` (generated, only while a batch is live)
- Test: `tests/test_eda_broker.py` (append)

**Interfaces:**
- Consumes: `broker_protocol`, `authorized_keys_block`.
- Produces the CLI:
  - `deploy` — resolve the remote `python3`; push `broker_protocol.py`, `remote_broker.py`,
    `authorized_keys_block.py` and the rendered `broker.sh` to `<root>/lib/eda_broker/` and
    `<root>/broker.sh`; `mkdir -m 700 <root>/ep`; pin the host key; write
    `opencode_probe/broker/deploy.json` with every remote path, its sha256, the resolved
    interpreter, the resolved `pt_shell`/`hspice` and the host-key fingerprint.
  - `provision --episode <id> --instance <path> --out <dir>` — the **single-episode** path, for the
    preflight and any dry run. Validate the id; `ssh-keygen -t ed25519 -N ''`; build
    `manifest.json` (`{"ops": [...], "sha256": {name: hex}}`) from the instance's `files/`; install
    it into `<root>/ep/<id>/`; add the `authorized_keys` line via the managed block; write
    `<out>/{key,key.pub,known_hosts,provision.json}`.
  - `provision-batch --plan <json> --out <dir>` — the **formal-arm** path (requirement E). Generates
    every key, installs every episode directory, then writes **all** the `authorized_keys` lines in
    one remote `add_entries` call. Writes `opencode_probe/broker/batch.json`.
  - `teardown --episode <id>` — remove the managed entry, `rm -rf <root>/ep/<id>`, then **verify**
    both are gone and report non-zero if either survives.
  - `teardown-batch` — one remote `remove_entries` call for every episode in the batch record,
    `rm -rf` each episode directory, verify both, then delete `batch.json`. Reports non-zero if any
    entry or directory survives.
  - `audit [--reap]` — list managed entries, `<root>/ep/*` and any quarantined lock directories;
    with `--reap`, remove entries and directories with no live provision record.
- Python API used by the preflight and the runner wrapper:
  `provision(episode_id, instance, out_dir) -> dict`, `teardown(episode_id) -> dict`,
  `provision_batch(plan, out_root) -> dict`, `teardown_batch() -> dict`,
  `audit(reap: bool = False) -> dict`, `episode_id(instance, condition, rep) -> str`,
  `formal_arm_plan() -> list[dict]`.

**The batch lock-out.** While `opencode_probe/broker/batch.json` exists, `provision` and `teardown`
refuse to run. That is what makes "`authorized_keys` is byte-static during the arm" a mechanical
property rather than an intention: there is no code path that mutates the file per episode while a
batch is live, so a stray helper or a retry loop cannot reintroduce the 48 rewrites the reviewer
removed.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_eda_broker.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/test_eda_broker.py -q
```

Expected: the five new tests fail on the missing module.

- [ ] **Step 3: Implement**

Create `scripts/eda_broker/broker_admin.py`. Key parts, in full:

```python
#!/usr/bin/env python3
"""Host-side provisioning for the restricted-SSH EDA broker.

This is the only component holding a credential that can write authorized_keys, and it runs outside
the sandbox. The agent never executes any of it.

Per episode: one ed25519 key, one manifest, one managed authorized_keys line, and a teardown that
verifies its own effect rather than assuming it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eda_broker import authorized_keys_block as akb   # noqa: E402
from eda_broker import broker_protocol as bp          # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DEPLOY_RECORD = REPO / "opencode_probe/broker/deploy.json"
BATCH_RECORD = REPO / "opencode_probe/broker/batch.json"
DEFAULT_HOST = "tsb@b04"
DEFAULT_ROOT = "/home/tsb/eda-probe-broker"
REMOTE_AK = "~/.ssh/authorized_keys"

FAMILY_OP = {"p15_sta_handoff": "sta_public", "p16_spice_handoff": "spice_public"}

# docs/opencode_probe_analysis_plan.md stage 1.
FORMAL_INSTANCE_IDS = tuple(f"p15_eval_{i:04d}" for i in range(4, 16))
FORMAL_CONDITIONS = ("Base", "BundleS")
FORMAL_REPS = (0, 1)
CONDITION_DIR = {"Base": "base", "BundleS": "bundles"}


class BatchActive(RuntimeError):
    """A batch is live, so per-episode authorized_keys mutation is refused.

    Requirement E is that the file is byte-static for the whole formal arm. Enforcing it here means
    no retry path, helper or operator habit can quietly reintroduce 48 rewrites on NFS.
    """


def _refuse_if_batch_active() -> None:
    if BATCH_RECORD.is_file():
        raise BatchActive(
            f"{BATCH_RECORD} exists: a batch is live and authorized_keys must stay static. "
            f"Run `teardown-batch` first.")


def episode_id(instance: str, condition: str, rep: int) -> str:
    """One compound token per episode, so `argv` stays length-2 and the forced command needs no
    additional fields. The client cannot forge it: it is in authorized_keys, not in the protocol."""
    ep = f"{instance}__{condition}__rep{int(rep)}"
    if not bp.valid_episode_id(ep):
        raise ValueError(f"illegal episode id from ({instance!r}, {condition!r}, {rep!r}): {ep!r}")
    return ep


def formal_arm_plan() -> list[dict]:
    """The 48 episodes of stage 1, derived rather than listed, so it cannot drift from the analysis
    plan silently. No selection on prior informativeness: all twelve instances, both conditions."""
    return [{"episode": episode_id(inst, cond, rep),
             "instance": f"{inst}_{CONDITION_DIR[cond]}",
             "instance_id": inst, "condition": cond, "rep": rep}
            for inst in FORMAL_INSTANCE_IDS for cond in FORMAL_CONDITIONS for rep in FORMAL_REPS]


def authorized_keys_line(episode_id: str, pubkey: str, root: str, from_addr: str | None) -> str:
    """`restrict` first, because it is default-deny: it implies no-pty, no-X11-forwarding,
    no-port-forwarding, no-agent-forwarding and no-user-rc, and it denies whatever a future
    OpenSSH invents. `command=` is what kills scp, sftp and rsync -- each needs to start its own
    server binary on the remote and none of them ever gets to run one."""
    if not bp.valid_episode_id(episode_id):
        raise ValueError(f"illegal episode id: {episode_id!r}")
    pubkey = pubkey.strip()
    if "\n" in pubkey or "\r" in pubkey:
        raise ValueError("public key must be a single line")
    opts = ["restrict"]
    if from_addr:
        opts.append(f'from="{from_addr}"')
    opts.append(f'command="{root}/broker.sh {episode_id}"')
    return ",".join(opts) + " " + pubkey


def build_manifest(instance: Path) -> dict:
    """sha256 for every canonical input of the instance's op. Contains no oracle and no task
    content, so its presence on the remote is not itself a disclosure."""
    instance = Path(instance)
    op_name = FAMILY_OP[instance.parent.name]
    op = bp.OPS[op_name]
    sha = {}
    for name in op.canonical:
        f = instance / "files" / name
        if not f.is_file():
            raise SystemExit(f"broker_admin: canonical input missing: {f}")
        sha[name] = hashlib.sha256(f.read_bytes()).hexdigest()
    return {"ops": [op_name], "sha256": sha,
            "built": time.strftime("%Y-%m-%dT%H:%M:%S")}


def _ssh(host: str, script: str, input_bytes: bytes | None = None, timeout: int = 120):
    return subprocess.run(["ssh", "-o", "BatchMode=yes", host, "bash", "-lc", script],
                          input=input_bytes, capture_output=True, timeout=timeout)
```

`deploy`, `provision`, `teardown` and `audit` follow the same shape; write them to these contracts:

```python
def deploy(host=DEFAULT_HOST, root=DEFAULT_ROOT, allow_keyscan=False) -> dict:
    """1. Resolve the remote interpreter and tools:
           bash -lc 'command -v python3; command -v pt_shell; command -v hspice'
       2. mkdir -m 700 <root> <root>/lib/eda_broker <root>/ep
       3. Copy broker_protocol.py, remote_broker.py, authorized_keys_block.py, __init__.py into
          <root>/lib/eda_broker/ (base64 over the same ssh channel; no rsync, no scp -- the
          operator's own key is used, but keeping the transfer to one mechanism keeps the deploy
          record honest about what crossed).
       4. Render broker_sh.template with @PYTHON3@ and @ROOT@; install 0700 as <root>/broker.sh.
       5. Pin the host key: prefer the existing entry in ~/.ssh/known_hosts for the host; only fall
          back to ssh-keyscan when allow_keyscan is True, because keyscan trusts whatever answers.
       6. Verify by reading back: sha256 of each installed file must equal the local sha256.
          `Verify that the verification ran` -- do not trust the copy, re-hash it.
       7. Write DEPLOY_RECORD with host, root, python3, pt_shell, hspice, per-file sha256, the host
          key fingerprint, and the local sha256 of each source file.
    """


def provision(episode_id: str, instance: Path, out_dir: Path,
              host=DEFAULT_HOST, root=DEFAULT_ROOT, from_addr=None) -> dict:
    """Single-episode provisioning, for the preflight and any dry run. Refuses while a batch is live.

       0. _refuse_if_batch_active()
       1. Validate episode_id (bp.valid_episode_id) -- before anything else.
       2. ssh-keygen -t ed25519 -N '' -C f'probe-{episode_id}' -f out_dir/key   (0700 out_dir)
       3. build_manifest(instance); install as <root>/ep/<episode_id>/manifest.json with
          mkdir -m 700; write a provision marker holding the pid and start time.
       4. Write the managed authorized_keys entry ON THE REMOTE: ship
          authorized_keys_block.py's add_entry as a one-shot remote python3 call, so the mutex,
          the fsync and the atomic rename all happen on the machine that owns the file.
       5. Copy the pinned known_hosts line into out_dir/known_hosts.
       6. Verify: `ssh -i out_dir/key` reaches the broker and a deliberately malformed request
          comes back REFUSED with reason FRAMING. That proves the key works AND that it reaches
          the forced command rather than a shell -- one round trip, zero model calls.
       7. Write out_dir/provision.json.
    """


def provision_batch(plan: list, out_root: Path,
                    host=DEFAULT_HOST, root=DEFAULT_ROOT, from_addr=None) -> dict:
    """Requirement E: install a whole arm's keys with ONE authorized_keys rewrite.

    Ordering matters and is not arbitrary. Everything that can fail per episode -- keygen, manifest
    construction, remote episode-directory creation -- happens BEFORE the single key install. So a
    failure leaves zero probe keys authorized rather than a partially-authorized arm, and the file
    is touched exactly once on the success path.

       0. Refuse if BATCH_RECORD already exists (an un-torn-down batch is not a thing to stack on).
       1. Validate every episode id and reject duplicates, before any work.
       2. For each entry: mkdir -m 700 <out_root>/<episode>; ssh-keygen; build_manifest for its
          instance; install <root>/ep/<episode>/manifest.json (mkdir -m 700) and the provision
          marker. Nothing is written to authorized_keys in this loop.
       3. ONE remote call to authorized_keys_block.add_entries with all N lines: one mutex, one
          atomic rewrite. Capture the managed-entry count reported back.
       4. Verify, WITHOUT rewriting the file: read back the managed block; assert exactly N entries,
          assert each line's command= names its own episode and no other, and assert the
          non-managed region of the file is byte-identical to the region captured in step 0 (the
          reviewer's first check -- the operator's own three keys).
       5. Round-trip one key -- not all N: send a deliberately malformed request and require
          `REFUSED FRAMING`, proving the key reaches the forced command rather than a shell.
       6. Write BATCH_RECORD: batch_id, episodes, per-episode key fingerprint, the sha256 of the
          non-managed region, and the count. Its presence locks out per-episode mutation.

    Returns {"batch_id", "n": int, "episodes": [...], "user_region_sha256": str, "ok": bool}.
    """


def teardown(episode_id: str, host=DEFAULT_HOST, root=DEFAULT_ROOT) -> dict:
    """Remove the managed entry, rm -rf <root>/ep/<episode_id>, then VERIFY both are gone and
    return {"key_removed": bool, "dir_removed": bool, "ok": bool}. Cleanup is verified rather than
    assumed: an unverified teardown is how a probe key outlives its episode. Refuses while a batch
    is live -- use teardown_batch."""


def teardown_batch(host=DEFAULT_HOST, root=DEFAULT_ROOT) -> dict:
    """Remove every key in the batch record with ONE rewrite, then verify.

       1. Read BATCH_RECORD. Absent -> nothing to do, ok=True, n=0.
       2. ONE remote call to remove_entries with every episode id.
       3. rm -rf <root>/ep/<episode> for each.
       4. VERIFY: the managed block is empty (or absent), no <root>/ep/<episode> survives, and the
          non-managed region's sha256 equals the one recorded at provision time -- so the operator's
          keys are proved unchanged across the whole arm, not just across the install.
       5. Only if all of that holds, unlink BATCH_RECORD. A failed teardown keeps the record, which
          keeps the lock-out in force and makes the residue impossible to ignore.

    Returns {"n", "keys_removed", "dirs_removed", "user_region_unchanged", "survivors", "ok"}.
    """


def audit(host=DEFAULT_HOST, root=DEFAULT_ROOT, reap=False) -> dict:
    """List managed entries, <root>/ep/* and any quarantined lock directories. With reap=True,
    remove every entry and directory with no live provision marker newer than the stale threshold.
    Crash residue is a custody problem. A quarantined lock is reported and never auto-removed: it is
    the record that somebody's lock was taken from them, and that is worth a human looking at it."""
```

Add an `argparse` front end with subcommands `deploy`, `provision`, `provision-batch`, `teardown`,
`teardown-batch`, `audit`, each printing its returned dict as JSON. `provision-batch` accepts
`--plan formal` (meaning `formal_arm_plan()`) or `--plan <path.json>`.

- [ ] **Step 4: Run the tests**

```bash
python3 -m pytest tests/test_eda_broker.py -q
```

Expected: all pass. These are pure-function tests — key generation, the remote paths and the batch
round trip are exercised in Task 8.

- [ ] **Step 5: Deploy to b04 and read back the record**

```bash
python3 -m eda_broker.broker_admin deploy 2>/dev/null || \
  PYTHONPATH=scripts python3 scripts/eda_broker/broker_admin.py deploy
cat opencode_probe/broker/deploy.json
```

Expected: every installed file's remote sha256 equals its local sha256; `python3`, `pt_shell` and
`hspice` all resolved; a host-key fingerprint recorded.

Confirm the operator's own keys are untouched:

```bash
ssh tsb@b04 'grep -c "^ssh-" ~/.ssh/authorized_keys; grep -c EDA-OPENCODE-PROBE ~/.ssh/authorized_keys'
```

Expected: `3` and `0` — three user keys, no managed block yet.

- [ ] **Step 6: Commit**

```bash
git add scripts/eda_broker/broker_admin.py opencode_probe/broker/deploy.json tests/test_eda_broker.py
git commit -m "provision one key per episode, with the episode burned into the server-side forced command"
```

---

## Task 7: Wire the broker into the sandbox

**Files:**
- Modify: `scripts/opencode_probe_agent.py`
- Test: `tests/test_eda_broker.py` (append)

**Interfaces:**
- Consumes: `broker_admin.provision` output directory layout (`key`, `known_hosts`).
- Produces: new in-sandbox paths `/tmp/eda-probe/{key,known_hosts,bin/pt_shell,bin/hspice}`, and
  `EDA_PT_CMD` / `EDA_HSPICE_CMD` pointing at the two shims.

First confirm the file is editable:

```bash
python3 -c "import sys; sys.path.insert(0,'scripts'); \
  from frozen_membership_verify import collect_pins, SCAN_ROOT; \
  print('scripts/opencode_probe_agent.py' in collect_pins(SCAN_ROOT))"
```

Expected `False`. If it prints `True`, **stop** — the file is sha256-pinned and this task needs a
different approach.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_eda_broker.py`:

```python
# --------------------------------------------------------------------------------------------
# Task 7 -- sandbox wiring
# --------------------------------------------------------------------------------------------

def _agent():
    import opencode_probe_agent as a
    return a


def test_the_sandbox_never_mounts_the_users_ssh_directory_or_the_forwarder(tmp_path):
    """The blocker this whole design exists to remove: mounting ~/.ssh and the forwarder gives the
    agent `ssh tsb@b04`, i.e. arbitrary execution on the host where grading deposits the oracles."""
    a = _agent()
    argv = a.bwrap_argv(tmp_path / "ws", tmp_path / "st", Path("/usr/bin/true"), ["true"],
                        ro_binds=[], seal_tool_output=False,
                        broker=a.BrokerMounts(key=tmp_path / "key",
                                              known_hosts=tmp_path / "kh",
                                              bin_dir=tmp_path / "bin"))
    joined = " ".join(argv)
    assert "/.ssh" not in joined
    assert "eda-remote-shim" not in joined
    assert "forwarder" not in joined


def test_the_probe_key_and_shims_are_bound_read_only_at_neutral_paths(tmp_path):
    a = _agent()
    for p, content in (("key", "PRIVATE"), ("kh", "b04 ssh-ed25519 AAAA")):
        (tmp_path / p).write_text(content)
    (tmp_path / "bin").mkdir()
    argv = a.bwrap_argv(tmp_path / "ws", tmp_path / "st", Path("/usr/bin/true"), ["true"],
                        ro_binds=[], seal_tool_output=False,
                        broker=a.BrokerMounts(key=tmp_path / "key",
                                              known_hosts=tmp_path / "kh",
                                              bin_dir=tmp_path / "bin"))
    ro_dests = {argv[i + 2] for i, x in enumerate(argv) if x == "--ro-bind"}
    rw_dests = {argv[i + 2] for i, x in enumerate(argv) if x == "--bind"}
    assert "/tmp/eda-probe/key" in ro_dests
    assert "/tmp/eda-probe/known_hosts" in ro_dests
    assert "/tmp/eda-probe/bin" in ro_dests
    assert not any(d.startswith(a.IN_SANDBOX_BROKER) for d in rw_dests), \
        "no broker mount may be writable -- the agent must not be able to replace its own key"


def test_the_shim_paths_are_exported_so_run_public_sh_dispatches_through_them(tmp_path):
    a = _agent()
    env = a.scrubbed_env(tmp_path / "cfg", tmp_path / "state", api_key="k", broker_enabled=True)
    assert env["EDA_PT_CMD"] == "/tmp/eda-probe/bin/pt_shell"
    assert env["EDA_HSPICE_CMD"] == "/tmp/eda-probe/bin/hspice"
    assert env["EDA_BROKER_KEY"] == "/tmp/eda-probe/key"
    assert env["EDA_BROKER_KNOWN_HOSTS"] == "/tmp/eda-probe/known_hosts"


def test_the_broker_paths_disclose_neither_the_repository_nor_the_remote_user(tmp_path):
    a = _agent()
    env = a.scrubbed_env(tmp_path / "cfg", tmp_path / "state", api_key="k", broker_enabled=True)
    for k in ("EDA_PT_CMD", "EDA_HSPICE_CMD", "EDA_BROKER_KEY", "EDA_BROKER_KNOWN_HOSTS"):
        assert "/data1" not in env[k] and "tsb" not in env[k] and "eda-agentbench" not in env[k]
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/test_eda_broker.py -q
```

Expected: the four new tests fail with `AttributeError: module 'opencode_probe_agent' has no
attribute 'BrokerMounts'`.

- [ ] **Step 3: Modify `scripts/opencode_probe_agent.py`**

Add near the other sandbox constants (after `RESOLV_STUB`):

```python
# Broker mounts, at neutral in-sandbox paths: they name neither the repository, nor the task, nor
# the remote account. /tmp is a bwrap tmpfs, so these are mount points inside it -- unlike /opt,
# which is already a read-only bind and cannot host new children.
IN_SANDBOX_BROKER = "/tmp/eda-probe"
BROKER_KEY = f"{IN_SANDBOX_BROKER}/key"
BROKER_KNOWN_HOSTS = f"{IN_SANDBOX_BROKER}/known_hosts"
BROKER_BIN = f"{IN_SANDBOX_BROKER}/bin"


@dataclass(frozen=True)
class BrokerMounts:
    """Everything the episode's tool channel needs, and nothing else. The agent holds the private
    key by design: it is a capability for two named operations on one episode, not an account. What
    it must NOT hold is ~/.ssh or the forwarder, which is the whole point of this design."""
    key: Path
    known_hosts: Path
    bin_dir: Path
```

(`from dataclasses import dataclass` at the top.)

In `bwrap_argv`, add a `broker: BrokerMounts | None = None` parameter and, just before the
`--chdir`:

```python
    if broker is not None:
        argv += ["--ro-bind", str(broker.key), BROKER_KEY]
        argv += ["--ro-bind", str(broker.known_hosts), BROKER_KNOWN_HOSTS]
        argv += ["--ro-bind", str(broker.bin_dir), BROKER_BIN]
```

In `scrubbed_env`, add a `broker_enabled: bool = False` parameter and, before `return env`:

```python
    if broker_enabled:
        # run_public.sh already dispatches through these two variables, so the broker needs no
        # change to any hash-pinned canonical file. EDA_TOOL_ROOT is deliberately NOT set: the
        # forwarder is not reachable from inside the sandbox and must not appear to be.
        env["EDA_PT_CMD"] = f"{BROKER_BIN}/pt_shell"
        env["EDA_HSPICE_CMD"] = f"{BROKER_BIN}/hspice"
        env["EDA_BROKER_KEY"] = BROKER_KEY
        env["EDA_BROKER_KNOWN_HOSTS"] = BROKER_KNOWN_HOSTS
        env.pop("EDA_TOOL_ROOT", None)
        env.pop("B04_HOST", None)
```

Add a `--broker-dir` CLI flag. When given, `main()` builds the `bin_dir` by copying
`scripts/eda_broker/{__init__,broker_protocol,broker_client}.py` into `<state>/broker/lib/eda_broker/`
and writing two executable launchers `<state>/broker/bin/pt_shell` and `.../hspice`:

```python
#!/bin/sh
exec python3 /tmp/eda-probe/bin/lib/eda_broker/broker_client.py "$@"
```

The launcher must be named `pt_shell` / `hspice` because the client selects its op from `argv[0]`;
the client is reached through `lib/` so its own filename does not have to be the shim name.

Also add `B04_HOST` and `EDA_TOOL_ROOT` to `SCRUB_EXACT`, so a stale forwarder pointer cannot
survive into the sandbox by inheritance.

- [ ] **Step 4: Run the tests**

```bash
python3 -m pytest tests/test_eda_broker.py tests/test_opencode_probe.py -q
```

Expected: all pass. `test_opencode_probe.py` must stay green — the wiring adds a parameter with a
default, so the existing call sites are unaffected.

- [ ] **Step 5: Re-verify the pin status of the edited file**

```bash
python3 -c "import sys; sys.path.insert(0,'scripts'); \
  from frozen_membership_verify import collect_pins, SCAN_ROOT; \
  print('scripts/opencode_probe_agent.py' in collect_pins(SCAN_ROOT))"
scripts/check
```

Expected: `False`, then `1065 pins / 9 missing / 2 mismatch / 1 multi-sha`. **Any other counts mean
stop and investigate** — do not adjust the baseline.

- [ ] **Step 6: Commit**

```bash
git add scripts/opencode_probe_agent.py tests/test_eda_broker.py
git commit -m "bind the per-episode broker capability into the sandbox, and keep ~/.ssh out of it"
```

---

## Task 8: The zero-call preflight

The verdict-bearing task. Fourteen negative controls, a **planted decoy**, cleanup verification, and
a forwarder-equivalence check. No model calls.

**Files:**
- Create: `scripts/opencode_probe_remote_broker_preflight.py`
- Create: `opencode_probe/evidence/remote_broker_preflight.json` (generated)
- Test: `tests/test_eda_broker.py` (append)

**Interfaces:**
- Consumes: `broker_admin.{deploy,provision,provision_batch,teardown,teardown_batch,audit}`,
  `broker_protocol`.
- Produces `opencode_probe/evidence/remote_broker_preflight.json`:
  `{"model_calls": 0, "controls": [{"id": int, "name": str, "attempt": str, "expected": str,
  "observed": str, "pass": bool}], "cleanup": {...}, "equivalence": {...},
  "disclosed_identifiers": [str], "verdict": "PASS"|"FAIL"}`.

### The control battery

| # | Attempt | Must observe |
|---|---|---|
| 1 | `ssh -i key tsb@b04 'cat /etc/passwd'` | forced command runs; the client command is ignored; no valid framed request on stdin → `REFUSED FRAMING` |
| 2 | `{"op":"ls"}` | `REFUSED UNKNOWN_OP` |
| 3 | input key set with an extra name | `REFUSED INPUT_SET_MISMATCH` |
| 4 | input name `../hidden/signoff_intent_truth.json` | `REFUSED ILLEGAL_INPUT_NAME` |
| 5 | `scp -i key file tsb@b04:/tmp/` | fails — no `scp -t` server ever runs |
| 6 | `sftp -i key tsb@b04` | fails — no `sftp-server` |
| 7 | `ssh -tt -i key tsb@b04` | PTY allocation refused |
| 8 | `ssh -L 9999:localhost:22 -i key tsb@b04` | forwarding refused |
| 9 | `ssh -A -i key tsb@b04` | agent forwarding refused, and no socket exists to forward |
| 10 | **cross-episode**: episode 0004's key, request naming 0005 in every way the protocol allows (extra JSON fields, `SSH_ORIGINAL_COMMAND`, argv) | the invocation is served for **0004** or refused; it must never touch 0005's directory |
| 11 | **planted decoy**: write `/tmp/eda_shim_PREFLIGHT/signoff_intent_truth.json` with a unique sentinel, then attempt to reach it through every op and every field | the sentinel never appears in any response; correctness must not depend on `/tmp` being clean |
| 12 | sandbox credential isolation | `~/.ssh` absent, `SSH_AUTH_SOCK` unset, only the probe key and `known_hosts` present under `/tmp/eda-probe` |
| 13 | **batch provision/teardown of the full 48** (requirement E) | the non-managed region of `authorized_keys` is byte-identical before, during and after; the block holds exactly 48 entries during and 0 after; every line forces only its own episode; the operator's 3 keys still authenticate |
| 14 | **cap hit fails closed** (requirement F) | with the caps temporarily lowered below the measured output, the response is `transport_output_limit` with **no** `stdout`/`stderr`/`artifacts` key, and the client exits 125 printing `MEASUREMENT_INVALID` and nothing on stdout |

Controls 1–11 and 13–14 are properties of the remote configuration; 12 is a property of the sandbox.

**Control 11 is why this preflight beats `find /tmp`.** The dry-run report measured 1492
`eda_shim_*` directories holding both families' truth files; those were removed, but the next
grading run recreates them. Proving the tree is empty proves nothing about the next episode. Proving
that a *deliberately planted* truth file is unreachable proves the property the arm needs.

**Control 13 is the one that can lock the operator out of the EDA host**, so it is the one written
most carefully. The comparison is on the **non-managed region** — everything outside
`# BEGIN/END EDA-OPENCODE-PROBE` — captured as a sha256 before the batch, re-read while the 48 keys
are installed, and re-read after teardown. Three reads, not two: a check that only compares before
and after would pass a bug that removed a user key during the arm and restored it at the end. The
control also re-authenticates with the operator's own key while the batch is live, because "the bytes
look right" and "the key still works" are different claims and only the second one is the one that
matters at 2 a.m.

**Control 14 lowers the caps rather than manufacturing a 1 MiB PrimeTime log.** It passes a reduced
`caps` dict to `enforce_output_caps` on the remote side via the episode manifest, so the fail-closed
path is exercised on real tool output. Manufacturing a genuinely oversized output would test the same
branch and take twenty minutes; lowering the threshold tests it in one round trip. What must not
happen — and what the control asserts — is that the reduced-cap response contains a shortened
`stdout` under any key name.

### Cleanup verification

- After each invocation: `<root>/ep/<id>/inv-*` is absent.
- After a deliberate timeout (an op whose remote step is made to overrun): no descendant of the
  killed process group survives — checked with `pgrep -g`.
- After `teardown` / `teardown-batch`: neither the managed `authorized_keys` entries nor
  `<root>/ep/<id>` exist, `batch.json` is gone, and the operator's three user keys are byte-identical
  to before the preflight started.
- No quarantined lock directory was created: `audit` reports `quarantine: []`. A quarantine during a
  preflight with one actor means the stale rule fired when it should not have.

### Forwarder equivalence

The single most valuable parity proof available at zero model cost. For `p15_dev_0000` — and for p15
only:

1. Copy `files/` to scratch A; run `run_public.sh` with the **forwarder** (`EDA_PT_CMD` from
   `env.sh`). Capture stdout, stderr, rc.
2. Copy `files/` to scratch B; run `run_public.sh` with the **broker client**
   (`EDA_PT_CMD=<broker bin>/pt_shell`). Capture stdout, stderr, rc.
3. Normalise both: drop lines matching dates, wall/CPU times, licence check-out lines, PIDs, and
   version banners; rewrite each scratch path to `@WORKDIR@`.
4. Assert the normalised texts are equal and the rcs are equal.

**Why p16 is absent, and why that is a limitation rather than a choice.** The equivalence check needs
an instance outside every studied panel, and for p16 there is none of the studied generation.
`p16_dev_0000` predates the immutable-core scheme: its `build_deck.py` writes `circuit_built.sp` from
scratch with no `circuit_core.sp`, and it ships the built deck in the task. So the op table — which
models `p16_eval_*` — cannot service it, and `build_manifest` refuses it rather than provisioning a
different input set from the one HSPICE will read. Using a studied p16 instance instead is not
available either: it would provision a panel directory from a preflight. The record therefore states
that forwarder equivalence is established **for the PrimeTime path only**, and that the HSPICE path
rests on the shared broker/client code plus the artifact round trip rather than on its own
end-to-end comparison. `test_the_p16_dev_instance_is_an_older_generation_and_is_refused_not_guessed_at`
pins the mechanical facts so this cannot later be read as an oversight.

Record the normalisation regexes in the evidence file. A normalisation that grows until the texts
match is the same failure as a verifier tuned until it prints nothing — so also record how many
lines each regex dropped, and fail if any single regex drops more than 20% of the output.

Additionally record, without failing on them, every remaining host/user/licence identifier in the
broker output. Those that also appear in the forwarder output are **parity** and stay; any that
appear only in the broker output are a new disclosure and **do** fail the check.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_eda_broker.py`:

```python
# --------------------------------------------------------------------------------------------
# Task 8 -- the preflight record
# --------------------------------------------------------------------------------------------

PREFLIGHT = REPO / "opencode_probe/evidence/remote_broker_preflight.json"


@pytest.mark.skipif(not PREFLIGHT.is_file(), reason="remote-broker preflight not yet run (Task 8)")
def test_the_preflight_record_is_complete_and_cost_nothing():
    r = json.loads(PREFLIGHT.read_text())
    assert r["model_calls"] == 0
    ids = sorted(c["id"] for c in r["controls"])
    assert ids == list(range(1, 15)), f"expected 14 controls, got {ids}"
    for c in r["controls"]:
        assert c["observed"], f"control {c['id']} recorded no observation"
    decoy = next(c for c in r["controls"] if c["id"] == 11)
    assert "sentinel" in decoy["attempt"].lower() or "decoy" in decoy["name"].lower()
    assert r["cleanup"]["user_keys_unchanged"] is True
    assert r["cleanup"]["episode_dir_removed"] is True
    assert r["cleanup"]["no_orphan_process"] is True
    assert r["cleanup"]["quarantine"] == []
    assert r["equivalence"]["rc_equal"] is True
    assert r["equivalence"]["normalised_equal"] is True
    assert r["equivalence"]["new_disclosures"] == []


@pytest.mark.skipif(not PREFLIGHT.is_file(), reason="remote-broker preflight not yet run (Task 8)")
def test_the_batch_control_compared_the_user_region_three_times():
    """Requirement E's acceptance check. Before-and-after alone would pass a bug that dropped a user
    key for the duration of the arm and put it back at teardown."""
    r = json.loads(PREFLIGHT.read_text())
    b = next(c for c in r["controls"] if c["id"] == 13)
    assert b["pass"] is True
    d = b["detail"]
    assert d["n_entries_during"] == 48
    assert d["n_entries_after"] == 0
    assert d["user_region_sha256_before"] == d["user_region_sha256_during"] == \
           d["user_region_sha256_after"]
    assert d["operator_key_authenticated_during_batch"] is True
    assert d["every_line_forces_only_its_own_episode"] is True


@pytest.mark.skipif(not PREFLIGHT.is_file(), reason="remote-broker preflight not yet run (Task 8)")
def test_the_cap_hit_control_observed_a_fail_closed_response():
    """Requirement F's acceptance check: a cap hit must arrive as an infrastructure fault carrying no
    output, not as a shortened tool log under any key name."""
    r = json.loads(PREFLIGHT.read_text())
    c = next(x for x in r["controls"] if x["id"] == 14)
    assert c["pass"] is True
    d = c["detail"]
    assert d["status"] == "transport_output_limit"
    assert d["response_keys_with_output"] == []
    assert d["client_exit_code"] == 125
    assert d["client_stdout_bytes"] == 0
    assert "MEASUREMENT_INVALID" in d["client_stderr_head"]


@pytest.mark.skipif(not PREFLIGHT.is_file(), reason="remote-broker preflight not yet run (Task 8)")
def test_the_preflight_does_not_claim_check_5_or_check_7_for_the_formal_arm():
    """Check 5's earlier PASS was established with the tools absent, and this design mounts a tool
    channel. Check 7 is untouched by any of this. Neither may be quietly inherited."""
    r = json.loads(PREFLIGHT.read_text())
    blob = json.dumps(r).lower()
    assert "formal arm authorized" not in blob
    assert r.get("authorizes_formal_arm") is False
```

- [ ] **Step 2: Run to confirm it skips**

```bash
python3 -m pytest tests/test_eda_broker.py -q -rs
```

Expected: four skipped with `remote-broker preflight not yet run (Task 8)`.
- [ ] **Step 3: Implement the preflight**

Create `scripts/opencode_probe_remote_broker_preflight.py`. Structure:

```python
#!/usr/bin/env python3
"""Zero-call preflight for the restricted-SSH EDA broker.

Fourteen negative controls, a planted oracle decoy, a full-size batch key install, a fail-closed cap
hit, verified cleanup, and a forwarder-equivalence check. No model is called; every one of these is a
property of the configuration, the remote host and the sandbox, and a model adds nothing to
establishing them.

This preflight does NOT authorize the formal 48-episode arm. It addresses one blocker. Check 7
remains UNSETTLED and check 5 must be re-established under this configuration -- its earlier PASS
was obtained with the tools absent, which is not the configuration the arm would use.
"""
```

Each control is a function returning
`{"id", "name", "attempt", "expected", "observed", "pass"}`, plus a `"detail"` dict where the control
carries structured facts (13 and 14 do). Two rules for writing them:

- **Record the observation, never a verdict alone.** `"observed": "ssh exit 255, stderr: 'PTY
  allocation request failed'"`, not `"refused"`.
- **A control that cannot run is a FAIL, not a skip.** If `scp` is not installed locally, control 5
  did not establish anything; record `"observed": "scp not available; control did not run"` and
  `"pass": False`. A battery that quietly shrinks is the failure mode this project keeps meeting.

The episode used throughout is `p15_dev_0000` — the only p15 directory outside every studied panel.
Provision a second episode id `p15_dev_0000_x` solely for control 10's cross-episode attempt, and
tear both down.

**Control 13 uses the real 48-episode plan but a dev instance.** It builds
`broker_admin.formal_arm_plan()`'s 48 episode *ids* — because 48 is the number whose NFS exposure
requirement E exists to remove — while pointing every one of them at `p15_dev_0000`'s `files/`. So
the `authorized_keys` write is exactly the size the formal arm would perform, and no studied
instance is provisioned by a preflight. Running the batch does **not** authorize the arm; it
establishes that installing its keys cannot cost the operator their host.

- [ ] **Step 4: Run the preflight**

```bash
source /data1/tongsb/eda-remote-shim/env.sh
python3 scripts/opencode_probe_remote_broker_preflight.py
```

Expected: `"verdict": "PASS"`, exit 0, all fourteen controls passing.

If any control fails, record it and stop. Do not weaken a control to reach a verdict — the point of
the battery is that it can say no.

- [ ] **Step 5: Confirm the remote host is clean afterwards**

```bash
ssh tsb@b04 'grep -c "^ssh-" ~/.ssh/authorized_keys; grep -c EDA-OPENCODE-PROBE ~/.ssh/authorized_keys; ls ~/eda-probe-broker/ep/ | wc -l; ls -d ~/.ssh/.eda-probe-akb.lock.d* 2>/dev/null | wc -l; rm -rf /tmp/eda_shim_PREFLIGHT'
git status --porcelain -- opencode_probe/broker/batch.json
git diff --stat -- tasks/
```

Expected: `3`, `0`, `0`, `0`, no `batch.json`, and an empty diff. The fourth number is the
quarantined-lock count: a preflight with a single actor must never break a lock.

- [ ] **Step 6: Run the tests**

```bash
python3 -m pytest tests/test_eda_broker.py -q
```

Expected: all pass, with the four previously-skipped tests now running.

- [ ] **Step 7: Commit**

```bash
git add scripts/opencode_probe_remote_broker_preflight.py tests/test_eda_broker.py \
        opencode_probe/evidence/remote_broker_preflight.json
git commit -m "prove the capability holds against a planted decoy, not against a clean /tmp"
```

---

## Task 9: Documentation, the check-6 amendment, and the gate

The design doc is currently **untracked**; it lands here, with the four required changes folded in,
in the same commit as the implementation it describes — so its paths resolve without a
`slim_link_check` exemption.

**Files:**
- Modify: `docs/opencode_probe_remote_broker_design.md` and `.zh.md`
- Modify: `docs/opencode_scaffold_probe_scope.md` and `.zh.md`
- Modify: `tests/test_opencode_probe.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_opencode_probe.py`:

```python
def test_check6_is_parity_not_absolute():
    """Check 6's criterion was corrected BEFORE the formal arm, and the correction is recorded as
    a dated amendment rather than by editing the original to look as though it always said this.

    The original demanded the agent "cannot recover the overflow by any path" -- a property the
    frozen control never had either (llm_agent_driver.py:67 does not block redirect-then-read), so
    it would have failed the probe for being EQUAL to the control. The quantity check 6 protects is
    comparability of the observation budget, and parity is that quantity.
    """
    for doc in (SCOPE, SCOPE_ZH):
        text = _flat(doc.read_text())
        assert "AMENDMENT" in doc.read_text() or "修订" in doc.read_text(), \
            f"{doc.name}: the correction must be a dated amendment with its own heading"
        # tightened half: mandatory and explicit
        assert "tool-output" in text and "/tmp/opencode" in text, \
            f"{doc.name}: the backing-store requirement must be explicit, not folded into a general ban"
        # loosened half: parity, not absolute
        assert ("by any path" not in text) or ("superseded" in text or "取代" in text), \
            f"{doc.name}: the absolute wording must be superseded, not left standing"


def test_the_broker_does_not_claim_to_authorize_the_formal_arm():
    design = REPO / "docs/opencode_probe_remote_broker_design.md"
    if not design.is_file():
        pytest.skip("design doc not yet committed")
    for doc in (design, REPO / "docs/opencode_probe_remote_broker_design.zh.md"):
        text = doc.read_text()
        assert "**English | [中文]" in text or "**[English]" in text, f"{doc.name}: missing bilingual header"
    text = _flat(design.read_text())
    assert "does not authorize the formal" in text or "NOT authorize" in design.read_text()


def test_the_broker_caps_are_justified_by_measurement():
    """`64 KiB is 16x the 4000-byte observation cap` is not evidence for a transport bound. The
    design must cite the measured raw-output audit instead."""
    design = REPO / "docs/opencode_probe_remote_broker_design.md"
    if not design.is_file():
        pytest.skip("design doc not yet committed")
    text = _flat(design.read_text())
    assert "raw_output_audit.json" in text, "the caps must cite the measured audit record"
    assert "16x the frozen 4000-byte" not in text and "16× the frozen 4000-byte" not in text, \
        "the superseded justification must be gone"


def test_the_design_states_the_limit_of_the_headroom_claim_and_the_fail_closed_rule():
    """Requirement F, in the document a later reader will quote. Headroom over a finite calibration
    set is not a proof, and the design must say which property covers the gap."""
    for name in ("opencode_probe_remote_broker_design.md",
                 "opencode_probe_remote_broker_design.zh.md"):
        doc = REPO / "docs" / name
        if not doc.is_file():
            pytest.skip("design doc not yet committed")
        raw = doc.read_text()
        text = _flat(raw)
        assert "transport_output_limit" in text, f"{name}: the sixth status must be documented"
        assert "measurement-invalid" in text or "测量无效" in raw, \
            f"{name}: a cap hit must be documented as measurement-invalid"
        assert "calibration set" in text or "校准集" in raw, \
            f"{name}: the headroom claim must name the set it holds over"


def test_the_design_does_not_claim_byte_for_byte_action_parity():
    """The broker hash-pins tool-authoritative inputs to the canonical task version; the frozen
    runner shipped whatever was in $PWD and caught tampering at scoring time. That is a real
    difference in the action surface, and the paper's own section 2 counts the action surface as task
    information -- so it gets recorded, not inferred away."""
    for name in ("opencode_probe_remote_broker_design.md",
                 "opencode_probe_remote_broker_design.zh.md"):
        doc = REPO / "docs" / name
        if not doc.is_file():
            pytest.skip("design doc not yet committed")
        raw = doc.read_text()
        text = _flat(raw)
        for overclaim in ("byte-for-byte action parity", "byte-for-byte parity of the action",
                          "identical action surface", "完全一致的动作面"):
            assert overclaim not in text and overclaim not in raw, \
                f"{name}: unestablished parity claim: {overclaim!r}"
        assert ("pins tool-authoritative inputs" in text
                or "canonical task version" in text
                or "规范任务版本" in raw), \
            f"{name}: the pinning difference must be stated positively, not merely not-denied"
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m pytest tests/test_opencode_probe.py -q
```

Expected: `test_check6_is_parity_not_absolute` fails (the scope doc still carries the absolute
wording) and `test_the_broker_caps_are_justified_by_measurement` fails.

- [ ] **Step 3: Edit `docs/opencode_probe_remote_broker_design.md`**

Nine edits, then mirror each into `.zh.md`:

1. **§2.1** — replace the single sentence about rewriting `authorized_keys` with a subsection
   describing the managed block: the `# BEGIN/END EDA-OPENCODE-PROBE` delimiters, the `mkdir`
   mutex (with the NFS reason — `flock` on `$HOME` is not dependable there), fsync +
   `os.replace`, the guarantee that non-probe lines are never rewritten, that concurrent episodes
   coexist, and that `audit --reap` removes crash residue. State the measured fact that b04's
   `authorized_keys` holds three real user keys.
2. **New §2.2 — batch provisioning (requirement E).** The formal arm installs all 48 public keys in
   **one** atomic rewrite before the arm and removes them in one after; each sandbox mounts only its
   own private key; `authorized_keys` is byte-static for the duration. Give the reason in the
   reviewer's terms rather than as a preference: `nfs(5)` disclaims cluster-coherent caching and
   lock survival across a partition, so 96 mutual-exclusion operations against the operator's real
   login keys is a bet the manual page itself declines to back, and `K_i ⇒ E_i` lives in each line's
   `command=` rather than in when the line was written. State that `batch.json` locks out
   per-episode mutation, and that per-episode `add_entry`/`remove_entry` survive for the preflight
   and dry-run paths.
3. **New §2.3 — the mutex's stale rule (requirement G).** The owner record
   (`owner_host`, `owner_pid`, `owner_nonce`, `created_at`, `heartbeat`) and the four-row decision
   table. Say explicitly that age alone never breaks a lock, that an unverifiable owner is
   quarantined by atomic rename rather than removed, and that release checks its own nonce so a
   broken-but-alive owner frees nothing. Do not describe `mkdir` as a correct distributed lock:
   `mkdir(2)` records NFS infelicities of its own, and the honest claim is that its create step is
   atomic and the rest of the design does not depend on more than that.
4. **§3** — restate the input protocol as the fixed schema it is: exact per-op key set, bare
   basenames only (`^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$`), per-file size caps, **no archive
   extraction of any kind**, and no client-supplied destination. Add a sentence saying the reason
   `tar xf -` is absent rather than hardened: an archive the agent controls can carry `../`,
   absolute paths, symlinks and hardlinks, and a whitelist of names has none of those shapes.
5. **§3.1 — what the canonical-input pinning costs in parity terms.** The broker hash-pins every
   tool-authoritative input to the canonical task version, which the frozen runner did not: it
   shipped whatever was in `$PWD` and caught tampering at scoring time. Record this as what it is —
   *the broker pins tool-authoritative inputs to canonical task versions* — and state plainly that
   the probe therefore **does not** claim byte-for-byte action-surface parity with the frozen
   runner. The tool-call contract is *more* explicit under the broker than under the forwarder. Say
   so here rather than letting a later reader infer parity that was never established; §2 of the
   paper already counts the action surface as task information, so an unclaimed difference in it is
   exactly the kind of thing that must be written down.
6. **§4.1** — replace the `stdout` / `stderr` rows. New values 1 MiB each, `hspice_run.lis` 8 MiB,
   request 2 MiB, with the justification column citing
   `opencode_probe/evidence/raw_output_audit.json` and the measured maximum, and a sentence
   separating the two layers explicitly:
   > The transport cap and the observation cap are different quantities on different layers. 4000
   > bytes is how much the model sees in one observation; the transport cap is how much the broker
   > may return at all. The frozen runner lets an agent redirect a large output to a file and
   > paginate it back, so a transport cap below the real output size would make the probe's action
   > surface *weaker* than the control's. The bound is therefore set from measured raw output —
   > `raw_output_audit.json`, ≥ 8× headroom over the complete calibration set — not from
   > `64 KiB / 4000 B = 16`.

   Then state the limit of that justification, in the record's own words: headroom over a finite
   calibration set is **not** a proof that a cap can never bind, and the design does not rely on one.
7. **New §4.2 — the error taxonomy.** A table of the six statuses (`ok`, `tool_timeout`,
   `refused`, `broker_error`, `transport_error`, `transport_output_limit`), the client exit code for
   each, and the rule that `transport_error`, `broker_error` and `transport_output_limit` are
   **measurement-invalid** and may never be recorded as tool or model behaviour. Include the
   fail-closed statement for `transport_output_limit` (requirement F): the broker returns no
   `stdout`, `stderr` or `artifacts` on a cap hit, the client prints nothing on stdout and exits 125,
   and the episode is discarded. Give the reason a truncation was rejected: it would be a second
   observation cap, invisible to the agent, absent from the frozen arm, and indistinguishable in a
   log from real tool output.

   **State the exit-code limitation honestly in the same subsection.** Both `run_public.sh` scripts
   are canonical, hash-pinned, end in `exit 0` and merge stderr into stdout with `2>&1`. So a client
   exit code of 125 does **not** reach whatever invoked `run_public.sh` — the only carrier that
   survives is the `eda-broker: MEASUREMENT_INVALID <status>:` marker in the merged text, which is
   exactly why it is worded to match the forwarder's own `eda-shim: remote execution … failed`
   convention. Any consumer that classifies episodes must key on the marker, not on a return code.
   The alternative — patching `run_public.sh` — is not available and should not be wanted: it is one
   of the 1020 sha256-pinned task files.
8. **§5** — state the kill discipline: each step runs in its own session (`start_new_session`), a
   wall-clock overrun sends `SIGTERM` then `SIGKILL` to the whole **process group**, and the
   invocation directory is removed on every exit path including signals. Name the consequence being
   avoided: orphan `pt_shell` descendants holding licences and writing into whatever runs next.
9. **§7** — extend the control table from 10 rows to the 14 of Task 8, adding the cross-episode
   control, the planted decoy, the full-size batch install and the fail-closed cap hit, and add the
   sentence: *broker correctness may not depend on b04's `/tmp` being clean; the next grading run
   recreates the mirrors, so the property is established against a deliberately planted truth file
   instead.*

Also correct two facts the draft has slightly wrong: the p15 generated file is
`agent_applied.sdc` (not `applied.sdc`), and `tiny.lib` is not an input to `sta_public`
(`run_public.tcl` reads `tiny.db`).

- [ ] **Step 4: Add the check-6 amendment to `docs/opencode_scaffold_probe_scope.md`**

Append a new section, and mirror it into `.zh.md`. Do **not** edit the original check-6 row — leave
it standing and mark it superseded, so the record shows what changed and when.

```markdown
## Amendment, 2026-08-21 — check 6 becomes a parity criterion

**Superseded wording.** Check 6 read: "confirm the agent cannot recover the overflow *by any
path*". That criterion is withdrawn. It is left in place above rather than rewritten, so the
record shows what was asked before and what is asked now.

**Replacement criterion**, in two halves, one stricter and one weaker:

- **Mandatory (new, stricter):** the OpenCode-specific overflow backing stores
  `<state>/data/opencode/tool-output/*` and `/tmp/opencode/*` must be unreachable. The dry run
  established this by making both read-only; every read returned not-found. This was previously
  folded into a general prohibition and is now an explicit, separately checkable requirement.
- **Permitted (new, weaker):** redirect-then-paginate recovery of an agent-created workspace file
  is allowed, because `scripts/llm_agent_driver.py:67` permits it in the frozen runner too.

**Why this is a pre-arm correction and not a post-hoc rescue.** The distinction matters here more
than usual, because the paper is about not making it loosely:

- It is made **before the formal arm runs**; no formal-arm outcome exists to be read.
- It was provoked by a **dry-run episode that is unscored and discarded by authorization**, on
  `p15_dev_0000` — an instance in no studied panel, carrying no condition variants, so no
  Base/BundleS contrast existed to be seen and none was computed.
- It **tightens as well as loosens**.
- The original criterion demanded a property the *control* never had, and would have failed the
  probe for being **equal to the frozen runner**. That is a defective criterion, not a defective
  probe. What check 6 exists to protect is comparability of the observation budget; parity is
  exactly that quantity.

`test_check6_is_parity_not_absolute` asserts this amendment is present in both languages.
```

- [ ] **Step 5: Run the tests**

```bash
python3 -m pytest tests/test_opencode_probe.py tests/test_eda_broker.py -q
```

Expected: all pass.

- [ ] **Step 6: Run the full gate**

```bash
scripts/check
#   [1] pytest, tool-free subset          expect: 0 failed
#   [2] structural task validation        expect: 84/84
#   [3] frozen membership                 expect: 1065 pins / 9 missing / 2 mismatch / 1 multi-sha

python3 scripts/phase7c_study1_ledger.py      --check
python3 scripts/phase7c_claim_statistics.py   --check
python3 scripts/phase7d_semantic_proxy_gap.py --check
python3 scripts/phase7e_answer_identifiability.py --check
python3 scripts/phase8a_claim_statistics.py   --check
python3 scripts/phase8a_arm2_gate.py          --check
python3 scripts/phase8a_arm2_cost_calibration.py --check
```

Every one must pass with the counts recorded in `CLAUDE.md`. The frozen-membership line is expected
to report non-zero counts; **do not** drive them to zero.

- [ ] **Step 7: Stage everything, then run the link check**

`slim_link_check.py` scans only *tracked* files, so it must run **after** `git add`:

```bash
git add docs/opencode_probe_remote_broker_design.md docs/opencode_probe_remote_broker_design.zh.md \
        docs/opencode_scaffold_probe_scope.md docs/opencode_scaffold_probe_scope.zh.md \
        tests/test_opencode_probe.py
python3 scripts/slim_link_check.py
```

Expected: no dangling references. Every path the design doc names now exists, because the
implementation landed in Tasks 1–8. **If it reports a dangling reference, fix the path — do not add
an entry to `EXEMPT_FILES` or `KNOWN_PROSE`.** A verifier that was taught to look at less is exactly
the false-pass mode this branch's own history records.

- [ ] **Step 8: Verify the manuscript is untouched**

Nothing in this plan changes `submission/`. Confirm:

```bash
git status --porcelain -- submission/
```

Expected: empty. The manuscript build and page-limit gate are therefore not required for this
change.

- [ ] **Step 9: Commit**

```bash
git commit -m "land the broker design with its implementation, and correct check 6 to a parity criterion

The design doc ships in the same commit as the code it describes, so its paths resolve without a
slim_link_check exemption. Check 6's absolute criterion is superseded by a parity one, before the
formal arm runs and against a dry run that is unscored and discarded -- recorded as a dated
amendment beside the original rather than by rewriting it.

Still true after this commit: the formal 48-episode arm is NOT authorized. Check 7 is UNSETTLED,
and check 5 must be re-established under this configuration because its earlier PASS was obtained
with the tools absent."
```

---

## Entry conditions for the next stage

Recorded here before implementation so the bar cannot move afterwards. Four mechanical checks decide
whether the **zero-model preflight with the real EDA tools present** may be treated as established.
They are the reviewer's own list, and each maps to an artifact this plan produces:

| | Check | Where it is decided |
|---|---|---|
| 1 | Batch key provisioning cannot touch the operator's three existing keys | Task 8 control 13 — three sha256 reads of the non-managed region plus a live re-authentication |
| 2 | The planted truth decoy is unreachable through the probe key | Task 8 control 11 |
| 3 | Broker and frozen forwarder produce equivalent *public* observations | Task 8's forwarder-equivalence check, including `new_disclosures == []` |
| 4 | A tool/output cap hit fails closed rather than becoming a hidden new truncation | Task 8 control 14 |

All four passing does **not** authorize the formal arm and does not authorize a paid dry run. The
order is fixed: these four → the tools-present zero-model preflight → only then is a further
discarded, unscored paid dry run worth its cost. Each step is a separate decision with its own
record, and a pass at one level is not evidence at the next. Check 7 stays UNSETTLED throughout.

If any of the four fails, the failure is recorded and the sequence stops there. None of them may be
weakened to obtain a pass: a control that was reworded until it agreed is worth less than no control,
because it also removes the reason anyone would look again.

---

## What this plan does not deliver

Stated here so it cannot be read off the task list as implied:

- **It does not authorize the formal arm.** Check 7 (stop behaviour) is untouched and remains
  UNSETTLED. Check 5 must be re-established under the tools-present configuration; Task 8 is the
  attempt, and its verdict is what it is.
- **It does not make the arm affordable.** No cost projection is produced. The `ARM2_NOT_RUN`
  post-mortem already paid for the lesson that a rate with no measured dispersion may not drive a
  gate.
- **It does not deliver Layer 1.** `n_tool_green_wrong` needs a real green tool signal *and* an
  unreachable oracle. This restores the first while attempting the second; whether both hold at once
  is what Task 8 measures, not what it assumes.
- **It computes no scaffold main effect,** and adds no key, table or script that could.
- **It changes no frozen number.** Nothing here is pooled with, summed into, averaged with or
  differenced against any `a89e084`-derived episode or statistic.
- **It does not establish that a transport cap can never bind.** Task 1 measures headroom over a
  finite calibration set; the property that covers the rest is the fail-closed runtime behaviour, and
  the two must not be conflated into "the caps are non-binding".
- **It does not establish byte-for-byte action-surface parity with the frozen runner.** The broker
  pins tool-authoritative inputs to their canonical task versions, which the frozen runner did not.
  That difference is recorded in the design doc, not resolved.
