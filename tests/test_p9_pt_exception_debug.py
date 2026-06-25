"""Tests for P9 PrimeTime Exception Debug: generator invariants + evaluator parsing.

Tool-free unit tests run everywhere; the real-PrimeTime integration test is marked
`requires_tools` (skipped unless the b04 shim is on PATH).
"""

from __future__ import annotations

import json

import pytest

from generators.p9_pt_exception_debug_gen import P9PrimeTimeExceptionDebugGenerator
from eda_agentbench.task.loader import structural_validate
from eda_agentbench.evaluator.pt_exception_debug import PTExceptionDebugEvaluator


@pytest.fixture
def gen_task(tmp_path):
    """Generate one P9 task into tmp; return (task_dir, meta)."""
    gen = P9PrimeTimeExceptionDebugGenerator(seed=7, output_dir=tmp_path, id_start=1)
    d = gen.generate_one(0)
    meta = json.loads((d / "metadata.json").read_text())
    return d, meta


# --- Generator structure ---------------------------------------------------

def test_structurally_valid(gen_task):
    d, _ = gen_task
    assert structural_validate(d) == []


def test_required_files_present(gen_task):
    d, _ = gen_task
    for rel in ["files/design_netlist.v", "files/tiny.lib", "files/tiny.db",
                "files/constraints.sdc", "files/run_public.sh", "files/run_public.tcl",
                "hidden/run_hidden.sh", "hidden/run_hidden.tcl", "hidden/run_grade.tcl",
                "solution/constraints.sdc"]:
        assert (d / rel).is_file(), f"missing {rel}"


def test_golden_has_multicycle_buggy_does_not(gen_task):
    d, _ = gen_task
    golden = (d / "solution" / "constraints.sdc").read_text()
    buggy = (d / "files" / "constraints.sdc").read_text()
    assert "set_multicycle_path" in golden
    assert "set_multicycle_path" not in buggy
    # buggy must NOT already silence the violation with a false_path either
    assert "set_false_path" not in buggy


@pytest.fixture
def gen_task_a(tmp_path):
    """Generate a Category-A task (odd task_index) into tmp; return (task_dir, meta)."""
    gen = P9PrimeTimeExceptionDebugGenerator(seed=7, output_dir=tmp_path, id_start=1)
    d = gen.generate_one(1)
    meta = json.loads((d / "metadata.json").read_text())
    return d, meta


def test_category_a_structure(gen_task_a):
    d, meta = gen_task_a
    assert meta["generator"]["category"] == "A"
    assert meta["expected_error_category"] == "overbroad_false_path"
    assert structural_validate(d) == []


def test_category_a_golden_scoped_buggy_overbroad(gen_task_a):
    """Golden scopes the false_path with -to (config sink only); buggy omits -to (over-broad)."""
    d, _ = gen_task_a
    golden = (d / "solution" / "constraints.sdc").read_text()
    buggy = (d / "files" / "constraints.sdc").read_text()
    assert "set_false_path" in golden and "-to [get_pins" in golden
    assert "set_false_path -from [get_pins" in buggy and "-to" not in buggy


def test_category_a_grader_has_exclude_check(gen_task_a):
    d, _ = gen_task_a
    grade = (d / "hidden" / "run_grade.tcl").read_text()
    assert "exclude" in grade and "meet" in grade


def test_slack_invariant_holds_across_batch(tmp_path):
    """Category B must VIOLATE at 1 cycle and MEET at the multicycle count; Category A's
    quasi-static path must VIOLATE if timed (so excluding it matters) while the datapath
    path MEETS. Also confirm the batch contains BOTH categories."""
    gen = P9PrimeTimeExceptionDebugGenerator(seed=42, output_dir=tmp_path, id_start=1)
    cats = set()
    for i in range(12):
        d = gen.generate_one(i)
        g = json.loads((d / "metadata.json").read_text())["generator"]
        cats.add(g["category"])
        if g["category"] == "B":
            assert g["expected_slack_1cyc"] < 0, f"task {i}: 1-cycle slack not a violation"
            assert g["expected_slack_ncyc"] >= 0, f"task {i}: multicycle slack does not meet"
        else:
            assert g["expected_qs_slack_if_timed"] < 0, f"task {i}: qs path wouldn't violate if timed"
            assert g["expected_dp_slack"] >= 0, f"task {i}: datapath path does not meet"
    assert cats == {"A", "B"}, f"batch should contain both categories, got {cats}"


