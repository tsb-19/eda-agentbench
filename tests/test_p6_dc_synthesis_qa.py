"""Tests for P6 DC Synthesis QA: parser, evaluator, generator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eda_agentbench.synthesis.dc_report_parser import parse_dc_report, DCReport
from eda_agentbench.evaluator.dc_synthesis_qa import (
    DCSynthesisQAEvaluator, _parse_numeric, _normalize_string,
)
from generators.p6_dc_synthesis_qa_gen import (
    DCSynthesisQAGenerator, EXPECTED_QUESTION_TYPES, QUESTION_TEMPLATES,
)
from eda_agentbench.schema import validate_metadata


# --- Parser tests ---

SAMPLE_REPORT = """\
============================================================
  Design Compiler Synthesis Report
============================================================

  Top Module:         alu_top
  Clock:              clk_100m

------------------------------------------------------------
  Area Report
------------------------------------------------------------
  Combinational area:  12500.50
  Noncombinational area: 8750.25
  Total cell area:     21250.75

------------------------------------------------------------
  Cell Report
------------------------------------------------------------
  Number of cells:     3500
  Number of registers: 1200

------------------------------------------------------------
  Timing Report
------------------------------------------------------------
  Clock period:        10.0000
  Worst slack:         -0.1500

------------------------------------------------------------
  Compile Status
------------------------------------------------------------
  Compile status:      0 errors, 3 warnings
  Warning count:       3
  Error count:         0

