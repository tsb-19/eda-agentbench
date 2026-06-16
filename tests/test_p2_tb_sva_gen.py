"""Tests for the P2 TB/SVA Generation generator and evaluator."""

import json
from pathlib import Path

import pytest

from generators.p2_tb_sva_gen import P2TBGenerator, DESIGN_TEMPLATES, EXPECTED_TEMPLATE_NAMES, GENERATED_TASK_COUNT
from eda_agentbench.schema import validate_metadata


# --- Generator tests ---

def test_generator_deterministic(tmp_path):
    """Same seed produces identical output."""
    gen1 = P2TBGenerator(seed=42, output_dir=tmp_path / "a")
    gen2 = P2TBGenerator(seed=42, output_dir=tmp_path / "b")
    p1 = gen1.generate_one(0)
    p2 = gen2.generate_one(0)
    meta1 = json.loads((p1 / "metadata.json").read_text())
    meta2 = json.loads((p2 / "metadata.json").read_text())
    assert meta1["task_id"] == meta2["task_id"]
    assert meta1["generator"]["template"] == meta2["generator"]["template"]
    assert meta1["generator"]["mutant_name"] == meta2["generator"]["mutant_name"]
    assert (p1 / "files" / "design_golden.sv").read_text() == (p2 / "files" / "design_golden.sv").read_text()
    assert (p1 / "solution" / "tb.sv").read_text() == (p2 / "solution" / "tb.sv").read_text()


def test_generator_metadata_valid(tmp_path):
    """Generated task metadata passes schema validation."""
    gen = P2TBGenerator(seed=42, output_dir=tmp_path)
    for i in range(GENERATED_TASK_COUNT):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        errors = validate_metadata(meta)
        assert errors == [], f"Task {i} metadata errors: {errors}"


def test_generator_files_exist(tmp_path):
    """All required files are created."""
    gen = P2TBGenerator(seed=42, output_dir=tmp_path)
    p = gen.generate_one(0)
    assert (p / "metadata.json").is_file()
    assert (p / "prompt.md").is_file()
    assert (p / "files" / "design_golden.sv").is_file()
    assert (p / "files" / "run_public.sh").is_file()
    assert (p / "hidden" / "design_mutant1.sv").is_file()
    assert (p / "hidden" / "design_mutant2.sv").is_file()
    assert (p / "hidden" / "run_hidden.sh").is_file()
    assert (p / "solution" / "tb.sv").is_file()


def test_generator_batch_creates_count(tmp_path):
    """generate_batch creates the requested number of tasks."""
    gen = P2TBGenerator(seed=42, output_dir=tmp_path)
    paths = gen.generate_batch(GENERATED_TASK_COUNT)
    assert len(paths) == GENERATED_TASK_COUNT
    for p in paths:
        assert (p / "metadata.json").is_file()


def test_generator_unique_task_ids(tmp_path):
    """All tasks have unique task IDs."""
    gen = P2TBGenerator(seed=42, output_dir=tmp_path)
    ids = set()
    for i in range(GENERATED_TASK_COUNT):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        assert meta["task_id"] not in ids, f"Duplicate task_id: {meta['task_id']}"
        ids.add(meta["task_id"])


def test_generator_task_id_format(tmp_path):
    """Task IDs start at 200001 and follow correct format."""
    gen = P2TBGenerator(seed=42, output_dir=tmp_path)
    p = gen.generate_one(0)
    meta = json.loads((p / "metadata.json").read_text())
    assert meta["task_id"] == "task_200001"

    p = gen.generate_one(GENERATED_TASK_COUNT - 1)
    meta = json.loads((p / "metadata.json").read_text())
    assert meta["task_id"] == f"task_{200001 + GENERATED_TASK_COUNT - 1:06d}"


def test_generator_all_templates_used(tmp_path):
    """All 10 templates are used in the generated batch."""
    from collections import Counter
    gen = P2TBGenerator(seed=42, output_dir=tmp_path)
    paths = gen.generate_batch(GENERATED_TASK_COUNT)
    templates = Counter()
    for p in paths:
        meta = json.loads((p / "metadata.json").read_text())
        templates[meta["generator"]["template"]] += 1
    assert set(templates.keys()) == set(EXPECTED_TEMPLATE_NAMES), f"Templates mismatch: {set(templates.keys())}"
    for t in EXPECTED_TEMPLATE_NAMES:
        assert templates[t] >= 8, f"{t}: expected >=8, got {templates[t]}"


