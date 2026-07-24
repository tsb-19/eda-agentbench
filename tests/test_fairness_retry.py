"""Regression tests for the corrected fairness-gate retry policy (scripts/fairness_retry.py).

Locks in the distinction: a candidate is retried ONLY on an explicit infra/tool failure (no valid
grade); a valid grader result with an unfavorable score is a HARD gate failure and is never retried."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fairness_retry as fr  # noqa: E402


def test_missing_result_is_infra_failure():
    assert fr.is_measurement_infra_failure(None) is True


def test_none_total_score_is_infra_failure():
    assert fr.is_measurement_infra_failure({"total_score": None, "error": None}) is True


def test_explicit_error_is_infra_failure():
    assert fr.is_measurement_infra_failure({"total_score": None, "error": "TimeoutExpired: ..."}) is True
    assert fr.is_measurement_infra_failure({"total_score": 1.0, "error": "license checkout failed"}) is True


def test_valid_unfavorable_score_is_NOT_infra_failure():
    # golden graded 0.2 with a real grade (signoff green, evgen 0) -> valid grader result, NOT infra
    assert fr.is_measurement_infra_failure({"total_score": 0.2, "error": None}) is False
    assert fr.is_measurement_infra_failure({"total_score": 0.1, "error": None}) is False


def test_should_retry_only_on_infra_and_within_cap():
    infra = {"total_score": None, "error": "stage1 timed out"}
    assert fr.should_retry(infra, 1.0, 1, 2) is True       # infra -> retry
    assert fr.should_retry(infra, 1.0, 3, 2) is False      # cap reached (1 + 2)


def test_should_retry_never_on_unfavorable_valid_score():
    wrong = {"total_score": 0.2, "error": None}            # valid but wrong (golden should be 1.0)
    assert fr.should_retry(wrong, 1.0, 1, 2) is False      # HARD gate failure, no retry
    assert fr.should_retry(wrong, 1.0, 1, 5) is False      # even with a high cap


def test_favorable_valid_score_not_retried():
    ok = {"total_score": 1.0, "error": None}
    assert fr.should_retry(ok, 1.0, 1, 2) is False
