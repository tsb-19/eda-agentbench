"""Tests for P3 Timing Report QA: parser, evaluator, generator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eda_agentbench.timing.report_parser import parse_timing_report, normalize_answer
from eda_agentbench.evaluator.timing_report_qa import TimingReportQAEvaluator
from eda_agentbench.evaluator.answer_match import match_answer
from generators.p3_timing_report_qa_gen import (
    P3TimingReportQAGenerator, EXPECTED_QUESTION_TYPES, QUESTION_TEMPLATES,
)
from eda_agentbench.schema import validate_metadata


# --- Parser tests ---

SAMPLE_REPORT = """\
**** Report : timing
    -path_type full
    -delay_type max
    -max_paths 3

wns: -0.2500
tns: -0.8500
violating_path_count: 3

Startpoint: u_core/alu_out
Endpoint: u_top/pipeline_reg
Path Group: clk_core
Clock: clk_core
----------------------------------------
Slack:                    -0.2500
Arrival Time:              3.2500
Required Time:             3.0000
Data Type: setup

Startpoint: u_io/spi_miso
Endpoint: u_core/fifo_din
Path Group: clk_io
Clock: clk_io
----------------------------------------
Slack:                    -0.2000
Arrival Time:              2.7000
Required Time:             2.5000
Data Type: setup

