#!/usr/bin/env python3
"""Phase-8A execution driver — runs the frozen schedule through the PINNED chain_executor.py.

Chain of custody, and what is new. Pinned and reused byte-identical:
  chain_executor.py     schedule iteration, replacement policy, canonical-integrity verification
                        (pre-run, after every episode, post-chain -> FAILED_INTEGRITY), durable state
  episode_arbiter.py    sole membership authority: ACCEPT / REPLACE / STOP
  llm_agent_driver.py   transport, the single retry authority, telemetry
  the p15 grader + evaluator
New, and deciding nothing about membership:
  phase8a_episode_runner.py   runs one episode, writes the two files classify() reads, keeps custody
  this driver                 which slots are fed, and when the budget says stop

Two reasons this wrapper exists rather than a single chain_executor invocation.

1. Retry budget. The replacement backend throttles (measured 503: 35% back-to-back, 8.3% at 15 s
   spacing). scripts/phase5c_run.py passes --max-chat-retries 1 on the command line and CLI beats
   env, so it cannot be raised there; going through chain_executor --runner leaves it configurable.
   Raised to 6, giving backoff 3/6/12/24/45 s, which reaches the un-throttled regime.
2. Resume. A 216-episode arm runs ~14 h. Blocks are run one per invocation, so a crash costs at most
   one block and completed blocks are skipped. The schedule is block-major, so running blocks in
   order and preserving each block's internal order reproduces the frozen execution order exactly;
   position balance is a within-block property and is untouched.

Usage:
  python3 scripts/phase8a_run.py --arm 1 [--budget 200] [--blocks 3] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
P8A = REPO / "phase8a" / "evidence"
BLOCKS = P8A / "blocks"
# A block aborted mid-way is re-executed whole, and its first pass is ARCHIVED here rather than
# deleted. It leaves the analysis; it does not leave the ledger. See _aborted_spend.
ABORTED = P8A / "aborted"
EXECUTOR = REPO / "scripts" / "chain_executor.py"
EPISODE_RUNNER = REPO / "scripts" / "phase8a_episode_runner.py"
TRACK = "p15_sta_handoff"
TOOL_ROOT = "/data1/tongsb/eda-remote-shim/EDA"
MAX_REPLACEMENTS = 2
MAX_ACTIONS = 60
EPISODE_TIMEOUT = 1800
TEMPERATURE = 0.7
RETRIES = "6"


PROGRAM_CAP = 200.0

# Money paid for an attempt the arbiter REPLACED. Such an attempt leaves no trace in the custody
# tree: phase8a_episode_runner writes `<custody>/<task_id>_r<rep>/episode.json`, the replacement
# re-runs the SAME slot under the SAME trial name, and so overwrites it. Only the last attempt's cost
# survives, and every earlier attempt's cost silently leaves the ledger.
#
# Measured, not hypothetical: arm 2 block 00 paid ¥0.5468 for Base/pos2 attempt 1, then two 503
# attempts costing ¥0 overwrote it, so the tree reports ¥0 for a slot that cost ¥0.5468.
#
# This matters most exactly when it is hardest to notice. Replacements are caused by provider faults,
# faults arrive in clusters, and each cluster erases more spend -- so the cap loosens precisely during
# an outage, which is when a run is burning money for no data. A cap that stops binding under load is
# not a cap. The chain log records every attempt's cost, so the driver harvests it into a durable
# record here; the executor is pinned and is not modified to do it.
ATTEMPT_LEDGER = P8A / "replaced_attempt_ledger.json"


def _ledger_entries():
    if not ATTEMPT_LEDGER.is_file():
        return []
    try:
        return json.loads(ATTEMPT_LEDGER.read_text()).get("entries") or []
    except Exception:  # noqa: BLE001
        return []


def _ledger_spend(model_name: str | None = None) -> float:
    """Spend on replaced attempts, optionally for one model only.

    float(), not just round(): sum([]) is the INT 0, so an existing-but-unmatched ledger printed `0`
    where a missing one printed `0.0` -- the same state serialized two ways.
    """
    return float(round(sum(float(e.get("cost_cny") or 0.0) for e in _ledger_entries()
                          if model_name is None or e.get("model_name") == model_name), 4))


def _pass_id(state_path: Path) -> str:
    """Identity of one pass over a block: the moment chain_executor started it.

    Needed because a block is re-run WHOLE on failure, so (arm, block, trial, attempt) repeats across
    passes and cannot say whether two identical rows are two real payments or one payment banked
    twice. The driver harvests after every pass and phase8a_archive_pass harvests again when the pass
    is archived; without this they would double-count, and a cap inflated by phantom spend stops the
    study early just as surely as one deflated by missing spend lets it overrun.
    """
    try:
        return str(json.loads(state_path.read_text()).get("started_at") or "")
    except Exception:  # noqa: BLE001
        return ""


def _harvest_replaced_attempts(arm: int, block_i: int, block_id: str, model_name: str,
                               log_path: Path, pass_id: str = ""):
    """Record the cost of every attempt superseded in the pass that just ran.

    chain_executor writes one `{"trial": ..., "cost": ...}` line per ATTEMPT. Grouped by trial in
    order, the final line is the attempt whose episode.json survives in custody; all earlier lines are
    money paid for episodes that no longer exist anywhere. Called once per pass, immediately after the
    executor returns, so entries accumulate rather than being recomputed -- a re-run of an archived
    block genuinely paid again, and both passes belong in the ledger.
    """
    if not log_path.is_file():
        return []
    order, seen = [], {}
    for line in log_path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line.startswith('{"trial":'):
            continue
        try:
            rec = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        t = rec.get("trial")
        if t not in seen:
            seen[t] = []
            order.append(t)
        seen[t].append(round(float(rec.get("cost") or 0.0), 4))

    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # Recorded defensively: this runs AFTER the money is spent, so a path shape it did not expect must
    # not be able to throw and lose the ledger entry. Provenance is worth less than the amount.
    try:
        src = str(log_path.resolve().relative_to(REPO))
    except ValueError:
        src = str(log_path)
    new = []
    already = {(e.get("arm"), e.get("block"), e.get("trial"), e.get("attempt"), e.get("pass_id"))
               for e in _ledger_entries()}
    for t in order:
        costs = seen[t]
        for k, c in enumerate(costs[:-1], start=1):   # every attempt but the surviving one
            if pass_id and (arm, block_i, t, k, pass_id) in already:
                continue                              # this pass's payment is already banked
            new.append({"arm": arm, "block": block_i, "block_id": block_id, "trial": t,
                        "attempt": k, "of_attempts": len(costs), "cost_cny": c,
                        "model_name": model_name, "recorded_at": stamp, "pass_id": pass_id,
                        "source_log": src,
                        "why": "superseded by a replacement; its episode.json was overwritten"})
    if not new:
        return []
    ATTEMPT_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    ATTEMPT_LEDGER.write_text(json.dumps(
        {"schema": "phase8a_replaced_attempt_ledger/v1",
         "note": "Cost of attempts the arbiter replaced. These episodes exist in NO custody tree -- "
                 "the replacement overwrote them -- so this is the only record that the money was "
                 "spent. Counts against the ¥200 program cap; enters no analysis, carries no score.",
         "entries": _ledger_entries() + new}, indent=2) + "\n")
    return new


def _program_spend() -> float:
    """Every ¥ this study has paid, wherever the episode landed -- or failed to land.

    Money paid is money paid (prereg section 5B.3 rule 3), so this counts live episodes of EVERY arm,
    archived aborted passes, and the arm-2 cost probe alike. The probe's custody deliberately sits
    outside the grading glob so it can never become a panel point -- but it must still be inside the
    SPEND glob, or the cap silently grows by whatever the probe cost. Replaced attempts have no
    episode.json at all, so they are added from the ledger; see ATTEMPT_LEDGER.
    """
    tot = 0.0
    for f in sorted(P8A.rglob("episode.json")):
        try:
            tot += float(json.loads(f.read_text()).get("total_cost") or 0.0)
        except Exception:  # noqa: BLE001
            pass
    return round(tot + _ledger_spend(), 4)


def _custody(arm: int) -> Path:
    """Where this arm's episodes live. Arm 1 keeps the original tree; later arms get their own.

    This is not tidiness. A trial directory is named `<task_id>_r<rep>` and `rep` restarts at 1 in
    every arm, so arm 2 at k=2 writes EXACTLY the names arm 1 wrote at reps 1 and 2 -- all 72 of
    them, verified against the generated schedule. One shared tree would therefore have overwritten
    72 of arm 1's 216 episodes with a different model's episodes, and left phase8a_report.py grading
    the mixture through a single `episodes/*/episode.json` glob as though it were one arm. The
    preregistration's "a different backend is a different measurement, never pooled" rule would have
    been broken by filename rather than by argument, and the report would have looked normal.
    """
    return P8A / ("episodes" if arm == 1 else f"episodes_arm{arm}")


def _blocks_of(schedule):
    """Split the frozen order into contiguous runs of equal block_id, order preserved."""
    out, cur, cur_id = [], [], None
    for slot in schedule["frozen_execution_order"]:
        if slot["block_id"] != cur_id:
            if cur:
                out.append((cur_id, cur))
            cur, cur_id = [], slot["block_id"]
        cur.append(slot)
    if cur:
        out.append((cur_id, cur))
    return out


def _state_path(arm, i):
    return P8A / f"run_state_arm{arm}_block{i:02d}.json"


def _done(path, n_expected):
    """A block is done only if the executor reported COMPLETE for every slot."""
    if not Path(path).is_file():
        return False
    try:
        d = json.loads(Path(path).read_text())
    except Exception:
        return False
    return d.get("state") == "COMPLETE" and d.get("completed_primary_slots", 0) >= n_expected


def _episode_records(arm_slots, custody: Path):
    """Per-episode records written by phase8a_episode_runner, in schedule order."""
    recs = []
    for s in arm_slots:
        f = custody / f"{s['task_id']}_r{s['rep']}" / "episode.json"
        if f.is_file():
            try:
                recs.append(json.loads(f.read_text()))
            except Exception:  # noqa: BLE001
                pass
    return recs


def _aborted_spend(model_name: str | None = None):
    """Money paid for episodes of an aborted block pass, archived out of the analysis tree.

    The budget cap is about money, not validity. A discarded pass was still billed, so leaving it out
    would let the gate authorise a block the account cannot actually afford -- the understatement
    grows with every abort. Archive layout: aborted/<pass>/<trial>/episode.json.
    """
    tot = 0.0
    for f in sorted(Path(ABORTED).glob("*/*/episode.json")):
        try:
            d = json.loads(f.read_text())
            # Attribute by the model actually recorded, not by where the archive sits: an arm must
            # not inherit another arm's discarded spend, and directory naming is a weaker key than
            # the episode's own record of which model it paid for.
            if model_name is not None and d.get("model_name") != model_name:
                continue
            tot += float(d.get("total_cost") or 0.0)
        except Exception:  # noqa: BLE001
            pass
    return round(tot, 4)


def _spent_so_far(schedule, custody: Path, model_name: str):
    """This arm's own spend: surviving episodes + its archived passes + its replaced attempts.

    All three are money this arm paid, so all three bind its budget. Attributed by the model recorded
    against the spend rather than by which tree it sits in.
    """
    return round(sum(float(r.get("total_cost") or 0.0)
                     for r in _episode_records(schedule["frozen_execution_order"], custody))
                 + _aborted_spend(model_name) + _ledger_spend(model_name), 4)


def _telemetry_faults(slots, custody: Path):
    """Episodes carrying no evidence a model was ever called.

    A smoke test caught this: when the driver refuses to start, run_single_agentic still grades the
    untouched workspace (0.5 on a p15 task) and writes no agentlog. With no telemetry the arbiter
    falls back to classification_source='legacy_error_scan' and reports measurement_valid=true.
    Every frozen episode instead carries 'request_telemetry'. Unchecked, a systemic transport failure
    becomes a full panel of junk episodes that look collected. An episode with no model call is
    measurement-invalid by definition and is certainly not a capability failure.
    """
    faults = []
    for r in _episode_records(slots, custody):
        why = []
        if not (r.get("total_cost") or 0) > 0:
            why.append(f"total_cost={r.get('total_cost')!r}")
        if "agentlog.sanitized.json" not in (r.get("custody") or {}):
            why.append("no agentlog custody")
        if why:
            faults.append(f"{r.get('trial')}: " + ", ".join(why))
    return faults


def _env(block_file: Path, model_name: str, custody: Path):
    e = dict(os.environ)
    # credential: read from .env explicitly so nothing depends on the driver's CWD
    envf = REPO / ".env"
    if envf.is_file():
        for line in envf.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                e.setdefault(k.strip(), v.strip().strip("'\""))
    if not e.get("TR_API_KEY"):
        raise SystemExit("phase8a_run: TR_API_KEY not provisioned (expected in .env)")
    # The pinned scripts/_llm_request_worker.py reads the credential from its inherited environment
    # by a FIXED candidate list (API_KEY, MIMO_API_KEY, OPENAI_API_KEY, LLM_API_KEY). A custom name
    # never reaches the isolated worker and the request dies as MissingApiKey. Export under a name it
    # accepts; phase8a/models_arm1.json pins the endpoint with a literal api_base, so which gateway
    # is in use is never ambiguous.
    e["API_KEY"] = e["TR_API_KEY"]
    e.update({
        "EDA_TOOL_ROOT": TOOL_ROOT,
        "B04_HOST": e.get("B04_HOST", "tsb@b04"),
        "EDA_PT_CMD": f"{TOOL_ROOT}/soft2/synopsys/prime/V-2023.12/bin/pt_shell",
        "EDA_HSPICE_CMD": f"{TOOL_ROOT}/soft2/synopsys/hspice/V-2023.12/hspice/bin/hspice",
        # thinking models: non-streaming transport censors them mid-reasoning
        "EDA_BENCH_STREAM_RESPONSES": "1",
        "EDA_BENCH_PRESERVE_FINAL_WORKSPACE": "1",
        "EDA_BENCH_LLM_REQUEST_TIMEOUT_SEC": "120",
        "EDA_BENCH_LLM_REQUEST_DEADLINE_SEC": "300",
        "EDA_BENCH_MAX_CHAT_RETRIES": RETRIES,
        "PHASE8A_SCHEDULE": str(block_file),
        "PHASE8A_MODEL_NAME": model_name,
        # Explicit even for arm 1, where it equals the runner's default: which tree an arm writes to
        # is a correctness property, not something to leave to a default that another arm shares.
        "PHASE8A_CUSTODY": str(custody),
    })
    return e


def main() -> int:
    ap = argparse.ArgumentParser(description="Run a Phase-8A arm block by block.")
    ap.add_argument("--arm", type=int, required=True, choices=(1, 2))
    # Default is this ARM'S SHARE of the program cap, not the whole cap. Arm 1 was the only spender,
    # so "cumulative" and "arm 1's own" were the same number and a literal 200 was harmless. For arm 2
    # they differ by everything already spent (arm 1 + the cost probe), and _spent_so_far counts only
    # the arm's own episodes -- so a default of 200 would have authorised arm 2 to spend a second
    # ¥200 on top of the first. The cap belongs to the program; it is not a flag to remember.
    ap.add_argument("--budget", type=float, default=None,
                    help="cap on THIS ARM's spend, CNY; default = 200 minus all other Phase-8A spend")
    # Measured, not guessed: block 00's 18 episodes cost ¥17.3237, i.e. ¥0.962/episode -- 2.15x the
    # ¥0.447 Amendment 1 projected, because _cost() bills every retried attempt's prompt and this
    # backend throttles. A per-slot figure BELOW the real rate makes the gate authorise a block the
    # budget cannot cover, so the default tracks the measurement. See prereg Amendment 2.
    ap.add_argument("--per-slot", type=float, default=0.962,
                    help="projected CNY/episode for the gate (measured block-00 mean)")
    ap.add_argument("--blocks", type=int, default=None, help="run at most N blocks this invocation")
    # Default follows the arm rather than pinning arm 1's file. Arm 2 running under arm 1's models
    # config would have silently billed DeepSeek episodes at Qwen's output rate and, worse, sent
    # --model-name qwen3.7-max to a runner that resolves the entry BY NAME -- so the S3 arm would
    # have measured the S2-F model. An arm is not a flag you remember to change.
    ap.add_argument("--models", default=None,
                    help="models config; defaults to phase8a/models_arm{arm}.json")
    ap.add_argument("--dry-run", action="store_true", help="plan only; make no model call")
    a = ap.parse_args()
    if a.models is None:
        a.models = f"phase8a/models_arm{a.arm}.json"

    # The runner resolves its model entry by NAME, so the name must come from the config that is
    # actually being used -- never from a literal in this file.
    cfg = json.loads((REPO / a.models).read_text())
    entries = [m for m in cfg.get("models", []) if not str(m.get("name", "")).startswith("_")]
    if len(entries) != 1:
        raise SystemExit(f"phase8a_run: {a.models} must hold exactly one model entry, "
                         f"found {len(entries)} -- one slot must not fan out across models")
    model_name = entries[0]["name"]

    sched_path = P8A / f"schedule_arm{a.arm}.json"
    if not sched_path.is_file():
        raise SystemExit(f"phase8a_run: missing frozen schedule {sched_path}")
    schedule = json.loads(sched_path.read_text())
    blocks = _blocks_of(schedule)
    custody = _custody(a.arm)
    spent = _spent_so_far(schedule, custody, model_name)
    other_spend = round(_program_spend() - spent, 4)
    if a.budget is None:
        a.budget = round(PROGRAM_CAP - other_spend, 4)

    print(json.dumps({"arm": a.arm, "model": schedule["model"], "blocks": len(blocks),
                      "episodes": schedule["episodes"], "budget_cny": a.budget,
                      "already_spent_cny": spent,
                      "spent_by_the_rest_of_phase8a_cny": other_spend,
                      "program_cap_cny": PROGRAM_CAP,
                      "custody": str(custody.relative_to(REPO)),
                      "of_which_aborted_passes_cny": _aborted_spend(model_name),
                      "of_which_replaced_attempts_cny": _ledger_spend(model_name),
                      "per_slot_projection_cny": a.per_slot,
                      "transport": {"max_chat_retries": int(RETRIES), "stream": True,
                                    "concurrency": 1},
                      "done_blocks": sum(1 for i, (_, s) in enumerate(blocks)
                                         if _done(_state_path(a.arm, i), len(s)))}, indent=2),
          flush=True)
    if a.dry_run:
        return 0

    manifest = P8A / "prerun_manifest.json"
    if not manifest.is_file():
        raise SystemExit("phase8a_run: run scripts/phase8a_preflight.py first (no prerun manifest)")

    BLOCKS.mkdir(parents=True, exist_ok=True)
    custody.mkdir(parents=True, exist_ok=True)
    (REPO / "runs" / "phase8a").mkdir(parents=True, exist_ok=True)
    # Fail closed on cross-arm contamination. An episode carrying another model's name in this arm's
    # tree means the custody separation has already failed, and the report would grade a mixture.
    foreign = sorted(f.parent.name for f in custody.glob("*/episode.json")
                     if (json.loads(f.read_text()).get("model_name") or model_name) != model_name)
    if foreign:
        raise SystemExit(f"phase8a_run: {len(foreign)} episode(s) in {custody.name} were run by a "
                         f"different model than {model_name} (e.g. {foreign[:3]}). Arms are separate "
                         f"measurements and are never pooled; resolve before spending.")
    ran = 0
    for i, (block_id, slots) in enumerate(blocks):
        state = _state_path(a.arm, i)
        if _done(state, len(slots)):
            print(f"[{i + 1}/{len(blocks)}] {block_id} complete -- skip", flush=True)
            continue
        if a.blocks is not None and ran >= a.blocks:
            print(json.dumps({"stopped": "block_limit", "ran": ran}), flush=True)
            break

        spent = _spent_so_far(schedule, custody, model_name)
        remaining = round(a.budget - spent, 4)
        if remaining <= len(slots) * a.per_slot:
            print(json.dumps({"stopped": "budget", "at_block": i, "spent_cny": spent,
                              "remaining_cny": remaining}), flush=True)
            break

        bf = BLOCKS / f"arm{a.arm}_block{i:02d}.json"
        head = {k: v for k, v in schedule.items() if k not in ("frozen_execution_order", "flat")}
        bf.write_text(json.dumps({**head, "block_id": block_id, "episodes": len(slots),
                                  "frozen_execution_order": slots, "flat": slots},
                                 indent=2) + "\n")

        # Arm-scoped, like the state file and the custody tree. Unscoped, arm 2 block 00 overwrote
        # arm 1's chain_b00.log -- and that log is the ONLY per-attempt cost record for its pass, so
        # the fourth instance of "an arm-scoped quantity written as a global" destroyed the very
        # evidence the new ledger harvests. Arm 1 block 00 happened to have no replaced attempt, so
        # nothing was lost; that was luck, not design.
        chain_log = REPO / "runs" / "phase8a" / f"chain_a{a.arm}_b{i:02d}.log"
        cmd = [sys.executable, str(EXECUTOR),
               "--schedule", str(bf), "--models", str(REPO / a.models), "--track", TRACK,
               "--runner", str(EPISODE_RUNNER), "--model-name", model_name,
               "--results-prefix", str(REPO / "runs" / "phase8a" / f"a{a.arm}"),
               "--state", str(state), "--log", str(chain_log),
               "--max-replacements", str(MAX_REPLACEMENTS), "--max-actions", str(MAX_ACTIONS),
               "--timeout", str(EPISODE_TIMEOUT), "--temperature", str(TEMPERATURE),
               "--elicit-confidence", "--integrity-manifest", str(manifest)]
        t0 = time.time()
        print(f"[{i + 1}/{len(blocks)}] {block_id}: {len(slots)} slots, budget left ¥{remaining}",
              flush=True)
        rc = subprocess.run(cmd, env=_env(bf, model_name, custody), cwd=str(REPO)).returncode
        ran += 1
        # Before any early return below: a replaced attempt's cost must be banked even when the pass
        # then fails, because a failing pass is exactly the pass that replaced the most attempts.
        harvested = _harvest_replaced_attempts(a.arm, i, block_id, model_name, chain_log,
                                               _pass_id(state))
        if harvested:
            print(json.dumps({"replaced_attempt_spend_recorded": len(harvested),
                              "cny": round(sum(e["cost_cny"] for e in harvested), 4),
                              "into": str(ATTEMPT_LEDGER.relative_to(REPO))}), flush=True)
        print(f"[{i + 1}/{len(blocks)}] rc={rc} in {round(time.time() - t0)}s "
              f"cumulative ¥{_spent_so_far(schedule, custody, model_name)}", flush=True)

        if rc == 3:
            print(json.dumps({"stopped": "FAILED_INTEGRITY", "at_block": i,
                              "note": "the canonical tree was mutated mid-run. Do NOT restore and "
                                      "continue: find the writer first."}), flush=True)
            return 3
        faults = _telemetry_faults(slots, custody)
        if faults:
            print(json.dumps({"stopped": "telemetry_faults", "at_block": i, "detail": faults[:6],
                              "note": "episodes with no evidence of a model call are "
                                      "measurement-invalid; fix the cause, delete this block's "
                                      "state, re-run. Completed blocks are skipped."}, indent=2),
                  flush=True)
            return 2
        if rc != 0:
            print(json.dumps({"stopped": "executor_exit", "at_block": i, "rc": rc,
                              "note": "rc=2 means the arbiter hit STOP: a slot stayed "
                                      "measurement-invalid past the replacement cap."}), flush=True)
            return rc

    print(json.dumps({"arm": a.arm,
                      "spent_cny": _spent_so_far(schedule, custody, model_name),
                      "budget_cny": a.budget,
                      "blocks_complete": sum(1 for i, (_, s) in enumerate(blocks)
                                             if _done(_state_path(a.arm, i), len(s))),
                      "blocks_total": len(blocks)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
