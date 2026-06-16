"""Tests for the robust QA answer matcher.

Two invariants matter: (1) correct VALUES wrapped in units/markdown/labels/prose must
PASS (fairness — don't measure format obedience); (2) wrong values must FAIL (protects
the solution>=0.9 / buggy<0.9 reliability gate). The adversarial cases guard (2).
"""

from __future__ import annotations

from eda_agentbench.evaluator import answer_match as am


# --- numeric: correct value, decorated forms must PASS ---------------------- #
def test_numeric_decorated_forms_pass():
    for s in ["-6.6087", "-6.6087 ns", "TNS = -6.6087", "**-6.6087**",
              "-6.6087.", " -6.6087 \n", "The TNS is -6.6087 ns.", "`-6.6087`"]:
        ok, detail = am.match_answer("-6.6087", s, "numeric", 0.0)
        assert ok, f"should PASS: {s!r} ({detail})"


def test_numeric_wrong_value_fails():
    for s in ["-6.61", "-6.7", "6.6087", "0", "-66.087"]:
        ok, _ = am.match_answer("-6.6087", s, "numeric", 0.0)
        assert not ok, f"should FAIL: {s!r}"


def test_numeric_relative_tolerance():
    # 1% tolerance band around 88409.51
    assert am.match_answer("88409.51", "88410", "numeric", 0.01)[0]
    assert am.match_answer("88409.51", "88409.51 um^2", "numeric", 0.01)[0]
    assert not am.match_answer("88409.51", "90000", "numeric", 0.01)[0]


def test_numeric_exact_counts():
    assert am.match_answer("12", "12 paths", "numeric", 0.0)[0]
    assert am.match_answer("12", "12.0", "numeric", 0.0)[0]
    assert not am.match_answer("12", "13", "numeric", 0.0)[0]


def test_numeric_thousands_separator():
    assert am.match_answer("27520", "27,520", "numeric", 0.0)[0]


def test_numeric_near_zero():
    assert am.match_answer("-0.0256", "-0.0256", "numeric", 0.01)[0]
    assert not am.match_answer("-0.0256", "0.5", "numeric", 0.01)[0]


def test_numeric_multiple_numbers_takes_last():
    # A reasoning-style answer that restates then concludes.
    ok, _ = am.match_answer("5", "There are 3 setup and 2 hold paths, total 5.", "numeric", 0.0)
    assert ok


# --- composite ("0 errors, 2 warnings") ------------------------------------- #
def test_composite_phrasing_variation_passes():
    for s in ["0 errors, 2 warnings", "0 errors and 2 warnings",
              "0 errors, 2 warnings.", "**0 errors, 2 warnings**"]:
        ok, detail = am.match_answer("0 errors, 2 warnings", s, "string", 0.0)
        assert ok, f"should PASS: {s!r} ({detail})"


def test_composite_wrong_numbers_fail():
    for s in ["2 errors, 0 warnings", "0 errors, 3 warnings", "1 error, 2 warnings"]:
        ok, _ = am.match_answer("0 errors, 2 warnings", s, "string", 0.0)
        assert not ok, f"should FAIL: {s!r}"


def test_composite_missing_keyword_fails():
    ok, _ = am.match_answer("0 errors, 2 warnings", "0 and 2", "string", 0.0)
    assert not ok


# --- string identifiers ----------------------------------------------------- #
def test_string_decorated_identifier_passes():
    for s in ["clk_main", "CLK_MAIN", "`clk_main`", "clk_main.", '"clk_main"', " clk_main\n"]:
        ok, detail = am.match_answer("clk_main", s, "string", 0.0)
        assert ok, f"should PASS: {s!r} ({detail})"


def test_string_wrong_identifier_fails():
    # Guards against over-lenient containment: a different but related name must fail.
    for s in ["clk", "clk_main_2", "clk_aux", "the clock is clk_main"]:
        ok, _ = am.match_answer("clk_main", s, "string", 0.0)
        assert not ok, f"should FAIL: {s!r}"


def test_path_group_names():
    assert am.match_answer("reg2reg", "reg2reg", "string", 0.0)[0]
    assert not am.match_answer("reg2reg", "in2reg", "string", 0.0)[0]


# --- int / bool (P8) -------------------------------------------------------- #
def test_int_with_commas_and_units():
    assert am.match_answer("356976", "356,976", "int", 0.0)[0]
    assert am.match_answer("356976", "356976 instances", "int", 0.0)[0]
    assert not am.match_answer("356976", "356977", "int", 0.0)[0]


def test_bool_synonyms():
    assert am.match_answer("true", "yes", "bool", 0.0)[0]
    assert am.match_answer("false", "violated", "bool", 0.0)[0]
    assert not am.match_answer("true", "no", "bool", 0.0)[0]


def test_empty_submission_fails():
    assert not am.match_answer("5", "", "numeric", 0.0)[0]
    assert not am.match_answer("clk", "   ", "string", 0.0)[0]
