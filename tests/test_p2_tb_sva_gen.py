"""Tests for the P2 TB/SVA Generation generator and evaluator."""

import json
from pathlib import Path

import pytest

from generators.p2_tb_sva_gen import P2TBGenerator, DESIGN_TEMPLATES, EXPECTED_TEMPLATE_NAMES
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
    for i in range(20):
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
    paths = gen.generate_batch(20)
    assert len(paths) == 20
    for p in paths:
        assert (p / "metadata.json").is_file()


def test_generator_unique_task_ids(tmp_path):
    """All tasks have unique task IDs."""
    gen = P2TBGenerator(seed=42, output_dir=tmp_path)
    ids = set()
    for i in range(20):
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

    p = gen.generate_one(19)
    meta = json.loads((p / "metadata.json").read_text())
    assert meta["task_id"] == "task_200020"


def test_generator_all_templates_used(tmp_path):
    """20 tasks cover all 5 templates (4 tasks each)."""
    from collections import Counter
    gen = P2TBGenerator(seed=42, output_dir=tmp_path)
    paths = gen.generate_batch(20)
    templates = Counter()
    for p in paths:
        meta = json.loads((p / "metadata.json").read_text())
        templates[meta["generator"]["template"]] += 1
    assert set(templates.keys()) == set(EXPECTED_TEMPLATE_NAMES), f"Templates mismatch: {set(templates.keys())}"
    for t in EXPECTED_TEMPLATE_NAMES:
        assert templates[t] == 4, f"{t}: expected 4, got {templates[t]}"


def test_generator_track_is_p2(tmp_path):
    """All tasks have track=p2_tb_sva_gen."""
    gen = P2TBGenerator(seed=42, output_dir=tmp_path)
    for i in range(20):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        assert meta["track"] == "p2_tb_sva_gen"


def test_generator_tool_is_vcs(tmp_path):
    """All tasks use VCS."""
    gen = P2TBGenerator(seed=42, output_dir=tmp_path)
    for i in range(20):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        assert meta["tool"] == ["vcs"]


def test_generator_golden_differs_from_mutants(tmp_path):
    """Golden design differs from both mutants."""
    gen = P2TBGenerator(seed=42, output_dir=tmp_path)
    for i in range(20):
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
    for i in range(20):
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
    for i in range(20):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        weights = meta["scoring"]["weights"]
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01, f"Task {i}: weights sum to {total}"


# --- Evaluator unit tests ---

def test_evaluator_compile_pass():
    """Evaluator detects successful compilation."""
    from eda_agentbench.evaluator.tb_sva_gen import TBSVAGenEvaluator
    meta = {"scoring": {"weights": {"compile": 0.2, "golden_pass": 0.4, "mutant_1": 0.2, "mutant_2": 0.2}}}
    evaluator = TBSVAGenEvaluator(Path("."), meta)
    log = "Chronologic VCS compiler\nsimv generated\n"
    comp = evaluator.evaluate_component("compile", Path("."), log)
    assert comp.raw_score == 1.0
    assert comp.weighted_score == 0.2


def test_evaluator_compile_fail():
    """Evaluator detects compilation failure."""
    from eda_agentbench.evaluator.tb_sva_gen import TBSVAGenEvaluator
    meta = {"scoring": {"weights": {"compile": 0.2, "golden_pass": 0.4, "mutant_1": 0.2, "mutant_2": 0.2}}}
    evaluator = TBSVAGenEvaluator(Path("."), meta)
    log = "Error-[UNKNOWN_ID] design.sv(5): undefined identifier\n"
    comp = evaluator.evaluate_component("compile", Path("."), log)
    assert comp.raw_score == 0.0
    assert comp.weighted_score == 0.0


def test_evaluator_golden_pass():
    """Evaluator detects golden design passing."""
    from eda_agentbench.evaluator.tb_sva_gen import TBSVAGenEvaluator
    meta = {"scoring": {"weights": {"compile": 0.2, "golden_pass": 0.4, "mutant_1": 0.2, "mutant_2": 0.2}}}
    evaluator = TBSVAGenEvaluator(Path("."), meta)
    log = "ALL_TESTS_PASS: 6/6\n$finish at time 100\n"
    comp = evaluator.evaluate_component("golden_pass", Path("."), log)
    assert comp.raw_score == 1.0
    assert comp.weighted_score == 0.4


def test_evaluator_golden_fail():
    """Evaluator detects golden design failing."""
    from eda_agentbench.evaluator.tb_sva_gen import TBSVAGenEvaluator
    meta = {"scoring": {"weights": {"compile": 0.2, "golden_pass": 0.4, "mutant_1": 0.2, "mutant_2": 0.2}}}
    evaluator = TBSVAGenEvaluator(Path("."), meta)
    log = "FAIL: sel=0 expected y=1, got 0\nTEST_FAIL: 0/6\n"
    comp = evaluator.evaluate_component("golden_pass", Path("."), log)
    assert comp.raw_score == 0.0
    assert comp.weighted_score == 0.0


