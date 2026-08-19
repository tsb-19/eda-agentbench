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
CUSTODY = P8A / "episodes"
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


def _episode_records(arm_slots):
    """Per-episode records written by phase8a_episode_runner, in schedule order."""
    recs = []
    for s in arm_slots:
        f = CUSTODY / f"{s['task_id']}_r{s['rep']}" / "episode.json"
        if f.is_file():
            try:
                recs.append(json.loads(f.read_text()))
            except Exception:  # noqa: BLE001
                pass
    return recs


def _aborted_spend():
    """Money paid for episodes of an aborted block pass, archived out of the analysis tree.

    The budget cap is about money, not validity. A discarded pass was still billed, so leaving it out
    would let the gate authorise a block the account cannot actually afford -- the understatement
    grows with every abort. Archive layout: aborted/<pass>/<trial>/episode.json.
    """
    tot = 0.0
    for f in sorted(Path(ABORTED).glob("*/*/episode.json")):
        try:
            tot += float(json.loads(f.read_text()).get("total_cost") or 0.0)
        except Exception:  # noqa: BLE001
            pass
    return round(tot, 4)


def _spent_so_far(schedule):
    return round(sum(float(r.get("total_cost") or 0.0)
                     for r in _episode_records(schedule["frozen_execution_order"]))
                 + _aborted_spend(), 4)


def _telemetry_faults(slots):
    """Episodes carrying no evidence a model was ever called.

    A smoke test caught this: when the driver refuses to start, run_single_agentic still grades the
    untouched workspace (0.5 on a p15 task) and writes no agentlog. With no telemetry the arbiter
    falls back to classification_source='legacy_error_scan' and reports measurement_valid=true.
    Every frozen episode instead carries 'request_telemetry'. Unchecked, a systemic transport failure
    becomes a full panel of junk episodes that look collected. An episode with no model call is
    measurement-invalid by definition and is certainly not a capability failure.
    """
    faults = []
    for r in _episode_records(slots):
        why = []
        if not (r.get("total_cost") or 0) > 0:
            why.append(f"total_cost={r.get('total_cost')!r}")
        if "agentlog.sanitized.json" not in (r.get("custody") or {}):
            why.append("no agentlog custody")
        if why:
            faults.append(f"{r.get('trial')}: " + ", ".join(why))
    return faults


def _env(block_file: Path, model_name: str):
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
    })
    return e


def main() -> int:
    ap = argparse.ArgumentParser(description="Run a Phase-8A arm block by block.")
    ap.add_argument("--arm", type=int, required=True, choices=(1, 2))
    ap.add_argument("--budget", type=float, default=200.0, help="hard cumulative cap, CNY")
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
    spent = _spent_so_far(schedule)

    print(json.dumps({"arm": a.arm, "model": schedule["model"], "blocks": len(blocks),
                      "episodes": schedule["episodes"], "budget_cny": a.budget,
                      "already_spent_cny": spent,
                      "of_which_aborted_passes_cny": _aborted_spend(),
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
    (REPO / "runs" / "phase8a").mkdir(parents=True, exist_ok=True)
    ran = 0
    for i, (block_id, slots) in enumerate(blocks):
        state = _state_path(a.arm, i)
        if _done(state, len(slots)):
            print(f"[{i + 1}/{len(blocks)}] {block_id} complete -- skip", flush=True)
            continue
        if a.blocks is not None and ran >= a.blocks:
            print(json.dumps({"stopped": "block_limit", "ran": ran}), flush=True)
            break

        spent = _spent_so_far(schedule)
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

        cmd = [sys.executable, str(EXECUTOR),
               "--schedule", str(bf), "--models", str(REPO / a.models), "--track", TRACK,
               "--runner", str(EPISODE_RUNNER), "--model-name", model_name,
               "--results-prefix", str(REPO / "runs" / "phase8a" / f"a{a.arm}"),
               "--state", str(state), "--log", str(REPO / "runs" / "phase8a" / f"chain_b{i:02d}.log"),
               "--max-replacements", str(MAX_REPLACEMENTS), "--max-actions", str(MAX_ACTIONS),
               "--timeout", str(EPISODE_TIMEOUT), "--temperature", str(TEMPERATURE),
               "--elicit-confidence", "--integrity-manifest", str(manifest)]
        t0 = time.time()
        print(f"[{i + 1}/{len(blocks)}] {block_id}: {len(slots)} slots, budget left ¥{remaining}",
              flush=True)
        rc = subprocess.run(cmd, env=_env(bf, model_name), cwd=str(REPO)).returncode
        ran += 1
        print(f"[{i + 1}/{len(blocks)}] rc={rc} in {round(time.time() - t0)}s "
              f"cumulative ¥{_spent_so_far(schedule)}", flush=True)

        if rc == 3:
            print(json.dumps({"stopped": "FAILED_INTEGRITY", "at_block": i,
                              "note": "the canonical tree was mutated mid-run. Do NOT restore and "
                                      "continue: find the writer first."}), flush=True)
            return 3
        faults = _telemetry_faults(slots)
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

    print(json.dumps({"arm": a.arm, "spent_cny": _spent_so_far(schedule), "budget_cny": a.budget,
                      "blocks_complete": sum(1 for i, (_, s) in enumerate(blocks)
                                             if _done(_state_path(a.arm, i), len(s))),
                      "blocks_total": len(blocks)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