def test_generator_track_is_p2(tmp_path):
    """All tasks have track=p2_tb_sva_gen."""
    gen = P2TBGenerator(seed=42, output_dir=tmp_path)
    for i in range(GENERATED_TASK_COUNT):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        assert meta["track"] == "p2_tb_sva_gen"


def test_generator_tool_is_vcs(tmp_path):
    """All tasks use VCS."""
    gen = P2TBGenerator(seed=42, output_dir=tmp_path)
    for i in range(GENERATED_TASK_COUNT):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        assert meta["tool"] == ["vcs"]


def test_generator_golden_differs_from_mutants(tmp_path):
    """Golden design differs from both mutants."""
    gen = P2TBGenerator(seed=42, output_dir=tmp_path)
    for i in range(GENERATED_TASK_COUNT):
        p = gen.generate_one(i)
        golden = (p / "files" / "design_golden.sv").read_text()
        mutant1 = (p / "hidden" / "design_mutant1.sv").read_text()
        mutant2 = (p / "hidden" / "design_mutant2.sv").read_text()
        assert golden != mutant1, f"Task {i}: golden == mutant1"
        assert golden != mutant2, f"Task {i}: golden == mutant2"
        assert mutant1 != mutant2, f"Task {i}: mutant1 == mutant2"


def test_generator_mutant_metadata(tmp_path):
    """Each task records mutant info in generator metadata."""
    gen = P2TBGenerator(seed=42, output_dir=tmp_path)
    for i in range(GENERATED_TASK_COUNT):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        g = meta["generator"]
        assert "template" in g
        assert "mutant_name" in g
        assert "mutant2_name" in g
        assert g["template"] in EXPECTED_TEMPLATE_NAMES


def test_generator_validate_sample_tasks(tmp_path):
    """Sample generated tasks pass structural validation."""
    from eda_agentbench.task.loader import TaskLoader
    gen = P2TBGenerator(seed=42, output_dir=tmp_path)
    loader = TaskLoader(tmp_path)
    paths = gen.generate_batch(5)
    for p in paths:
        meta = loader.load(p)  # raises on failure
        assert meta["track"] == "p2_tb_sva_gen"


def test_generator_scoring_weights_sum(tmp_path):
    """Scoring weights sum to 1.0."""
    gen = P2TBGenerator(seed=42, output_dir=tmp_path)
    for i in range(GENERATED_TASK_COUNT):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        weights = meta["scoring"]["weights"]
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01, f"Task {i}: weights sum to {total}"


# --- Evaluator unit tests ---

WEIGHTS = {"compile": 0.1, "golden_pass": 0.2, "mutant_1": 0.35, "mutant_2": 0.35}


def _ev():
    from eda_agentbench.evaluator.tb_sva_gen import TBSVAGenEvaluator
    return TBSVAGenEvaluator(Path("."), {"scoring": {"weights": WEIGHTS}})


# Realistic VCS run fragments: boilerplate (banner/timestamp/binary name/report) plus
# the testbench's own $display behavioral lines. Normalization must keep only the latter.
_GOLDEN_RUN = """\
=== Golden Design ===
1 module and 0 UDP read.
../simv_golden up to date
Chronologic VCS simulator copyright 1991-2021
Compiler version S-2021.09; Runtime version S-2021.09;  Jun 16 12:44 2026
CHECK: data_out=a5 valid=1 ready=0
ALL_TESTS_PASS: 5/5
$finish at simulation time                  125
           V C S   S i m u l a t i o n   R e p o r t
CPU Time:      0.300 seconds;       Data structure size:   0.0Mb
Tue Jun 16 12:44:52 2026
"""

_MUTANT_DIFF_RUN = """\
=== Mutant 1 ===
../simv_mutant1 up to date
Chronologic VCS simulator copyright 1991-2021
Compiler version S-2021.09; Runtime version S-2021.09;  Jun 16 12:45 2026
CHECK: data_out=00 valid=0 ready=1
FAIL: capture expected a5
$finish at simulation time                  125
CPU Time:      0.310 seconds;       Data structure size:   0.0Mb
Tue Jun 16 12:45:01 2026
"""

