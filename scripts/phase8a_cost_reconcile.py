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


def _passes(arm: int, block: int):
    """Every pass over this block: the live one, and each archived attempt.

    Needed because a corrected pass does not stay live. Once block 00 was re-run clean, a --check
    scoped to the live pass reported "nothing understated" and quietly stopped verifying the ¥4.9775
    already recovered from the archived pass -- money that is still bound into the ¥200 cap. A
    verifier that goes green because it stopped looking is worse than no verifier.

    Returns [(label, state_path, chain_log)], live first.
    """
    ev = REPO / "phase8a" / "evidence"
    out = []
    live_state = ev / f"run_state_arm{arm}_block{block:02d}.json"
    live_log = REPO / "runs" / "phase8a" / f"chain_a{arm}_b{block:02d}.log"
    if live_state.is_file():
        out.append(("live", live_state, live_log if live_log.is_file() else None))
    for st in sorted(ev.glob(f"run_state_arm{arm}_block{block:02d}_attempt*.json")):
        k = st.stem.rsplit("attempt", 1)[-1]
        arch = ev / "aborted" / f"arm{arm}_block{block:02d}_attempt{k}"
        log = arch / f"chain_log_arm{arm}_block{block:02d}.log"
        out.append((f"attempt{k}", st, log if log.is_file() else None))
    return out


def _booked_from(log: Path | None):
    """Per-attempt costs as the chain log booked them -- i.e. what custody + ledger together hold."""
    if log is None or not log.is_file():
        return []
    rows = re.findall(r'\{"trial": "([^"]+)", "total_score": [^,]+, "cost": ([0-9.]+)', log.read_text())
    return [(t, float(c)) for t, c in rows]


def _window_of(state_path: Path):
    """(start, end) epoch seconds of one pass, from that pass's own run state.

    Needed because run directories are keyed by (block, condition, position, attempt) and REUSED
    across passes: globbing the block's dirs also returns attempts left behind by an earlier pass
    that the current one did not happen to overwrite. Arm 2 block 00 has exactly one such leftover.
    Counting it here would charge this pass for money the archived pass has already accounted for --
    the same stale-artifact-at-a-reused-path fault this script exists to correct, made a third time.
    """
    if not state_path.is_file():
        return None, None
    d = json.loads(state_path.read_text())

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


def _reconcile(arm: int, block: int, block_id: str, model_name: str, rates,
               label: str, state_path: Path, log: Path | None):
    """Booked vs true for ONE pass, plus the per-attempt breakdown."""
    booked = _booked_from(log)
    true_rows, skipped = _true(arm, block_id, rates, _window_of(state_path))
    booked_total = round(sum(c for _t, c in booked), 4)
    true_total = round(sum(c for _n, c, _e in true_rows if c is not None), 4)
    return {"arm": arm, "block": block, "block_id": block_id, "model_name": model_name,
            "pass": label, "pass_id": R._pass_id(state_path),
            "attempts_booked": len(booked), "attempts_with_a_driver_log": len(true_rows),
            "booked_cny": booked_total, "true_cny": true_total,
            "understated_by_cny": round(true_total - booked_total, 4),
            "attempts_without_a_log": [n for n, c, _e in true_rows if c is None],
            # listed, never silently dropped: a reader must be able to see what was excluded
            "excluded_as_another_passs_leftovers": skipped,
            "source": str(log.relative_to(REPO)) if log else None,
            "breakdown": [{"attempt_dir": n, "true_cny": c, "note": e} for n, c, e in true_rows]}