def test_prompt_does_not_name_the_fix(gen_task, gen_task_a):
    # The prompt states design INTENT/behaviour, never the SDC command (no answer-naming),
    # for BOTH categories.
    for d, _ in (gen_task, gen_task_a):
        prompt = (d / "prompt.md").read_text().lower()
        assert "set_multicycle_path" not in prompt
        assert "set_false_path" not in prompt


# --- Evaluator marker parsing (no PrimeTime) -------------------------------

def test_eval_exception_score_parsed(gen_task):
    d, meta = gen_task
    ev = PTExceptionDebugEvaluator(d, meta)
    for log, want in [("EXC_EXEC_OK\nEXC_SCORE: 1.000\n", 1.0),
                      ("EXC_EXEC_OK\nEXC_SCORE: 0.500\n", 0.5),
                      ("EXC_EXEC_OK\nEXC_SCORE: 0.000\n", 0.0)]:
        c = ev.evaluate_component("exception_check", d, log)
        assert c.raw_score == want, f"{log!r} -> {c.raw_score}"


def test_eval_ignores_injected_prefixed_marker(gen_task):
    """An agent-injected EXC_SCORE in the apply phase is prefixed '[apply] ' and must
    NOT match the ^-anchored marker; only the laundered grade score counts."""
    d, meta = gen_task
    ev = PTExceptionDebugEvaluator(d, meta)
    log = "[apply] EXC_SCORE: 1.000\nEXC_EXEC_OK\nEXC_SCORE: 0.000\n"
    c = ev.evaluate_component("exception_check", d, log)
    assert c.raw_score == 0.0


def test_eval_execution_pass(gen_task):
    d, meta = gen_task
    ev = PTExceptionDebugEvaluator(d, meta)
    assert ev.evaluate_component("execution_pass", d, "EXC_EXEC_OK\n").raw_score == 1.0
    assert ev.evaluate_component("execution_pass", d, "EXC_EXEC_FAIL: no_applied_sdc\n").raw_score == 0.0
    assert ev.evaluate_component("execution_pass", d, "Segmentation fault\n").raw_score == 0.0


def test_eval_no_score_marker_is_zero(gen_task):
    d, meta = gen_task
    ev = PTExceptionDebugEvaluator(d, meta)
    assert ev.evaluate_component("exception_check", d, "some unrelated output\n").raw_score == 0.0


def test_eval_explanation_decorative_in_submission(gen_task):
    d, meta = gen_task
    ev = PTExceptionDebugEvaluator(d, meta)
    assert ev.evaluate_component("explanation", d, "", mode="submission").raw_score == 1.0


# --- Real PrimeTime integration (requires the b04 shim) --------------------

@pytest.mark.requires_tools
def test_golden_scores_high_buggy_low(gen_task):
    """Golden constraints score ~1.0 and the seeded-buggy file scores lower, through the
    real two-session run_hidden grader. Requires pt_shell (b04 shim) on PATH."""
    from eda_agentbench.cli import _evaluate_single
    d, meta = gen_task
    _, sr_g = _evaluate_single(d, d / "solution", meta, 300)
    _, sr_b = _evaluate_single(d, d / "files", meta, 300)
    assert sr_g.total_score >= 0.9, f"golden {sr_g.total_score}"
    assert sr_g.total_score - sr_b.total_score >= 0.15, f"margin {sr_g.total_score - sr_b.total_score}"
