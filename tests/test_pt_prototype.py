"""Tests for PrimeTime Timing Report QA prototype: parser, generator, evaluator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eda_agentbench.timing.report_parser import parse_timing_report
from eda_agentbench.evaluator.timing_report_qa import TimingReportQAEvaluator
from eda_agentbench.schema import validate_metadata
from eda_agentbench.sanitizer.log_sanitizer import LogSanitizer


# --- Parser tests against realistic sanitized PrimeTime report ---

PT_PROTOTYPE_REPORT = """\
Information: Updating design information... (INT-234)

  Loading db file '<EDA_ROOT>/libraries/synopsis/std_cell/ss_0p99v_125c.db'
Information: Timer using 'POSIX' clock source. (TIM-211)

**** Report : timing
        -path_type full
        -delay_type max
        -max_paths 5
        -nworst 1

Startpoint: u_core/reg_a_reg
Endpoint: u_core/reg_b_reg
Path Group: clk
Clock: clk
----------------------------------------
Slack:                    -0.4200
Arrival Time:              0.5600
Required Time:             0.9800
Data Type: setup

Startpoint: u_top/fifo_wr/wr_ptr_reg
Endpoint: u_top/fifo_wr/wr_data_reg
Path Group: clk_100m
Clock: clk_100m
----------------------------------------
Slack:                    -0.4080
Arrival Time:              0.6320
Required Time:             1.0400
Data Type: setup

Startpoint: u_top/fifo_rd/rd_ptr_reg
Endpoint: u_top/fifo_rd/rd_data_reg
Path Group: clk_100m
Clock: clk_100m
----------------------------------------
Slack:                    -0.5770
Arrival Time:              0.4730
Required Time:             1.0500
Data Type: setup

wns: -0.5770
tns: -1.4050
violating_path_count: 3
"""


def test_parse_pt_prototype_wns():
    report = parse_timing_report(PT_PROTOTYPE_REPORT)
    assert report.get_wns() == pytest.approx(-0.577, abs=0.001)


def test_parse_pt_prototype_tns():
    report = parse_timing_report(PT_PROTOTYPE_REPORT)
    assert report.get_tns() == pytest.approx(-1.405, abs=0.001)


def test_parse_pt_prototype_paths():
    report = parse_timing_report(PT_PROTOTYPE_REPORT)
    assert len(report.paths) == 3


def test_parse_pt_prototype_worst_path():
    report = parse_timing_report(PT_PROTOTYPE_REPORT)
    worst = report.get_worst_path()
    assert worst is not None
    assert worst.slack == pytest.approx(-0.577, abs=0.001)
    assert worst.endpoint == "u_top/fifo_rd/rd_data_reg"


def test_parse_pt_prototype_sanitized_no_usernames():
    """Report should contain no real usernames or paths."""
    report = PT_PROTOTYPE_REPORT
    assert "/home/" not in report
    assert "<EDA_ROOT>" in report


def test_parse_pt_prototype_path_fields():
    report = parse_timing_report(PT_PROTOTYPE_REPORT)
    p = report.paths[0]
    assert p.startpoint == "u_core/reg_a_reg"
    assert p.endpoint == "u_core/reg_b_reg"
    assert p.path_group == "clk"
    assert p.clock == "clk"
    assert p.arrival_time == pytest.approx(0.56, abs=0.001)
    assert p.required_time == pytest.approx(0.98, abs=0.001)
    assert p.data_type == "setup"


def test_parse_pt_prototype_violating_count():
    report = parse_timing_report(PT_PROTOTYPE_REPORT)
    assert report.get_violating_count() == 3


# --- Generator tests ---

def test_handcrafted_generates_8_tasks(tmp_path):
    """Handcrafted mode generates exactly 8 tasks."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.generate_pt_report_prototypes import generate_handcrafted

    task_dirs = generate_handcrafted(tmp_path, seed=42)
    assert len(task_dirs) == 8