# Same behavioral output as golden (only boilerplate differs) -> NOT caught.
_MUTANT_SAME_RUN = """\
=== Mutant 2 ===
../simv_mutant2 up to date
Chronologic VCS simulator copyright 1991-2021
Compiler version S-2021.09; Runtime version S-2021.09;  Jun 16 12:46 2026
CHECK: data_out=a5 valid=1 ready=0
ALL_TESTS_PASS: 5/5
$finish at simulation time                  125
CPU Time:      0.290 seconds;       Data structure size:   0.0Mb
Tue Jun 16 12:46:10 2026
"""


def _packed(golden, mutant):
    from eda_agentbench.evaluator.tb_sva_gen import _GOLDEN_MUTANT_SEP
    return golden + "\n" + _GOLDEN_MUTANT_SEP + "\n" + mutant


def test_normalize_strips_boilerplate_keeps_behavior():
    from eda_agentbench.evaluator.tb_sva_gen import _normalize_transcript
    norm = _normalize_transcript(_GOLDEN_RUN)
    assert norm == ["CHECK: data_out=a5 valid=1 ready=0", "ALL_TESTS_PASS: 5/5"]
    # No banner/timestamp/binary-name/report lines survive.
    joined = "\n".join(norm)
    for vol in ["VCS", "simv", "CPU Time", "$finish", "Jun", "==="]:
        assert vol not in joined


def test_normalize_empty_for_do_nothing_tb():
    from eda_agentbench.evaluator.tb_sva_gen import _normalize_transcript
    stub = "=== Golden Design ===\n../simv_golden up to date\n$finish at simulation time 0\n"
    assert _normalize_transcript(stub) == []


def test_evaluator_compile_pass():
    log = "Chronologic VCS compiler\nsimv generated\n"
    comp = _ev().evaluate_component("compile", Path("."), log)
    assert comp.raw_score == 1.0
    assert abs(comp.weighted_score - 0.1) < 1e-9


def test_evaluator_compile_fail():
    log = "Error-[UNKNOWN_ID] design.sv(5): undefined identifier\n"
    comp = _ev().evaluate_component("compile", Path("."), log)
    assert comp.raw_score == 0.0


def test_evaluator_compile_fail_when_tool_did_not_run():
    """Regression: empty / not-found / timeout logs must score 0.0, never 1.0."""
    for bad_log in ["", "vcs: command not found\n", "Script run_public.sh timed out\n"]:
        comp = _ev().evaluate_component("compile", Path("."), bad_log)
        assert comp.raw_score == 0.0, f"log {bad_log!r} should score 0.0"


def test_golden_runs_clean_passes():
    """golden_pass is a precondition: tb runs to completion on golden, no self-verdict."""
    comp = _ev().evaluate_component("golden_pass", Path("."), _GOLDEN_RUN)
    assert comp.raw_score == 1.0
    assert abs(comp.weighted_score - 0.2) < 1e-9


def test_golden_fails_on_compile_error_or_no_output():
    ev = _ev()
    assert ev.evaluate_component("golden_pass", Path("."), "").raw_score == 0.0
    err = "Error-[SE] design_golden.sv(3): syntax error\n"
    assert ev.evaluate_component("golden_pass", Path("."), err).raw_score == 0.0
    crash = "../simv_golden\nSegmentation fault (core dumped)\n"
    assert ev.evaluate_component("golden_pass", Path("."), crash).raw_score == 0.0


def test_golden_pass_does_not_read_self_verdict():
    """A tb that prints TEST_FAIL on the golden but still runs cleanly is NOT
    failed here (the old token-based check is gone); discrimination is what counts."""
    log = _GOLDEN_RUN.replace("ALL_TESTS_PASS: 5/5", "TEST_FAIL: something")
    assert _ev().evaluate_component("golden_pass", Path("."), log).raw_score == 1.0


def test_mutant_caught_when_behavior_differs():
    comp = _ev().evaluate_component("mutant_1", Path("."), _packed(_GOLDEN_RUN, _MUTANT_DIFF_RUN))
    assert comp.raw_score == 1.0
    assert abs(comp.weighted_score - 0.35) < 1e-9


def test_mutant_not_caught_when_behavior_identical():
    comp = _ev().evaluate_component("mutant_2", Path("."), _packed(_GOLDEN_RUN, _MUTANT_SAME_RUN))
    assert comp.raw_score == 0.0


def test_mutant_caught_by_compile_error():
    """A mutant the tb fails to compile/run against still differs from the golden
    baseline -> distinguished -> caught."""
    mutant_err = "=== Mutant 1 ===\nError-[SE] design_mutant1.sv(4): syntax error\n"
    comp = _ev().evaluate_component("mutant_1", Path("."), _packed(_GOLDEN_RUN, mutant_err))
    assert comp.raw_score == 1.0


