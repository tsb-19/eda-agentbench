#!/usr/bin/env python3
"""Phase-7C claim statistics: uncertainty quantification for the manuscript's claim cells.

This script adds **no new data**. It re-reads the same frozen records the manuscript
already reports and attaches uncertainty to numbers that were previously printed as bare
fractions or as a single p-value. Motivation: a paper whose thesis is claim calibration
must not present ``1/3 -> 3/3`` in a way that reads as a precise effect, and must not let
``p=1.0`` be misread as a demonstrated zero.

Three things are computed, each from a frozen source:

1. **Per-cell exact intervals.** Clopper-Pearson 95% intervals for every headline cell of
   Study I / Study II, plus the two-sided Fisher exact p for each Base-vs-BundleS contrast.
   Source: ``reports/synthetic_p14_study1_ledger.json`` (itself re-derived from the
   preserved per-episode submissions).

2. **STA panel estimate and its sensitivity to panel composition.** The point estimate of
   the panel mean difference Delta_hat = mean_i(BundleS_i - Base_i), together with a
   percentile bootstrap that resamples the 12 **instances** (the declared independent unit
   -- never the 72 trajectories). Source: ``reports/synthetic_phase7a_sta72_report.json``.

   What that band is and is not. The declared estimand is the *realized* panel: inference
   is to these twelve instances and no further. A realized panel's composition carries no
   sampling uncertainty, so resampling instances does not estimate uncertainty *about* the
   estimand -- it changes the panel. We therefore report the result as an
   **instance-resampling sensitivity band**: how far the point estimate moves when the
   panel's membership is perturbed. It is not a confidence interval, it is not a
   finite-population design-based interval, and it is used for no hypothesis test and no
   decision. The frozen primary analysis (exact paired sign test) and its permutation
   sensitivity are unchanged and remain the reported inferential result.

3. **Backend run-window provenance.** Per stage, the set of dates retained in the
   preserved ``stream_diagnostics.json`` records, and the resolved-snapshot coverage.
   This exists to support an honest limitation rather than a result. Two distinct counts
   matter and the manuscript states both: *no* episode retained a provider-resolved model
   snapshot, response id or system fingerprint (the per-episode diagnostic record has no
   such field, which the assertion below enforces), and only a subset of ledger episodes
   retained even the requested alias and run date. Backend version drift therefore cannot
   be excluded as a contributor to the across-window variation the manuscript reports.

Every derived quantity is asserted against the frozen report's own declared values, so a
changed input fails the build instead of silently changing a printed number.

Usage:
    python3 scripts/phase7c_claim_statistics.py            # write JSON + LaTeX macros
    python3 scripts/phase7c_claim_statistics.py --check     # verify committed outputs
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from datetime import date
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "reports" / "synthetic_p14_study1_ledger.json"
STA = REPO / "reports" / "synthetic_phase7a_sta72_report.json"
PILOT = REPO / "reports" / "synthetic_phase5d_collection_report.json"
EVIDENCE = REPO / "reports" / "evidence"
OUT_JSON = REPO / "reports" / "synthetic_p14_claim_statistics.json"
OUT_TEX = REPO / "submission" / "tables" / "claim_stats.tex"
OUT_PILOT_TEX = REPO / "submission" / "tables" / "sta_pilot.tex"

ALPHA = 0.05
BOOTSTRAP_REPLICATES = 100_000
BOOTSTRAP_SEED = 20260813


# --------------------------------------------------------------------------- exact stats


def binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p), exact summation."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


def binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p), exact summation."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(0, k + 1))


def _bisect(f, target: float, lo: float, hi: float, tol: float = 1e-12) -> float:
    """Solve f(p) = target on [lo, hi]; f must be monotone."""
    f_lo = f(lo)
    increasing = f(hi) > f_lo
    for _ in range(200):
        mid = (lo + hi) / 2
        v = f(mid)
        if (v < target) == increasing:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return (lo + hi) / 2


def clopper_pearson(k: int, n: int, alpha: float = ALPHA) -> tuple[float, float]:
    """Exact (Clopper-Pearson) two-sided 100(1-alpha)% interval for a binomial proportion."""
    if not 0 <= k <= n:
        raise ValueError(f"k={k} out of range for n={n}")
    lo = 0.0 if k == 0 else _bisect(lambda p: binom_sf(k, n, p), alpha / 2, 0.0, 1.0)
    hi = 1.0 if k == n else _bisect(lambda p: binom_cdf(k, n, p), alpha / 2, 0.0, 1.0)
    return lo, hi


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p for [[a, b], [c, d]], computed in exact rationals.

    Rows are conditions, columns are (correct, wrong). Two-sided by the standard
    point-probability method: sum every table at least as extreme as the observed one.
    """
    n = a + b + c + d
    row1, col1 = a + b, a + c
    total = math.comb(n, col1)

    def prob(x: int) -> Fraction:
        return Fraction(math.comb(row1, x) * math.comb(n - row1, col1 - x), total)

    lo = max(0, col1 - (n - row1))
    hi = min(row1, col1)
    observed = prob(a)
    # Guard against float wobble at the boundary by comparing exact rationals.
    p = sum((prob(x) for x in range(lo, hi + 1) if prob(x) <= observed), Fraction(0))
    return float(p)