def test_evaluator_mutant_caught():
    """Evaluator detects that a mutant was caught."""
    from eda_agentbench.evaluator.tb_sva_gen import TBSVAGenEvaluator
    meta = {"scoring": {"weights": {"compile": 0.2, "golden_pass": 0.4, "mutant_1": 0.2, "mutant_2": 0.2}}}
    evaluator = TBSVAGenEvaluator(Path("."), meta)
    log = "FAIL: sel=0 expected y=1, got 0\nTEST_FAIL: 2/6\n"
    comp = evaluator.evaluate_component("mutant_1", Path("."), log)
    assert comp.raw_score == 1.0
    assert comp.weighted_score == 0.2


def test_evaluator_mutant_not_caught():
    """Evaluator detects that a mutant was NOT caught (test passed on buggy design)."""
    from eda_agentbench.evaluator.tb_sva_gen import TBSVAGenEvaluator
    meta = {"scoring": {"weights": {"compile": 0.2, "golden_pass": 0.4, "mutant_1": 0.2, "mutant_2": 0.2}}}
    evaluator = TBSVAGenEvaluator(Path("."), meta)
    log = "ALL_TESTS_PASS: 6/6\n$finish at time 100\n"
    comp = evaluator.evaluate_component("mutant_1", Path("."), log)
    assert comp.raw_score == 0.0
    assert comp.weighted_score == 0.0


def test_evaluator_mutant_caught_by_error():
    """Evaluator detects mutant caught via VCS error."""
    from eda_agentbench.evaluator.tb_sva_gen import TBSVAGenEvaluator
    meta = {"scoring": {"weights": {"compile": 0.2, "golden_pass": 0.4, "mutant_1": 0.2, "mutant_2": 0.2}}}
    evaluator = TBSVAGenEvaluator(Path("."), meta)
    log = "Error-[UNKNOWN_ID] design.sv(5): undefined identifier\n"
    comp = evaluator.evaluate_component("mutant_1", Path("."), log)
    assert comp.raw_score == 1.0


def test_evaluator_mutant_caught_no_output():
    """Evaluator treats empty output as mutant NOT caught."""
    from eda_agentbench.evaluator.tb_sva_gen import TBSVAGenEvaluator
    meta = {"scoring": {"weights": {"compile": 0.2, "golden_pass": 0.4, "mutant_1": 0.2, "mutant_2": 0.2}}}
    evaluator = TBSVAGenEvaluator(Path("."), meta)
    comp = evaluator.evaluate_component("mutant_1", Path("."), "")
    assert comp.raw_score == 0.0


def test_evaluator_full_score_solution(tmp_path):
    """Full evaluation with solution gives score 1.0."""
    from eda_agentbench.evaluator.tb_sva_gen import TBSVAGenEvaluator
    meta = {"scoring": {"weights": {"compile": 0.2, "golden_pass": 0.4, "mutant_1": 0.2, "mutant_2": 0.2}}}
    evaluator = TBSVAGenEvaluator(Path("."), meta)

    golden_log = "=== Golden Design ===\nsimv generated\nALL_TESTS_PASS: 6/6\n$finish\n"
    mutant1_log = "=== Mutant 1 ===\nFAIL: sel=0 expected y=1\nTEST_FAIL: 2/6\n"
    mutant2_log = "=== Mutant 2 ===\nFAIL: output stuck\nTEST_FAIL: 0/6\n"

    compile_score = evaluator.evaluate_component("compile", Path("."), golden_log)
    golden_score = evaluator.evaluate_component("golden_pass", Path("."), golden_log)
    m1_score = evaluator.evaluate_component("mutant_1", Path("."), mutant1_log)
    m2_score = evaluator.evaluate_component("mutant_2", Path("."), mutant2_log)

    total = compile_score.weighted_score + golden_score.weighted_score + m1_score.weighted_score + m2_score.weighted_score
    assert abs(total - 1.0) < 0.01, f"Expected 1.0, got {total}"


def test_evaluator_weak_baseline(tmp_path):
    """Evaluation with empty testbench gives score 0.0."""
    from eda_agentbench.evaluator.tb_sva_gen import TBSVAGenEvaluator
    meta = {"scoring": {"weights": {"compile": 0.2, "golden_pass": 0.4, "mutant_1": 0.2, "mutant_2": 0.2}}}
    evaluator = TBSVAGenEvaluator(Path("."), meta)

    # Empty TB compiles but has no test output
    compile_log = "simv golden generated\n"
    empty_log = "$finish at time 0\n"

    compile_score = evaluator.evaluate_component("compile", Path("."), compile_log)
    golden_score = evaluator.evaluate_component("golden_pass", Path("."), empty_log)
    m1_score = evaluator.evaluate_component("mutant_1", Path("."), empty_log)
    m2_score = evaluator.evaluate_component("mutant_2", Path("."), empty_log)

    total = compile_score.weighted_score + golden_score.weighted_score + m1_score.weighted_score + m2_score.weighted_score
    assert total == 0.2, f"Expected 0.2 (compile only), got {total}"


# --- Template tests ---

def test_all_templates_have_required_fields():
    """All design templates have required fields."""
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
