#!/usr/bin/env python3
"""Phase-8A instance-level report (report-only; NO model calls).

Re-grades every collected episode's submitted binding against the golden truth using the
sha256-PINNED grader (generators/p15_sta_handoff/grade_sta_handoff.py), then reports the
preregistered hierarchy from docs/phase8a_prereg.md:

  Primary confirmatory : BundleS vs Base
  Secondary            : TypedContract vs Base ; TypedContract vs BundleS

Analysis unit is the task instance (n=12). The k reps per (instance, condition) are NESTED
observations: 216 trajectories are NOT n=216.

NOT POOLABLE WITH PHASE-7A. Phase-7A ran on llmapi.paratera.com, which no longer serves these
models; Phase-8A runs on a different provider. Same design, different apparatus, therefore a
different measurement. This script prints the two side by side and refuses to combine them.

Outputs phase8a/reports/phase8a_sta_report.{json,md} -- deliberately outside reports/, see
phase8a/README.md.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from collections import defaultdict
from math import comb
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "generators" / "p15_sta_handoff"))
from grade_sta_handoff import grade  # noqa: E402  (PINNED grader, reused byte-identical)

P8A = REPO / "phase8a"
EV = P8A / "evidence" / "episodes"
OUT_JSON = P8A / "reports" / "phase8a_sta_report.json"
OUT_MD = P8A / "reports" / "phase8a_sta_report.md"
COND = ["Base", "BundleS", "TypedContract"]
PILOTS = ["p15_eval_0001", "p15_eval_0002", "p15_eval_0003"]
PHASE7A = REPO / "reports" / "synthetic_phase7a_sta72_report.json"
PERM_SEED = 20260817
PERM_MC = 10000


def _states():
    """Every run-state chunk, in execution order. Chunked runs keep a crash cheap."""
    return sorted((P8A / "evidence").glob("run_state_arm*.json"))


def _truth_for(inst):
    p = REPO / "tasks" / "p15_sta_handoff" / f"{inst}_bundles" / "hidden" / "signoff_intent_truth.json"
    return json.loads(p.read_text())


def _regrade(submitted, truth):
    """semantic_binding + subtype via the frozen grader, in a throwaway cwd."""
    t = tempfile.mkdtemp()
    try:
        (Path(t) / "signoff_intent_truth.json").write_text(json.dumps(truth))
        (Path(t) / "exception_config.json").write_text(json.dumps(submitted))
        (Path(t) / "signoff_result.json").write_text('{"signoff_green": true}')
        (Path(t) / "applied_hidden.sdc").write_text("")
        cwd = os.getcwd()
        os.chdir(t)
        try:
            m = grade()
        finally:
            os.chdir(cwd)
        return bool(m["checks"]["semantic_binding"]), m.get("failure_subtype")
    finally:
        shutil.rmtree(t, ignore_errors=True)


def _core_of(task_id):
    return (task_id.rsplit("_", 1)[0]
            if task_id.endswith(("base", "bundles", "typedcontract")) else task_id)


def _sign_p(diffs):
    n = sum(1 for d in diffs if d != 0)
    k = sum(1 for d in diffs if d > 0)
    if n == 0:
        return n, k, 1.0
    p = 2.0 * sum(comb(n, i) for i in range(min(k, n - k) + 1)) / (2 ** n)
    return n, k, min(p, 1.0)


def build():
    states = _states()
    if not states:
        raise SystemExit("phase8a_report: no run_state_arm*.json under phase8a/evidence/")

    episodes, spent, invalid, aborted, replaced = [], 0.0, 0, 0, 0
    for s in states:
        d = json.loads(s.read_text())
        episodes.extend(d.get("episodes", []))
        spent += float(d.get("spent") or 0.0)
        invalid += int(d.get("invalid") or 0)
        aborted += int(d.get("aborted") or 0)
        replaced += int(d.get("replaced") or 0)

    per = defaultdict(lambda: defaultdict(list))
    excluded_invalid = []
    for e in episodes:
        if e.get("aborted"):
            continue
        # A measurement-invalid episode is NEVER graded. It is not a capability failure.
        if e.get("measurement_valid") is False:
            excluded_invalid.append(e.get("trial"))
            continue
        trial, tid = e["trial"], e["task_id"]
        inst = _core_of(tid)
        f = EV / trial / "exception_config.submitted.json"
        if not f.is_file():
            excluded_invalid.append(f"{trial}:no_submitted_artifact")
            continue
        sem, subtype = _regrade(json.loads(f.read_text()), _truth_for(inst))
        per[inst][e["condition"]].append({"rep": e["rep"], "sem": sem, "subtype": subtype,
                                          "trial": trial})

    instances = sorted(i for i in per if i not in PILOTS)
    rows = []
    for inst in instances:
        row = {"instance": inst}
        agree = {}
        for c in COND:
            reps = sorted(per[inst][c], key=lambda r: r["rep"])
            vals = [r["sem"] for r in reps]
            row[f"{c}_reps"] = vals
            row[f"{c}_rate"] = round(sum(vals) / len(vals), 4) if vals else None
            row[f"{c}_subtypes"] = [r["subtype"] for r in reps]
            row[f"{c}_k"] = len(vals)
            agree[c] = ("agree" if len(set(vals)) == 1 else "disagree") if vals else None
        row["within_inst_agreement"] = agree
        b, s, t = row["Base_rate"], row["BundleS_rate"], row["TypedContract_rate"]
        row["BundleS_minus_Base"] = round(s - b, 4) if None not in (s, b) else None
        row["TC_minus_Base"] = round(t - b, 4) if None not in (t, b) else None
        row["TC_minus_BundleS"] = round(t - s, 4) if None not in (t, s) else None
        rows.append(row)

    def tally(key):
        imp = dec = tie = 0
        for r in rows:
            d = r[key]
            if d is None:
                continue
            imp, dec, tie = (imp + (d > 0)), (dec + (d < 0)), (tie + (d == 0))
        return {"improve": imp, "decline": dec, "tie": tie, "n": imp + dec + tie}

    def mean_rate(c):
        v = [r[f"{c}_rate"] for r in rows if r[f"{c}_rate"] is not None]
        return round(sum(v) / len(v), 4) if v else None

    diffs = [r["BundleS_minus_Base"] for r in rows if r["BundleS_minus_Base"] is not None]
    n_nz, k_pos, p_sign = _sign_p(diffs)

    # Per-instance permutation sensitivity: shuffle condition labels within each instance's own
    # reps, generalised over k (Phase-7A hardcoded a stride of 2). Descriptive only.
    import random
    rng = random.Random(PERM_SEED)
    obs = round(sum(diffs), 4)
    ge = 0
    pools = {}
    for inst in instances:
        pool, ks = [], {}
        for c in COND:
            v = [r["sem"] for r in sorted(per[inst][c], key=lambda r: r["rep"])]
            ks[c] = len(v)
            pool.extend(v)
        pools[inst] = (pool, ks)
    for _ in range(PERM_MC):
        tot = 0.0
        for inst in instances:
            pool, ks = pools[inst]
            p = pool[:]
            rng.shuffle(p)
            kb, ks_ = ks["Base"], ks["BundleS"]
            if not kb or not ks_:
                continue
            tot += (sum(p[kb:kb + ks_]) / ks_) - (sum(p[0:kb]) / kb)
        if abs(round(tot, 4)) >= abs(obs):
            ge += 1

    k_used = sorted({r[f"{c}_k"] for r in rows for c in COND})
    report = {
        "schema": "phase8a_sta_report/v1",
        "study": "Phase-8A STA power expansion on a replacement backend",
        "preregistration": "docs/phase8a_prereg.md",
        "backend": {
            "endpoint_host": "tokenrhythm.studio",
            "frozen_program_endpoint": "llmapi.paratera.com",
            "frozen_endpoint_status": "403 team not allowed to access model (both model IDs)",
            "consequence": "different serving stack => a DIFFERENT measurement",
        },
        "not_poolable_with": {
            "path": "reports/synthetic_phase7a_sta72_report.json",
            "rule": "report side by side; never sum, average, difference or pool into one n",
        },
        "n_episodes_collected": len(episodes),
        "episodes_graded": sum(len(per[i][c]) for i in instances for c in COND),
        "measurement_invalid_excluded": excluded_invalid,
        "spent_cny": round(spent, 4),
        "invalid": invalid, "aborted": aborted, "replaced": replaced,
        "unit": f"task instance (n={len(instances)}); k reps nested; trajectories are NOT n",
        "k_per_condition_observed": k_used,
        "frozen_hierarchy": {"primary": "BundleS vs Base",
                             "secondary": ["TypedContract vs Base", "TypedContract vs BundleS"]},
        "pilot_instances_excluded_from_primary": PILOTS,
        "condition_mean_rates_over_instances_descriptive": {c: mean_rate(c) for c in COND},
        "contrast_tally_instance_level": {
            "primary_BundleS_vs_Base": tally("BundleS_minus_Base"),
            "secondary_TC_vs_Base": tally("TC_minus_Base"),
            "secondary_TC_vs_BundleS": tally("TC_minus_BundleS"),
        },
        "primary_sign_test": {"n_nonzero_instance_diffs": n_nz, "k_positive": k_pos,
                              "two_sided_exact_p": round(p_sign, 5)},
        "primary_permutation_sensitivity": {
            "observed_sum_BundleS_minus_Base": obs, "mc_replicates": PERM_MC,
            "two_sided_permutation_p": round(ge / PERM_MC, 5), "seed": PERM_SEED,
            "note": "per-instance shuffle of condition labels over that instance's own reps; "
                    "descriptive sensitivity only, NOT a population-rate p-value",
        },
        "instances": rows,
        "interpretation_note": "Reported at the preregistered k. No adaptive k, no "
                               "trajectory-pooled p-value, no outcome-dependent reanalysis.",
    }
    return report


def _markdown(rep):
    c = rep["condition_mean_rates_over_instances_descriptive"]
    pri = rep["contrast_tally_instance_level"]["primary_BundleS_vs_Base"]
    md = [f"# Phase-8A — STA panel at k={rep['k_per_condition_observed']} on a replacement backend",
          "",
          f"{rep['episodes_graded']} graded episodes (¥{rep['spent_cny']}, {rep['invalid']} invalid, "
          f"{rep['replaced']} replacement(s)). **Unit = task instance (n={len(rep['instances'])}); "
          "reps nested; trajectories are NOT n.**",
          "",
          "> **Not poolable with Phase-7A.** Phase-7A ran on `llmapi.paratera.com`, which now returns "
          "403 for both model IDs. Phase-8A runs on `tokenrhythm.studio`. Same design, different "
          "apparatus, therefore a different measurement. Reported side by side, never combined.",
          "",
          "## Condition mean rates over instances (descriptive)",
          f"- Base **{c['Base']}** | BundleS **{c['BundleS']}** | TypedContract **{c['TypedContract']}**",
          "",
          "## Instance-level contrast tallies",
          f"- **Primary BundleS vs Base:** improve {pri['improve']}, decline {pri['decline']}, "
          f"tie {pri['tie']} (n={pri['n']})",
          f"- Secondary TC vs Base: {rep['contrast_tally_instance_level']['secondary_TC_vs_Base']}",
          f"- Secondary TC vs BundleS: {rep['contrast_tally_instance_level']['secondary_TC_vs_BundleS']}",
          "",
          "## Primary sensitivity",
          f"- Exact paired sign test: k+={rep['primary_sign_test']['k_positive']} of "
          f"{rep['primary_sign_test']['n_nonzero_instance_diffs']} non-zero instance diffs; "
          f"two-sided p={rep['primary_sign_test']['two_sided_exact_p']}",
          f"- Permutation ({rep['primary_permutation_sensitivity']['mc_replicates']} MC): "
          f"observed sum={rep['primary_permutation_sensitivity']['observed_sum_BundleS_minus_Base']}; "
          f"p={rep['primary_permutation_sensitivity']['two_sided_permutation_p']} (descriptive)",
          "",
          "## Per-instance outcomes",
          "| instance | Base | BundleS | TypedContract | B−Base | TC−Base | TC−B |",
          "|---|---|---|---|---|---|---|"]
    for r in rep["instances"]:
        def cell(cn):
            v = r[f"{cn}_reps"]
            return ("".join("✓" if x else "✗" for x in v) + f" ({r[f'{cn}_rate']})") if v else "—"
        md.append(f"| {r['instance']} | {cell('Base')} | {cell('BundleS')} | {cell('TypedContract')} "
                  f"| {r['BundleS_minus_Base']} | {r['TC_minus_Base']} | {r['TC_minus_BundleS']} |")
    if PHASE7A.is_file():
        p7 = json.loads(PHASE7A.read_text())
        p7c = p7["condition_mean_rates_over_instances_descriptive"]
        md += ["", "## Side by side with Phase-7A (NEVER pooled)", "",
               "| | backend | k | Base | BundleS | TypedContract |", "|---|---|---|---|---|---|",
               f"| Phase-7A | llmapi.paratera.com (now 403) | 2 | {p7c['Base']} | {p7c['BundleS']} "
               f"| {p7c['TypedContract']} |",
               f"| Phase-8A | tokenrhythm.studio | {rep['k_per_condition_observed']} | {c['Base']} "
               f"| {c['BundleS']} | {c['TypedContract']} |",
               "",
               "These are two measurements of the same design on different apparatus. The rows are "
               "not combined, and neither row is evidence about the other's backend."]
    return "\n".join(md) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase-8A instance-level report (no model calls).")
    ap.add_argument("--check", action="store_true", help="verify the committed report reproduces")
    args = ap.parse_args()

    rep = build()
    blob = json.dumps(rep, indent=2) + "\n"
    if args.check:
        if not OUT_JSON.is_file():
            print(f"FAIL: {OUT_JSON} missing", file=sys.stderr)
            return 1
        if OUT_JSON.read_text(encoding="utf-8") != blob:
            print(f"FAIL: {OUT_JSON} does not reproduce", file=sys.stderr)
            return 1
        print(json.dumps({"ok": True, "graded": rep["episodes_graded"],
                          "spent_cny": rep["spent_cny"]}))
        return 0

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(blob, encoding="utf-8")
    OUT_MD.write_text(_markdown(rep), encoding="utf-8")
    print(json.dumps({k: rep[k] for k in (
        "condition_mean_rates_over_instances_descriptive", "contrast_tally_instance_level",
        "primary_sign_test", "primary_permutation_sensitivity", "spent_cny")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
