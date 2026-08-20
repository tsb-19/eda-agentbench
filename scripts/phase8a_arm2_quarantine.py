#!/usr/bin/env python3
"""Record the quarantined arm-2 trajectories without ever reading their outcomes.

Seventy-two DeepSeek-V4-Pro STA episodes exist at the S3 coordinate. They must not be confused
with the preregistered S3 arm, which did not run:

    02:56Z  the preregistered cost gate writes ARM2_NOT_RUN into phase8a/evidence/
    04:31Z  blocks 01-11 begin, under a quarantine whose entire write surface was redirected
            to runs/ -- gitignored, outside phase8a/evidence/, invisible to every --check

The exclusion decision therefore *predates the data*. That ordering is the only reason these
episodes can be disclosed without disturbing anything, and it is worth more than any result they
could contain: "excluded before they existed, and never analysed" is a stronger statement than a
number. It survives exactly as long as nobody computes the contrast.

So this script is written to be incapable of computing it. It opens `episode.json` and
`SHA256SUMS` and nothing else -- never `result.json`, never `exception_config.submitted.json`
(the agent's submitted binding *is* the outcome), never the agent log. Of `episode.json` it drops
`total_score` and `semantic_binding` before the object is used for anything, and asserts that they
never reach the record. A test drives this script under an audit hook that fails if it opens a
forbidden path, because a promise in a docstring is not a control.

What the record does carry is money and orchestration, which the gate itself declared
outcome-free (`reads_scores: false`). That is enough for the one finding these episodes support:
the gate refused an arm that was affordable. It projected ¥0.805125/episode from a twelve-episode
probe and so put the 66 remaining episodes at ¥53.14 against ¥44.53 available; they cost ¥38.46.
The projection was high because the probe pooled the cost probe with block 00, and block 00 is
`p15_eval_0004` -- the most expensive of the twelve instances, 1.77x the panel mean and 3.4x the
cheapest. The gate had already recorded the spread it was averaging away (`spread_factor 6.86`).

The gate is not thereby wrong: it applied its preregistered rule correctly to the data it had. Its
*rate estimator* was calibrated on a sample that did not represent the panel it gated. That is the
same finding as this paper's scientific one, in a different currency -- panel composition, not run
noise, decided the estimate -- and it needs no condition contrast to state.

Usage:
    python3 scripts/phase8a_arm2_quarantine.py            # write phase8a/evidence/arm2_quarantine_record.json
    python3 scripts/phase8a_arm2_quarantine.py --check    # recompute and fail on drift
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
QUARANTINE_ROOT = REPO / "runs" / "phase8a_exploratory_arm2"
GATE_DECISION = REPO / "phase8a" / "evidence" / "arm2_gate_decision.json"
RECORD = REPO / "phase8a" / "evidence" / "arm2_quarantine_record.json"
MACROS = REPO / "submission" / "tables" / "arm2_quarantine.tex"

# The only two files an episode directory may be opened for, and the only keys taken from the first.
# `result.json` holds the graded verdict; `exception_config.submitted.json` holds the binding the
# agent submitted, which is the same information in raw form; `agentlog.sanitized.json` contains the
# reasoning that produced it. None is opened here.
EPISODE_MANIFEST = "episode.json"
CUSTODY_MANIFEST = "SHA256SUMS"
FORBIDDEN_FILES = ("result.json", "exception_config.submitted.json", "agentlog.sanitized.json")
OUTCOME_KEYS = ("total_score", "semantic_binding")
READABLE_KEYS = ("block_id", "condition", "family", "model_name", "position_in_block", "rep",
                 "task_id", "track", "transport", "trial", "total_cost", "rates_cny_per_M",
                 "custody", "error")

RATIONALE = (
    "The exclusion decision was fixed before any S3 outcome was observed. Although 72 quarantined "
    "trajectories were subsequently generated, opening them now would convert a pre-outcome "
    "exclusion into an outcome-informed exploratory analysis. We therefore disclose their "
    "existence and realized cost but leave their outcomes unexamined."
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_episode(directory: Path) -> dict:
    """Return only the non-outcome fields of one episode, dropping the rest before use."""
    raw = json.loads((directory / EPISODE_MANIFEST).read_text())
    kept = {k: raw[k] for k in READABLE_KEYS if k in raw}
    assert not any(k in kept for k in OUTCOME_KEYS), f"outcome field survived filtering in {directory}"
    kept["episode_id"] = directory.name
    kept["custody_manifest_sha256"] = sha256_file(directory / CUSTODY_MANIFEST)
    return kept


def instance_of(episode_id: str) -> str:
    return "_".join(episode_id.split("_")[:3])          # p15_eval_0004_base_r1 -> p15_eval_0004


def build() -> dict:
    if not QUARANTINE_ROOT.exists():
        raise SystemExit(f"quarantine tree absent: {QUARANTINE_ROOT} (it is gitignored by design; "
                         "the committed record is the durable artifact)")

    episodes = [read_episode(d) for d in sorted((QUARANTINE_ROOT / "episodes_arm2").iterdir())
                if d.is_dir()]

    blocks = []
    for state_file in sorted(QUARANTINE_ROOT.glob("run_state_arm2_block*.json")):
        st = json.loads(state_file.read_text())
        blocks.append({
            "block": state_file.stem.replace("run_state_arm2_block", ""),
            "state": st["state"],
            "started_at": st["started_at"],
            "finished_at": st["executor_finished_at"],
            "expected_primary_slots": st["expected_primary_slots"],
            "completed_primary_slots": st["completed_primary_slots"],
            "excluded_invalid_attempts": len(st["excluded_invalid_attempts"]),
            "report_pending": st["report_pending"],
        })

    gate = json.loads(GATE_DECISION.read_text())
    assert gate["decision"] == "ARM2_NOT_RUN", gate["decision"]
    assert gate["reads_scores"] is False, "the gate is only quotable here because it read no scores"

    # Block 00 is byte-identical to the block committed under phase8a/evidence/: the quarantine
    # copied it forward so the runner could resume at block 01. Its money is already in the study
    # ledger and must not be counted twice.
    committed_block = REPO / "phase8a" / "evidence" / "episodes_arm2"
    carried_forward = sorted(d.name for d in committed_block.iterdir() if d.is_dir()) \
        if committed_block.exists() else []
    for name in carried_forward:
        a = sha256_file(committed_block / name / CUSTODY_MANIFEST)
        b = next(e["custody_manifest_sha256"] for e in episodes if e["episode_id"] == name)
        assert a == b, f"{name} differs between the study tree and the quarantine; it was re-run"

    new = [e for e in episodes if e["episode_id"] not in carried_forward]
    spend_new = round(sum(e["total_cost"] for e in new), 4)
    spend_all = round(sum(e["total_cost"] for e in episodes), 4)

    per_instance = {}
    for e in episodes:
        per_instance.setdefault(instance_of(e["episode_id"]), []).append(e["total_cost"])
    per_instance = {k: {"n": len(v), "cny": round(sum(v), 4),
                        "per_episode": round(sum(v) / len(v), 4)}
                    for k, v in sorted(per_instance.items())}

    actual_rate = round(spend_all / len(episodes), 4)
    projected_rate = gate["rate"]["r_prime_cny_per_episode"]
    remaining = gate["remainder_cross_check"]["episodes_remaining"]
    projected_new = gate["remainder_cross_check"]["projected_cny"]
    available = gate["budget"]["remaining_after_holdback_cny"]
    calibration_instance = instance_of(carried_forward[0]) if carried_forward else None

    return {
        "schema": "phase8a_arm2_quarantine/v1",
        "analysis_status": "never_analyzed",
        "what_this_is": (
            "72 DeepSeek-V4-Pro episodes at the S3 coordinate (12 instances x 3 conditions x k=2), "
            "generated under quarantine after the preregistered cost gate had already refused the "
            "arm. They are not the preregistered S3 arm, they carry no preregistered analysis, and "
            "no condition contrast has ever been computed from them."
        ),
        "rationale": RATIONALE,
        "s3_status": {
            "preregistered_eligible_arm": "not executed",
            "quarantined_trajectories": len(episodes),
            "condition_contrast_computed": False,
            "s3_effect_estimate": None,
            "reason_no_estimate": (
                "Reporting a contrast would convert an exclusion fixed before the data existed into "
                "an outcome-informed exploratory analysis, and these episodes are the shallower "
                "k=2 arm the preregistration declined to fund."
            ),
        },
        "ordering_that_makes_this_safe": {
            "gate_decided_at": gate["decided_at"],
            "gate_decision": gate["decision"],
            "first_quarantined_block_started_at": min(b["started_at"] for b in blocks
                                                      if b["block"] != "00"),
            "last_quarantined_block_finished_at": max(b["finished_at"] for b in blocks),
            "note": ("Every block after 00 began after the gate had been decided and committed, so "
                     "no S3 outcome could have informed the decision to exclude them."),
        },
        "read_discipline": {
            "files_opened": [EPISODE_MANIFEST, CUSTODY_MANIFEST],
            "files_never_opened": list(FORBIDDEN_FILES),
            "episode_keys_kept": list(READABLE_KEYS),
            "episode_keys_dropped": list(OUTCOME_KEYS),
            "enforced_by": "tests/test_phase8a.py, under an audit hook, not by this docstring",
        },
        "execution": {
            "blocks": blocks,
            "blocks_complete": sum(b["state"] == "COMPLETE" for b in blocks),
            "slots_completed": sum(b["completed_primary_slots"] for b in blocks),
            "slots_expected": sum(b["expected_primary_slots"] for b in blocks),
            "invalid_attempts": sum(b["excluded_invalid_attempts"] for b in blocks),
            "aggregate_report_generated": not any(b["report_pending"] for b in blocks),
        },
        "money": {
            "episodes_total": len(episodes),
            "episodes_carried_forward_from_study_ledger": len(carried_forward),
            "episodes_new": len(new),
            "realized_cny_total": spend_all,
            "realized_cny_new": spend_new,
            # The programme ledger the manuscript reports covers the study; this run sits outside it
            # and enters no analysis, but the money was really spent, so both figures are carried.
            "eligible_analysis_cny": gate["budget"]["program_spend_cny"],
            "total_realized_cny": round(gate["budget"]["program_spend_cny"] + spend_new, 4),
            "cap_cny": gate["budget"]["cap_cny"],
            "cap_breached": round(gate["budget"]["program_spend_cny"] + spend_new, 4)
                            > gate["budget"]["cap_cny"],
            "note": ("Block 00 is byte-identical to the block already committed under "
                     "phase8a/evidence/episodes_arm2 and its money is already in the study ledger; "
                     "only realized_cny_new is additional programme spend."),
            "per_instance": per_instance,
        },
        "cost_gate_calibration": {
            "finding": ("The preregistered gate refused an arm that was affordable at realized "
                        "cost. Its rule was applied correctly; its rate estimator was calibrated "
                        "on a sample that did not represent the panel it gated."),
            "projected_rate_cny_per_episode": projected_rate,
            "realized_rate_cny_per_episode": actual_rate,
            "rate_overestimate_pct": round(100 * (projected_rate / actual_rate - 1), 1),
            "episodes_the_gate_priced": remaining,
            "projected_cny_for_those": projected_new,
            "realized_cny_for_those": spend_new,
            "available_after_holdback_cny": available,
            "gate_verdict": "does not fit",
            "verdict_at_realized_cost": "fits" if spend_new <= available else "does not fit",
            "margin_at_realized_cost_cny": round(available - spend_new, 4),
            "why_the_estimator_missed": {
                "calibration_pooled": gate["rate"]["pooled_episodes"],
                "calibration_instance": calibration_instance,
                "calibration_instance_rate": per_instance[calibration_instance]["per_episode"]
                                             if calibration_instance else None,
                "panel_mean_rate": actual_rate,
                "cheapest_instance_rate": min(v["per_episode"] for v in per_instance.values()),
                "dearest_instance_rate": max(v["per_episode"] for v in per_instance.values()),
                "instance_spread_factor": round(max(v["per_episode"] for v in per_instance.values())
                                                / min(v["per_episode"] for v in per_instance.values()), 2),
                "spread_the_gate_recorded_and_averaged_away": gate["rate"]["spread_factor"],
            },
        },
        "episodes": sorted(episodes, key=lambda e: e["episode_id"]),
    }


def outcome_keys_leaked(record: dict) -> list[str]:
    """Outcome key names appearing anywhere except the block that documents dropping them.

    `read_discipline.episode_keys_dropped` has to name them -- that is its whole content -- so it is
    the one place the scan must skip. Everywhere else a match means an outcome reached the record.
    """
    scanned = {k: v for k, v in record.items() if k != "read_discipline"}
    blob = json.dumps(scanned, ensure_ascii=False)
    return [k for k in OUTCOME_KEYS if k in blob]


def macros(record: dict) -> str:
    """Emit the accounting figures as LaTeX macros, so the manuscript transcribes no number.

    Only money and counts appear here. There is no macro this file could grow that would carry a
    condition contrast, because the record it reads has none.
    """
    c, m = record["cost_gate_calibration"], record["money"]
    w = c["why_the_estimator_missed"]
    pairs = [
        ("StatArmTwoQuarantined", m["episodes_total"]),
        ("StatArmTwoQuarantinedNew", m["episodes_new"]),
        ("StatArmTwoQuarantinedCny", f"{m['realized_cny_new']:.2f}"),
        ("StatArmTwoEligibleCny", f"{record['money']['eligible_analysis_cny']:.2f}"),
        ("StatArmTwoRealizedCny", f"{record['money']['total_realized_cny']:.2f}"),
        ("StatArmTwoRateProjected", f"{c['projected_rate_cny_per_episode']:.3f}"),
        ("StatArmTwoRateRealized", f"{c['realized_rate_cny_per_episode']:.3f}"),
        ("StatArmTwoPriced", c["episodes_the_gate_priced"]),
        ("StatArmTwoPricedProjected", f"{c['projected_cny_for_those']:.2f}"),
        ("StatArmTwoPricedRealized", f"{c['realized_cny_for_those']:.2f}"),
        ("StatArmTwoAvailable", f"{c['available_after_holdback_cny']:.2f}"),
        ("StatArmTwoMargin", f"{c['margin_at_realized_cost_cny']:.2f}"),
        ("StatArmTwoCalibInstance", w["calibration_instance"].replace("_", r"\_")),
        ("StatArmTwoCalibRate", f"{w['calibration_instance_rate']:.3f}"),
        ("StatArmTwoPanelRate", f"{w['panel_mean_rate']:.3f}"),
        ("StatArmTwoCheapestRate", f"{w['cheapest_instance_rate']:.3f}"),
        ("StatArmTwoGateSpread", w["spread_the_gate_recorded_and_averaged_away"]),
    ]
    head = ("% Generated by scripts/phase8a_arm2_quarantine.py -- do not edit.\n"
            "% Accounting for the quarantined arm-2 trajectories. Money and counts only:\n"
            "% their condition contrast has never been computed and no macro here can carry one.\n")
    return head + "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in pairs)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="recompute and fail on drift")
    args = ap.parse_args()

    if args.check and not QUARANTINE_ROOT.exists():
        # The tree is gitignored, so a fresh clone cannot re-derive it. Verify what is committed.
        record = json.loads(RECORD.read_text())
        assert record["analysis_status"] == "never_analyzed", record["analysis_status"]
        assert record["s3_status"]["condition_contrast_computed"] is False
        assert record["s3_status"]["s3_effect_estimate"] is None
        assert not outcome_keys_leaked(record), outcome_keys_leaked(record)
        print("quarantine tree absent (gitignored); committed record self-consistent: "
              f"{record['money']['episodes_total']} episodes, never analyzed")
        return 0

    built = build()
    assert not outcome_keys_leaked(built), f"an outcome key reached the record: {outcome_keys_leaked(built)}"

    if args.check:
        current = json.loads(RECORD.read_text())
        drift = [name for name, have, want in
                 (("arm2_quarantine_record.json", current, built),
                  ("tables/arm2_quarantine.tex", MACROS.read_text(), macros(built)))
                 if have != want]
        if drift:
            print(f"DRIFT: {', '.join(drift)} does not match the tree", file=sys.stderr)
            return 1
        print(f"ok: {built['money']['episodes_total']} quarantined episodes, "
              f"{built['execution']['blocks_complete']}/{len(built['execution']['blocks'])} blocks "
              f"complete, ¥{built['money']['realized_cny_new']} new spend, never analyzed")
        return 0

    RECORD.write_text(json.dumps(built, indent=2, ensure_ascii=False) + "\n")
    MACROS.write_text(macros(built))
    print(f"wrote {RECORD.relative_to(REPO)} and {MACROS.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
