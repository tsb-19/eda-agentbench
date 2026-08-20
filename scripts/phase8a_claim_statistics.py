#!/usr/bin/env python3
"""Phase-8A claim statistics: the manuscript-facing numbers of the k=6 STA panel.

This script adds **no new data**. It re-reads the frozen Phase-8A report and re-derives
every quantity the manuscript prints, so that no k=6 number is transcribed by hand -- the
same discipline ``phase7c_claim_statistics.py`` applies to the k=2 study.

Four things are computed, each from a committed source:

1. **Panel estimate and its composition sensitivity.** Delta_hat = mean_i(BundleS_i -
   Base_i) over the twelve instances, plus a percentile bootstrap resampling the twelve
   **instances** (the declared unit -- never the 216 trajectories). The band is an
   *instance-resampling sensitivity band*, not a confidence interval, for exactly the
   reason the v14 script states: the estimand is the realized panel, whose composition has
   no sampling distribution. It is used for no hypothesis test and no decision; the frozen
   preregistered sign test remains the inferential result.

2. **Panel anatomy.** How many of the twelve instances can express a condition difference
   at all. The predicate is *identical* to the one v14 applied to the k=2 panel, and this
   script proves that mechanically: it runs its own classifier over Phase-7A's instances
   and asserts the counts equal Phase-7A's frozen ``panel_anatomy`` block. Without that
   check, "the anatomy reproduces" could be an artifact of two differently-worded rules.

3. **Cross-batch structural concordance (post hoc, not preregistered).** Per instance, the
   class and the sign of the difference under each batch. This is a *structural* comparison
   of two independently executed batches. It is **not pooling**: no quantity is summed,
   averaged or differenced across the two studies, and neither batch licenses an inference
   about the other's serving endpoint.

4. **Within-cell replication stability.** How many of the 36 (instance, condition) cells
   have six identical repetitions that disagree with each other. This is the quantity that
   makes low-repetition harness estimates fragile, and it is only visible at k>2.

The arm-2 cost-gate figures are carried through as macros too, so the manuscript's
statement that S3 was *not executed* cites the arithmetic that refused it rather than
paraphrasing it.

Usage:
    python3 scripts/phase8a_claim_statistics.py            # write JSON + LaTeX
    python3 scripts/phase8a_claim_statistics.py --check    # verify committed outputs
"""

from __future__ import annotations

import argparse
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

BOOTSTRAP_REPLICATES = 100_000
BOOTSTRAP_SEED = 20260820

CONDITIONS = ("Base", "BundleS", "TypedContract")


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

    return {
        "schema": "phase8a_claim_statistics/v1",
        "purpose": (
            "manuscript-facing re-derivation of the k=6 STA panel; no new data, no model "
            "call, no tool run"
        ),
        "sources": {
            "k6_panel": str(EIGHTA.relative_to(REPO)),
            "k2_panel": str(SEVENA.relative_to(REPO)),
            "arm2_gate": str(GATE.relative_to(REPO)),
            "arm2_incomplete_block": str(EIGHTA_ARM2.relative_to(REPO)),
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
        "arm2_not_executed": {
            "status": "NOT EXECUTED -- failed the preregistered cost gate",
            "not_a_negative_result": (
                "an experiment that did not run produces no effect direction. This may not be "
                "restated as 'no effect', 'failed to improve' or a negative result."
            ),
            "decision": gate["decision"],
            "r_prime_cny_per_episode": gate["rate"]["r_prime_cny_per_episode"],
            "pooled_episodes_behind_rate": gate["rate"]["pooled_episodes"],
            "remaining_after_holdback_cny": gate["budget"]["remaining_after_holdback_cny"],
            "cheapest_ladder_rung_cny": min(x["projected_arm2_cny"] for x in gate["gate"]["ladder"]),
            "blocks_executed": 1,
            "episodes_executed": arm2["n_episodes_collected"],
            "condition_contrast_drawn": False,
            "why_no_contrast": arm2["unit"],
        },
        "money": {
            "arm1_cny": eight["spent_cny"],
            "arm1_aborted_block_passes_cny": eight["spent_on_aborted_block_passes_cny"],
            "arm2_incomplete_block_cny": arm2["spent_cny"],
            "programme_spend_cny": gate["budget"]["program_spend_cny"],
            "cap_cny": gate["budget"]["cap_cny"],
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

    g = st["arm2_not_executed"]
    macro("StatArmTwoRate", f"{g['r_prime_cny_per_episode']:.2f}")
    macro("StatArmTwoPooled", str(g["pooled_episodes_behind_rate"]))
    macro("StatArmTwoCheapest", f"{g['cheapest_ladder_rung_cny']:.2f}")
    macro("StatArmTwoRemaining", f"{g['remaining_after_holdback_cny']:.2f}")
    macro("StatArmTwoEpisodes", str(g["episodes_executed"]))

    m = st["money"]
    macro("StatEightASpend", f"{m['arm1_cny']:.2f}")
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
            "arm2": st["arm2_not_executed"]["decision"],
        }))
        return 0 if ok else 1

    for path, text in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        print(f"wrote {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
