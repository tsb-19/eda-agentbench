#!/usr/bin/env python3
"""Fairness-gate retry policy (corrected, review-directed 2026-07-24).

A fairness candidate may be retried ONLY when the attempt is measurement-invalid due to an EXPLICIT
infrastructure/tool failure. A valid grader result whose score differs from the expected fairness
result is a HARD gate failure and must NOT be retried merely because the score is unfavorable.

Retryable measurement-infra failures:
  - PT launch / tool crash; license/shim failure;
  - truncated or unparsable output that yields NO valid grade (total_score is None);
  - explicit infrastructure timeout (regen/grade raised);
  - other predeclared tool-health failures.

NOT retryable (hard gate):
  - a gradeable result with a real numeric score that is simply wrong (e.g. golden graded 0.2 with
    signoff green / evidence-gen 0 -- a valid grader outcome, not an infra failure).
"""
from __future__ import annotations


def is_measurement_infra_failure(result) -> bool:
    """True iff the attempt is measurement-invalid due to an explicit infra/tool failure (retryable).

    result: the graded-candidate dict (from _grade_one) or None. A None result, a None total_score,
    or a present 'error' => infra failure. A real numeric total_score (even an unfavorable one) is a
    VALID grader result => NOT an infra failure (hard gate, no retry)."""
    if result is None:
        return True
    if result.get("total_score") is None:
        return True
    err = result.get("error")
    if err:
        return True
    return False


def should_retry(result, expected_score, attempt, max_replacements) -> bool:
    """Decide whether to retry a fairness candidate. Retries ONLY on infra failure, up to
    max_replacements. A valid wrong score NEVER retries (returns False -> hard gate failure)."""
    if attempt >= 1 + max_replacements:
        return False
    if not is_measurement_infra_failure(result):
        return False  # valid grader result (favorable or not) -- never retry-around a score
    return True


# sentinel policy (separate from candidate retry): a sentinel failure pauses/aborts the gate but does
# NOT change candidate membership or candidate outcomes.
SENTINEL_ABORT_ON_FAILURE = True
SENTINEL_RECORD_SEPARATE = True
