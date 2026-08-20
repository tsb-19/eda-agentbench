#!/usr/bin/env python3
"""Arm-2 cost calibration: what the gate projected against what the arm actually cost.

This is an **engineering record, not a scientific result**, and it is deliberately kept out of the
manuscript. It exists because the number it contains is the study's own finding restated in a
different currency, and because a project that discovers its own gate was miscalibrated should say
so in a place a future maintainer will find.

The finding. The preregistered cost gate priced arm 2 at r' = CNY 0.8051/episode and concluded that
no rung of the ladder fitted the remaining budget, returning ``ARM2_NOT_RUN``. The arm was later
executed anyway and cost CNY 0.6266/episode. For the 66 episodes the gate was pricing, that is
CNY 38.46 against a projection of CNY 53.14, versus CNY 44.53 then available -- so the arm was
affordable, by roughly CNY 6.

The gate applied its rule correctly and its arithmetic was right. What was wrong was the **rate
estimator feeding it**: r' pooled the cost probe with the single block that had executed, and that
block was ``p15_eval_0004`` -- the dearest of the twelve instances at CNY 1.109/episode against a
panel mean of CNY 0.627 and a cheapest instance of CNY 0.330. The gate had itself recorded the
spread it then averaged away. That is this paper's own result about panel composition, except that
here composition determined not an effect size but whether an experiment happened.

Note what this record does *not* do: it does not reopen the gate's decision as a decision. The
episodes were subsequently run and are now analysed under a plan fixed before their outcomes were
read (``docs/phase8a_arm2_analysis_plan.md``), which is a different and better justification than
"the refusal turned out to be too conservative".

Usage:
    python3 scripts/phase8a_arm2_cost_calibration.py            # write the record
    python3 scripts/phase8a_arm2_cost_calibration.py --check    # recompute and fail on drift
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EPISODES = REPO / "phase8a" / "evidence" / "episodes_arm2"
GATE = REPO / "phase8a" / "evidence" / "arm2_gate_decision.json"
RECORD = REPO / "phase8a" / "evidence" / "arm2_cost_calibration.json"

HOLDBACK_PRICED_EPISODES = 66  # what the gate was pricing: 72 planned minus the block already paid
PREPAID_INSTANCE = "p15_eval_0004"  # block 00, executed and paid for before the gate fired


def _instance_of(task_id: str) -> str:
    return task_id.rsplit("_", 1)[0]


def build() -> dict:
    per: dict[str, list[float]] = defaultdict(list)
    for d in sorted(EPISODES.iterdir()):
        if not (d / "episode.json").is_file():
            continue
        e = json.loads((d / "episode.json").read_text())
        per[_instance_of(e["task_id"])].append(float(e.get("total_cost") or 0.0))

    costs = [c for v in per.values() for c in v]
    assert len(costs) == 72, f"expected 72 arm-2 episodes, found {len(costs)}"
    realized_rate = sum(costs) / len(costs)

    rates = {i: sum(v) / len(v) for i, v in per.items()}
    dearest = max(rates, key=rates.get)
    cheapest = min(rates, key=rates.get)

    gate = json.loads(GATE.read_text())
    projected_rate = gate["rate"]["r_prime_cny_per_episode"]
    available = gate["budget"]["remaining_after_holdback_cny"]
    projected = projected_rate * HOLDBACK_PRICED_EPISODES
    # What those 66 actually cost: the SUM of their episode costs, not the panel mean times 66.
    # Block 00 (p15_eval_0004) was already paid for and already inside the gate's own spend figure,
    # so charging it again here would inflate the comparison on both sides.
    already_paid = gate["rate"]["from_clean_block00"]
    realized = round(sum(costs) - sum(per[PREPAID_INSTANCE]), 4)
    assert len(per[PREPAID_INSTANCE]) == already_paid["n"], (
        f"expected {already_paid['n']} pre-paid episodes on {PREPAID_INSTANCE}, "
        f"found {len(per[PREPAID_INSTANCE])}"
    )

    return {
        "schema": "phase8a_arm2_cost_calibration/v1",
        "what_this_is": "an engineering record of a miscalibrated cost gate; NOT a scientific "
                        "result, and cited in no part of the manuscript",
        "does_not_reopen_the_gate_decision": (
            "the arm's analysis rests on a plan fixed before its outcomes were read, not on the "
            "discovery that the refusal was too conservative"
        ),
        "rate": {
            "projected_cny_per_episode": round(projected_rate, 6),
            "realized_cny_per_episode": round(realized_rate, 6),
            "overestimate_pct": round(100 * (projected_rate - realized_rate) / realized_rate, 1),
        },
        "the_66_episodes_the_gate_priced": {
            "n": HOLDBACK_PRICED_EPISODES,
            "projected_cny": round(projected, 4),
            "realized_cny": realized,
            "available_after_holdback_cny": available,
            "gate_verdict": gate["decision"],
            "verdict_at_realized_cost": "would have fitted",
            "margin_at_realized_cost_cny": round(available - realized, 4),
        },
        "why_the_estimator_missed": {
            "calibration_pooled_episodes": gate["rate"]["pooled_episodes"],
            "calibration_dominated_by_instance": dearest,
            "that_instance_rate_cny": round(rates[dearest], 4),
            "panel_mean_rate_cny": round(realized_rate, 4),
            "cheapest_instance": cheapest,
            "cheapest_instance_rate_cny": round(rates[cheapest], 4),
            # Two different spreads, named apart because quoting one as the other is exactly the
            # kind of slippage this file exists to record.
            "instance_level_spread_factor": round(rates[dearest] / rates[cheapest], 2),
            "episode_level_spread_factor_the_gate_recorded":
                gate["rate"]["spread_factor"],
            "lesson": (
                "a cost gate must be calibrated on a sample representative of the panel it "
                "governs, and must carry the dispersion it has itself measured into the decision "
                "rather than collapsing it to a pooled mean"
            ),
        },
        "per_instance_cny_per_episode": {i: round(r, 4) for i, r in sorted(rates.items())},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="recompute and fail on drift")
    args = ap.parse_args()

    built = build()
    blob = json.dumps(built, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not RECORD.is_file():
            print(f"MISSING: {RECORD.relative_to(REPO)}", file=sys.stderr)
            return 1
        if RECORD.read_text() != blob:
            print(f"DRIFT: {RECORD.relative_to(REPO)} does not match recomputation",
                  file=sys.stderr)
            return 1
        r = built["the_66_episodes_the_gate_priced"]
        w = built["why_the_estimator_missed"]
        print(json.dumps({"ok": True,
                          "projected_cny": r["projected_cny"], "realized_cny": r["realized_cny"],
                          "available_cny": r["available_after_holdback_cny"],
                          "margin_cny": r["margin_at_realized_cost_cny"],
                          "instance_spread": w["instance_level_spread_factor"],
                          "episode_spread_the_gate_had":
                              w["episode_level_spread_factor_the_gate_recorded"]}))
        return 0

    RECORD.write_text(blob)
    print(f"wrote {RECORD.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
