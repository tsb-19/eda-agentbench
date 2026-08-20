#!/usr/bin/env python3
"""Apply the frozen §2.2 cost gate to arm 2 and record the decision (NO model calls).

This is the last decision in the Phase-8A programme, so it is the one most worth making
mechanically. §2.2 fixes the rule; docs/phase8a_prereg.md §5F.5 fixes -- before the re-run that
produces the deciding number -- how the rule is re-applied after block 00 was re-executed:

  1. block 00 is re-run whole on the fixed runner (it had to be re-run in any case);
  2. `r'` is recomputed from the driver logs, POOLED with the cost probe's six episodes;
  3. the frozen §2.2 formula is re-applied UNCHANGED. Whole arm, or none of it.

The formula itself is never reimplemented here -- `phase8a_cost_probe.k2_from` is imported and
called. A gate that decides whether ¥50-odd is spent must not run on a second, drifting copy of the
arithmetic it claims to apply.

## The one judgement call, stated openly

`k2_from`'s first parameter is named `spent_arm1`, because when §2.2 was written the only money that
existed was arm 1's. Arm 2 has since paid ¥19.65 -- two archived passes and one valid block -- and
the probe ¥3.01. Passing the arm-1 figure today would be literal but false: it would hide real outlay
from a cap whose entire job is to see it, and the gate would approve a spend the ¥200 cap cannot
cover. "Apply the formula unchanged" constrains the arithmetic, not the honesty of its inputs, so
this script feeds it TOTAL program spend and prints the stale-argument reading beside it so a reader
can see exactly what the choice was worth.

Both readings are reported. Per the doctrine already written into `k2_from`, the stricter binds.

  python3 scripts/phase8a_arm2_gate.py            # report
  python3 scripts/phase8a_arm2_gate.py --apply    # write the decision record
  python3 scripts/phase8a_arm2_gate.py --check    # verify the record still reproduces
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import phase8a_cost_probe as P  # noqa: E402  (the frozen formula, imported never copied)
import phase8a_run as R  # noqa: E402

DECISION = REPO / "phase8a" / "evidence" / "arm2_gate_decision.json"
ARM2_CUSTODY = REPO / "phase8a" / "evidence" / "episodes_arm2"
EPISODES_PER_BLOCK = 6


def _costs(custody: Path):
    """Every collected episode's cost. Cost is the ONLY field read -- the gate never sees a score."""
    out = []
    for f in sorted(custody.glob("*/episode.json")):
        try:
            out.append(float(json.loads(f.read_text()).get("total_cost") or 0.0))
        except Exception:  # noqa: BLE001
            pass
    return out