def test_mutant_no_baseline_scores_zero():
    """Missing the golden separator (no baseline) cannot be judged -> 0.0."""
    comp = _ev().evaluate_component("mutant_1", Path("."), "some log without separator")
    assert comp.raw_score == 0.0


def test_full_score_solution():
    """A discriminating testbench: compiles, runs clean on golden, catches both."""
    ev = _ev()
    total = (
        ev.evaluate_component("compile", Path("."), _GOLDEN_RUN).weighted_score
        + ev.evaluate_component("golden_pass", Path("."), _GOLDEN_RUN).weighted_score
        + ev.evaluate_component("mutant_1", Path("."), _packed(_GOLDEN_RUN, _MUTANT_DIFF_RUN)).weighted_score
        + ev.evaluate_component("mutant_2", Path("."), _packed(_GOLDEN_RUN, _MUTANT_DIFF_RUN)).weighted_score
    )
    assert abs(total - 1.0) < 1e-9


def test_weak_baseline_do_nothing_tb():
    """A tb that compiles and runs on golden but catches nothing scores only the
    precondition weight (0.1 compile + 0.2 golden = 0.3), well under the 0.5 pass
    line and the 0.9 reliability gate."""
    ev = _ev()
    stub_golden = "=== Golden Design ===\n../simv_golden up to date\nsimv generated\n$finish at simulation time 0\n"
    stub_mutant = "=== Mutant 1 ===\n../simv_mutant1 up to date\n$finish at simulation time 0\n"
    total = (
        ev.evaluate_component("compile", Path("."), stub_golden).weighted_score
        + ev.evaluate_component("golden_pass", Path("."), stub_golden).weighted_score
        + ev.evaluate_component("mutant_1", Path("."), _packed(stub_golden, stub_mutant)).weighted_score
        + ev.evaluate_component("mutant_2", Path("."), _packed(stub_golden, stub_mutant)).weighted_score
    )
    assert abs(total - 0.3) < 1e-9, f"expected 0.3, got {total}"


# --- Template tests ---

def test_all_templates_have_required_fields():
    """All 10 design templates have required fields."""
    for template_fn in DESIGN_TEMPLATES:
        t = template_fn()
        assert "name" in t
        assert "difficulty" in t
        assert "module_name" in t
        assert "golden" in t
        assert "mutants" in t
        assert "solution_tb" in t
        assert "ports" in t
        assert "description" in t
        assert len(t["mutants"]) == 2
        for m in t["mutants"]:
            assert "name" in m
            assert "code" in m
            assert "bug_description" in m


def test_template_golden_differs_from_mutants():
    """All templates have golden != mutant code."""
    for template_fn in DESIGN_TEMPLATES:
        t = template_fn()
        for m in t["mutants"]:
            assert t["golden"] != m["code"], f"{t['name']}: golden == mutant {m['name']}"


def test_template_solution_tb_has_markers():
    """All solution testbenches have ALL_TESTS_PASS marker."""
    for template_fn in DESIGN_TEMPLATES:
        t = template_fn()
        assert "ALL_TESTS_PASS" in t["solution_tb"], f"{t['name']}: missing ALL_TESTS_PASS"
        assert "TEST_FAIL" in t["solution_tb"], f"{t['name']}: missing TEST_FAIL"
        assert "$finish" in t["solution_tb"], f"{t['name']}: missing $finish"


# --- CLI log section extraction test ---

def test_extract_p2_log_sections():
    """Log section extraction works correctly."""
    from eda_agentbench.cli import _extract_p2_log_sections
    log = """\
=== Mutant 1 ===
FAIL: sel=0 expected y=1
TEST_FAIL: 2/6
=== Mutant 2 ===
FAIL: output stuck
TEST_FAIL: 0/6
"""
    sections = _extract_p2_log_sections(log)
    assert "mutant_1" in sections
    assert "mutant_2" in sections
    assert "FAIL: sel=0" in sections["mutant_1"]
    assert "FAIL: output stuck" in sections["mutant_2"]
    assert "mutant_1" not in sections["mutant_2"]


def test_extract_p2_log_sections_empty():
    """Empty log produces empty sections."""
    from eda_agentbench.cli import _extract_p2_log_sections
    sections = _extract_p2_log_sections("")
    assert sections == {}
