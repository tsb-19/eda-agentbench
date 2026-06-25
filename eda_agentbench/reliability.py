"""Reliability / calibration measurement layer for the P1-P9 battery.

Motivation (2026-06-24 pivot, memory `reliability-calibration-pivot`): once frontier models are
near-saturated on raw capability, pass@1 is no longer the right primary instrument. What separates
models is whether they are *reliable* (consistent across identical trials), *calibrated* (know when
they're unsure; avoid catastrophic confident-wrong answers), and *protocol-compliant* (follow the
output contract instead of failing format/empty/budget). This module is the pure, reusable core:
prompt instruction + parsing + per-trial classification + aggregate metrics. Grading itself stays in
the existing evaluators; this layer consumes (passed, confidence, protocol) trial records.

A canonical TRIAL record is a dict:
    {model, task, track?, outcome, confidence, format_ok, tokens?, latency?, tool_calls?, retries?}
  outcome    in OUTCOMES (capability + protocol unified status)
  confidence in CONFIDENCE_LEVELS (lowercased) or "" if none parsed
  format_ok  bool — did the response use the exact ANSWER:/CONFIDENCE: contract

Capability rates are computed over INFRA-VALID trials only (gateway/empty excluded but counted in a
protocol tally). pass^k (all-of-k) is the reliability floor; pass@k (any-of-k) the capability ceiling;
reliability gap = pass@1 - pass^k exposes "capable but inconsistent". Calibration splits failures into
OVERCONFIDENT-WRONG (fail while confident — catastrophic) vs CAUTIOUS (fail while low/abstain), and
credits CONFIDENT-CORRECT while lightly debiting UNDERCONFIDENT-CORRECT and ABSTAIN.
"""
from __future__ import annotations

import re

CONFIDENCE_LEVELS = ("high", "medium", "low", "abstain")
CONFIDENT = {"high", "medium"}

# outcome status values -----------------------------------------------------------------------------
PASS, FAIL, ABSTAIN = "pass", "fail", "abstain"
# protocol failures (tracked SEPARATELY from reasoning failures, per the pivot spec):
PARSE_FAIL = "parse_fail"        # produced output but not a usable answer
EMPTY = "empty"                  # no/blank response
HTTP_429 = "http_429"            # gateway rate limit
BUDGET_EXHAUSTED = "budget_exhausted"  # agentic: ran out of tool-call / token budget
NOCOMMIT = "nocommit"            # agentic: never emitted a final answer/commit
TOOL_MISUSE = "tool_misuse"      # agentic: malformed/forbidden tool use dominated
ANTI_CHEAT = "anti_cheat"        # disqualified by anti-cheat
OUTCOMES = (PASS, FAIL, ABSTAIN, PARSE_FAIL, EMPTY, HTTP_429, BUDGET_EXHAUSTED,
            NOCOMMIT, TOOL_MISUSE, ANTI_CHEAT)
INFRA = {EMPTY, HTTP_429}        # never count as capability OR as a model failure
PROTOCOL_FAILS = {PARSE_FAIL, EMPTY, HTTP_429, BUDGET_EXHAUSTED, NOCOMMIT, TOOL_MISUSE, ANTI_CHEAT}

# Instruction appended to task prompts so every trial yields a calibrated decision. ------------------
CONFIDENCE_INSTRUCTION = (
    "\n\nAfter your answer, on a new line outside any code block, declare your calibrated confidence "
    "that your answer is correct:\n"
    "CONFIDENCE: <HIGH | MEDIUM | LOW | ABSTAIN>\n"
    "Use ABSTAIN (equivalently 'needs human review') only if you genuinely cannot determine the "
    "answer. Report honestly — a wrong answer given with HIGH confidence is the worst outcome.")

_CONF_RE = re.compile(r"CONFIDENCE\s*[:=]\s*\**\s*(HIGH|MEDIUM|MED|LOW|ABSTAIN)", re.I)
_BARE = {"HIGH", "MEDIUM", "LOW", "ABSTAIN"}


def parse_confidence(text: str) -> tuple[str, bool]:
    """Return (confidence, format_ok). Lenient: accept a bare confidence token if the exact
    'CONFIDENCE:' marker is absent, but record format_ok=False so protocol-compliance is measured."""
    if not text:
        return "", False
    m = _CONF_RE.search(text)
    if m:
        c = m.group(1).lower()
        return ("medium" if c == "med" else c), True
    for ln in text.splitlines():                       # bare token fallback
        tok = ln.strip().strip("*`").upper()
        if tok in _BARE:
            return tok.lower(), False
    return "", False


