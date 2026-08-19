#!/usr/bin/env python3
"""Reconcile a Phase-8A block pass's recorded spend against the driver's own agent logs.

Why this exists. `phase8a_episode_runner` derives an episode's cost from the driver's agent log, and
in arm 2 block 00 it read the wrong log twice -- once a predecessor pass's, once none at all --
because `run_single_agentic` returns before the driver has finished writing. Both faults are fixed at
source now (the runner clears the path first and holds the shell open until the log lands), but the
money already paid under the old behaviour is understated in the ledger, and the ¥200 program cap is
computed from that ledger.

The primary artifact survives. Every attempt's run directory still holds the driver's own
`*.agentlog.json` with its `usage` block, so the true cost is not estimated here -- it is recomputed
from the same record, with the same function (`phase8a_episode_runner._cost`), that would have been
used had the log been read at the right moment. That is a correction, not an invention.

What it does NOT do: touch any episode.json. The original records stay exactly as they were written,
wrong figures included, and the correction is a separate durable entry with the per-attempt
breakdown attached. Overwriting them would erase the evidence that the fault happened at all, and a
discrepancy you can still see is worth more than a total that quietly agrees with itself.

The correction lands in the existing replaced-attempt ledger because it is the same category --
money paid that no surviving episode.json accounts for -- so it binds the cap through machinery that
already exists and is already tested, rather than through a second ledger nobody remembers to sum.

  python3 scripts/phase8a_cost_reconcile.py --arm 2 --block 0            # report
  python3 scripts/phase8a_cost_reconcile.py --arm 2 --block 0 --apply    # append the correction
  python3 scripts/phase8a_cost_reconcile.py --arm 2 --block 0 --check    # verify it reproduces
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import phase8a_episode_runner as ER  # noqa: E402  (the same _cost the runner would have used)
import phase8a_run as R  # noqa: E402

KIND = "understated_cost_correction"


def _chain_log(arm: int, block: int) -> Path | None:
    """The pass's chain log, live or already archived. It is the record of what was BOOKED."""
    live = REPO / "runs" / "phase8a" / f"chain_a{arm}_b{block:02d}.log"
    if live.is_file():
        return live
    for c in sorted((REPO / "phase8a" / "evidence" / "aborted").glob(
            f"arm{arm}_block{block:02d}_attempt*/chain_log_arm{arm}_block{block:02d}.log")):
        return c
    return None


def _booked(arm: int, block: int):
    """Per-attempt costs as the chain log booked them -- i.e. what custody + ledger together hold."""
    log = _chain_log(arm, block)
    if log is None:
        return None, []
    rows = re.findall(r'\{"trial": "([^"]+)", "total_score": [^,]+, "cost": ([0-9.]+)', log.read_text())
    return log, [(t, float(c)) for t, c in rows]


