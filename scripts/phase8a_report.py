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
# Per arm. `rep` restarts at 1 in every arm, so a shared tree would let arm 2's k=2 episodes
# overwrite arm 1's reps 1-2 and leave this grader pooling two backends through one glob -- the exact
# thing the prereg's "not poolable" rule forbids, arriving by filename. See phase8a_run.py::_custody.
def _ev(arm: int) -> Path:
    return P8A / "evidence" / ("episodes" if arm == 1 else f"episodes_arm{arm}")


ARM_MODEL_NAME = {1: "qwen3.7-max", 2: "deepseek-v4-pro"}
# A block aborted mid-way is re-executed whole and its first pass archived here. It MUST sit outside
# EV: `EV/*/episode.json` is the grading glob, so an archive nested inside it would be re-graded and
# the same trial would enter the analysis twice -- once from the discarded pass, once from the re-run.
ABORTED = P8A / "evidence" / "aborted"
def _out(arm: int):
    suffix = "" if arm == 1 else f"_arm{arm}"
    return (P8A / "reports" / f"phase8a_sta_report{suffix}.json",
            P8A / "reports" / f"phase8a_sta_report{suffix}.md")
COND = ["Base", "BundleS", "TypedContract"]
PILOTS = ["p15_eval_0001", "p15_eval_0002", "p15_eval_0003"]
PHASE7A = REPO / "reports" / "synthetic_phase7a_sta72_report.json"
PERM_SEED = 20260817
PERM_MC = 10000


def _states(arm: int):
    """This arm's chain_executor run-state chunks. Chunked runs keep a crash cheap.

    Scoped to the arm: a glob over `run_state_arm*.json` would charge arm 1's invalid and replaced
    attempts to arm 2's report, and vice versa.
    """
    return sorted((P8A / "evidence").glob(f"run_state_arm{arm}*.json"))


def _schedule(arm: int):
    p = P8A / "evidence" / f"schedule_arm{arm}.json"
    if not p.is_file():
        raise SystemExit(f"phase8a_report: missing frozen schedule {p}")
    return json.loads(p.read_text())


def _aborted_spend(model_name: str):
    """Money paid for the episodes of an aborted block pass, archived out of the analysis tree.

    Block 01's first pass was aborted mid-way by a provider 502 window and the block was re-executed
    whole (prereg Amendment 2). Those episodes are discarded from the ANALYSIS -- a discarded pass is
    not evidence -- but they are not discarded from the LEDGER. Prereg section 4 requires the summed
    episode cost to equal the reported total; if the archive silently dropped out, that identity
    would still print as true while understating what the account actually paid.
    """
    tot = 0.0
    for f in sorted(ABORTED.glob("*/*/episode.json")):
        try:
            d = json.loads(f.read_text())
            # Attributed by the model the episode actually recorded, not by archive path: an arm must
            # not inherit another arm's discarded spend.
            if d.get("model_name") != model_name:
                continue
            tot += float(d.get("total_cost") or 0.0)
        except Exception:  # noqa: BLE001
            pass
    return round(tot, 4)


def _replaced_attempt_spend(model_name: str):
    """Money paid for attempts the arbiter replaced, which survive in no custody tree at all.

    A replacement re-runs the same slot under the same trial name, so it overwrites the previous
    attempt's episode.json. `_aborted_spend` reaches into the archive for a discarded PASS; this
    reaches into the ledger for a discarded ATTEMPT, which has nowhere else to be. Written by
    scripts/phase8a_run.py from the chain log, which records every attempt's cost.
    """
    p = P8A / "evidence" / "replaced_attempt_ledger.json"
    if not p.is_file():
        return 0.0
    try:
        entries = json.loads(p.read_text()).get("entries") or []
    except Exception:  # noqa: BLE001
        return 0.0
    # float(), not just round(): sum([]) is the INT 0, so an existing-but-unmatched ledger serialized
    # as `0` while a missing one serialized as `0.0` -- the same state, two byte strings, and --check
    # failing on a difference that is not a difference.
    return float(round(sum(float(e.get("cost_cny") or 0.0) for e in entries
                           if e.get("model_name") == model_name), 4))