def calibration_bucket(passed: bool | None, confidence: str) -> str:
    """Classify a gradable trial for calibration accounting."""
    c = (confidence or "").lower()
    if c == "abstain" or passed is None:
        return "abstain"
    if passed:
        return "confident_correct" if c in CONFIDENT else "underconfident_correct"
    return "overconfident_wrong" if c in CONFIDENT else "cautious_fail"


def trust_per_trial(outcome: str, confidence: str) -> float:
    """Operationalizes 'avoid catastrophic confident failures'. Range ~[-1, +1]."""
    c = (confidence or "").lower()
    if outcome == PASS:
        return {"high": 1.0, "medium": 0.9, "low": 0.6}.get(c, 0.8)
    if outcome == ABSTAIN:
        return 0.0
    if outcome in PROTOCOL_FAILS - INFRA:              # protocol miss (non-infra)
        return -0.2
    if outcome == FAIL:
        return {"high": -1.0, "medium": -0.7, "low": -0.3}.get(c, -0.7)
    return 0.0                                          # infra: neutral (excluded from aggregates)


def is_infra(outcome: str) -> bool:
    return outcome in INFRA


def per_task(trials: list[dict]) -> dict | None:
    """Reliability stats for one (model, task) over its k trials. None if all-infra."""
    valid = [t for t in trials if not is_infra(t["outcome"])]
    if not valid:
        return None
    passes = [1 if t["outcome"] == PASS else 0 for t in valid]
    n = len(valid)
    return {
        "n_valid": n,
        "pass1": sum(passes) / n,
        "all_pass": 1 if all(passes) else 0,           # pass^k (reliability floor)
        "any_pass": 1 if any(passes) else 0,           # pass@k (capability ceiling)
        "flipped": 1 if (0 < sum(passes) < n) else 0,
    }


def _mean(xs):
    return (sum(xs) / len(xs)) if xs else 0.0


def per_model(trials: list[dict]) -> dict:
    """Aggregate one model's trials (across tasks) into reliability + calibration + cost + protocol."""
    by_task: dict[str, list[dict]] = {}
    for t in trials:
        by_task.setdefault(t["task"], []).append(t)
    task_stats = [s for s in (per_task(ts) for ts in by_task.values()) if s]

    pass1 = _mean([s["pass1"] for s in task_stats])
    passk_all = _mean([s["all_pass"] for s in task_stats])
    passk_any = _mean([s["any_pass"] for s in task_stats])

    valid = [t for t in trials if not is_infra(t["outcome"])]
    buckets: dict[str, int] = {}
    for t in valid:
        if t["outcome"] in (PASS, FAIL, ABSTAIN):
            b = calibration_bucket(t["outcome"] == PASS if t["outcome"] != ABSTAIN else None,
                                   t["confidence"])
            buckets[b] = buckets.get(b, 0) + 1
    confident_attempts = buckets.get("confident_correct", 0) + buckets.get("overconfident_wrong", 0)
    proto: dict[str, int] = {}
    for t in trials:
        proto[t["outcome"]] = proto.get(t["outcome"], 0) + 1

    return {
        "n_tasks": len(task_stats),
        "n_trials": len(trials),
        "pass1": pass1,
        "passk_all": passk_all,                        # pass^k
        "passk_any": passk_any,                        # pass@k
        "reliability_gap": pass1 - passk_all,
        "flip_rate": _mean([s["flipped"] for s in task_stats]),
        # calibration
        "overconf_rate": (buckets.get("overconfident_wrong", 0) / confident_attempts)
        if confident_attempts else 0.0,
        "n_overconf_wrong": buckets.get("overconfident_wrong", 0),
        "n_underconf_correct": buckets.get("underconfident_correct", 0),
        "n_cautious_fail": buckets.get("cautious_fail", 0),
        "abstain_rate": (buckets.get("abstain", 0) / len(valid)) if valid else 0.0,
        "format_compliance": _mean([1 if t.get("format_ok") else 0 for t in valid]),
        "trust": _mean([trust_per_trial(t["outcome"], t["confidence"]) for t in valid]),
        # protocol / infra tally (over ALL trials)
        "protocol": proto,
        "protocol_fail_rate": _mean([1 if t["outcome"] in PROTOCOL_FAILS else 0 for t in trials]),
        # cost (secondary)
        "mean_tokens": _mean([t["tokens"] for t in trials if t.get("tokens")]),
        "mean_latency": _mean([t["latency"] for t in trials if t.get("latency")]),
        "mean_tool_calls": _mean([t["tool_calls"] for t in trials if t.get("tool_calls") is not None]),
        "mean_retries": _mean([t["retries"] for t in trials if t.get("retries") is not None]),
    }