def main() -> int:
    ap = argparse.ArgumentParser(description="Reconcile a block pass's spend against the agent logs.")
    ap.add_argument("--arm", type=int, required=True, choices=(1, 2))
    ap.add_argument("--block", type=int, required=True)
    ap.add_argument("--pass-label", default="live",
                    help="which pass to reconcile: 'live' or 'attemptK' (see --apply)")
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

    passes = _passes(a.arm, a.block)
    if not passes:
        print(json.dumps({"error": f"no pass on record for arm {a.arm} block {a.block}"}))
        return 1
    entries = R._ledger_entries()

    # --check verifies EVERY pass of this block, not just whichever one is live. A correction is
    # recovered money bound into the ¥200 cap; it does not stop needing verification because the
    # pass that produced it was later archived and re-run.
    #
    # But the primary artifact does not always survive. `runs/phase8a/` is gitignored AND its
    # directories are keyed by (block, condition, position, attempt), so re-running block 00 whole
    # overwrote the very driver logs the archived passes' corrections were computed from. Three
    # outcomes must therefore be distinguished, and collapsing them would be its own defect:
    #   PASS          the ledger still reproduces from logs on disk;
    #   FAIL          the logs are there and disagree with the ledger;
    #   SOURCE_GONE   the logs this entry was computed from no longer exist, so the entry can only
    #                 be checked against its own recorded per-attempt breakdown.
    # SOURCE_GONE is reported loudly rather than swallowed. It is not a pass in the same sense, and
    # a verifier that printed green here would be asserting something it can no longer see.
    if a.check:
        results, ok, degraded = [], True, 0
        for label, state_path, log in passes:
            r = _reconcile(a.arm, a.block, block_id, model_name, rates, label, state_path, log)
            pid = r["pass_id"]
            prior = [e for e in entries
                     if e.get("kind") == KIND and e.get("arm") == a.arm
                     and e.get("block") == a.block and e.get("pass_id") == pid]
            got = round(sum(float(e.get("cost_cny") or 0.0) for e in prior), 4)
            delta = r["understated_by_cny"]
            now_dirs = {b["attempt_dir"] for b in r["breakdown"] if b["true_cny"] is not None}
            rec_dirs = {b["attempt_dir"] for e in prior for b in (e.get("breakdown") or [])
                        if b.get("true_cny") is not None}
            source_gone = (rec_dirs and rec_dirs != now_dirs) or (not prior and delta < 0)

            row = {"pass": label, "pass_id": pid, "booked_cny": r["booked_cny"]}
            if source_gone:
                degraded += 1
                # Fall back to the entry's own arithmetic: does the breakdown it recorded still add
                # up to the correction it claims? That is weaker than recomputation and is labelled
                # as weaker, but it is not nothing.
                consistent = True
                for e in prior:
                    bsum = round(sum(float(b.get("true_cny") or 0.0)
                                     for b in (e.get("breakdown") or [])), 4)
                    if (abs(bsum - float(e.get("true_cny") or 0.0)) > 1e-6
                            or abs(round(float(e.get("true_cny") or 0.0)
                                         - float(e.get("booked_cny") or 0.0), 4)
                                   - float(e.get("cost_cny") or 0.0)) > 1e-6):
                        consistent = False
                if not consistent:
                    ok = False
                row.update({
                    "verdict": "SOURCE_GONE: " + ("the recorded breakdown is self-consistent"
                                                  if consistent else
                                                  "the recorded breakdown does NOT add up"),
                    "ledger_cny": got,
                    "why": "the driver logs this pass was reconciled from lived in gitignored "
                           "runs/phase8a/ under directories that the whole-block re-run reused and "
                           "overwrote; they cannot be re-read",
                    "still_committed": str(log.relative_to(REPO)) if log else None,
                })
            elif delta > 0 and not prior:
                ok = False
                row.update({"verdict": "FAIL: understated and not corrected",
                            "true_cny": r["true_cny"], "understated_by_cny": delta,
                            "ledger_cny": got})
            elif prior and abs(got - delta) > 1e-6:
                ok = False
                row.update({"verdict": "FAIL: ledger disagrees with the logs",
                            "true_cny": r["true_cny"], "understated_by_cny": delta,
                            "ledger_cny": got})
            else:
                row.update({"verdict": "PASS: correction reproduces" if prior
                                       else "PASS: nothing understated",
                            "true_cny": r["true_cny"], "understated_by_cny": delta,
                            "ledger_cny": got})
            results.append(row)
        print(json.dumps({"check": "PASS" if ok else "FAIL",
                          "passes_verified": len(results),
                          "passes_no_longer_recomputable": degraded,
                          "results": results}, indent=2))
        return 0 if ok else 1


    sel = [p for p in passes if p[0] == a.pass_label]
    if not sel:
        print(json.dumps({"error": f"no pass labelled {a.pass_label!r}",
                          "available": [p[0] for p in passes]}))
        return 1
    label, state_path, log = sel[0]
    report = _reconcile(a.arm, a.block, block_id, model_name, rates, label, state_path, log)
    print(json.dumps(report, indent=2))
    delta = report["understated_by_cny"]

    # Keyed by PASS, not by block. A block is re-run whole, so (arm, block) alone would match the
    # correction already recorded for an earlier pass and silently skip a later pass's shortfall --
    # the same "a re-run repeats the key" trap that made the ledger need a pass identity at all.
    pass_id = report["pass_id"]
    prior = [e for e in entries
             if e.get("kind") == KIND and e.get("arm") == a.arm and e.get("block") == a.block
             and e.get("pass_id") == pass_id]

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
        "booked_cny": report["booked_cny"], "true_cny": report["true_cny"],
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": report["source"],
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