def compute() -> dict:
    probe = _costs(P.PROBE_CUSTODY)
    block = _costs(ARM2_CUSTODY)
    if not probe or not block:
        raise SystemExit("phase8a_arm2_gate: need both the cost probe and a clean block 00")
    pool = probe + block
    r = sum(pool) / len(pool)

    spent_total = R._program_spend()
    arm1 = float(json.loads((REPO / "phase8a" / "reports"
                             / "phase8a_sta_report.json").read_text())["spent_cny"])

    k2, remaining, detail = P.k2_from(r, spent_total, 0.0)
    # The reading §2.2 would have produced if handed the argument its parameter name literally
    # asks for. Shown, not used: arm 2's own paid money is missing from it.
    k2_stale, remaining_stale, _ = P.k2_from(r, arm1, P._probe_spend())

    # Credit the block already paid for: does the REMAINDER of arm 2 fit, even though §2.2 prices
    # the whole arm? Reported because a reader will ask, and because if the two disagreed the
    # disagreement would have to be resolved in writing rather than quietly.
    done_blocks = 1 if len(block) >= EPISODES_PER_BLOCK else 0
    fwd_eps = P.N_INSTANCES * P.N_CONDITIONS * 2 - done_blocks * EPISODES_PER_BLOCK
    fwd = fwd_eps * r

    return {
        "schema": "phase8a_arm2_gate/v1",
        "decided_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rule": "docs/phase8a_prereg.md §2.2, re-applied per §5F.5 step 3",
        "reads_scores": False,
        "rate": {
            "r_prime_cny_per_episode": round(r, 6),
            "pooled_episodes": len(pool),
            "from_cost_probe": {"n": len(probe), "cny": round(sum(probe), 4),
                                "per_episode": round(sum(probe) / len(probe), 4)},
            "from_clean_block00": {"n": len(block), "cny": round(sum(block), 4),
                                   "per_episode": round(sum(block) / len(block), 4)},
            # The spread is the reason the ¥10 holdback is not negotiable below.
            "min": round(min(pool), 4), "max": round(max(pool), 4),
            "spread_factor": round(max(pool) / min(pool), 2),
            "stdev": round(statistics.stdev(pool), 4),
        },
        "budget": {"cap_cny": P.CAP, "holdback_cny": P.HOLDBACK,
                   "program_spend_cny": spent_total,
                   "of_which_arm1_cny": round(arm1, 4),
                   "remaining_after_holdback_cny": remaining},
        "gate": {"k2": k2, "ladder": detail},
        "stale_argument_reading": {
            "note": "what §2.2 returns if fed arm-1 spend only, as its parameter name literally "
                    "says. Not used: it omits ¥%.4f of arm-2 money already paid."
                    % round(spent_total - arm1 - P._probe_spend(), 4),
            "k2": k2_stale, "remaining_after_holdback_cny": remaining_stale,
        },
        "remainder_cross_check": {
            "blocks_already_valid": done_blocks, "episodes_remaining": fwd_eps,
            "projected_cny": round(fwd, 4),
            "fits_after_holdback": fwd <= remaining,
            "fits_only_if_holdback_is_abandoned": fwd > remaining and fwd <= (P.CAP - spent_total),
            "margin_without_holdback_cny": round((P.CAP - spent_total) - fwd, 4),
        },
        "decision": "RUN_FULL_ARM2" if k2 else "ARM2_NOT_RUN",
        "why": (
            "No k in {6,4,2} satisfies 12*3*k*r' <= remaining. k is already at the floor of the "
            "preregistered ladder and §5E.5 forbids a partial arm, so the only answers available "
            "were run-the-whole-arm or do-not-run-it. Arm 2 is reported as the one preregistered "
            "cell that could not be filled within budget."
        ) if not k2 else "The full 72 episodes fit under the frozen formula.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply the frozen §2.2 cost gate to arm 2.")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    now = compute()
    print(json.dumps(now, indent=2))

    if a.check:
        if not DECISION.is_file():
            print(json.dumps({"check": "FAIL", "note": "no decision record"}))
            return 1
        was = json.loads(DECISION.read_text())
        same = (was["decision"] == now["decision"]
                and was["gate"]["k2"] == now["gate"]["k2"]
                and abs(was["rate"]["r_prime_cny_per_episode"]
                        - now["rate"]["r_prime_cny_per_episode"]) < 1e-6)
        print(json.dumps({"check": "PASS" if same else "FAIL",
                          "recorded": was["decision"], "recomputed": now["decision"],
                          "recorded_r": was["rate"]["r_prime_cny_per_episode"],
                          "recomputed_r": now["rate"]["r_prime_cny_per_episode"]}))
        return 0 if same else 1

    if not a.apply:
        return 0
    if DECISION.is_file():
        prior = json.loads(DECISION.read_text())
        print(json.dumps({"applied": False, "note": "a decision is already recorded; §2.2 says k2 "
                                                    "is never revised after it is fixed",
                          "recorded": prior["decision"]}))
        return 0
    DECISION.write_text(json.dumps(now, indent=2) + "\n")
    print(json.dumps({"applied": True, "record": str(DECISION.relative_to(REPO)),
                      "decision": now["decision"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