def instance_resampling_band(
    values: list[float], replicates: int, seed: int, alpha: float = ALPHA
) -> tuple[float, float]:
    """Percentile bootstrap of the mean, resampling the units in `values`.

    Deliberately *not* named `..._ci`. The mechanism is a percentile bootstrap, but the
    quantity reported is a sensitivity band over panel composition, not a confidence
    interval: the manuscript's estimand is the realized panel, whose membership has no
    sampling distribution to be uncertain about. See the module docstring.
    """
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(replicates):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo_idx = int(math.floor((alpha / 2) * replicates))
    hi_idx = min(replicates - 1, int(math.ceil((1 - alpha / 2) * replicates)) - 1)
    return means[lo_idx], means[hi_idx]


# --------------------------------------------------------------------------- study cells

# Headline cells the manuscript states in the main text, as exact (stage, condition, model,
# task) keys into the frozen ledger, so the counts are never transcribed by hand. Within a
# controlled pair the two conditions are distinct frozen task instances (same hidden truth
# and grader, different harness), which is why the task ids differ across base/treat.
HEADLINE_CONTRASTS = [
    {
        "scope": "S0",
        "label": "workflow development instance, Qwen3.7-Max",
        "base": ("4V-pair", "Base(0009)", "Qwen", "0009"),
        "treat": ("4W-Run2", "BundleS", "Qwen", "0015"),
    },
    {
        "scope": "S1",
        "label": "workflow pre-frozen held-out instance, Qwen3.7-Max",
        "base": ("4W-Held", "Base(0011)", "Qwen", "0011"),
        "treat": ("4W-Held", "Held(0017)", "Qwen", "0017"),
    },
    {
        "scope": "S2-M",
        "label": "workflow, DeepSeek-V4-Pro (cross-model)",
        "base": ("4X-S1C", "Base(0009)", "DeepSeek", "0009"),
        "treat": ("4X-S1C", "BundleS", "DeepSeek", "0015"),
    },
]


def load_ledger_cells() -> dict:
    data = json.loads(LEDGER.read_text())
    out = {}
    for row in data["cells"]:
        out[(row["stage"], row["condition"], row["model"], row["task"])] = row
    return out


def find_cell(cells: dict, key: tuple) -> dict:
    """Locate a ledger cell by its exact frozen key, failing loudly if it moved."""
    if key not in cells:
        raise KeyError(
            f"ledger cell {key} not found -- the frozen ledger's keys changed, so the "
            f"manuscript's headline contrast can no longer be re-derived"
        )
    return cells[key]


# --------------------------------------------------------------------------- provenance


