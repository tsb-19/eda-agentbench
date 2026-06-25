"""Reliability/calibration metrics for the Phase-0 probe (pure functions, unit-testable).

A trial is a dict: {model, task, rep, outcome, confidence, tokens, latency}.
  outcome   in {"pass","fail","abstain","parse_fail","empty","http_429"}
  confidence in {"high","medium","low","abstain",""} (lowercased; "" if unpar? -> treated low-trust)

Capability rates are computed over INFRA-VALID trials only (empty/http_429 excluded but counted in a
protocol tally). pass^k (all-of-k) is the reliability floor; pass@k (any-of-k) is the capability
ceiling; the reliability GAP = pass@1 - pass^k exposes "capable but inconsistent". Calibration splits
failures into OVERCONFIDENT-WRONG (fail while confident — catastrophic) vs CAUTIOUS (fail while low/
abstain). A per-trial trust score rewards confident-correct and heavily penalizes overconfident-wrong.
"""
from __future__ import annotations

import statistics as _st

INFRA = {"empty", "http_429"}
CONFIDENT = {"high", "medium"}


def is_infra(outcome: str) -> bool:
    return outcome in INFRA


def trust_per_trial(outcome: str, confidence: str) -> float:
    """Operationalizes 'avoid catastrophic confident failures'. Range ~[-1, +1]."""
    c = (confidence or "").lower()
    if outcome == "pass":
        return {"high": 1.0, "medium": 0.9, "low": 0.6}.get(c, 0.8)
    if outcome == "abstain":
        return 0.0
    if outcome == "parse_fail":
        return -0.2
    if outcome == "fail":
        return {"high": -1.0, "medium": -0.7, "low": -0.3}.get(c, -0.7)
    return 0.0  # infra: neutral (excluded elsewhere)


def per_task(trials: list[dict]) -> dict | None:
    """Reliability stats for one (model, task) over its k trials. None if all-infra."""
    valid = [t for t in trials if not is_infra(t["outcome"])]
    if not valid:
        return None
    passes = [1 if t["outcome"] == "pass" else 0 for t in valid]
    n = len(valid)
    return {
        "n_valid": n,
        "pass1": sum(passes) / n,                 # mean per-trial pass
        "all_pass": 1 if all(passes) else 0,      # pass^k (reliability floor)
        "any_pass": 1 if any(passes) else 0,      # pass@k (capability ceiling)
        "flipped": 1 if (0 < sum(passes) < n) else 0,   # disagreement across identical trials
    }


def per_model(trials: list[dict]) -> dict:
    """Aggregate one model's trials (across tasks) into reliability + calibration + cost."""
    by_task: dict[str, list[dict]] = {}
    for t in trials:
        by_task.setdefault(t["task"], []).append(t)

    task_stats = [s for s in (per_task(ts) for ts in by_task.values()) if s]
    n_tasks = len(task_stats)
    mean = lambda xs: (sum(xs) / len(xs)) if xs else 0.0

    pass1 = mean([s["pass1"] for s in task_stats])
    passk_all = mean([s["all_pass"] for s in task_stats])   # pass^k
    passk_any = mean([s["any_pass"] for s in task_stats])   # pass@k
    flip_rate = mean([s["flipped"] for s in task_stats])

    valid = [t for t in trials if not is_infra(t["outcome"])]
    confident = [t for t in valid if (t["confidence"] or "").lower() in CONFIDENT]
    overconf_wrong = [t for t in confident if t["outcome"] == "fail"]
    cautious_fail = [t for t in valid
                     if t["outcome"] == "fail" and (t["confidence"] or "").lower() not in CONFIDENT]
    abstains = [t for t in valid if t["outcome"] == "abstain"]
    parse_fails = [t for t in valid if t["outcome"] == "parse_fail"]

    # protocol / infra tally (over ALL trials)
    proto = {}
    for t in trials:
        proto[t["outcome"]] = proto.get(t["outcome"], 0) + 1

    return {
        "n_tasks": n_tasks,
        "n_trials": len(trials),
        "pass1": pass1,
        "passk_all": passk_all,                       # pass^k
        "passk_any": passk_any,                       # pass@k
        "reliability_gap": pass1 - passk_all,         # capable-but-inconsistent
        "flip_rate": flip_rate,
        # calibration
        "overconf_rate": (len(overconf_wrong) / len(confident)) if confident else 0.0,  # P(fail|confident)
        "n_overconf_wrong": len(overconf_wrong),
        "n_cautious_fail": len(cautious_fail),
        "abstain_rate": (len(abstains) / len(valid)) if valid else 0.0,
        "parse_fail_rate": (len(parse_fails) / len(valid)) if valid else 0.0,
        "format_compliance": mean([1 if t.get("format_ok") else 0 for t in valid]),
        "trust": mean([trust_per_trial(t["outcome"], t["confidence"]) for t in valid]),
        # protocol/infra
        "protocol": proto,
        # cost (over trials that have it)
        "mean_tokens": mean([t["tokens"] for t in trials if t.get("tokens")]),
        "mean_latency": mean([t["latency"] for t in trials if t.get("latency")]),
    }


def discriminates(model_rows: dict[str, dict], key: str, min_spread: float) -> bool:
    """True if `key` spreads >= min_spread across models (the GO test, per metric)."""
    vals = [r[key] for r in model_rows.values() if r.get("n_tasks")]
    return bool(vals) and (max(vals) - min(vals) >= min_spread)