============================================================
"""


def test_parser_extracts_top_module():
    report = parse_dc_report(SAMPLE_REPORT)
    assert report.get_top_module() == "alu_top"


def test_parser_extracts_total_area():
    report = parse_dc_report(SAMPLE_REPORT)
    assert report.get_total_area() == pytest.approx(21250.75, abs=0.01)


def test_parser_extracts_combinational_area():
    report = parse_dc_report(SAMPLE_REPORT)
    assert report.get_combinational_area() == pytest.approx(12500.50, abs=0.01)


def test_parser_extracts_sequential_area():
    report = parse_dc_report(SAMPLE_REPORT)
    assert report.get_sequential_area() == pytest.approx(8750.25, abs=0.01)


def test_parser_extracts_cell_count():
    report = parse_dc_report(SAMPLE_REPORT)
    assert report.get_cell_count() == 3500


def test_parser_extracts_register_count():
    report = parse_dc_report(SAMPLE_REPORT)
    assert report.get_register_count() == 1200


def test_parser_extracts_worst_slack():
    report = parse_dc_report(SAMPLE_REPORT)
    assert report.get_worst_slack() == pytest.approx(-0.15, abs=0.001)


def test_parser_extracts_clock_period():
    report = parse_dc_report(SAMPLE_REPORT)
    assert report.get_clock_period() == pytest.approx(10.0, abs=0.001)


def test_parser_extracts_compile_status():
    report = parse_dc_report(SAMPLE_REPORT)
    assert report.get_compile_status() == "0 errors, 3 warnings"


def test_parser_extracts_warning_count():
    report = parse_dc_report(SAMPLE_REPORT)
    assert report.get_warning_count() == 3


def test_parser_extracts_error_count():
    report = parse_dc_report(SAMPLE_REPORT)
    assert report.get_error_count() == 0


def test_parser_empty_report():
    report = parse_dc_report("")
    assert report.top_module == ""
    assert report.total_area is None
    assert report.cell_count is None


def test_parser_partial_report():
    """Report with only some fields."""
    text = "Top Module: my_design\nTotal cell area: 5000.00\n"
    report = parse_dc_report(text)
    assert report.get_top_module() == "my_design"
    assert report.get_total_area() == pytest.approx(5000.0, abs=0.01)
    assert report.cell_count is None


# --- Evaluator tests ---

def test_evaluator_numeric_tolerance_pass():
    """Numeric answers within tolerance should pass."""
    evaluator = DCSynthesisQAEvaluator.__new__(DCSynthesisQAEvaluator)
    evaluator.answer_config = {"type": "numeric", "expected": "21250.75", "tolerance": 0.01}
    score = evaluator._compare_numeric("21250.00", "21250.75", 0.01)
    assert score == 1.0


def test_evaluator_numeric_tolerance_fail():
    """Numeric answers outside tolerance should fail."""
    evaluator = DCSynthesisQAEvaluator.__new__(DCSynthesisQAEvaluator)
    evaluator.answer_config = {"type": "numeric", "expected": "21250.75", "tolerance": 0.01}
    score = evaluator._compare_numeric("20000.00", "21250.75", 0.01)
    assert score == 0.0


def test_evaluator_numeric_zero():
    """Numeric answer exactly zero should work."""
    evaluator = DCSynthesisQAEvaluator.__new__(DCSynthesisQAEvaluator)
    evaluator.answer_config = {"type": "numeric", "expected": "0.0", "tolerance": 0.01}
    score = evaluator._compare_numeric("0.0001", "0.0", 0.01)
    assert score == 1.0


def test_evaluator_string_exact():
    """String answers should match exactly (normalized)."""
    evaluator = DCSynthesisQAEvaluator.__new__(DCSynthesisQAEvaluator)
    evaluator.answer_config = {"type": "string", "expected": "alu_top", "tolerance": 0.0}
    score = evaluator._compare_string("alu_top", "alu_top")
    assert score == 1.0


def test_evaluator_string_case_insensitive():
    """String answers should be case-insensitive."""
    evaluator = DCSynthesisQAEvaluator.__new__(DCSynthesisQAEvaluator)
    evaluator.answer_config = {"type": "string", "expected": "alu_top", "tolerance": 0.0}
    score = evaluator._compare_string("ALU_TOP", "alu_top")
    assert score == 1.0


def test_evaluator_string_wrong():
    """Wrong string answers should fail."""
    evaluator = DCSynthesisQAEvaluator.__new__(DCSynthesisQAEvaluator)
    evaluator.answer_config = {"type": "string", "expected": "alu_top", "tolerance": 0.0}
    score = evaluator._compare_string("fifo_ctrl", "alu_top")
    assert score == 0.0


def test_evaluator_numeric_parse():
    """_parse_numeric should handle various formats."""
    assert _parse_numeric("21250.75") == 21250.75
    assert _parse_numeric("3500") == 3500.0
    assert _parse_numeric("0") == 0.0
    assert _parse_numeric("  -0.15  ") == -0.15
    assert _parse_numeric("abc") is None


def test_evaluator_string_normalize():
    """_normalize_string should lowercase and strip."""
    assert _normalize_string("  Hello World  ") == "hello world"
    assert _normalize_string("ABC") == "abc"
    assert _normalize_string("  spaces  ") == "spaces"


def test_evaluator_answer_match_integration(tmp_path):
    """Full evaluator integration: correct answer scores 1.0."""
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    meta = {
        "scoring": {"weights": {"answer_match": 1.0}},
        "answer": {"type": "numeric", "expected": "21250.75", "tolerance": 0.01},
    }
    evaluator = DCSynthesisQAEvaluator(task_dir, meta)

    work_dir = tmp_path / "work"
    work_dir.mkdir()
    (work_dir / "answer.txt").write_text("21250.75\n")

    comp = evaluator.evaluate_component("answer_match", work_dir, "")
    assert comp.raw_score == 1.0
    assert comp.weighted_score == 1.0


def test_evaluator_answer_match_wrong(tmp_path):
    """Full evaluator integration: wrong answer scores 0.0."""
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    meta = {
        "scoring": {"weights": {"answer_match": 1.0}},
        "answer": {"type": "numeric", "expected": "21250.75", "tolerance": 0.01},
    }
    evaluator = DCSynthesisQAEvaluator(task_dir, meta)

    work_dir = tmp_path / "work"
    work_dir.mkdir()
    (work_dir / "answer.txt").write_text("99.9999\n")

    comp = evaluator.evaluate_component("answer_match", work_dir, "")
    assert comp.raw_score == 0.0
    assert comp.weighted_score == 0.0


def test_evaluator_no_answer_file(tmp_path):
    """Missing answer.txt should score 0.0."""
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    meta = {
        "scoring": {"weights": {"answer_match": 1.0}},
        "answer": {"type": "numeric", "expected": "21250.75", "tolerance": 0.01},
    }
    evaluator = DCSynthesisQAEvaluator(task_dir, meta)

    work_dir = tmp_path / "work"
    work_dir.mkdir()

    comp = evaluator.evaluate_component("answer_match", work_dir, "")
    assert comp.raw_score == 0.0


def test_evaluator_string_answer_integration(tmp_path):
    """Full evaluator integration: string answer."""
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    meta = {
        "scoring": {"weights": {"answer_match": 1.0}},
        "answer": {"type": "string", "expected": "alu_top", "tolerance": 0.0},
    }
    evaluator = DCSynthesisQAEvaluator(task_dir, meta)

    work_dir = tmp_path / "work"
    work_dir.mkdir()
    (work_dir / "answer.txt").write_text("alu_top\n")

    comp = evaluator.evaluate_component("answer_match", work_dir, "")
    assert comp.raw_score == 1.0


# --- Generator tests ---

def test_generator_deterministic(tmp_path):
    """Same seed produces identical output."""
    gen1 = DCSynthesisQAGenerator(seed=42, output_dir=tmp_path / "a")
    gen2 = DCSynthesisQAGenerator(seed=42, output_dir=tmp_path / "b")
    p1 = gen1.generate_one(0)
    p2 = gen2.generate_one(0)
    meta1 = json.loads((p1 / "metadata.json").read_text())
    meta2 = json.loads((p2 / "metadata.json").read_text())
    assert meta1["task_id"] == meta2["task_id"]
    assert meta1["answer"]["expected"] == meta2["answer"]["expected"]
    assert (p1 / "files" / "synthesis_report.rpt").read_text() == (
        p2 / "files" / "synthesis_report.rpt"
    ).read_text()


def test_generator_metadata_valid(tmp_path):
    """Generated task metadata passes schema validation."""
    gen = DCSynthesisQAGenerator(seed=42, output_dir=tmp_path)
    for i in range(10):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        errors = validate_metadata(meta)
        assert errors == [], f"Task {i} metadata errors: {errors}"


def test_generator_files_exist(tmp_path):
    """All required files are created."""
    gen = DCSynthesisQAGenerator(seed=42, output_dir=tmp_path)
    p = gen.generate_one(0)
    assert (p / "metadata.json").is_file()
    assert (p / "prompt.md").is_file()
    assert (p / "files" / "synthesis_report.rpt").is_file()
    assert (p / "files" / "answer.txt").is_file()
    assert (p / "solution" / "answer.txt").is_file()


def test_generator_answer_matches_parser(tmp_path):
    """Generated answer matches what the parser extracts from the report."""
    gen = DCSynthesisQAGenerator(seed=42, output_dir=tmp_path)
    for i in range(10):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        report_text = (p / "files" / "synthesis_report.rpt").read_text()
        report = parse_dc_report(report_text)
        expected = meta["answer"]["expected"]
        qtype = meta["answer"]["question_type"]

        if qtype == "total_area":
            assert float(expected) == pytest.approx(report.get_total_area(), abs=0.1)
        elif qtype == "combinational_area":
            assert float(expected) == pytest.approx(report.get_combinational_area(), abs=0.1)
        elif qtype == "sequential_area":
            assert float(expected) == pytest.approx(report.get_sequential_area(), abs=0.1)
        elif qtype == "cell_count":
            assert int(float(expected)) == report.get_cell_count()
        elif qtype == "register_count":
            assert int(float(expected)) == report.get_register_count()
        elif qtype == "top_module":
            assert expected == report.get_top_module()
        elif qtype == "worst_slack":
            assert float(expected) == pytest.approx(report.get_worst_slack(), abs=0.01)
        elif qtype == "compile_status":
            assert expected == report.get_compile_status()
        elif qtype == "clock_period":
            assert float(expected) == pytest.approx(report.get_clock_period(), abs=0.01)
        elif qtype == "warning_count":
            assert int(float(expected)) == report.get_warning_count()


def test_generator_question_type_distribution(tmp_path):
    """50 tasks should cover all 10 question types, 5 each."""
    from collections import Counter
    gen = DCSynthesisQAGenerator(seed=42, output_dir=tmp_path)
    types = Counter()
    for i in range(50):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        types[meta["answer"]["question_type"]] += 1
    assert set(types.keys()) == set(EXPECTED_QUESTION_TYPES)
    for qt in EXPECTED_QUESTION_TYPES:
        assert types[qt] == 5, f"{qt}: expected 5, got {types[qt]}"


def test_generator_unique_task_ids(tmp_path):
    """All 50 tasks have unique task IDs."""
    gen = DCSynthesisQAGenerator(seed=42, output_dir=tmp_path)
    ids = set()
    for i in range(50):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        assert meta["task_id"] not in ids, f"Duplicate task_id: {meta['task_id']}"
        ids.add(meta["task_id"])


def test_generator_validate_sample_tasks(tmp_path):
    """Sample generated tasks pass structural validation."""
    from eda_agentbench.task.loader import TaskLoader
    gen = DCSynthesisQAGenerator(seed=42, output_dir=tmp_path)
    paths = gen.generate_batch(3)
    loader = TaskLoader(tmp_path)
    for p in paths:
        meta = loader.load(p)
        assert meta["track"] == "p6_dc_synthesis_qa"


def test_generator_task_count(tmp_path):
    """50 tasks generated, 51 total with smoke."""
    gen = DCSynthesisQAGenerator(seed=42, output_dir=tmp_path)
    paths = gen.generate_batch(50)
    assert len(paths) == 50


# --- Dataset report integration ---

def test_p6_track_in_summary():
    """P6 track appears in dataset summary."""
    from eda_agentbench.cli import _build_dataset_summary
    results = [
        {
            "task_id": "p6_dc_syn_000000", "track": "p6_dc_synthesis_qa",
            "tool": ["dc"], "difficulty": "easy", "status": "pass",
            "total_score": 1.0, "objective_score": 1.0, "explanation_score": 0.0,
        },
    ]
    summary = _build_dataset_summary(results, "test", "solution", None)
    assert "p6_dc_synthesis_qa" in summary["per_track"]
    assert summary["per_track"]["p6_dc_synthesis_qa"]["total"] == 1


def test_p6_question_type_distribution():
    """Question types are correctly distributed."""
    from collections import Counter
    assert len(EXPECTED_QUESTION_TYPES) == 10
    assert len(set(EXPECTED_QUESTION_TYPES)) == 10


# --- Schema validation ---

def test_p6_track_in_schema_enum():
    """p6_dc_synthesis_qa is in the track enum."""
    from eda_agentbench.schema import METADATA_SCHEMA
    track_enum = METADATA_SCHEMA["properties"]["track"]["enum"]
    assert "p6_dc_synthesis_qa" in track_enum


def test_p6_task_id_pattern():
    """p6_dc_syn_NNNNNN matches the task_id regex."""
    import re
    from eda_agentbench.schema import METADATA_SCHEMA
    pattern = METADATA_SCHEMA["properties"]["task_id"]["pattern"]
    assert re.match(pattern, "p6_dc_syn_000000")
    assert re.match(pattern, "p6_dc_syn_999999")
    assert not re.match(pattern, "p6_dc_syn_00000")  # too few digits
    assert not re.match(pattern, "p6_dc_syn_0000000")  # too many digits
