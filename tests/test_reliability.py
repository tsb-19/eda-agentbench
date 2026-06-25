"""Tool-free unit tests for the reliability/calibration layer (eda_agentbench/reliability.py)."""
from __future__ import annotations

import eda_agentbench.reliability as R


# ---------- parse_confidence ----------
def test_parse_confidence_labeled():
    assert R.parse_confidence("ANSWER: 3\nCONFIDENCE: HIGH") == ("high", True)
    assert R.parse_confidence("CONFIDENCE: MED") == ("medium", True)
    assert R.parse_confidence("blah\nCONFIDENCE: ABSTAIN") == ("abstain", True)


def test_parse_confidence_bare_is_not_format_ok():
    assert R.parse_confidence("11.0757\nHIGH") == ("high", False)
    assert R.parse_confidence("**LOW**") == ("low", False)


def test_parse_confidence_none():
    assert R.parse_confidence("just an answer, no confidence") == ("", False)
    assert R.parse_confidence("") == ("", False)


# ---------- calibration_bucket ----------
def test_calibration_buckets():
    assert R.calibration_bucket(True, "high") == "confident_correct"
    assert R.calibration_bucket(True, "low") == "underconfident_correct"
    assert R.calibration_bucket(False, "high") == "overconfident_wrong"
    assert R.calibration_bucket(False, "low") == "cautious_fail"
    assert R.calibration_bucket(None, "abstain") == "abstain"
    assert R.calibration_bucket(True, "abstain") == "abstain"   # abstain dominates


# ---------- trust_per_trial ----------
def test_trust_extremes():
    assert R.trust_per_trial(R.PASS, "high") == 1.0
    assert R.trust_per_trial(R.FAIL, "high") == -1.0            # catastrophic confident-wrong
    assert R.trust_per_trial(R.FAIL, "low") == -0.3             # cautious failure
    assert R.trust_per_trial(R.ABSTAIN, "abstain") == 0.0
    assert R.trust_per_trial(R.PARSE_FAIL, "") == -0.2          # protocol miss
    assert R.trust_per_trial(R.EMPTY, "") == 0.0                # infra neutral


# ---------- per_task ----------
def _t(outcome, conf="high", task="a", fmt=True):
    return {"model": "m", "task": task, "outcome": outcome, "confidence": conf, "format_ok": fmt}


def test_per_task_all_pass_reliable():
    s = R.per_task([_t(R.PASS), _t(R.PASS), _t(R.PASS)])
    assert s["pass1"] == 1.0 and s["all_pass"] == 1 and s["any_pass"] == 1 and s["flipped"] == 0


def test_per_task_flip_breaks_passk_all():
    s = R.per_task([_t(R.PASS), _t(R.FAIL), _t(R.PASS)])
    assert s["all_pass"] == 0 and s["any_pass"] == 1 and s["flipped"] == 1
    assert abs(s["pass1"] - 2 / 3) < 1e-9


def test_per_task_all_infra_is_none():
    assert R.per_task([_t(R.EMPTY), _t(R.HTTP_429)]) is None


# ---------- per_model fairness baselines (must behave) ----------
def _synth(outcome, conf, n_tasks=4, k=5, fmt=True):
    return [{"model": "_", "task": f"t{i}", "outcome": outcome, "confidence": conf, "format_ok": fmt}
            for i in range(n_tasks) for _ in range(k)]


def test_baseline_always_correct_high():
    r = R.per_model(_synth(R.PASS, "high"))
    assert r["pass1"] == 1.0 and r["passk_all"] == 1.0 and r["reliability_gap"] == 0.0
    assert r["overconf_rate"] == 0.0 and r["trust"] == 1.0 and r["format_compliance"] == 1.0


def test_baseline_always_wrong_high_is_worst():
    r = R.per_model(_synth(R.FAIL, "high"))
    assert r["overconf_rate"] == 1.0 and r["n_overconf_wrong"] == 20 and r["trust"] == -1.0


def test_baseline_abstain_is_neutral():
    r = R.per_model(_synth(R.ABSTAIN, "abstain"))
    assert r["abstain_rate"] == 1.0 and r["trust"] == 0.0 and r["overconf_rate"] == 0.0


def test_baseline_cautious_not_flagged_overconfident():
    r = R.per_model(_synth(R.FAIL, "low"))
    assert r["overconf_rate"] == 0.0 and r["n_cautious_fail"] == 20 and r["trust"] == -0.3


# ---------- per_model: pass@k vs pass^k, format, protocol, infra ----------
def test_passk_any_exceeds_passk_all_when_inconsistent():
    # one task: 1 pass + 1 fail -> any_pass=1, all_pass=0
    trials = [_t(R.PASS, task="x"), _t(R.FAIL, task="x")]
    r = R.per_model(trials)
    assert r["passk_any"] == 1.0 and r["passk_all"] == 0.0 and r["reliability_gap"] == 0.5


def test_format_compliance_and_protocol_tally():
    trials = [_t(R.PASS, fmt=True), _t(R.PASS, fmt=False),
              _t(R.PARSE_FAIL, conf="", fmt=False), _t(R.HTTP_429, conf="", fmt=False)]
    r = R.per_model(trials)
    # valid (non-infra) = 3 trials; 1 of 3 format_ok
    assert abs(r["format_compliance"] - 1 / 3) < 1e-9
    assert r["protocol"][R.HTTP_429] == 1 and r["protocol"][R.PARSE_FAIL] == 1
    assert abs(r["protocol_fail_rate"] - 2 / 4) < 1e-9       # parse_fail + http_429 over ALL trials