def _collect(arm: int):
    """Episode records in frozen schedule order, plus the arbiter's exclusions.

    Inclusion is asserted here, not assumed, because a stated rule did not stop an earlier
    aggregation in this project from collapsing 70 episodes to 54. An episode enters the analysis
    only if it proves a model was called (non-zero cost AND agentlog custody), left a gradeable
    artifact, and recorded no error. Everything else is measurement-invalid and is never graded --
    an infrastructure fault is not a capability failure.
    """
    sched = _schedule(arm)
    ev = _ev(arm)
    included, excluded = [], []
    for slot in sched["frozen_execution_order"]:
        trial = f"{slot['task_id']}_r{slot['rep']}"
        f = ev / trial / "episode.json"
        if not f.is_file():
            excluded.append(f"{trial}:not_collected")
            continue
        rec = json.loads(f.read_text())
        why = []
        if not (rec.get("total_cost") or 0) > 0:
            why.append("no_cost")
        if "agentlog.sanitized.json" not in (rec.get("custody") or {}):
            why.append("no_telemetry_custody")
        if not (ev / trial / "exception_config.submitted.json").is_file():
            why.append("no_submitted_artifact")
        if rec.get("error"):
            why.append("episode_error")
        if why:
            excluded.append(f"{trial}:" + "+".join(why))
            continue
        rec.setdefault("condition", slot["condition"])
        rec.setdefault("rep", slot["rep"])
        included.append(rec)

    # Spend counts EVERY collected episode, valid or not: a measurement-invalid episode is excluded
    # from the analysis but it was still paid for, and the budget cap is about money, not validity.
    # The same reasoning extends to an aborted block pass -- see _aborted_spend.
    spent = 0.0
    for d in sorted(ev.glob("*/episode.json")):
        try:
            spent += float(json.loads(d.read_text()).get("total_cost") or 0.0)
        except Exception:  # noqa: BLE001
            pass
    aborted_spend = _aborted_spend(ARM_MODEL_NAME[arm])
    replaced_spend = _replaced_attempt_spend(ARM_MODEL_NAME[arm])
    spent = round(spent + aborted_spend + replaced_spend, 4)
    replaced = invalid = 0
    for s in _states(arm):
        try:
            d = json.loads(s.read_text())
        except Exception:  # noqa: BLE001
            continue
        for x in d.get("excluded_invalid_attempts", []):
            if x.get("reason") == "terminal_invalid_replaced":
                replaced += 1
            else:
                invalid += 1
    return sched, included, excluded, spent, invalid, replaced, aborted_spend, replaced_spend


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


def build(arm: int = 1):
    (sched, included, excluded_invalid, spent, invalid, replaced, aborted_spend,
     replaced_spend) = _collect(arm)
    ev = _ev(arm)

    per = defaultdict(lambda: defaultdict(list))
    for e in included:
        inst = _core_of(e["task_id"])
        sub = json.loads((ev / e["trial"] / "exception_config.submitted.json").read_text())
        sem, subtype = _regrade(sub, _truth_for(inst))
        per[inst][e["condition"]].append({"rep": e["rep"], "sem": sem, "subtype": subtype,
                                          "trial": e["trial"]})

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
        "arm": arm,
        "model_name": ARM_MODEL_NAME[arm],
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
        "n_episodes_collected": len(included) + len(excluded_invalid),
        "episodes_graded": sum(len(per[i][c]) for i in instances for c in COND),
        "measurement_invalid_excluded": excluded_invalid,
        "spent_cny": round(spent, 4),
        "spent_on_aborted_block_passes_cny": round(aborted_spend, 4),
        # Attempts the arbiter replaced. Their episode.json was overwritten by the replacement,
        # so unlike an aborted pass they exist in no tree; the ledger is the only record.
        "spent_on_replaced_attempts_cny": round(replaced_spend, 4),
        "measurement_invalid_attempts": invalid, "replaced_attempts": replaced,
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
          f"{rep['episodes_graded']} graded episodes (¥{rep['spent_cny']}, "
          f"{rep['measurement_invalid_attempts']} measurement-invalid attempts, "
          f"{rep['replaced_attempts']} replaced). **Unit = task instance (n={len(rep['instances'])}); "
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
    ap.add_argument("--arm", type=int, default=1, choices=(1, 2),
                    help="which arm to report; each arm has its own custody tree and its own report")
    ap.add_argument("--check", action="store_true", help="verify the committed report reproduces")
    args = ap.parse_args()

    out_json, out_md = _out(args.arm)
    rep = build(args.arm)
    blob = json.dumps(rep, indent=2) + "\n"
    if args.check:
        if not out_json.is_file():
            print(f"FAIL: {out_json} missing", file=sys.stderr)
            return 1
        if out_json.read_text(encoding="utf-8") != blob:
            print(f"FAIL: {out_json} does not reproduce", file=sys.stderr)
            return 1
        print(json.dumps({"ok": True, "arm": args.arm, "graded": rep["episodes_graded"],
                          "spent_cny": rep["spent_cny"]}))
        return 0

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(blob, encoding="utf-8")
    out_md.write_text(_markdown(rep), encoding="utf-8")
    print(json.dumps({k: rep[k] for k in (
        "condition_mean_rates_over_instances_descriptive", "contrast_tally_instance_level",
        "primary_sign_test", "primary_permutation_sensitivity", "spent_cny")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