def scan_run_windows() -> dict:
    """Per evidence stage: retained dates and resolved-snapshot coverage.

    Returns counts and dates, never raw paths, so the output is safe for an anonymous
    supplement. The calendar span matters: the manuscript reads across-window variation of
    the same condition as stochastic instability, and a rolling provider alias could
    contribute to that variation over a span of weeks.
    """
    stages = {}
    for diag in sorted(EVIDENCE.glob("*/*/stream_diagnostics.json")):
        stage = diag.parent.parent.name
        try:
            d = json.loads(diag.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        rec = stages.setdefault(
            stage,
            {"episodes_with_diagnostics": 0, "dates": set(), "requested_aliases": set(),
             "resolved_snapshot_present": 0},
        )
        rec["episodes_with_diagnostics"] += 1
        if d.get("date"):
            rec["dates"].add(d["date"])
        if d.get("model"):
            rec["requested_aliases"].add(d["model"])
        # A provider-resolved snapshot would appear as any of these; none is retained.
        if any(k in d for k in ("resolved_model", "system_fingerprint", "response_model")):
            rec["resolved_snapshot_present"] += 1
    return {
        stage: {
            "episodes_with_diagnostics": r["episodes_with_diagnostics"],
            "dates": sorted(r["dates"]),
            "requested_aliases": sorted(r["requested_aliases"]),
            "resolved_snapshot_present": r["resolved_snapshot_present"],
        }
        for stage, r in sorted(stages.items())
    }


def summarize_run_windows(windows: dict) -> dict:
    """Calendar envelope of the retained run windows."""
    iso = []
    for rec in windows.values():
        for d in rec["dates"]:
            m = re.match(r"(\d{4})-(\d{2})-(\d{2})", d)
            if m:
                iso.append(date(*(int(g) for g in m.groups())))
    if not iso:
        raise RuntimeError("no parseable run-window dates were retained")
    first, last = min(iso), max(iso)
    return {
        "earliest": first.isoformat(),
        "latest": last.isoformat(),
        "span_days": (last - first).days,
        "episodes_with_diagnostics": sum(
            r["episodes_with_diagnostics"] for r in windows.values()
        ),
        "resolved_snapshot_present": sum(
            r["resolved_snapshot_present"] for r in windows.values()
        ),
    }


# --------------------------------------------------------------------------- computation


def compute() -> dict:
    cells = load_ledger_cells()

    contrasts = []
    for spec in HEADLINE_CONTRASTS:
        base = find_cell(cells, spec["base"])
        treat = find_cell(cells, spec["treat"])
        b_lo, b_hi = clopper_pearson(base["correct"], base["k"])
        t_lo, t_hi = clopper_pearson(treat["correct"], treat["k"])
        p = fisher_exact_two_sided(
            treat["correct"], treat["k"] - treat["correct"],
            base["correct"], base["k"] - base["correct"],
        )
        contrasts.append({
            "scope": spec["scope"],
            "label": spec["label"],
            "base": {"correct": base["correct"], "k": base["k"], "ci95": [b_lo, b_hi],
                     "axis_binding_failure": base["axis"]},
            "treat": {"correct": treat["correct"], "k": treat["k"], "ci95": [t_lo, t_hi],
                      "axis_binding_failure": treat["axis"]},
            "fisher_two_sided_p": p,
        })

    # Post hoc pooling of the two workflow instances is NOT licensed by the design (the
    # instance is the declared unit). Reported only so a reader can see it was not hidden.
    s0, s1 = contrasts[0], contrasts[1]
    pooled_p = fisher_exact_two_sided(
        s0["treat"]["correct"] + s1["treat"]["correct"],
        (s0["treat"]["k"] - s0["treat"]["correct"]) + (s1["treat"]["k"] - s1["treat"]["correct"]),
        s0["base"]["correct"] + s1["base"]["correct"],
        (s0["base"]["k"] - s0["base"]["correct"]) + (s1["base"]["k"] - s1["base"]["correct"]),
    )

    # ---- STA finite panel -------------------------------------------------------------
    sta = json.loads(STA.read_text())
    diffs = [inst["BundleS_rate"] - inst["Base_rate"] for inst in sta["instances"]]
    n_inst = len(diffs)
    delta_hat = sum(diffs) / n_inst
    d_lo, d_hi = instance_resampling_band(diffs, BOOTSTRAP_REPLICATES, BOOTSTRAP_SEED)

    # Mechanical agreement with the frozen report (fail loudly rather than drift).
    declared = sta["condition_mean_rates_over_instances_descriptive"]
    assert n_inst == 12, f"expected 12 instances, got {n_inst}"
    assert abs(sum(diffs) - sta["primary_permutation_sensitivity"]["observed_sum_BundleS_minus_Base"]) < 1e-9, \
        "recomputed sum of per-instance differences disagrees with the frozen report"
    assert abs(delta_hat - (declared["BundleS"] - declared["Base"])) < 5e-4, \
        "recomputed panel difference disagrees with the frozen descriptive means"
    tally = sta["contrast_tally_instance_level"]["primary_BundleS_vs_Base"]
    assert (sum(d > 0 for d in diffs), sum(d < 0 for d in diffs), sum(d == 0 for d in diffs)) == \
        (tally["improve"], tally["decline"], tally["tie"]), \
        "recomputed improve/decline/tie tally disagrees with the frozen report"

    # ---- Panel anatomy (post hoc; added in v14) ----------------------------------------
    # A tie is not one thing. Six instances sit at zero in BOTH arms and one at one in both,
    # so seven of twelve cannot express any condition difference and the contrast rests on
    # five. Reported because "12 instances" otherwise reads as twelve units of discriminating
    # power, which would overstate what the panel can resolve either way.
    rates = [(i["instance"], i["Base_rate"], i["BundleS_rate"]) for i in sta["instances"]]
    floor = [n for n, b, s in rates if b == 0.0 and s == 0.0]
    ceiling = [n for n, b, s in rates if b == 1.0 and s == 1.0]
    informative = [n for n, b, s in rates if s - b != 0.0]
    assert len(floor) + len(ceiling) + len(informative) == n_inst, \
        "floor/ceiling/informative partition does not cover the panel"
    assert len(informative) == tally["improve"] + tally["decline"], \
        "informative count disagrees with the frozen improve+decline tally"

    # Leave-two-out: DROP the two largest-contributing instances (n=10). Distinguished from
    # zeroing them inside n=12, which is a different operation and a different number; the
    # payload carries both so neither can be quoted as the other.
    order = sorted(rates, key=lambda r: -(r[2] - r[1]))
    dominant = [n for n, _, _ in order[:2]]
    kept = [s - b for n, b, s in rates if n not in set(dominant)]
    delta_leave_two_out = sum(kept) / len(kept)
    delta_two_zeroed = sum(kept) / n_inst
    assert (delta_hat > 0) != (delta_leave_two_out > 0), \
        "leave-two-out was expected to reverse the descriptive sign; it did not"

    windows = scan_run_windows()
    envelope = summarize_run_windows(windows)
    ledger_episodes = json.loads(LEDGER.read_text())["totals"]["episodes"]

    # The manuscript states, as its own limitation, that *no* episode retained a
    # provider-resolved model identity. Enforce it here so the sentence cannot go stale if
    # the evidence tree ever gains such a field.
    assert envelope["resolved_snapshot_present"] == 0, (
        "the manuscript states that no episode retained a provider-resolved snapshot, "
        "but the evidence tree now contains one"
    )
    episodes_without_record = ledger_episodes - envelope["episodes_with_diagnostics"]
    assert episodes_without_record >= 0, (
        "more per-episode diagnostic records than ledger episodes; the two are misaligned"
    )

    # ---- three-instance pilot ----------------------------------------------------------
    # The manuscript claims the prospective expansion *reversed* the pilot's descriptive
    # direction. That claim is only checkable if the pilot's per-instance values are
    # published, so we re-derive them here rather than asserting the reversal in prose.
    pilot_raw = json.loads(PILOT.read_text())
    pilot_rows = [r for r in pilot_raw["instance_level"] if r["family"] == "A_sta"]
    pilot_declared = pilot_raw["family_mean_rates"]["A_sta"]
    pilot_base = sum(r["rates"]["Base"] for r in pilot_rows) / len(pilot_rows)
    pilot_bundles = sum(r["rates"]["BundleS"] for r in pilot_rows) / len(pilot_rows)
    assert len(pilot_rows) == 3, f"expected a 3-instance STA pilot, got {len(pilot_rows)}"
    assert abs(pilot_base - pilot_declared["Base"]) < 5e-4 and \
        abs(pilot_bundles - pilot_declared["BundleS"]) < 5e-4, \
        "recomputed pilot means disagree with the frozen pilot report"
    pilot_delta = pilot_bundles - pilot_base
    assert (pilot_delta < 0) != (delta_hat < 0), \
        "the manuscript claims the pilot and prospective directions differ in sign; they do not"

    return {
        "schema": "p14_claim_statistics/v1",
        "purpose": "uncertainty quantification of already-reported frozen results; no new data",
        "sources": {
            "study1_ledger": str(LEDGER.relative_to(REPO)),
            "sta_prospective": str(STA.relative_to(REPO)),
        },
        "method": {
            "interval": "Clopper-Pearson exact, two-sided 95%",
            "contrast_test": "Fisher exact, two-sided, exact rational arithmetic",
            "panel_sensitivity_band": (
                f"percentile bootstrap resampling the {12} instances "
                f"({BOOTSTRAP_REPLICATES} replicates, seed {BOOTSTRAP_SEED}); reported as "
                "an instance-resampling sensitivity band over panel composition, NOT a "
                "confidence interval and NOT a finite-population design-based interval"
            ),
            "preregistered_analysis_unchanged": (
                "the frozen exact paired sign test (p=1.0) and permutation sensitivity "
                "(p=0.31) remain the reported inferential result; the band is descriptive "
                "and is used for no hypothesis test and no decision"
            ),
        },
        "contrasts": contrasts,
        "post_hoc_pooled_two_instances": {
            "fisher_two_sided_p": pooled_p,
            "note": "NOT licensed by the design (instance is the declared unit); reported for transparency only",
        },
        "sta_finite_panel": {
            "n_instances": n_inst,
            "estimand": "the realized 12-instance panel; inference goes no further",
            "delta_hat_BundleS_minus_Base": delta_hat,
            "instance_resampling_band95": [d_lo, d_hi],
            "band_interpretation": (
                "how far the point estimate moves when panel membership is resampled; "
                "not a confidence interval for a parameter, since the realized panel's "
                "composition carries no sampling uncertainty"
            ),
            "frozen_sign_test_two_sided_p": sta["primary_sign_test"]["two_sided_exact_p"],
            "frozen_permutation_two_sided_p": sta["primary_permutation_sensitivity"]["two_sided_permutation_p"],
            "panel_anatomy": {
                "post_hoc": True,
                "floor_limited_both_arms": len(floor),
                "ceiling_limited_both_arms": len(ceiling),
                "informative_instances": len(informative),
                "dominant_instances": dominant,
                "delta_leave_two_out_n10": delta_leave_two_out,
                "delta_two_zeroed_within_n12": delta_two_zeroed,
                "interpretation": (
                    "seven of twelve instances cannot express a condition difference (six at "
                    "the floor in both arms, one at the ceiling), so five carry the contrast "
                    "and two of those account for more than all of it. Dropping those two "
                    "(n=10) reverses the descriptive sign. This bounds how much directional "
                    "weight the aggregate ordering can carry; it is not evidence that the "
                    "treatment harms, and it does not change the frozen confirmatory verdict."
                ),
                "two_operations_are_distinct": (
                    "delta_leave_two_out_n10 drops the instances and divides by 10; "
                    "delta_two_zeroed_within_n12 keeps twelve denominators. Both are given so "
                    "neither can be quoted as the other."
                ),
            },
        },
        "sta_pilot": {
            "n_instances": len(pilot_rows),
            "source": str(PILOT.relative_to(REPO)),
            "per_instance": [
                {"instance": r["instance"], "Base": r["rates"]["Base"],
                 "BundleS": r["rates"]["BundleS"], "TypedContract": r["rates"]["TypedContract"],
                 "reps_per_condition": r["n_per_cond"]["Base"]}
                for r in pilot_rows
            ],
            "mean_Base": pilot_base,
            "mean_BundleS": pilot_bundles,
            "delta_hat_BundleS_minus_Base": pilot_delta,
            "direction_reversal_vs_prospective": True,
            "note": "not pooled with the prospective panel; published so the reversal is checkable",
        },
        "backend_provenance": {
            "run_windows": windows,
            "envelope": envelope,
            "ledger_episodes": ledger_episodes,
            "episodes_with_resolved_snapshot": envelope["resolved_snapshot_present"],
            "episodes_with_alias_and_date": envelope["episodes_with_diagnostics"],
            "episodes_without_any_transport_record": episodes_without_record,
            "resolved_snapshot_retained": envelope["resolved_snapshot_present"] > 0,
            "note": (
                "two distinct counts: NO episode retained a provider-resolved snapshot, "
                "response id or system fingerprint (the per-episode record has no such "
                "field), and only a subset retained even the requested alias and run date; "
                "the remainder have no per-episode transport record at all. Backend "
                "version drift therefore cannot be excluded as a contributor to "
                "across-window variation"
            ),
        },
    }


def pct(x: float) -> str:
    return f"{100 * x:.1f}"


def render_tex(stats: dict) -> str:
    """Emit \\newcommand macros so the manuscript never transcribes these numbers."""
    c = {x["scope"]: x for x in stats["contrasts"]}
    sta = stats["sta_finite_panel"]
    lines = [
        "% Generated by scripts/phase7c_claim_statistics.py -- do not edit by hand.",
        "% Uncertainty for already-reported frozen results; no new data.",
    ]

    def macro(name: str, value: str) -> None:
        lines.append(f"\\newcommand{{\\{name}}}{{{value}}}")

    for scope, tag in (("S0", "SZero"), ("S1", "SOne"), ("S2-M", "STwoM")):
        x = c[scope]
        macro(f"Stat{tag}BaseCI",
              f"{pct(x['base']['ci95'][0])}--{pct(x['base']['ci95'][1])}\\%")
        macro(f"Stat{tag}TreatCI",
              f"{pct(x['treat']['ci95'][0])}--{pct(x['treat']['ci95'][1])}\\%")
        macro(f"Stat{tag}Fisher", f"{x['fisher_two_sided_p']:.2f}")
    macro("StatPooledFisher", f"{stats['post_hoc_pooled_two_instances']['fisher_two_sided_p']:.2f}")
    macro("StatStaDelta", f"{100 * sta['delta_hat_BundleS_minus_Base']:+.1f}")
    macro("StatStaBandLo", f"{100 * sta['instance_resampling_band95'][0]:+.1f}")
    macro("StatStaBandHi", f"{100 * sta['instance_resampling_band95'][1]:+.1f}")
    _anat = sta["panel_anatomy"]
    macro("StatStaFloorN", str(_anat["floor_limited_both_arms"]))
    macro("StatStaCeilingN", str(_anat["ceiling_limited_both_arms"]))
    macro("StatStaInformativeN", str(_anat["informative_instances"]))
    macro("StatStaLeaveTwoOut", f"{100 * _anat['delta_leave_two_out_n10']:+.1f}")
    env = stats["backend_provenance"]["envelope"]
    macro("StatRunFirst", env["earliest"])
    macro("StatRunLast", env["latest"])
    macro("StatRunSpanDays", str(env["span_days"]))
    macro("StatDiagEpisodes", str(env["episodes_with_diagnostics"]))
    macro("StatNoDiagEpisodes",
          str(stats["backend_provenance"]["episodes_without_any_transport_record"]))
    macro("StatSnapshotEpisodes",
          str(stats["backend_provenance"]["episodes_with_resolved_snapshot"]))
    macro("StatLedgerEpisodes", str(stats["backend_provenance"]["ledger_episodes"]))
    pilot = stats["sta_pilot"]
    macro("StatPilotDelta", f"{100 * pilot['delta_hat_BundleS_minus_Base']:+.1f}")
    macro("StatPilotBase", f"{pilot['mean_Base']:.3f}")
    macro("StatPilotBundleS", f"{pilot['mean_BundleS']:.3f}")
    macro("StatPilotN", str(pilot["n_instances"]))
    return "\n".join(lines) + "\n"


def render_pilot_table(stats: dict) -> str:
    """Emit the three-instance pilot table body so the appendix never transcribes it."""
    pilot = stats["sta_pilot"]
    lines = [
        "% Generated by scripts/phase7c_claim_statistics.py -- do not edit by hand.",
        "\\begin{tabular}{l ccc c}",
        "\\toprule",
        "instance & Base & BundleS & TypedContract & BundleS$-$Base \\\\",
        "\\midrule",
    ]
    for r in pilot["per_instance"]:
        d = r["BundleS"] - r["Base"]
        sign = "$-$" if d < 0 else ("" if d == 0 else "$+$")
        lines.append(
            f"{r['instance'].replace('p15_eval_', '')} & {r['Base']:.1f} & "
            f"{r['BundleS']:.1f} & {r['TypedContract']:.1f} & {sign}{abs(d):.1f} \\\\"
        )
    dm = pilot["delta_hat_BundleS_minus_Base"]
    lines += [
        "\\midrule",
        f"\\textbf{{mean}} & \\textbf{{{pilot['mean_Base']:.3f}}} & "
        f"\\textbf{{{pilot['mean_BundleS']:.3f}}} & "
        f"\\textbf{{{sum(r['TypedContract'] for r in pilot['per_instance']) / len(pilot['per_instance']):.3f}}} & "
        f"\\textbf{{{'$-$' if dm < 0 else '$+$'}{abs(dm):.3f}}} \\\\",
        "\\bottomrule",
        "\\end{tabular}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify the committed outputs reproduce exactly; write nothing")
    args = ap.parse_args()

    stats = compute()
    tex = render_tex(stats)
    pilot_tex = render_pilot_table(stats)
    payload = json.dumps(stats, indent=2, sort_keys=True) + "\n"

    if args.check:
        ok = True
        for path, expected in ((OUT_JSON, payload), (OUT_TEX, tex), (OUT_PILOT_TEX, pilot_tex)):
            if not path.exists():
                print(f"MISSING: {path.relative_to(REPO)}", file=sys.stderr)
                ok = False
            elif path.read_text() != expected:
                print(f"DRIFT: {path.relative_to(REPO)} does not match recomputation",
                      file=sys.stderr)
                ok = False
        summary = {
            "ok": ok,
            "sta_delta_pp": round(100 * stats["sta_finite_panel"]["delta_hat_BundleS_minus_Base"], 1),
            "sta_band_pp": [round(100 * v, 1)
                            for v in stats["sta_finite_panel"]["instance_resampling_band95"]],
            "pilot_delta_pp": round(100 * stats["sta_pilot"]["delta_hat_BundleS_minus_Base"], 1),
            "fisher": {x["scope"]: round(x["fisher_two_sided_p"], 3) for x in stats["contrasts"]},
            "resolved_snapshot_retained": stats["backend_provenance"]["resolved_snapshot_retained"],
        }
        print(json.dumps(summary))
        return 0 if ok else 1

    OUT_JSON.write_text(payload)
    OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
    OUT_TEX.write_text(tex)
    OUT_PILOT_TEX.write_text(pilot_tex)
    for p in (OUT_JSON, OUT_TEX, OUT_PILOT_TEX):
        print(f"wrote {p.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
