#!/usr/bin/env python3
"""Phase-8A claim statistics: the manuscript-facing numbers of both STA panels.

This script adds **no new data**. It re-reads the frozen Phase-8A reports and re-derives
every quantity the manuscript prints, so that no number is transcribed by hand -- the same
discipline ``phase7c_claim_statistics.py`` applies to the k=2 study.

Two panels are covered, by the *same* functions:

* **arm 1** -- ``qwen3.7-max``, 12 instances x 3 conditions x k=6 (216 episodes). The
  preregistered arm; cross-family (S2-F).
* **arm 2** -- ``deepseek-v4-pro``, the same 12 frozen instances at k=2 (72 episodes). The
  joint model x family coordinate (S3).

Arm 2's provenance is stated rather than smoothed over. Its episodes were executed *after*
the preregistered cost gate returned ``ARM2_NOT_RUN``, so they are **not** the arm that
preregistration sized, and this script asserts ``provenance.preregistered is False`` on its
report. What governs the analysis is
``phase8a/evidence/arm2_analysis_plan.json``, committed before any arm-2 outcome field was
read; ``compute()`` asserts the report was built against that exact byte sequence, so
editing the plan afterwards breaks ``--check`` rather than silently re-governing a published
number. Nothing was relaxed to permit the analysis: ``phase8a_report.py`` withholds
condition aggregates iff a planned instance is missing, and arm 2 ran 12 of 12.

What is computed, each from a committed source:

1. **Panel estimate and its composition sensitivity**, per arm. Delta_hat =
   mean_i(BundleS_i - Base_i) over the twelve instances, plus a percentile bootstrap
   resampling the twelve **instances** (the declared unit -- never the trajectories). The
   band is an *instance-resampling sensitivity band*, not a confidence interval, for exactly
   the reason the v14 script states: the estimand is the realized panel, whose composition
   has no sampling distribution. The frozen exact sign test remains the inferential result.

2. **Panel anatomy**, per arm. How many of the twelve instances can express a condition
   difference at all. The predicate is *identical* to the one v14 applied to the k=2 panel,
   and this script proves that mechanically: it runs its own classifier over Phase-7A's
   instances and asserts the counts equal Phase-7A's frozen ``panel_anatomy`` block.
   Without that check, "the anatomy reproduces" could be an artifact of two
   differently-worded rules.

3. **Structural concordance (post hoc, not preregistered)**, in two flavours that are kept
   apart because they are confounded differently: *cross-batch* (same model, k=2 vs k=6) and
   *cross-model* (arm 1 vs arm 2, which differ in the model **and** in k, so agreement
   cannot be attributed to the model alone). Neither is pooling: no quantity is summed,
   averaged or differenced across batches or arms.

4. **Within-cell replication stability.** How many of the 36 (instance, condition) cells
   have six identical repetitions that disagree with each other. This is the quantity that
   makes low-repetition harness estimates fragile, and it is only visible at k>2. It is also
   why arm 2's k=2 cell values carry no magnitude claim.

5. **The interpretation branch**, evaluated from the plan's pre-committed thresholds in code
   rather than chosen after reading the numbers.

Usage:
    python3 scripts/phase8a_claim_statistics.py            # write JSON + LaTeX
    python3 scripts/phase8a_claim_statistics.py --check    # verify committed outputs
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from phase7c_claim_statistics import instance_resampling_band  # noqa: E402

EIGHTA = REPO / "phase8a" / "reports" / "phase8a_sta_report.json"
EIGHTA_ARM2 = REPO / "phase8a" / "reports" / "phase8a_sta_report_arm2.json"
GATE = REPO / "phase8a" / "evidence" / "arm2_gate_decision.json"
SEVENA = REPO / "reports" / "synthetic_phase7a_sta72_report.json"
SEVENA_STATS = REPO / "reports" / "synthetic_p14_claim_statistics.json"

OUT_JSON = REPO / "phase8a" / "reports" / "phase8a_claim_statistics.json"
OUT_TEX = REPO / "submission" / "tables" / "phase8a_stats.tex"
OUT_PANEL_TEX = REPO / "submission" / "tables" / "sta12_k6.tex"
OUT_CONCORD_TEX = REPO / "submission" / "tables" / "sta_concordance.tex"
OUT_ARM2_TEX = REPO / "submission" / "tables" / "sta12_arm2.tex"

BOOTSTRAP_REPLICATES = 100_000
BOOTSTRAP_SEED = 20260820

CONDITIONS = ("Base", "BundleS", "TypedContract")

# The plan that governs the arm-2 analysis. Committed before any arm-2 outcome was read; compute()
# asserts the arm-2 report was built against this exact byte sequence.
ARM2_PLAN = REPO / "phase8a" / "evidence" / "arm2_analysis_plan.json"


def _programme_spend() -> float:
    """Every CNY this study paid, from the one function the runner itself uses.

    Recomputed rather than read out of the gate decision: the gate recorded the spend as it stood
    when it fired, and quoting that stale figure as the programme total is how a cap silently grows
    by everything spent afterwards.
    """
    sys.path.insert(0, str(REPO / "scripts"))
    import phase8a_run  # noqa: PLC0415
    return phase8a_run._program_spend()


# --------------------------------------------------------------------------- classifier


def classify(base_rate: float, bundles_rate: float) -> str:
    """Partition an instance by whether it can express a Base-vs-BundleS difference.

    Byte-for-byte the rule v14 used on the k=2 panel: floor = zero in both arms, ceiling =
    one in both arms, informative = a non-zero difference. Kept as one function precisely so
    the two batches cannot be classified by two subtly different rules -- which is the only
    thing that would make the concordance below a rhetorical coincidence rather than a
    measurement.
    """
    if base_rate == 0.0 and bundles_rate == 0.0:
        return "floor"
    if base_rate == 1.0 and bundles_rate == 1.0:
        return "ceiling"
    if bundles_rate - base_rate != 0.0:
        return "informative"
    return "unclassified"


def anatomy(instances: list[dict]) -> dict:
    """floor/ceiling/informative counts under `classify`, plus the members of each class."""
    rows = [(i["instance"], i["Base_rate"], i["BundleS_rate"]) for i in instances]
    out: dict[str, list[str]] = {"floor": [], "ceiling": [], "informative": [],
                                 "unclassified": []}
    for name, b, s in rows:
        out[classify(b, s)].append(name)
    assert not out["unclassified"], (
        f"instances {out['unclassified']} are neither floor, ceiling nor informative; the "
        "partition v14 declared does not cover this panel and must not be reported as if it did"
    )
    return out


def _rates_from_reps(inst: dict) -> dict:
    """Recompute each condition's rate from its booleans.

    The report stores rates rounded to four places. Deriving from the raw repetition
    booleans keeps the arithmetic exact and lets the rounded values serve as a cross-check
    rather than as the input.
    """
    out = {}
    for cond in CONDITIONS:
        reps = inst[f"{cond}_reps"]
        out[cond] = sum(1 for r in reps if r) / len(reps)
        assert abs(out[cond] - inst[f"{cond}_rate"]) < 5e-4, (
            f"{inst['instance']}/{cond}: rate recomputed from repetitions disagrees with "
            "the value the frozen report declares"
        )
    return out


# --------------------------------------------------------------------------- computation


def compute() -> dict:
    eight = json.loads(EIGHTA.read_text())
    seven = json.loads(SEVENA.read_text())
    gate = json.loads(GATE.read_text())
    arm2 = json.loads(EIGHTA_ARM2.read_text())
    seven_stats = json.loads(SEVENA_STATS.read_text())

    assert eight["arm"] == 1 and eight["n_episodes_collected"] == 216, \
        "expected the complete 216-episode arm-1 panel"
    k_observed = eight["k_per_condition_observed"]
    assert k_observed == [6], f"expected k=6 throughout, got {k_observed}"

    # ---- the classifier reproduces v14's frozen anatomy on v14's own panel --------------
    # Run our rule over the *k=2* panel and require it to return exactly what v14 recorded.
    # If it does not, the two panels are not being classified by one rule and no structural
    # comparison between them may be drawn.
    seven_anat = anatomy(seven["instances"])
    declared7 = seven_stats["sta_finite_panel"]["panel_anatomy"]
    assert (len(seven_anat["floor"]), len(seven_anat["ceiling"]),
            len(seven_anat["informative"])) == (
        declared7["floor_limited_both_arms"], declared7["ceiling_limited_both_arms"],
        declared7["informative_instances"]), (
        "this script's classifier does not reproduce the frozen Phase-7A panel anatomy; "
        "the cross-batch comparison would then be comparing two different rules"
    )

    # ---- the k=6 panel ------------------------------------------------------------------
    per_instance = []
    for inst in eight["instances"]:
        rates = _rates_from_reps(inst)
        k = len(inst["Base_reps"])
        per_instance.append({
            "instance": inst["instance"],
            "correct_of_k": {c: sum(1 for r in inst[f"{c}_reps"] if r) for c in CONDITIONS},
            "k": k,
            "rates": rates,
            "BundleS_minus_Base": rates["BundleS"] - rates["Base"],
            "TC_minus_Base": rates["TypedContract"] - rates["Base"],
            "class": classify(rates["Base"], rates["BundleS"]),
            # A cell that is neither all-correct nor all-wrong is, by definition, six
            # identical repetitions that disagreed with each other.
            "cells_unstable": [c for c in CONDITIONS
                               if 0 < sum(1 for r in inst[f"{c}_reps"] if r) < k],
        })

    diffs = [r["BundleS_minus_Base"] for r in per_instance]
    n_inst = len(diffs)
    delta_hat = sum(diffs) / n_inst
    d_lo, d_hi = instance_resampling_band(diffs, BOOTSTRAP_REPLICATES, BOOTSTRAP_SEED)

    declared = eight["condition_mean_rates_over_instances_descriptive"]
    assert n_inst == 12, f"expected 12 instances, got {n_inst}"
    assert abs(delta_hat - (declared["BundleS"] - declared["Base"])) < 5e-4, \
        "recomputed panel difference disagrees with the frozen descriptive means"
    tally = eight["contrast_tally_instance_level"]["primary_BundleS_vs_Base"]
    assert (sum(d > 0 for d in diffs), sum(d < 0 for d in diffs), sum(d == 0 for d in diffs)) == \
        (tally["improve"], tally["decline"], tally["tie"]), \
        "recomputed improve/decline/tie tally disagrees with the frozen report"

    eight_anat = anatomy(eight["instances"])
    assert len(eight_anat["informative"]) == tally["improve"] + tally["decline"], \
        "informative count disagrees with the frozen improve+decline tally"

    # Leave-two-out, in the two forms v14 keeps distinct so neither is quoted as the other.
    order = sorted(per_instance, key=lambda r: -r["BundleS_minus_Base"])
    dominant = [r["instance"] for r in order[:2]]
    kept = [r["BundleS_minus_Base"] for r in per_instance if r["instance"] not in set(dominant)]
    delta_leave_two_out = sum(kept) / len(kept)
    delta_two_zeroed = sum(kept) / n_inst

    # ---- within-cell replication stability ---------------------------------------------
    unstable = [(r["instance"], c) for r in per_instance for c in r["cells_unstable"]]
    total_cells = n_inst * len(CONDITIONS)
    seven_unstable = sum(
        1 for i in seven["instances"] for c in CONDITIONS
        if 0 < sum(1 for r in i[f"{c}_reps"] if r) < len(i[f"{c}_reps"])
    )

    # ---- cross-batch structural concordance (post hoc) ---------------------------------
    seven_by_name = {i["instance"]: i for i in seven["instances"]}
    concordance = []
    for r in per_instance:
        s = seven_by_name[r["instance"]]
        s_cls = classify(s["Base_rate"], s["BundleS_rate"])
        s_diff = s["BundleS_rate"] - s["Base_rate"]
        concordance.append({
            "instance": r["instance"],
            "k2_class": s_cls, "k2_diff": s_diff,
            "k6_class": r["class"], "k6_diff": r["BundleS_minus_Base"],
            "same_class": s_cls == r["class"],
            "informative_in_both": s_cls == "informative" and r["class"] == "informative",
            "same_sign": (s_diff > 0) == (r["BundleS_minus_Base"] > 0)
            if (s_cls == "informative" and r["class"] == "informative") else None,
        })
    same_class = [c["instance"] for c in concordance if c["same_class"]]
    both_inf = [c for c in concordance if c["informative_in_both"]]
    sign_agree = [c["instance"] for c in both_inf if c["same_sign"]]

    # ---- arm 2: the joint model x family panel ------------------------------------------
    # Computed by the same functions as arm 1, deliberately. The plan that governs this analysis
    # (phase8a/evidence/arm2_analysis_plan.json) was committed before any arm-2 outcome was read;
    # assert the report was built against that exact plan, so a later edit to the plan cannot
    # retroactively re-govern a published number.
    plan_sha = hashlib.sha256(ARM2_PLAN.read_bytes()).hexdigest()
    assert arm2["governing_analysis_plan_sha256"] == plan_sha, (
        "arm 2's report was built against a different analysis plan than the one on disk; the "
        "pre-outcome ordering that makes this analysis interpretable can no longer be verified"
    )
    assert arm2["provenance"]["preregistered"] is False, (
        "arm 2 must never be recorded as preregistered: it was executed after the preregistered "
        "cost gate returned ARM2_NOT_RUN"
    )
    assert arm2["n_episodes_collected"] == 72 and arm2["k_per_condition_observed"] == [2], \
        "expected the complete 72-episode arm-2 panel at k=2"

    a2_per_instance = []
    for inst in arm2["instances"]:
        rates = _rates_from_reps(inst)
        a2_per_instance.append({
            "instance": inst["instance"],
            "correct_of_k": {c: sum(1 for r in inst[f"{c}_reps"] if r) for c in CONDITIONS},
            "k": len(inst["Base_reps"]),
            "rates": rates,
            "BundleS_minus_Base": rates["BundleS"] - rates["Base"],
            "TC_minus_Base": rates["TypedContract"] - rates["Base"],
            "class": classify(rates["Base"], rates["BundleS"]),
        })
    a2_diffs = [r["BundleS_minus_Base"] for r in a2_per_instance]
    a2_delta = sum(a2_diffs) / len(a2_diffs)
    a2_lo, a2_hi = instance_resampling_band(a2_diffs, BOOTSTRAP_REPLICATES, BOOTSTRAP_SEED)
    a2_anat = anatomy(arm2["instances"])
    a2_declared = arm2["condition_mean_rates_over_instances_descriptive"]
    a2_tally = arm2["contrast_tally_instance_level"]["primary_BundleS_vs_Base"]
    assert abs(a2_delta - (a2_declared["BundleS"] - a2_declared["Base"])) < 5e-4, \
        "recomputed arm-2 panel difference disagrees with its frozen descriptive means"

    # The plan fixed which wording each outcome licenses. Evaluate those criteria in code rather
    # than by reading the numbers and choosing, so the branch is a computed fact.
    a2_sign = arm2["primary_sign_test"]
    a2_band_excludes_zero = not (a2_lo <= 0.0 <= a2_hi)
    a2_p_significant = a2_sign["two_sided_exact_p"] < 0.05
    a2_direction_favourable = a2_tally["improve"] > a2_tally["decline"]
    a2_support = a2_p_significant and a2_band_excludes_zero and a2_direction_favourable

    # Cross-MODEL concordance. Note the confound and do not launder it: the two arms differ in the
    # model AND in k, so agreement cannot be attributed to the model alone.
    a1_by_name = {r["instance"]: r for r in per_instance}
    cross_model = []
    for r in a2_per_instance:
        a1r = a1_by_name[r["instance"]]
        both = a1r["class"] == "informative" and r["class"] == "informative"
        cross_model.append({
            "instance": r["instance"],
            "arm1_k6_class": a1r["class"], "arm1_k6_diff": a1r["BundleS_minus_Base"],
            "arm2_k2_class": r["class"], "arm2_k2_diff": r["BundleS_minus_Base"],
            "same_class": a1r["class"] == r["class"],
            "informative_in_both": both,
            "same_sign": ((a1r["BundleS_minus_Base"] > 0) == (r["BundleS_minus_Base"] > 0))
            if both else None,
        })
    xm_both = [c for c in cross_model if c["informative_in_both"]]
    xm_agree = [c["instance"] for c in xm_both if c["same_sign"]]
    xm_disagree = [c["instance"] for c in xm_both if c["same_sign"] is False]
    a2_model_dependence = len(xm_disagree) > len(xm_both) / 2

    return {
        "schema": "phase8a_claim_statistics/v1",
        "purpose": (
            "manuscript-facing re-derivation of both Phase-8A panels -- the k=6 arm-1 panel "
            "and the k=2 arm-2 joint model x family panel; no new data, no model call, no "
            "tool run"
        ),
        "sources": {
            "k6_panel": str(EIGHTA.relative_to(REPO)),
            "k2_panel": str(SEVENA.relative_to(REPO)),
            "arm2_gate": str(GATE.relative_to(REPO)),
            "arm2_panel": str(EIGHTA_ARM2.relative_to(REPO)),
            "arm2_analysis_plan": str(ARM2_PLAN.relative_to(REPO)),
        },
        "method": {
            "panel_sensitivity_band": (
                f"percentile bootstrap resampling the {n_inst} instances "
                f"({BOOTSTRAP_REPLICATES} replicates, seed {BOOTSTRAP_SEED}); an "
                "instance-resampling sensitivity band over panel composition, NOT a "
                "confidence interval"
            ),
            "preregistered_analysis_unchanged": (
                "the frozen exact paired sign test and permutation sensitivity remain the "
                "reported inferential result; the band and the anatomy are descriptive"
            ),
            "classifier_provenance": (
                "floor/ceiling/informative uses one function for both batches, asserted "
                "against Phase-7A's frozen panel_anatomy block before any comparison is made"
            ),
        },
        "k6_panel": {
            "n_instances": n_inst,
            "k_per_cell": 6,
            "n_episodes": eight["n_episodes_collected"],
            "estimand": "the realized 12-instance panel at k=6; inference goes no further",
            "condition_means": declared,
            "delta_hat_BundleS_minus_Base": delta_hat,
            "instance_resampling_band95": [d_lo, d_hi],
            "band_interpretation": (
                "how far the point estimate moves when panel membership is resampled; not a "
                "confidence interval, since the realized panel's composition carries no "
                "sampling uncertainty"
            ),
            "frozen_sign_test": eight["primary_sign_test"],
            "frozen_permutation_two_sided_p":
                eight["primary_permutation_sensitivity"]["two_sided_permutation_p"],
            "panel_anatomy": {
                "post_hoc": True,
                "floor_limited_both_arms": len(eight_anat["floor"]),
                "ceiling_limited_both_arms": len(eight_anat["ceiling"]),
                "informative_instances": len(eight_anat["informative"]),
                "floor_members": eight_anat["floor"],
                "ceiling_members": eight_anat["ceiling"],
                "informative_members": eight_anat["informative"],
                "dominant_instances": dominant,
                "delta_leave_two_out_n10": delta_leave_two_out,
                "delta_two_zeroed_within_n12": delta_two_zeroed,
                "heterogeneity_range": [min(diffs), max(diffs)],
            },
            "per_instance": per_instance,
        },
        "within_cell_replication_stability": {
            "cells_total": total_cells,
            "cells_whose_six_repetitions_disagree": len(unstable),
            "cells": [{"instance": i, "condition": c} for i, c in unstable],
            "k2_comparison": {
                "cells_total": len(seven["instances"]) * len(CONDITIONS),
                "cells_whose_two_repetitions_disagree": seven_unstable,
                "note": (
                    "not a rate comparison: two repetitions can disagree in one way and six "
                    "in five ways, so the two counts are not on one scale. Reported only to "
                    "show the quantity is invisible at k=2, not to contrast the batches."
                ),
            },
            "interpretation": (
                "a cell that is neither all-correct nor all-wrong is a set of identical "
                "repetitions that disagreed. At k=6 that is measurable per cell; a single "
                "trajectory drawn from such a cell is a coin flip about the cell's own value."
            ),
        },
        "cross_batch_structural_concordance": {
            "post_hoc": True,
            "preregistered": False,
            "is_pooling": False,
            "what_it_is": (
                "a comparison of the per-instance CLASS and SIGN produced by two independently "
                "executed batches. No quantity is summed, averaged or differenced across them."
            ),
            "what_it_is_not": (
                "evidence about either batch's serving endpoint, and not a replication in the "
                "sense of the paper's qualification standard: the k=6 batch re-runs the same "
                "frozen instances, which is repeated measurement of stability, not scope."
            ),
            "instances_classified_identically": len(same_class),
            "instances_total": n_inst,
            "identical_members": same_class,
            "informative_in_both": [c["instance"] for c in both_inf],
            "sign_agreement_among_informative_in_both": [len(sign_agree), len(both_inf)],
            "class_changes": [
                {"instance": c["instance"], "k2": c["k2_class"], "k6": c["k6_class"],
                 "k2_diff": c["k2_diff"], "k6_diff": c["k6_diff"]}
                for c in concordance if not c["same_class"]
            ],
            "per_instance": concordance,
        },
        "arm2_joint_panel": {
            "coordinate": "S3 -- joint model x family: a different model AND a different family "
                          "than the setting where the effect was first observed",
            "model_name": arm2["model_name"],
            "n_instances": len(a2_diffs),
            "k_per_cell": 2,
            "n_episodes": arm2["n_episodes_collected"],
            "measurement_invalid_attempts": arm2["measurement_invalid_attempts"],
            "provenance": {
                "preregistered": False,
                "why_not": (
                    "these episodes were executed after the preregistered cost gate returned "
                    "ARM2_NOT_RUN, so they are not the arm the preregistration sized. The claim "
                    "that they were preregistered and executed per docs/phase8a_prereg.md is "
                    "false and is made nowhere."
                ),
                "what_is_claimed": (
                    "the analysis plan was committed before any outcome field was read, and it "
                    "is the arm-1 analysis in the arm-1 code"
                ),
                "analysis_plan": "docs/phase8a_arm2_analysis_plan.md",
                "analysis_plan_sha256": plan_sha,
                "no_rule_was_weakened": (
                    "phase8a_report.py withholds condition aggregates iff a planned instance is "
                    "missing. Arm 2 ran 12 of 12, so the unmodified rule permits them; the "
                    "control's precondition is satisfied rather than relaxed."
                ),
            },
            "condition_means": a2_declared,
            "delta_hat_BundleS_minus_Base": a2_delta,
            "instance_resampling_band95": [a2_lo, a2_hi],
            "sign_test": a2_sign,
            "permutation_two_sided_p":
                arm2["primary_permutation_sensitivity"]["two_sided_permutation_p"],
            "contrast_tally": arm2["contrast_tally_instance_level"],
            "panel_anatomy": {
                "post_hoc": True,
                "floor_limited_both_arms": len(a2_anat["floor"]),
                "ceiling_limited_both_arms": len(a2_anat["ceiling"]),
                "informative_instances": len(a2_anat["informative"]),
                "floor_members": a2_anat["floor"],
                "ceiling_members": a2_anat["ceiling"],
                "informative_members": a2_anat["informative"],
                "heterogeneity_range": [min(a2_diffs), max(a2_diffs)],
            },
            # The plan's criteria, evaluated in code so the wording is a computed consequence of
            # pre-committed thresholds rather than a choice made after seeing the numbers.
            "interpretation_branch": {
                "criteria_fixed_in": "phase8a/evidence/arm2_analysis_plan.json "
                                     "-> interpretation_fixed_in_advance",
                "p_below_0_05": a2_p_significant,
                "band_excludes_zero": a2_band_excludes_zero,
                "improvements_outnumber_declines": a2_direction_favourable,
                "branch": "support" if a2_support else "not_established",
                "wording_licensed": (
                    "joint model x family transfer observed at S3 on this panel at k=2"
                    if a2_support else
                    "joint model x family transfer NOT ESTABLISHED on this panel"
                ),
                "descriptively": (
                    "the point estimate favours BundleS and improvements outnumber declines "
                    f"({a2_tally['improve']} to {a2_tally['decline']}), but the sign test cannot "
                    "distinguish that split from a coin and the band spans zero"
                ) if a2_direction_favourable and not a2_support else None,
                "must_not_be_worded_as": (
                    "evidence that BundleS has no effect. A panel with "
                    f"{len(a2_anat['floor'])} floor-limited and "
                    f"{len(a2_anat['ceiling'])} ceiling-limited instances fails to show a "
                    "difference for reasons independent of whether one exists."
                ),
            },
            "repetition_depth_limit": {
                "k": 2,
                "why_it_binds": (
                    "arm 1 measured 7 of 36 cells disagreeing across six identical repetitions on "
                    "this same family, so a single trajectory is a coin flip about its cell's own "
                    "value roughly 19% of the time. No claim is made about the magnitude or "
                    "stability of any arm-2 cell value."
                ),
                "forbidden_comparison": (
                    "arm 2's aggregate may not be set beside arm 1's k=6 aggregate as though the "
                    "two were equally resolved"
                ),
            },
            "per_instance": a2_per_instance,
        },
        "cross_model_structural_concordance": {
            "post_hoc": True,
            "preregistered": False,
            "is_pooling": False,
            "confounded": True,
            "confound": (
                "arm 1 and arm 2 differ in the MODEL and in k (6 vs 2). Agreement therefore "
                "cannot be attributed to the model alone, and this is not an estimate of "
                "anything -- it is a description of which instances carry the effect."
            ),
            "what_it_is": (
                "a comparison of per-instance CLASS and SIGN across two models on the same "
                "twelve frozen instances. No quantity is summed, averaged or differenced."
            ),
            "instances_classified_identically": len([c for c in cross_model if c["same_class"]]),
            "instances_total": len(cross_model),
            "informative_in_both": [c["instance"] for c in xm_both],
            "sign_agreement_among_informative_in_both": [len(xm_agree), len(xm_both)],
            "sign_agreeing_members": xm_agree,
            "sign_disagreeing_members": xm_disagree,
            "model_dependence_branch_fires": a2_model_dependence,
            "reading": (
                "the same instances tend to carry the effect in the same direction under both "
                "models, which locates the heterogeneity in the INSTANCES rather than in the "
                "model. It does not establish transfer of the aggregate effect, which neither "
                "arm establishes."
            ),
            "per_instance": cross_model,
        },
        "money": {
            "arm1_cny": eight["spent_cny"],
            "arm1_aborted_block_passes_cny": eight["spent_on_aborted_block_passes_cny"],
            "arm2_cny": arm2["spent_cny"],
            "arm2_aborted_block_passes_cny": arm2["spent_on_aborted_block_passes_cny"],
            "arm2_replaced_attempts_cny": arm2["spent_on_replaced_attempts_cny"],
            # One figure. The earlier split into "eligible analysis spend" and "total realized
            # spend" existed only because arm 2's episodes were excluded from analysis; now that
            # they are analysed, every ¥ paid is behind a reported number and one total is honest.
            "programme_spend_cny": _programme_spend(),
            "cap_cny": gate["budget"]["cap_cny"],
            "cap_breached": _programme_spend() > gate["budget"]["cap_cny"],
            "note": ("counts live episodes of every arm, archived aborted passes, replaced "
                     "attempts and the arm-2 cost probe; money paid is money paid"),
        },
    }



# --------------------------------------------------------------------------- rendering


def render_tex(st: dict) -> str:
    lines = [
        "% Generated by scripts/phase8a_claim_statistics.py -- do not edit by hand.",
        "% Phase-8A k=6 STA panel; re-derived from the frozen report, no new data.",
    ]

    def macro(name: str, value: str) -> None:
        lines.append(f"\\newcommand{{\\{name}}}{{{value}}}")

    p = st["k6_panel"]
    macro("StatEightAK", str(p["k_per_cell"]))
    macro("StatEightAEpisodes", str(p["n_episodes"]))
    macro("StatEightAInstances", str(p["n_instances"]))
    macro("StatEightABase", f"{p['condition_means']['Base']:.3f}")
    macro("StatEightABundleS", f"{p['condition_means']['BundleS']:.3f}")
    macro("StatEightATC", f"{p['condition_means']['TypedContract']:.3f}")
    macro("StatEightADelta", f"{100 * p['delta_hat_BundleS_minus_Base']:+.1f}")
    macro("StatEightABandLo", f"{100 * p['instance_resampling_band95'][0]:+.1f}")
    macro("StatEightABandHi", f"{100 * p['instance_resampling_band95'][1]:+.1f}")
    macro("StatEightASignNonzero", str(p["frozen_sign_test"]["n_nonzero_instance_diffs"]))
    macro("StatEightASignPositive", str(p["frozen_sign_test"]["k_positive"]))
    macro("StatEightASignP", f"{p['frozen_sign_test']['two_sided_exact_p']:.2f}")
    macro("StatEightAPermP", f"{p['frozen_permutation_two_sided_p']:.2f}")
    a = p["panel_anatomy"]
    macro("StatEightAFloorN", str(a["floor_limited_both_arms"]))
    macro("StatEightACeilingN", str(a["ceiling_limited_both_arms"]))
    macro("StatEightAInformativeN", str(a["informative_instances"]))
    macro("StatEightALeaveTwoOut", f"{100 * a['delta_leave_two_out_n10']:+.1f}")
    macro("StatEightAHetLo", f"{100 * a['heterogeneity_range'][0]:+.1f}")
    macro("StatEightAHetHi", f"{100 * a['heterogeneity_range'][1]:+.1f}")

    s = st["within_cell_replication_stability"]
    macro("StatEightAUnstableCells", str(s["cells_whose_six_repetitions_disagree"]))
    macro("StatEightACells", str(s["cells_total"]))

    c = st["cross_batch_structural_concordance"]
    macro("StatConcordSame", str(c["instances_classified_identically"]))
    macro("StatConcordTotal", str(c["instances_total"]))
    macro("StatConcordSignAgree", str(c["sign_agreement_among_informative_in_both"][0]))
    macro("StatConcordSignOf", str(c["sign_agreement_among_informative_in_both"][1]))

    j = st["arm2_joint_panel"]
    macro("StatArmTwoModel", "DeepSeek-V4-Pro")
    macro("StatArmTwoEpisodes", str(j["n_episodes"]))
    macro("StatArmTwoInstances", str(j["n_instances"]))
    macro("StatArmTwoK", str(j["k_per_cell"]))
    macro("StatArmTwoBase", f"{j['condition_means']['Base']:.3f}")
    macro("StatArmTwoBundleS", f"{j['condition_means']['BundleS']:.3f}")
    macro("StatArmTwoTC", f"{j['condition_means']['TypedContract']:.3f}")
    macro("StatArmTwoDelta", f"{100 * j['delta_hat_BundleS_minus_Base']:+.1f}")
    macro("StatArmTwoBandLo", f"{100 * j['instance_resampling_band95'][0]:+.1f}")
    macro("StatArmTwoBandHi", f"{100 * j['instance_resampling_band95'][1]:+.1f}")
    macro("StatArmTwoSignNonzero", str(j["sign_test"]["n_nonzero_instance_diffs"]))
    macro("StatArmTwoSignPositive", str(j["sign_test"]["k_positive"]))
    macro("StatArmTwoSignP", f"{j['sign_test']['two_sided_exact_p']:.2f}")
    macro("StatArmTwoPermP", f"{j['permutation_two_sided_p']:.2f}")
    tal = j["contrast_tally"]["primary_BundleS_vs_Base"]
    macro("StatArmTwoImprove", str(tal["improve"]))
    macro("StatArmTwoDecline", str(tal["decline"]))
    macro("StatArmTwoTie", str(tal["tie"]))
    ja = j["panel_anatomy"]
    macro("StatArmTwoFloorN", str(ja["floor_limited_both_arms"]))
    macro("StatArmTwoCeilingN", str(ja["ceiling_limited_both_arms"]))
    macro("StatArmTwoInformativeN", str(ja["informative_instances"]))
    macro("StatArmTwoHetLo", f"{100 * ja['heterogeneity_range'][0]:+.1f}")
    macro("StatArmTwoHetHi", f"{100 * ja['heterogeneity_range'][1]:+.1f}")

    x = st["cross_model_structural_concordance"]
    macro("StatXModelSame", str(x["instances_classified_identically"]))
    macro("StatXModelTotal", str(x["instances_total"]))
    macro("StatXModelSignAgree", str(x["sign_agreement_among_informative_in_both"][0]))
    macro("StatXModelSignOf", str(x["sign_agreement_among_informative_in_both"][1]))

    m = st["money"]
    macro("StatEightASpend", f"{m['arm1_cny']:.2f}")
    macro("StatArmTwoSpend", f"{m['arm2_cny']:.2f}")
    macro("StatEightAProgramme", f"{m['programme_spend_cny']:.2f}")
    macro("StatEightACap", f"{m['cap_cny']:.0f}")
    return "\n".join(lines) + "\n"


_CLASS_TEX = {"floor": "floor", "ceiling": "ceil.", "informative": "\\textbf{inf.}"}


def _signed(x: float, places: int = 2) -> str:
    if x == 0:
        return f"{0:.{places}f}"
    return ("$-$" if x < 0 else "$+$") + f"{abs(x):.{places}f}"


def render_panel_table(st: dict) -> str:
    """The k=6 per-instance table. Correct-of-k is printed, not the rate.

    Printing `4/6` rather than `0.667` is what makes the replication-stability point
    readable off the table: every cell that is neither 0/6 nor 6/6 is one of the cells whose
    six identical repetitions disagreed.
    """
    p = st["k6_panel"]
    lines = [
        "% Generated by scripts/phase8a_claim_statistics.py -- do not edit by hand.",
        "\\begin{tabular}{l ccc cc l}",
        "\\toprule",
        " & \\multicolumn{3}{c}{correct of $k$=6} & \\multicolumn{2}{c}{difference} & \\\\",
        "\\cmidrule(lr){2-4}\\cmidrule(lr){5-6}",
        "inst. & Base & BundleS & TC & S$-$B & TC$-$B & class \\\\",
        "\\midrule",
    ]
    for r in p["per_instance"]:
        c = r["correct_of_k"]
        lines.append(
            f"{r['instance'].replace('p15_eval_', '')} & "
            f"{c['Base']}/6 & {c['BundleS']}/6 & {c['TypedContract']}/6 & "
            f"{_signed(r['BundleS_minus_Base'])} & {_signed(r['TC_minus_Base'])} & "
            f"{_CLASS_TEX[r['class']]} \\\\"
        )
    m = p["condition_means"]
    lines += [
        "\\midrule",
        f"\\textbf{{mean rate}} & \\textbf{{{m['Base']:.3f}}} & "
        f"\\textbf{{{m['BundleS']:.3f}}} & \\textbf{{{m['TypedContract']:.3f}}} & "
        f"\\textbf{{{_signed(p['delta_hat_BundleS_minus_Base'], 3)}}} & & \\\\",
        "\\bottomrule",
        "\\end{tabular}",
    ]
    return "\n".join(lines) + "\n"


def render_arm2_panel_table(st: dict) -> str:
    """The arm-2 (joint model x family) per-instance table, at k=2.

    Same shape as the k=6 table so the two can be read against each other -- but the header says
    k=2 and the caption in the manuscript says why that matters. Correct-of-2 makes the resolution
    limit visible on its face: a cell reading 1/2 is a cell whose two repetitions disagreed, and at
    k=2 that is the only unstable value expressible.
    """
    j = st["arm2_joint_panel"]
    lines = [
        "% Generated by scripts/phase8a_claim_statistics.py -- do not edit by hand.",
        "\\begin{tabular}{l ccc cc l}",
        "\\toprule",
        " & \\multicolumn{3}{c}{correct of $k$=2} & \\multicolumn{2}{c}{difference} & \\\\",
        "\\cmidrule(lr){2-4}\\cmidrule(lr){5-6}",
        "inst. & Base & BundleS & TC & S$-$B & TC$-$B & class \\\\",
        "\\midrule",
    ]
    for r in j["per_instance"]:
        c = r["correct_of_k"]
        lines.append(
            f"{r['instance'].replace('p15_eval_', '')} & "
            f"{c['Base']}/2 & {c['BundleS']}/2 & {c['TypedContract']}/2 & "
            f"{_signed(r['BundleS_minus_Base'])} & {_signed(r['TC_minus_Base'])} & "
            f"{_CLASS_TEX[r['class']]} \\\\"
        )
    m = j["condition_means"]
    lines += [
        "\\midrule",
        f"\\textbf{{mean rate}} & \\textbf{{{m['Base']:.3f}}} & "
        f"\\textbf{{{m['BundleS']:.3f}}} & \\textbf{{{m['TypedContract']:.3f}}} & "
        f"\\textbf{{{_signed(j['delta_hat_BundleS_minus_Base'], 3)}}} & & \\\\",
        "\\bottomrule",
        "\\end{tabular}",
    ]
    return "\n".join(lines) + "\n"


def render_concordance_table(st: dict) -> str:
    c = st["cross_batch_structural_concordance"]
    lines = [
        "% Generated by scripts/phase8a_claim_statistics.py -- do not edit by hand.",
        "% Post hoc, not preregistered, and NOT pooling: nothing is summed across batches.",
        "\\begin{tabular}{l cc cc c}",
        "\\toprule",
        " & \\multicolumn{2}{c}{earlier batch ($k$=2)} & "
        "\\multicolumn{2}{c}{this batch ($k$=6)} & \\\\",
        "\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}",
        "inst. & class & S$-$B & class & S$-$B & same class \\\\",
        "\\midrule",
    ]
    for r in c["per_instance"]:
        lines.append(
            f"{r['instance'].replace('p15_eval_', '')} & "
            f"{_CLASS_TEX[r['k2_class']]} & {_signed(r['k2_diff'])} & "
            f"{_CLASS_TEX[r['k6_class']]} & {_signed(r['k6_diff'])} & "
            f"{'\\ding{51}' if r['same_class'] else '\\ding{55}'} \\\\"
        )
    lines += [
        "\\bottomrule",
        "\\end{tabular}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="verify the committed outputs reproduce exactly; write nothing")
    args = ap.parse_args()

    st = compute()
    payload = json.dumps(st, indent=2, sort_keys=True) + "\n"
    outputs = (
        (OUT_JSON, payload),
        (OUT_TEX, render_tex(st)),
        (OUT_PANEL_TEX, render_panel_table(st)),
        (OUT_CONCORD_TEX, render_concordance_table(st)),
        (OUT_ARM2_TEX, render_arm2_panel_table(st)),
    )

    if args.check:
        ok = True
        for path, expected in outputs:
            if not path.exists():
                print(f"MISSING: {path.relative_to(REPO)}", file=sys.stderr)
                ok = False
            elif path.read_text() != expected:
                print(f"DRIFT: {path.relative_to(REPO)} does not match recomputation",
                      file=sys.stderr)
                ok = False
        p = st["k6_panel"]
        print(json.dumps({
            "ok": ok,
            "k6_delta_pp": round(100 * p["delta_hat_BundleS_minus_Base"], 1),
            "k6_band_pp": [round(100 * v, 1) for v in p["instance_resampling_band95"]],
            "anatomy": [p["panel_anatomy"]["floor_limited_both_arms"],
                        p["panel_anatomy"]["ceiling_limited_both_arms"],
                        p["panel_anatomy"]["informative_instances"]],
            "unstable_cells": (
                f"{st['within_cell_replication_stability']['cells_whose_six_repetitions_disagree']}"
                f"/{st['within_cell_replication_stability']['cells_total']}"),
            "same_class": (
                f"{st['cross_batch_structural_concordance']['instances_classified_identically']}"
                f"/{st['cross_batch_structural_concordance']['instances_total']}"),
            "arm2_delta_pp": round(100 * st["arm2_joint_panel"]["delta_hat_BundleS_minus_Base"], 1),
            "arm2_band_pp": [round(100 * v, 1)
                             for v in st["arm2_joint_panel"]["instance_resampling_band95"]],
            "arm2_sign_p": st["arm2_joint_panel"]["sign_test"]["two_sided_exact_p"],
            "arm2_branch": st["arm2_joint_panel"]["interpretation_branch"]["branch"],
            "xmodel_sign_agree": (
                f"{st['cross_model_structural_concordance']['sign_agreement_among_informative_in_both'][0]}"
                f"/{st['cross_model_structural_concordance']['sign_agreement_among_informative_in_both'][1]}"),
            "programme_cny": st["money"]["programme_spend_cny"],
        }))
        return 0 if ok else 1

    for path, text in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        print(f"wrote {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
