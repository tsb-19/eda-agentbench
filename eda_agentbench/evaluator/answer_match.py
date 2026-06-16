"""Robust answer matching for report-QA tracks (P3, P6 Synthesis QA, P8).

The judgment problem is not "is this one number right?" — a model's answer may be
correct yet wrapped in units, markdown, labels, or prose, and some answers are
*structured* ("0 errors, 2 warnings"). Grading must be liberal in the ACCEPTED FORM
but strict about the VALUE, so the leaderboard measures EDA ability, not format
obedience — without ever letting a wrong value pass (which would break the
solution>=0.9 / buggy<0.9 reliability gate).

Design:
  * numeric  — strip decoration, extract the number (units/markdown/labels ignored,
               thousands-commas removed, sci-notation aware), compare with tolerance
               (relative when tol>0, near-exact when tol==0) and an absolute floor.
  * composite ("N word, M word") — compare the ordered number sequence AND require
               each alphabetic keyword of the expected answer to appear. Phrasing
               ("0 errors and 2 warnings") is tolerated; wrong/reordered numbers fail.
  * string   — strip wrapping markdown/quotes/punctuation, collapse whitespace,
               case-insensitive equality (identifiers/phrases).
  * int/bool — tolerant scalar parse (commas/units), exact / truth-set compare.

Every function returns (matched: bool, detail: str).
"""

from __future__ import annotations

import re

# Signed integer / decimal / scientific-notation token.
_NUM_RE = re.compile(r"[-+]?(?:\d+\.\d+|\.\d+|\d+)(?:[eE][-+]?\d+)?")
# Markdown / wrapping characters with no semantic content for an answer.
_STRIP_CHARS = "`*_$#~"
_BOOL_TRUE = {"true", "1", "yes", "y", "met", "pass", "passed", "ok"}
_BOOL_FALSE = {"false", "0", "no", "n", "violated", "fail", "failed", "not met"}


def _strip_decoration(s: str) -> str:
    """Remove markdown, wrapping quotes/brackets, and outer punctuation/space."""
    s = s.strip()
    # Drop fenced code markers if the whole thing is fenced.
    if s.startswith("```") and s.endswith("```"):
        s = s.strip("`").strip()
        if "\n" in s:  # drop an optional language tag on the first line
            first, _, rest = s.partition("\n")
            if first and not any(c.isspace() for c in first):
                s = rest
    for ch in _STRIP_CHARS:
        s = s.replace(ch, "")
    s = s.strip().strip("'\"")
    # Strip a trailing sentence period and surrounding brackets/quotes.
    s = s.strip().strip("().,;:!").strip()
    return s


def _remove_thousands(s: str) -> str:
    return re.sub(r"(?<=\d),(?=\d)", "", s)


def _extract_numbers(s: str) -> list[float]:
    return [float(m) for m in _NUM_RE.findall(_remove_thousands(s))]


def _to_float(s: str) -> float | None:
    s = _remove_thousands(_strip_decoration(s))
    try:
        return float(s)
    except ValueError:
        nums = _NUM_RE.findall(s)
        if len(nums) == 1:
            return float(nums[0])
        if nums:                      # multiple — models conclude with the answer
            return float(nums[-1])
        return None


def _is_composite(expected: str) -> bool:
    """A structured multi-token answer like "0 errors, 2 warnings": has a digit, a
    letter, AND whitespace. Single tokens with digits (clk_100m, reg2reg, mux_4to1)
    are identifiers, NOT composites, and must go through string matching."""
    e = expected.strip()
    return (bool(re.search(r"\d", e)) and bool(re.search(r"[A-Za-z]", e))
            and bool(re.search(r"\s", e)))


def match_numeric(expected: str, submission: str, tolerance: float) -> tuple[bool, str]:
    exp = _to_float(expected)
    if exp is None:                   # expected not numeric -> defer to string
        return match_string(expected, submission)

    def close(sub: float) -> bool:
        if tolerance and tolerance > 0:
            if exp == 0.0:
                return abs(sub) <= max(tolerance, 1e-9)
            return abs(sub - exp) / abs(exp) <= tolerance
        return abs(sub - exp) <= 1e-6 + 1e-9 * abs(exp)   # exact, tolerant of repr

    # Candidate values: a clean single parse if the whole thing is one number;
    # otherwise the FIRST and LAST extracted numbers (a decorated single value puts
    # the answer first, e.g. "88409.51 um^2"; a restating answer puts it last, e.g.
    # "...total 5"). Bounded to two positions to avoid report-dump false positives.
    cleaned = _remove_thousands(_strip_decoration(submission))
    try:
        cands = [float(cleaned)]
    except ValueError:
        nums = _extract_numbers(submission)
        cands = [nums[0], nums[-1]] if nums else []
    if not cands:
        return False, f"no number found in submission {submission.strip()[:60]!r}"
    return any(close(c) for c in cands), f"numeric expected={exp}, cands={cands} (tol={tolerance})"


def match_composite(expected: str, submission: str) -> tuple[bool, str]:
    exp_nums = _extract_numbers(expected)
    sub_nums = _extract_numbers(submission)
    if exp_nums != sub_nums:
        return False, f"number sequence expected={exp_nums}, got={sub_nums}"
    sub_lower = submission.lower()
    missing = [w for w in re.findall(r"[A-Za-z]+", expected.lower())
               if w not in sub_lower]
    if missing:
        return False, f"missing keyword(s) {missing} in {submission.strip()[:60]!r}"
    return True, f"composite match (nums={exp_nums})"


def match_string(expected: str, submission: str) -> tuple[bool, str]:
    e = re.sub(r"\s+", " ", _strip_decoration(expected)).lower()
    s = re.sub(r"\s+", " ", _strip_decoration(submission)).lower()
    return (e == s), f"string expected={expected.strip()!r}, got={submission.strip()!r}"


def match_int(expected: str, submission: str) -> tuple[bool, str]:
    e, s = _to_float(expected), _to_float(submission)
    if e is None or s is None:
        return False, f"int parse: expected={expected.strip()!r}, got={submission.strip()!r}"
    return (round(e) == round(s)), f"int expected={round(e)}, got={round(s)}"


def match_bool(expected: str, submission: str) -> tuple[bool, str]:
    def truth(x: str):
        t = _strip_decoration(x).lower()
        if t in _BOOL_TRUE:
            return True
        if t in _BOOL_FALSE:
            return False
        return None
    e, s = truth(expected), truth(submission)
    return (e is not None and e == s), f"bool expected={expected.strip()!r}, got={submission.strip()!r}"


def match_answer(expected: str, submission: str, answer_type: str = "string",
                 tolerance: float = 0.0) -> tuple[bool, str]:
    """Dispatch on declared type, then on the structure of the expected answer."""
    expected, submission = str(expected), str(submission)
    if not submission.strip():
        return False, "empty submission"
    if answer_type == "numeric":
        # A composite expected ("0 errors, 2 warnings") is mislabeled numeric in some
        # data; route it structurally so it isn't reduced to a single number.
        if _is_composite(expected):
            return match_composite(expected, submission)
        return match_numeric(expected, submission, tolerance)
    if answer_type in ("int", "integer"):
        return match_int(expected, submission)
    if answer_type in ("bool", "boolean"):
        return match_bool(expected, submission)
    # string (default): structured composite, else plain identifier/phrase.
    if _is_composite(expected):
        return match_composite(expected, submission)
    return match_string(expected, submission)