def test_handcrafted_metadata_valid(tmp_path):
    """All handcrafted tasks pass schema validation."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.generate_pt_report_prototypes import generate_handcrafted

    task_dirs = generate_handcrafted(tmp_path, seed=42)
    for td in task_dirs:
        meta = json.loads((td / "metadata.json").read_text())
        errors = validate_metadata(meta)
        assert errors == [], f"{td.name} metadata errors: {errors}"


def test_handcrafted_solution_scores_1(tmp_path):
    """Evaluator gives 1.0 on solution for all handcrafted tasks."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.generate_pt_report_prototypes import generate_handcrafted

    task_dirs = generate_handcrafted(tmp_path, seed=42)
    for td in task_dirs:
        meta = json.loads((td / "metadata.json").read_text())
        evaluator = TimingReportQAEvaluator(td, meta)
        score = evaluator.evaluate_component("answer_match", td / "solution", "")
        assert score.raw_score == 1.0, f"{td.name} solution score: {score.raw_score}"


def test_handcrafted_deterministic(tmp_path):
    """Same seed produces identical output."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.generate_pt_report_prototypes import generate_handcrafted

    dirs1 = generate_handcrafted(tmp_path / "a", seed=42)
    dirs2 = generate_handcrafted(tmp_path / "b", seed=42)
    for d1, d2 in zip(dirs1, dirs2):
        meta1 = json.loads((d1 / "metadata.json").read_text())
        meta2 = json.loads((d2 / "metadata.json").read_text())
        assert meta1["task_id"] == meta2["task_id"]
        assert meta1["answer"]["expected"] == meta2["answer"]["expected"]
        assert (d1 / "files" / "timing_report.rpt").read_text() == (
            d2 / "files" / "timing_report.rpt"
        ).read_text()


def test_handcrafted_files_exist(tmp_path):
    """All required files are created."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.generate_pt_report_prototypes import generate_handcrafted

    task_dirs = generate_handcrafted(tmp_path, seed=42)
    for td in task_dirs:
        assert (td / "metadata.json").is_file()
        assert (td / "prompt.md").is_file()
        assert (td / "files" / "timing_report.rpt").is_file()
        assert (td / "files" / "answer.txt").is_file()
        assert (td / "solution" / "answer.txt").is_file()


def test_handcrafted_question_types(tmp_path):
    """All 8 question types are covered."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.generate_pt_report_prototypes import generate_handcrafted

    task_dirs = generate_handcrafted(tmp_path, seed=42)
    types = set()
    for td in task_dirs:
        meta = json.loads((td / "metadata.json").read_text())
        types.add(meta["answer"]["question_type"])
    expected = {"wns", "tns", "worst_endpoint", "worst_startpoint",
                "violating_paths", "path_group", "clock_name", "arrival_time"}
    assert types == expected


def test_handcrafted_parser_extracts_paths(tmp_path):
    """Parser can extract paths from all generated reports."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.generate_pt_report_prototypes import generate_handcrafted

    task_dirs = generate_handcrafted(tmp_path, seed=42)
    for td in task_dirs:
        report_text = (td / "files" / "timing_report.rpt").read_text()
        report = parse_timing_report(report_text)
        assert len(report.paths) > 0, f"{td.name}: parser found 0 paths"


def test_handcrafted_task_loader(tmp_path):
    """Generated tasks pass TaskLoader.load()."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from eda_agentbench.task.loader import TaskLoader
    from scripts.generate_pt_report_prototypes import generate_handcrafted

    task_dirs = generate_handcrafted(tmp_path, seed=42)
    loader = TaskLoader(tmp_path)
    for td in task_dirs:
        meta = loader.load(td)
        assert meta["track"] == "p3_timing_report_qa"


def test_sanitizer_applied(tmp_path):
    """Generated reports are sanitized (no raw EDA paths)."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.generate_pt_report_prototypes import generate_handcrafted

    task_dirs = generate_handcrafted(tmp_path, seed=42)
    for td in task_dirs:
        report = (td / "files" / "timing_report.rpt").read_text()
        assert "/EDA/soft2/" not in report


# --- Integration test: real PrimeTime ---

@pytest.mark.skipif(
    not Path("/EDA/soft2/synopsys/prime").is_dir(),
    reason="PrimeTime not available",
)
def test_real_pt_generate_one(tmp_path):
    """Generate 1 task with real PrimeTime mode (skips if PT unavailable)."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.generate_pt_report_prototypes import generate_real

    task_dirs = generate_real(tmp_path, seed=42)
    if not task_dirs:
        pytest.skip("PrimeTime not available at runtime")
    assert len(task_dirs) > 0
    meta = json.loads((task_dirs[0] / "metadata.json").read_text())
    assert meta["data_type"] == "flow_synthetic"
