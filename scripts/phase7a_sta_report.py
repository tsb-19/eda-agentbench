#!/usr/bin/env python3
"""Phase-7A Study A — instance-level report on the 72-episode run (report-only; no model calls).

Re-grades each episode's submitted binding vs the golden truth (semantic_binding on the
typed axes + family-specific subtype), then reports the FROZEN statistical hierarchy:
  Primary confirmatory : BundleS vs Base
  Secondary            : TypedContract vs Base; TypedContract vs BundleS
The 12 new task instances are the prospective dataset (n=12); the 3 pilot instances are
NOT pooled in. Task instance is the independent unit; 2 reps are nested observations.
72 trajectories are NOT treated as n=72. An exact paired sign test + a per-instance
permutation sensitivity are reported as sensitivity only.

Emits reports/synthetic_phase7a_sta72_report.{json,md}.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from collections import defaultdict
from math import comb
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "generators" / "p15_sta_handoff"))
from grade_sta_handoff import grade  # noqa: E402

STATE = json.loads((REPO / "reports" / "evidence" / "phase7a_state.json").read_text())
EV = REPO / "reports" / "evidence" / "phase7a_episodes"
COND = ["Base", "BundleS", "TypedContract"]


def _truth_for(task_id_core):
    # golden truth is condition-independent; read from the BundleS tree
    p = REPO / "tasks" / "p15_sta_handoff" / f"{task_id_core}_bundles" / "hidden" / "signoff_intent_truth.json"
    return json.loads(p.read_text())


def _regrade(submitted, truth):
    """semantic_binding (submitted==golden on typed axes) + subtype, via the frozen grader."""
    import tempfile, shutil, os
    t = tempfile.mkdtemp()
    try:
        (Path(t) / "signoff_intent_truth.json").write_text(json.dumps(truth))
        (Path(t) / "exception_config.json").write_text(json.dumps(submitted))
        (Path(t) / "signoff_result.json").write_text('{"signoff_green": true}')
        (Path(t) / "applied_hidden.sdc").write_text("")
        cwd = os.getcwd(); os.chdir(t)
        try:
            m = grade()
        finally:
            os.chdir(cwd)
        sem = bool(m["checks"]["semantic_binding"])
        return sem, m.get("failure_subtype")
    finally:
        shutil.rmtree(t, ignore_errors=True)


def _core_of(task_id):
    # task_id like p15_eval_0004_typedcontract -> core p15_eval_0004 ; trial core is the instance
    return task_id.rsplit("_", 1)[0] if task_id.endswith(("base", "bundles", "typedcontract")) else task_id


def main():
    # build per (instance, condition) -> [rep outcomes]
    per_inst_cond = defaultdict(lambda: defaultdict(list))   # inst -> cond -> [(rep, sem, subtype, trial)]
    for e in STATE["episodes"]:
        trial = e["trial"]; tid = e["task_id"]; cond = e["condition"]; rep = e["rep"]
        inst = _core_of(tid)
        sub = json.loads((EV / trial / "exception_config.submitted.json").read_text())
        truth = _truth_for(inst)
        sem, subtype = _regrade(sub, truth)
        per_inst_cond[inst][cond].append({"rep": rep, "sem": sem, "subtype": subtype, "trial": trial,
                                          "measurement_valid": e.get("measurement_valid")})

    instances = sorted(per_inst_cond)
    # per-instance table
    inst_rows = []
    for inst in instances:
        row = {"instance": inst}
        agree = {}
        for c in COND:
            reps = sorted(per_inst_cond[inst][c], key=lambda r: r["rep"])
            vals = [r["sem"] for r in reps]
            rate = sum(vals) / len(vals) if vals else None
            row[f"{c}_reps"] = vals
            row[f"{c}_rate"] = round(rate, 3) if rate is not None else None
            row[f"{c}_subtypes"] = [r["subtype"] for r in reps]
            agree[c] = ("agree" if len(set(vals)) == 1 else "disagree") if vals else None
        row["within_inst_agreement"] = agree
        # paired diffs (instance-level rates)
        b, s, t = row["Base_rate"], row["BundleS_rate"], row["TypedContract_rate"]
        row["BundleS_minus_Base"] = round(s - b, 3) if None not in (s, b) else None
        row["TC_minus_Base"] = round(t - b, 3) if None not in (t, b) else None
        row["TC_minus_BundleS"] = round(t - s, 3) if None not in (t, s) else None
        inst_rows.append(row)

    # contrast tallies across instances (improve/decline/tie at the instance level)
    def tally(diff_key):
        imp = dec = tie = 0
        for r in inst_rows:
            d = r[diff_key]
            if d is None: continue
            if d > 0: imp += 1
            elif d < 0: dec += 1
            else: tie += 1
        return {"improve": imp, "decline": dec, "tie": tie, "n": imp + dec + tie}
    contrasts = {
        "primary_BundleS_vs_Base": tally("BundleS_minus_Base"),
        "secondary_TC_vs_Base": tally("TC_minus_Base"),
        "secondary_TC_vs_BundleS": tally("TC_minus_BundleS"),
    }

    # condition-level mean over instances (descriptive; NOT a population estimate)
    def mean_rate(c):
        vals = [r[f"{c}_rate"] for r in inst_rows if r[f"{c}_rate"] is not None]
        return round(sum(vals) / len(vals), 3) if vals else None
    cond_means = {c: mean_rate(c) for c in COND}

    # ---- sensitivity: exact paired sign test on the PRIMARY (BundleS vs Base) ----
    # instance-level signed differences; count strict improve vs strict decline
    diffs = [r["BundleS_minus_Base"] for r in inst_rows if r["BundleS_minus_Base"] is not None]
    n_nonzero = sum(1 for d in diffs if d != 0)
    k_pos = sum(1 for d in diffs if d > 0)
    # two-sided exact sign-test p: 2 * sum_{i<=min(k,n-k)} C(n,i) / 2^n
    p_sign = 2.0 * sum(comb(n_nonzero, i) for i in range(min(k_pos, n_nonzero - k_pos) + 1)) / (2 ** n_nonzero) if n_nonzero > 0 else 1.0
    p_sign = min(p_sign, 1.0)

    # ---- sensitivity: per-instance permutation (shuffle condition labels within each instance's 6 reps) ----
    # descriptive: under the sharp null (no condition effect), how often does the observed |sum(BundleS-Base)|
    # reach/exceed the observed, by per-instance label permutation. Exact over the 20 ways to assign 2 of 6
    # reps to "Base" within each instance is infeasible to enumerate jointly for 12 instances; use a seeded
    # Monte-Carlo (no Date.now/Math.random in this context -> seed fixed).
    import random
    rng = random.Random(20260811)
    obs_sum = round(sum(diffs), 3)
    mc = 10000
    ge = 0
    # build per-instance 6-rep pools (Base2, BundleS2, TC2) as binary sem lists
    pools = {}
    for inst in instances:
        pool = []
        for c in COND:
            pool.extend([r["sem"] for r in sorted(per_inst_cond[inst][c], key=lambda r: r["rep"])])
        pools[inst] = pool  # length 6
    for _ in range(mc):
        s_perm = 0.0
        for inst in instances:
            perm = pools[inst][:]; rng.shuffle(perm)
            # assign first 2 -> Base, next 2 -> BundleS (rate diff BundleS-Base)
            base_r = sum(perm[0:2]) / 2
            bund_r = sum(perm[2:4]) / 2
            s_perm += (bund_r - base_r)
        if abs(round(s_perm, 3)) >= abs(obs_sum):
            ge += 1
    p_perm = ge / mc

    report = {
        "schema": "phase7a_sta72_report/v1",
        "study": "Phase-7A Study A prospective STA confirmatory expansion",
        "n_episodes": len(STATE["episodes"]), "spent_cny": STATE.get("spent"),
        "invalid": STATE.get("invalid"), "aborted": STATE.get("aborted"), "replaced": STATE.get("replaced"),
        "unit": "task instance (n=12); 2 reps nested; 72 trajectories NOT n=72",
        "frozen_hierarchy": {"primary": "BundleS vs Base", "secondary": ["TypedContract vs Base", "TypedContract vs BundleS"]},
        "pilot_instances_excluded_from_primary": ["p15_eval_0001", "p15_eval_0002", "p15_eval_0003"],
        "condition_mean_rates_over_instances_descriptive": cond_means,
        "contrast_tally_instance_level": contrasts,
        "primary_sign_test": {"n_nonzero_instance_diffs": n_nonzero, "k_positive": k_pos, "two_sided_exact_p": round(p_sign, 5)},
        "primary_permutation_sensitivity": {"observed_sum_BundleS_minus_Base": obs_sum, "mc_replicates": mc, "two_sided_permutation_p": round(p_perm, 5),
                                            "note": "per-instance shuffle of condition labels over 6 reps; descriptive sensitivity only, NOT a population-rate p-value"},
        "instances": inst_rows,
        "interpretation_note": "Reported at the preregistered result; no adaptive k; no trajectory-pooled p-value.",
    }
    out = REPO / "reports" / "synthetic_phase7a_sta72_report.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    # markdown
    md = ["# Phase-7A Study A — 72-Episode Instance-Level Report (prospective, n=12 instances)",
          "",
          f"72/72 episodes collected (¥{report['spent_cny']}, {report['invalid']} invalid, {report['replaced']} validity-only replacement). "
          f"**Unit = task instance (n=12); 2 reps nested; 72 trajectories are NOT n=72.** Pilot 0001-0003 excluded from primary.",
          "",
          "## Condition mean rates over instances (descriptive)",
          f"- Base: **{cond_means['Base']}**  | BundleS: **{cond_means['BundleS']}**  | TypedContract: **{cond_means['TypedContract']}**",
          "",
          "## Instance-level contrast tallies (improve / decline / tie of the 12 instances)",
          f"- **Primary BundleS vs Base:** improve {contrasts['primary_BundleS_vs_Base']['improve']}, "
          f"decline {contrasts['primary_BundleS_vs_Base']['decline']}, tie {contrasts['primary_BundleS_vs_Base']['tie']}",
          f"- Secondary TypedContract vs Base: {contrasts['secondary_TC_vs_Base']}",
          f"- Secondary TypedContract vs BundleS: {contrasts['secondary_TC_vs_BundleS']}",
          "",
          f"## Primary sensitivity (BundleS vs Base)",
          f"- Exact paired sign test: k+={k_pos} of {n_nonzero} non-zero instance diffs; two-sided p={round(p_sign,5)}",
          f"- Per-instance permutation ({mc} MC): observed Σ(BundleS−Base)={obs_sum}; two-sided p={round(p_perm,5)} "
          "(descriptive sensitivity; NOT a population-rate p-value)",
          "",
          "## Per-instance outcomes (✓=correct typed binding)",
          "| instance | Base | BundleS | TypedContract | B−Base | TC−Base | TC−B | agree |",
          "|---|---|---|---|---|---|---|---|"]
    for r in inst_rows:
        def cell(c):
            v = r[f"{c}_reps"]; return "".join("✓" if x else "✗" for x in v) if v else "—"
        md.append(f"| {r['instance']} | {cell('Base')} ({r['Base_rate']}) | {cell('BundleS')} ({r['BundleS_rate']}) | "
                  f"{cell('TypedContract')} ({r['TypedContract_rate']}) | {r['BundleS_minus_Base']} | {r['TC_minus_Base']} | {r['TC_minus_BundleS']} | "
                  f"{r['within_inst_agreement'].get('Base','')[:3]}/{r['within_inst_agreement'].get('BundleS','')[:3]}/{r['within_inst_agreement'].get('TypedContract','')[:3]} |")
    (REPO / "reports" / "synthetic_phase7a_sta72_report.md").write_text("\n".join(md) + "\n")
    print(json.dumps({k: report[k] for k in ("condition_mean_rates_over_instances_descriptive", "contrast_tally_instance_level",
                                              "primary_sign_test", "primary_permutation_sensitivity")}, indent=2))


if __name__ == "__main__":
    main()