Startpoint: u_mem/cache_addr
Endpoint: u_core/decoder_in
Path Group: clk_core
Clock: clk_core
----------------------------------------
Slack:                    -0.1800
Arrival Time:              3.1800
Required Time:             3.0000
Data Type: setup
"""


def test_parser_extracts_wns():
    report = parse_timing_report(SAMPLE_REPORT)
    assert report.get_wns() == pytest.approx(-0.25, abs=0.001)


def test_parser_extracts_tns():
    report = parse_timing_report(SAMPLE_REPORT)
    # TNS from summary line is -0.8500; parser prefers summary when available
    assert report.get_tns() == pytest.approx(-0.85, abs=0.001)


def test_parser_extracts_violating_count():
    report = parse_timing_report(SAMPLE_REPORT)
    assert report.get_violating_count() == 3


def test_parser_extracts_paths():
    report = parse_timing_report(SAMPLE_REPORT)
    assert len(report.paths) == 3


def test_parser_extracts_slack():
    report = parse_timing_report(SAMPLE_REPORT)
    assert report.paths[0].slack == pytest.approx(-0.25, abs=0.001)
    assert report.paths[1].slack == pytest.approx(-0.20, abs=0.001)
    assert report.paths[2].slack == pytest.approx(-0.18, abs=0.001)


def test_parser_extracts_path_fields():
    report = parse_timing_report(SAMPLE_REPORT)
    p = report.paths[0]
    assert p.startpoint == "u_core/alu_out"
    assert p.endpoint == "u_top/pipeline_reg"
    assert p.path_group == "clk_core"
    assert p.clock == "clk_core"
    assert p.arrival_time == pytest.approx(3.25, abs=0.001)
    assert p.required_time == pytest.approx(3.00, abs=0.001)
    assert p.data_type == "setup"


def test_parser_worst_path():
    report = parse_timing_report(SAMPLE_REPORT)
    worst = report.get_worst_path()
    assert worst is not None
    assert worst.slack == pytest.approx(-0.25, abs=0.001)
    assert worst.endpoint == "u_top/pipeline_reg"


def test_parser_path_by_endpoint():
    report = parse_timing_report(SAMPLE_REPORT)
    p = report.get_path_by_endpoint("u_core/fifo_din")
    assert p is not None
    assert p.slack == pytest.approx(-0.20, abs=0.001)


def test_parser_empty_report():
    report = parse_timing_report("")
    assert report.paths == []
    assert report.get_wns() is None
    assert report.get_tns() is None


def test_parser_summary_only():
    """Report with summary lines but no detailed paths."""
    text = "wns: -0.5000\ntns: -1.2000\nviolating_path_count: 5\n"
    report = parse_timing_report(text)
    assert report.wns == pytest.approx(-0.5, abs=0.001)
    assert report.tns == pytest.approx(-1.2, abs=0.001)
    assert report.violating_count == 5


# --- Evaluator answer-matching tests (routed through the shared matcher;
# exhaustive form/adversarial coverage lives in tests/test_answer_match.py) ---

def test_evaluator_numeric_tolerance_pass():
    assert match_answer("-0.2500", "-0.2510", "numeric", 0.01)[0]


def test_evaluator_numeric_tolerance_fail():
    assert not match_answer("-0.2500", "-0.3000", "numeric", 0.01)[0]


def test_evaluator_numeric_zero():
    assert match_answer("0.0", "0.0001", "numeric", 0.01)[0]


def test_evaluator_string_exact():
    assert match_answer("u_top/pipeline_reg", "u_top/pipeline_reg", "string", 0.0)[0]


def test_evaluator_string_case_insensitive():
    assert match_answer("u_top/pipeline_reg", "U_TOP/PIPELINE_REG", "string", 0.0)[0]


def test_evaluator_string_wrong():
    assert not match_answer("u_top/pipeline_reg", "u_core/alu_out", "string", 0.0)[0]


def test_evaluator_answer_match_integration(tmp_path):
    """Full evaluator integration: correct answer scores 1.0."""
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    meta = {
        "scoring": {"weights": {"answer_match": 1.0}},
        "answer": {"type": "numeric", "expected": "-0.2500", "tolerance": 0.01},
    }
    evaluator = TimingReportQAEvaluator(task_dir, meta)

    # Create submission with correct answer
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    (work_dir / "answer.txt").write_text("-0.2500\n")

    comp = evaluator.evaluate_component("answer_match", work_dir, "")
    assert comp.raw_score == 1.0
    assert comp.weighted_score == 1.0


def test_evaluator_answer_match_wrong(tmp_path):
    """Full evaluator integration: wrong answer scores 0.0."""
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    meta = {
        "scoring": {"weights": {"answer_match": 1.0}},
        "answer": {"type": "numeric", "expected": "-0.2500", "tolerance": 0.01},
    }
    evaluator = TimingReportQAEvaluator(task_dir, meta)

    # Create submission with wrong answer
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
        "answer": {"type": "numeric", "expected": "-0.2500", "tolerance": 0.01},
    }
    evaluator = TimingReportQAEvaluator(task_dir, meta)

    work_dir = tmp_path / "work"
    work_dir.mkdir()

    comp = evaluator.evaluate_component("answer_match", work_dir, "")
    assert comp.raw_score == 0.0


# --- Generator tests ---

def test_generator_deterministic(tmp_path):
    """Same seed produces identical output."""
    gen1 = P3TimingReportQAGenerator(seed=42, output_dir=tmp_path / "a")
    gen2 = P3TimingReportQAGenerator(seed=42, output_dir=tmp_path / "b")
    p1 = gen1.generate_one(0)
    p2 = gen2.generate_one(0)
    meta1 = json.loads((p1 / "metadata.json").read_text())
    meta2 = json.loads((p2 / "metadata.json").read_text())
    assert meta1["task_id"] == meta2["task_id"]
    assert meta1["answer"]["expected"] == meta2["answer"]["expected"]
    assert (p1 / "files" / "timing_report.rpt").read_text() == (
        p2 / "files" / "timing_report.rpt"
    ).read_text()


def test_generator_metadata_valid(tmp_path):
    """Generated task metadata passes schema validation."""
    gen = P3TimingReportQAGenerator(seed=42, output_dir=tmp_path)
    for i in range(10):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        errors = validate_metadata(meta)
        assert errors == [], f"Task {i} metadata errors: {errors}"


def test_generator_files_exist(tmp_path):
    """All required files are created."""
    gen = P3TimingReportQAGenerator(seed=42, output_dir=tmp_path)
    p = gen.generate_one(0)
    assert (p / "metadata.json").is_file()
    assert (p / "prompt.md").is_file()
    assert (p / "files" / "timing_report.rpt").is_file()
    assert (p / "files" / "answer.txt").is_file()
    assert (p / "solution" / "answer.txt").is_file()


def test_generator_answer_matches_parser(tmp_path):
    """Generated answer matches what the parser extracts from the report."""
    gen = P3TimingReportQAGenerator(seed=42, output_dir=tmp_path)
    for i in range(10):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        report_text = (p / "files" / "timing_report.rpt").read_text()
        report = parse_timing_report(report_text)
        expected = meta["answer"]["expected"]
        qtype = meta["answer"]["question_type"]

        # Verify the answer is consistent with the report
        if qtype == "wns":
            assert float(expected) == pytest.approx(report.get_wns(), abs=0.01)
        elif qtype == "tns":
            assert float(expected) == pytest.approx(report.get_tns(), abs=0.01)
        elif qtype == "violating_paths":
            assert int(float(expected)) == report.get_violating_count()
        elif qtype == "worst_endpoint":
            assert expected == report.get_worst_path().endpoint
        elif qtype == "worst_startpoint":
            assert expected == report.get_worst_path().startpoint
        elif qtype == "path_group":
            assert expected == report.get_worst_path().path_group
        elif qtype == "clock_name":
            assert expected == report.get_worst_path().clock
        elif qtype == "required_time":
            assert float(expected) == pytest.approx(
                report.get_worst_path().required_time, abs=0.01
            )
        elif qtype == "arrival_time":
            assert float(expected) == pytest.approx(
                report.get_worst_path().arrival_time, abs=0.01
            )


def test_generator_question_type_distribution(tmp_path):
    """100 tasks should cover all 10 question types, 10 each."""
    from collections import Counter
    gen = P3TimingReportQAGenerator(seed=42, output_dir=tmp_path)
    types = Counter()
    for i in range(100):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        types[meta["answer"]["question_type"]] += 1
    assert set(types.keys()) == set(EXPECTED_QUESTION_TYPES)
    for qt in EXPECTED_QUESTION_TYPES:
        assert types[qt] == 10, f"{qt}: expected 10, got {types[qt]}"


def test_generator_unique_task_ids(tmp_path):
    """All 100 tasks have unique task IDs."""
    gen = P3TimingReportQAGenerator(seed=42, output_dir=tmp_path)
    ids = set()
    for i in range(100):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        assert meta["task_id"] not in ids, f"Duplicate task_id: {meta['task_id']}"
        ids.add(meta["task_id"])


def test_generator_validate_sample_tasks(tmp_path):
    """Sample generated tasks pass structural validation."""
    from eda_agentbench.task.loader import TaskLoader
    gen = P3TimingReportQAGenerator(seed=42, output_dir=tmp_path)
    paths = gen.generate_batch(3)
    loader = TaskLoader(tmp_path)
    for p in paths:
        meta = loader.load(p)
        assert meta["track"] == "p3_timing_report_qa"


def test_generator_slack_of_named_path(tmp_path):
    """slack_of_named_path questions reference a valid endpoint."""
    gen = P3TimingReportQAGenerator(seed=42, output_dir=tmp_path)
    # Find a slack_of_named_path task
    for i in range(10):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        if meta["answer"]["question_type"] == "slack_of_named_path":
            # Verify the endpoint exists in the report
            report_text = (p / "files" / "timing_report.rpt").read_text()
            report = parse_timing_report(report_text)
            # Extract endpoint from question
            question = (p / "prompt.md").read_text()
            # The question mentions an endpoint
            assert "ending at" in question
            # The expected answer should match a path in the report
            expected = float(meta["answer"]["expected"])
            found = any(
                pytest.approx(expected, abs=0.01) == path.slack
                for path in report.paths
            )
            assert found, f"Expected slack {expected} not found in report"
            break


# --- Dataset report integration ---

def test_p3_track_in_summary():
    """P3 track appears in dataset summary."""
    from eda_agentbench.cli import _build_dataset_summary
    results = [
        {
            "task_id": "p3_timing_000000", "track": "p3_timing_report_qa",
            "tool": ["pt"], "difficulty": "easy", "status": "pass",
            "total_score": 1.0, "objective_score": 1.0, "explanation_score": 0.0,
        },
    ]
    summary = _build_dataset_summary(results, "test", "solution", None)
    assert "p3_timing_report_qa" in summary["per_track"]
    assert summary["per_track"]["p3_timing_report_qa"]["total"] == 1


def test_p3_question_type_distribution():
    """Question types are correctly distributed."""
    from collections import Counter
    assert len(EXPECTED_QUESTION_TYPES) == 10
    assert len(set(EXPECTED_QUESTION_TYPES)) == 10


# --- Normalize answer ---

def test_normalize_answer_integer():
    assert normalize_answer("3.0000") == "3"
    assert normalize_answer("0.0000") == "0"


def test_normalize_answer_float():
    assert normalize_answer("-0.2500") == "-0.25"
    assert normalize_answer("3.1400") == "3.14"


def test_normalize_answer_string():
    assert normalize_answer("  Hello World  ") == "hello world"
    assert normalize_answer("ABC") == "abc"