def test_infra_excluded_from_capability():
    # all-infra task contributes no task stats
    r = R.per_model([_t(R.EMPTY, conf=""), _t(R.HTTP_429, conf="")])
    assert r["n_tasks"] == 0 and r["pass1"] == 0.0


def test_per_model_aggregates_cost_secondary():
    trials = [{"model": "m", "task": "a", "outcome": R.PASS, "confidence": "high", "format_ok": True,
               "tokens": 30000, "tool_calls": 5, "latency": 120.0, "retries": 1},
              {"model": "m", "task": "b", "outcome": R.FAIL, "confidence": "low", "format_ok": True,
               "tokens": 50000, "tool_calls": 7, "latency": 180.0, "retries": 3}]
    r = R.per_model(trials)
    assert r["mean_tokens"] == 40000 and r["mean_tool_calls"] == 6.0
    assert r["mean_latency"] == 150.0 and r["mean_retries"] == 2.0


# ---------- discriminates ----------
def test_discriminates():
    rows = {"A": {"n_tasks": 4, "trust": 1.0}, "B": {"n_tasks": 4, "trust": 0.7}}
    assert R.discriminates(rows, "trust", 0.15) is True
    assert R.discriminates(rows, "trust", 0.5) is False


# ---------- join helpers: response + grade -> trial / annotation ----------
def test_protocol_and_outcome_from():
    assert R.protocol_from(error="HTTP 429 rate") == R.HTTP_429
    assert R.protocol_from(error="boom") == R.EMPTY
    assert R.protocol_from(parse_ok=False) == "ok"          # format signal, not infra
    assert R.outcome_from(True, "ok", "high") == R.PASS
    assert R.outcome_from(False, "ok", "high") == R.FAIL
    assert R.outcome_from(True, "ok", "abstain") == R.ABSTAIN
    assert R.outcome_from(True, R.HTTP_429, "high") == R.HTTP_429


# ---------- agentic_protocol (episode-signal -> protocol status, with precedence) ----------
def test_agentic_protocol_ok_when_finished_with_edits():
    assert R.agentic_protocol(clean=True, finished=True, n_edits=1, n_actions=4) == "ok"


def test_agentic_protocol_nocommit_vs_budget():
    # never finished, made no edits -> gave up, nothing to grade
    assert R.agentic_protocol(finished=False, n_edits=0, n_actions=12) == R.NOCOMMIT
    # never finished but DID edit -> partial work, ran out of actions
    assert R.agentic_protocol(finished=False, n_edits=2, n_actions=12) == R.BUDGET_EXHAUSTED


def test_agentic_protocol_timeout_is_budget():
    assert R.agentic_protocol(timed_out=True, finished=True, n_edits=1) == R.BUDGET_EXHAUSTED


def test_agentic_protocol_anticheat_beats_budget():
    assert R.agentic_protocol(clean=False, timed_out=True, finished=False) == R.ANTI_CHEAT


def test_agentic_protocol_infra_error_wins():
    # an API failure makes the episode an invalid measurement regardless of edits/cheat
    assert R.agentic_protocol(clean=False, error="HTTP 429", finished=False) == R.HTTP_429
    assert R.agentic_protocol(error="connection reset", finished=True, n_edits=3) == R.EMPTY


def test_agentic_protocol_tool_misuse_when_all_actions_refused():
    assert R.agentic_protocol(finished=False, n_edits=0, n_actions=5, n_valid_actions=0) == R.TOOL_MISUSE
    # default n_valid_actions=None => tool_misuse never fires, falls through to nocommit
    assert R.agentic_protocol(finished=False, n_edits=0, n_actions=5) == R.NOCOMMIT


def test_trial_record_credits_capability_despite_bad_fileformat():
    # model answered correctly but ignored the file-block contract (parse_ok=False) and used a bare
    # confidence token -> still a PASS, but format_ok=False (the fairness fix from the probe).
    t = R.trial_record("m", "x", "p3", True, response_text="11.0757\nHIGH", parse_ok=False)
    assert t["outcome"] == R.PASS and t["confidence"] == "high" and t["format_ok"] is False


def test_trial_record_infra_on_error():
    t = R.trial_record("m", "x", "p3", None, error="HTTP 429")
    assert t["outcome"] == R.HTTP_429 and t["format_ok"] is False


def test_annotate_score_sets_reliability_fields():
    from eda_agentbench.types import ScoreResult
    s = ScoreResult(task_id="x", track="p3", mode="single_shot", total_score=0.0, max_possible=1.0,
                    components=[], passed=False, passing_threshold=0.5, evaluation_time_sec=0.0,
                    anti_cheat={}, resource_usage={}, metadata={})
    R.annotate_score(s, response_text="ANSWER: 9\nCONFIDENCE: HIGH")   # wrong + HIGH
    assert s.confidence_decision == "high" and s.format_ok is True
    assert s.overconfident_wrong is True and s.protocol_status == "ok"
    d = s.to_dict()
    assert d["reliability"]["overconfident_wrong"] is True

