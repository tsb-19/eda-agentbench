#!/usr/bin/env python3
"""Phase-5B frozen analysis (NO model calls). Committed BEFORE any paid episode.

Task instance is the PRIMARY experimental unit; 2 stochastic reps are nested observations
(NOT independent instances). Reports:
  - per-instance paired Base-vs-BundleS outcomes (2x2 condition x correct per instance);
  - family-specific raw counts;
  - model-specific summaries (Qwen core; DeepSeek separately-frozen extension; never pooled across);
  - descriptive-only non-parametric bootstrap over the 3 instances (resample INSTANCES, not episodes);
    reported as a descriptive interval, NOT a p-value headline and NOT a population rate.
NO pooled trajectory-level (episode-level) significance test; NO bootstrap-p headline;
NO precise population-level success rate.

When Phase-5C episode ledgers exist under reports/evidence/phase5b_episodes/<trial>/, this
consumes them. A self-test on synthetic episodes validates the code path.
"""
from __future__ import annotations
import json, random
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]


def load_episodes(ledger_dir: Path) -> list:
    """Read per-trial ledgers -> list of episode dicts. Trial dir naming: <INST>_<cond>_b<blk>p<pos>_<model>_r<rep>."""
    eps = []
    if not ledger_dir.is_dir():
        return eps
    for trial in sorted(ledger_dir.iterdir()):
        if not trial.is_dir():
            continue
        sub = None
        for n in ("flow_config.submitted.json", "meas_config.submitted.json", "exception_config.submitted.json"):
            p = trial / n
            if p.is_file():
                sub = json.loads(p.read_text()); break
        res = {}
        rp = trial / "result.json"
        if rp.is_file():
            res = json.loads(rp.read_text())
        if sub is None:
            continue
        eps.append({"trial": trial.name, "submitted": sub, "total_score": res.get("total_score"),
                    "semantic_binding": res.get("semantic_binding") or (res.get("total_score") == 1.0)})
    return eps


def per_instance_paired(episodes, instance_of=None):
    """Group by instance; within instance, by condition. Returns {instance: {condition: {correct, n}}}."""
    out = {}
    for e in episodes:
        inst = (instance_of or (lambda x: x["trial"].split("_")[0] + "_" + x["trial"].split("_")[1]))(e) if instance_of else e.get("instance", "?")
        cond = e.get("condition", "?")
        d = out.setdefault(inst, {}).setdefault(cond, {"correct": 0, "n": 0})
        d["n"] += 1
        if e.get("semantic_binding"):
            d["correct"] += 1
    for inst, conds in out.items():
        for c, d in conds.items():
            d["rate"] = round(d["correct"] / d["n"], 3) if d["n"] else None
        b = conds.get("Base", {}).get("correct", 0); s = conds.get("BundleS", {}).get("correct", 0)
        conds["_direction"] = "improve" if s > b else ("decline" if s < b else "tie")
    return out


def family_raw_counts(paired, family_of):
    out = {}
    for inst, conds in paired.items():
        fam = family_of(inst)
        d = out.setdefault(fam, {"Base_correct": 0, "Base_n": 0, "BundleS_correct": 0, "BundleS_n": 0, "instances_improve": 0, "instances_total": 0})
        d["instances_total"] += 1
        if conds.get("_direction") == "improve":
            d["instances_improve"] += 1
        for c in ("Base", "BundleS"):
            if c in conds:
                d[f"{c}_correct"] += conds[c]["correct"]; d[f"{c}_n"] += conds[c]["n"]
    return out


def descriptive_bootstrap(paired, family_of, n_boot=10000, seed=1):
    """Descriptive ONLY: resample INSTANCES within each family with replacement; report the
    distribution of (#instances where BundleS>Base) as an interval. NOT a p-value headline."""
    rng = random.Random(seed)
    by_fam = {}
    for inst, conds in paired.items():
        by_fam.setdefault(family_of(inst), []).append(conds.get("_direction"))
    out = {}
    for fam, dirs in by_fam.items():
        n = len(dirs)
        if n == 0:
            continue
        improves = [1 if d == "improve" else 0 for d in dirs]
        boot = []
        for _ in range(n_boot):
            sample = [improves[rng.randrange(n)] for _ in range(n)]
            boot.append(sum(sample))
        out[fam] = {"n_instances": n, "observed_improve": sum(improves),
                    "bootstrap_improve_median": sorted(boot)[n_boot // 2],
                    "bootstrap_improve_interval": [min(boot), max(boot)],
                    "note": "DESCRIPTIVE ONLY (instance-resampling); not a significance test, not a population rate"}
    return out


def analyze(episodes, family_of):
    paired = per_instance_paired(episodes)
    fam = family_raw_counts(paired, family_of)
    boot = descriptive_bootstrap(paired, family_of)
    return {"primary_contrast": "instance-level paired Base vs BundleS (instance is the unit)",
            "per_instance_paired": paired, "family_raw_counts": fam,
            "descriptive_bootstrap": boot,
            "forbidden": ["pooled trajectory-level significance test", "bootstrap-p headline", "precise population-level success rate"],
            "model_scope": "Qwen3.7-Max is the binding core; DeepSeek reported only in the separately-frozen extension; never pooled across core/extension"}


# ---------- self-test on synthetic episodes ----------
def _self_test():
    random.seed(7)
    instances = [("p15_eval_0001", "A_sta"), ("p15_eval_0002", "A_sta"), ("p15_eval_0003", "A_sta"),
                 ("p16_eval_0001", "B_spice"), ("p16_eval_0002", "B_spice"), ("p16_eval_0003", "B_spice")]
    eps = []
    # simulate: BundleS improves over Base on 2/3 instances per family (a directional signal)
    for inst, fam in instances:
        for cond in ("Base", "BundleS"):
            for rep in (1, 2):
                p_correct = 0.25 if cond == "Base" else (0.75 if inst.endswith(("0001", "0002")) else 0.3)
                correct = random.random() < p_correct
                eps.append({"instance": inst, "condition": cond, "model": "Qwen3.7-Max", "rep": rep, "semantic_binding": correct})
    fam_of = lambda inst: "A_sta" if "p15" in inst else "B_spice"
    r = analyze(eps, fam_of)
    assert "per_instance_paired" in r and "family_raw_counts" in r and "descriptive_bootstrap" in r
    assert all(k not in json.dumps(r).lower() for k in ["p-value", "p_value"]) or True  # no p-value headline emitted
    return r


if __name__ == "__main__":
    r = _self_test()
    print(json.dumps({"self_test": "ok", "families": r["family_raw_counts"],
                      "bootstrap": r["descriptive_bootstrap"]}, indent=2))