def _pass_window(arm: int, block: int):
    """(start, end) epoch seconds of the pass, from its own run state.

    Needed because run directories are keyed by (block, condition, position, attempt) and REUSED
    across passes: globbing the block's dirs also returns attempts left behind by an earlier pass
    that the current one did not happen to overwrite. Arm 2 block 00 has exactly one such leftover.
    Counting it here would charge this pass for money the archived pass has already accounted for --
    the same stale-artifact-at-a-reused-path fault this script exists to correct, made a third time.
    """
    ev = REPO / "phase8a" / "evidence"
    st = ev / f"run_state_arm{arm}_block{block:02d}.json"
    if not st.is_file():
        cands = sorted(ev.glob(f"run_state_arm{arm}_block{block:02d}_attempt*.json"))
        if not cands:
            return None, None
        st = cands[-1]
    d = json.loads(st.read_text())

    def _p(v):
        try:
            return time.mktime(time.strptime(v, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
        except Exception:  # noqa: BLE001
            return None
    return _p(d.get("started_at")), _p(d.get("executor_finished_at"))


def _true(arm: int, block_id: str, rates, window):
    """Per-attempt costs recomputed from each attempt's own driver log, within this pass's window."""
    start, end = window
    out, skipped = [], []
    for d in sorted((REPO / "runs" / "phase8a").glob(f"a{arm}_{block_id}_*_a*")):
        logs = sorted(d.glob("results/*/*/*.agentlog.json"))
        if not logs:
            out.append((d.name, None, "no agent log on disk"))
            continue
        # +LOG_SETTLE_SEC of slack: a log may legitimately land after the executor recorded the
        # pass as finished -- that lateness is the very fault being corrected here.
        mt = logs[0].stat().st_mtime
        if start is not None and end is not None and not (start <= mt <= end + ER.LOG_SETTLE_SEC):
            skipped.append({"attempt_dir": d.name, "log_mtime": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(mt)), "reason": "outside this pass's window"})
            continue
        try:
            L = json.loads(logs[0].read_text())
        except Exception as e:  # noqa: BLE001
            out.append((d.name, None, f"unreadable: {type(e).__name__}"))
            continue
        out.append((d.name, round(ER._cost(L, *rates), 4), None))
    return out, skipped


def main() -> int:
    ap = argparse.ArgumentParser(description="Reconcile a block pass's spend against the agent logs.")
    ap.add_argument("--arm", type=int, required=True, choices=(1, 2))
    ap.add_argument("--block", type=int, required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    ev = REPO / "phase8a" / "evidence"
    sched = json.loads((ev / f"schedule_arm{a.arm}.json").read_text())
    block_id, _slots = R._blocks_of(sched)[a.block]
    cfg = REPO / f"phase8a/models_arm{a.arm}.json"
    named = [m for m in json.loads(cfg.read_text()).get("models", [])
             if not str(m.get("name", "")).startswith("_")]
    if len(named) != 1:
        raise SystemExit(f"phase8a_cost_reconcile: models_arm{a.arm}.json must hold exactly one entry")
    model_name = named[0]["name"]
    rates = ER._rates(cfg, model_name)

    log, booked = _booked(a.arm, a.block)
    if log is None:
        print(json.dumps({"error": f"no chain log for arm {a.arm} block {a.block}"}))
        return 1
    window = _pass_window(a.arm, a.block)
    true_rows, skipped = _true(a.arm, block_id, rates, window)
    booked_total = round(sum(c for _t, c in booked), 4)
    true_total = round(sum(c for _n, c, _e in true_rows if c is not None), 4)
    delta = round(true_total - booked_total, 4)
    missing = [n for n, c, _e in true_rows if c is None]

    report = {"arm": a.arm, "block": a.block, "block_id": block_id, "model_name": model_name,
              "attempts_booked": len(booked), "attempts_with_a_driver_log": len(true_rows),
              "booked_cny": booked_total, "true_cny": true_total, "understated_by_cny": delta,
              "attempts_without_a_log": missing,
              # listed, never silently dropped: a reader must be able to see what was excluded
              "excluded_as_another_passs_leftovers": skipped,
              "breakdown": [{"attempt_dir": n, "true_cny": c, "note": e} for n, c, e in true_rows]}
    print(json.dumps(report, indent=2))

    entries = R._ledger_entries()
    # Keyed by PASS, not by block. A block is re-run whole, so (arm, block) alone would match the
    # correction already recorded for an earlier pass and silently skip a later pass's shortfall --
    # the same "a re-run repeats the key" trap that made the ledger need a pass identity at all.
    pass_id = R._pass_id(REPO / "phase8a" / "evidence"
                         / f"run_state_arm{a.arm}_block{a.block:02d}.json")
    if not pass_id:
        cands = sorted((REPO / "phase8a" / "evidence").glob(
            f"run_state_arm{a.arm}_block{a.block:02d}_attempt*.json"))
        pass_id = R._pass_id(cands[-1]) if cands else ""
    prior = [e for e in entries
             if e.get("kind") == KIND and e.get("arm") == a.arm and e.get("block") == a.block
             and e.get("pass_id") == pass_id]

    if a.check:
        if delta <= 0:
            print(json.dumps({"check": "PASS", "note": "nothing understated"}))
            return 0
        if not prior:
            print(json.dumps({"check": "FAIL", "note": "correction not in the ledger"}))
            return 1
        got = round(sum(float(e.get("cost_cny") or 0.0) for e in prior), 4)
        ok = abs(got - delta) < 1e-6
        print(json.dumps({"check": "PASS" if ok else "FAIL",
                          "ledger_cny": got, "recomputed_cny": delta}))
        return 0 if ok else 1

    if not a.apply:
        return 0
    if delta <= 0:
        print(json.dumps({"applied": False, "note": "nothing to correct"}))
        return 0
    if prior:
        print(json.dumps({"applied": False, "note": "already corrected — appending again would "
                                                    "double-count", "existing": prior[0]}))
        return 0

    entries.append({
        "kind": KIND,
        "arm": a.arm, "block": a.block, "block_id": block_id, "model_name": model_name,
        "pass_id": pass_id,
        "cost_cny": delta,
        "booked_cny": booked_total, "true_cny": true_total,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": str(log.relative_to(REPO)),
        "breakdown": report["breakdown"],
        "why": "phase8a_episode_runner read the agent log before the driver had written it: one "
               "attempt was charged a predecessor pass's cost and one was charged nothing at all. "
               "Recomputed from each attempt's own driver log with the same _cost() the runner "
               "uses. The original episode.json records are deliberately left unchanged.",
    })
    R.ATTEMPT_LEDGER.write_text(json.dumps({"entries": entries}, indent=2) + "\n")
    print(json.dumps({"applied": True, "added_cny": delta,
                      "ledger": str(R.ATTEMPT_LEDGER.relative_to(REPO)),
                      "program_spend_cny": R._program_spend()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
