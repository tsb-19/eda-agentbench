#!/usr/bin/env python3
"""Phase-8A execution driver — runs the frozen schedule through the PINNED phase5c_run.py.

Why a wrapper at all. `scripts/phase5c_run.py` is the project's paid-run orchestrator: it owns
custody, the arbiter verdicts, validity-only replacement, the budget ceiling and durable state, and
it is sha256-pinned, so it is reused byte-identical. But it rebuilds its state from scratch on every
invocation -- there is no resume. A single 216-episode arm runs ~14 h at the Phase-7A observed pace
of ~238 s/episode, and a crash at episode 200 would discard all of it.

So this driver slices the frozen schedule at its OWN BLOCK BOUNDARIES and runs one block per
invocation. The schedule is block-major, so running blocks in order and preserving each block's
internal order reproduces the frozen execution order exactly -- position balance is a within-block
property and is untouched. A crash now costs at most one block (~70 min), and completed blocks are
skipped on restart.

It adds no membership logic. The arbiter remains the sole membership authority; this driver only
decides which slots are fed and stops when the budget says stop.

Usage:
  python3 scripts/phase8a_run.py --arm 1 [--budget 200] [--per-slot 0.7] [--dry-run]
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
RUNNER = REPO / "scripts" / "phase5c_run.py"
GATEWAY = REPO / "phase8a" / "gateway.env"


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
    """A block counts as done only if its state is terminal AND every slot produced a record."""
    if not path.is_file():
        return False
    try:
        d = json.loads(path.read_text())
    except Exception:
        return False
    return d.get("status") in ("complete", "incomplete_collection_budget_stop") and \
        len(d.get("episodes", [])) >= n_expected


def _spent_so_far(arm):
    total = 0.0
    for p in sorted(P8A.glob(f"run_state_arm{arm}_block*.json")):
        try:
            total += float(json.loads(p.read_text()).get("spent") or 0.0)
        except Exception:
            pass
    return round(total, 4)


def _telemetry_faults(state_path):
    """Episodes that the arbiter called valid but that carry NO evidence a model was called.

    A smoke test caught this: when the driver refuses to start (in that case a config entry whose
    credential was absent), run_single_agentic still grades the untouched workspace -- 0.5 on a p15
    task -- and no agentlog is written. With no telemetry the arbiter falls back to
    `legacy_error_scan` and reports measurement_valid=true. Every frozen episode instead carries
    classification_source='request_telemetry'.

    Left unchecked that turns a systemic failure into a full panel of junk episodes that look
    collected. An episode with no model call is measurement-invalid by definition; it is certainly
    not a capability failure. The arbiter is pinned, so the check lives here and it aborts the run
    rather than continuing to spend.
    """
    faults = []
    try:
        d = json.loads(Path(state_path).read_text())
    except Exception:
        return [f"{state_path}: unreadable state"]
    for e in d.get("episodes", []):
        if e.get("aborted"):
            continue
        cls = (e.get("final") or {}).get("classification") or {}
        why = []
        if cls.get("classification_source") != "request_telemetry":
            why.append(f"classification_source={cls.get('classification_source')!r}")
        if not (e.get("total_cost") or 0) > 0:
            why.append(f"total_cost={e.get('total_cost')!r}")
        if "agentlog.sanitized.json" not in (e.get("custody") or {}):
            why.append("no agentlog custody")
        if why:
            faults.append(f"{e.get('trial')}: " + ", ".join(why))
    return faults


def main() -> int:
    ap = argparse.ArgumentParser(description="Run a Phase-8A arm block by block.")
    ap.add_argument("--arm", type=int, required=True, choices=(1, 2))
    ap.add_argument("--budget", type=float, default=200.0, help="hard cumulative cap, CNY")
    ap.add_argument("--per-slot", type=float, default=0.7,
                    help="projected CNY/episode used by the runner's stop gate")
    ap.add_argument("--dry-run", action="store_true", help="plan only; make no model call")
    args = ap.parse_args()

    sched_path = P8A / f"schedule_arm{args.arm}.json"
    if not sched_path.is_file():
        raise SystemExit(f"phase8a_run: missing frozen schedule {sched_path}")
    schedule = json.loads(sched_path.read_text())
    blocks = _blocks_of(schedule)

    if not args.dry_run and not GATEWAY.is_file():
        raise SystemExit(
            f"phase8a_run: missing {GATEWAY}. It must define API_KEY and BASE_URL for the "
            "replacement backend, and must stay gitignored (it holds a credential).")

    plan = {"arm": args.arm, "model": schedule["model"], "blocks": len(blocks),
            "episodes": schedule["episodes"], "budget_cny": args.budget,
            "already_spent_cny": _spent_so_far(args.arm),
            "block_sizes": sorted({len(b) for _, b in blocks})}
    print(json.dumps(plan, indent=2), flush=True)
    if args.dry_run:
        return 0

    BLOCKS.mkdir(parents=True, exist_ok=True)
    for i, (block_id, slots) in enumerate(blocks):
        state = _state_path(args.arm, i)
        if _done(state, len(slots)):
            print(f"[block {i + 1}/{len(blocks)}] {block_id} already complete -- skipping",
                  flush=True)
            continue

        spent = _spent_so_far(args.arm)
        remaining_budget = round(args.budget - spent, 4)
        if remaining_budget <= len(slots) * args.per_slot:
            print(json.dumps({"stopped": "budget", "at_block": i, "spent_cny": spent,
                              "remaining_cny": remaining_budget}), flush=True)
            break

        bf = BLOCKS / f"arm{args.arm}_block{i:02d}.json"
        bf.write_text(json.dumps({**{k: v for k, v in schedule.items()
                                     if k not in ("frozen_execution_order", "flat")},
                                  "block_id": block_id,
                                  "frozen_execution_order": slots}, indent=2) + "\n")

        env = dict(os.environ)
        env.update({
            "PHASE5_SCHEDULE": str(bf.relative_to(REPO)),
            "PHASE5_RUNS": "runs/phase8a",
            "PHASE5_EVIDENCE": "phase8a/evidence/episodes",
            "PHASE5_STATE": str(state.relative_to(REPO)),
            "PHASE5_CEILING": str(min(remaining_budget, 1000.0)),
            "PHASE5_PER_SLOT": str(args.per_slot),
            "EDA_BENCH_GATEWAY_ENV": str(GATEWAY),
        })
        t0 = time.time()
        print(f"[block {i + 1}/{len(blocks)}] {block_id}: {len(slots)} slots, "
              f"budget left ¥{remaining_budget}", flush=True)
        rc = subprocess.run([sys.executable, str(RUNNER)], env=env, cwd=str(REPO)).returncode
        print(f"[block {i + 1}/{len(blocks)}] rc={rc} in {round(time.time() - t0)}s "
              f"cumulative ¥{_spent_so_far(args.arm)}", flush=True)
        if rc != 0:
            print(json.dumps({"stopped": "runner_nonzero_exit", "at_block": i, "rc": rc}),
                  flush=True)
            return rc
        faults = _telemetry_faults(state)
        if faults:
            print(json.dumps({"stopped": "telemetry_faults", "at_block": i,
                              "detail": faults[:6],
                              "note": "episodes with no evidence of a model call are "
                                      "measurement-invalid; aborting rather than collecting a "
                                      "panel of junk. Fix the cause, delete this block's state, "
                                      "and re-run -- completed blocks are skipped."}, indent=2),
                  flush=True)
            return 2

    print(json.dumps({"arm": args.arm, "spent_cny": _spent_so_far(args.arm),
                      "budget_cny": args.budget}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