def discriminates(model_rows: dict[str, dict], key: str, min_spread: float) -> bool:
    """True if `key` spreads >= min_spread across models with data (the per-metric GO test)."""
    vals = [r[key] for r in model_rows.values() if r.get("n_tasks")]
    return bool(vals) and (max(vals) - min(vals) >= min_spread)


# ---- harness join helpers: a (response, grade) pair -> reliability annotation / trial record ----

def protocol_from(error=None, parse_ok: bool = True) -> str:
    """Map raw inference signals to a protocol status. NOTE: parse_ok=False (model ignored the
    file-block contract) is a FORMAT signal, not infra — the answer may still be graded, so it does
    NOT void capability here; it only lowers format_ok."""
    if error:
        return HTTP_429 if "429" in str(error) else EMPTY
    return "ok"


def agentic_protocol(*, clean: bool = True, error=None, timed_out: bool = False,
                     finished: bool = False, n_edits: int = 0, n_actions: int = 0,
                     n_valid_actions: int | None = None) -> str:
    """Map one agentic episode's raw signals to a protocol status — the agentic analog of
    protocol_from. Precedence (most-decisive first):
      1. infra error (gateway 429 / empty)  — not a valid measurement; exclude + rerun (#79/#102)
      2. anti-cheat dirty                    — forbidden edit / shadow / tcl-injection: a real DQ
      3. timed_out                           — hit the wall-clock budget
      4. all actions refused/unrecognized    — never used a tool successfully (tool_misuse)
      5. never FINISHed:  no edits -> NOCOMMIT (gave up, nothing to grade);
                          with edits -> BUDGET_EXHAUSTED (partial work, ran out of actions)
      6. otherwise "ok"  (a deliberate submission — grade it for capability)
    `n_valid_actions` defaults to None so tool_misuse only fires when the caller supplies the count."""
    if error:
        return HTTP_429 if "429" in str(error) else EMPTY
    if not clean:
        return ANTI_CHEAT
    if timed_out:
        return BUDGET_EXHAUSTED
    if n_actions > 0 and n_valid_actions == 0:
        return TOOL_MISUSE
    if not finished:
        return NOCOMMIT if n_edits == 0 else BUDGET_EXHAUSTED
    return "ok"


def outcome_from(passed: bool | None, protocol: str, confidence: str) -> str:
    if protocol and protocol != "ok":
        return protocol
    if (confidence or "").lower() == "abstain":
        return ABSTAIN
    return PASS if passed else FAIL


def _format_ok(proto: str, parse_ok: bool, conf_fmt: bool, elicited: bool) -> bool:
    if proto != "ok":
        return False
    return bool(parse_ok) and (conf_fmt if elicited else True)


def trial_record(model: str, task: str, track: str, passed: bool | None, *,
                 response_text: str = "", error=None, parse_ok: bool = True,
                 elicited: bool = True, **cost) -> dict:
    """Canonical trial dict for aggregation, joining a model response with its grade."""
    conf, conf_fmt = parse_confidence(response_text or "")
    proto = protocol_from(error, parse_ok)
    return {"model": model, "task": task, "track": track,
            "outcome": outcome_from(passed, proto, conf),
            "confidence": conf, "format_ok": _format_ok(proto, parse_ok, conf_fmt, elicited),
            **cost}


def annotate_score(score, *, response_text: str = "", error=None, parse_ok: bool = True,
                   elicited: bool = True):
    """Populate a ScoreResult's reliability fields from the model response that produced it."""
    conf, conf_fmt = parse_confidence(response_text or "")
    proto = protocol_from(error, parse_ok)
    score.confidence_decision = conf
    score.format_ok = _format_ok(proto, parse_ok, conf_fmt, elicited)
    score.protocol_status = proto
    graded_pass = None if (proto != "ok" or conf == "abstain") else bool(score.passed)
    b = calibration_bucket(graded_pass, conf)
    score.overconfident_wrong = (b == "overconfident_wrong")
    score.underconfident_correct = (b == "underconfident_correct")
    score.abstained = (b == "abstain")
    return score
