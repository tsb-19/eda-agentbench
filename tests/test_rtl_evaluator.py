"""Unit tests for the P1 RTL Debug evaluator (compile / test gating)."""

from pathlib import Path

from eda_agentbench.evaluator.rtl_debug import VCSRTLEvaluator


def _rtl_evaluator():
    meta = {"scoring": {"weights": {"compile": 0.2, "public_test": 0.3,
                                    "hidden_test": 0.4, "explanation": 0.1}}}
    return VCSRTLEvaluator(Path("/nonexistent"), meta)


# --- compile gating (regression) ---

def test_compile_pass_on_clean_output():
    """A non-empty log with no error markers scores 1.0."""
    ev = _rtl_evaluator()
    comp = ev.evaluate_component("compile", Path("/nonexistent"),
                                 "Chronologic VCS simulator\nsimv up to date\n")
    assert comp.raw_score == 1.0


def test_compile_fail_when_tool_did_not_run():
    """Regression: empty / timeout / not-found logs must score 0.0, never 1.0."""
    ev = _rtl_evaluator()
    for bad_log in [
        "",
        "VCS not found in PATH",
        "VCS compilation timed out",
    ]:
        comp = ev.evaluate_component("compile", Path("/nonexistent"), bad_log)
        assert comp.raw_score == 0.0, f"log {bad_log!r} should score 0.0, got {comp.raw_score}"


def test_compile_fail_on_error_line():
    """A leading 'Error' line marks compilation failure."""
    ev = _rtl_evaluator()
    comp = ev.evaluate_component("compile", Path("/nonexistent"),
                                 "Error-[SE] Syntax error\n  design.sv line 4\n")
    assert comp.raw_score == 0.0


# --- test counting (already positive-evidence gated) ---

def test_public_test_requires_results():
    """No PASS:/FAIL: markers -> 0.0 (no false credit)."""
    ev = _rtl_evaluator()
    comp = ev.evaluate_component("public_test", Path("/nonexistent"), "no results here\n")
    assert comp.raw_score == 0.0


def test_public_test_counts_pass_fraction():
    """Score is the pass fraction of PASS:/FAIL: markers."""
    ev = _rtl_evaluator()
    comp = ev.evaluate_component("public_test", Path("/nonexistent"),
                                 "PASS: t1\nPASS: t2\nFAIL: t3\n")
    assert abs(comp.raw_score - 2 / 3) < 1e-9
