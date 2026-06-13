"""Tests for P8 PnR Report QA track."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


class TestPnRReportParser:
    """Test the PnR report parser."""

    def test_parse_icc2_report(self):
        from eda_agentbench.pnr.pnr_report_parser import parse_pnr_report

        report = """Design          : test_design
Stage           : route
Setup WNS               : -0.5
Setup TNS               : -2.5
Setup Violating Paths   : 5
Hold WNS                : -0.1
Hold TNS                : -0.3
Hold Violating Paths    : 2
Worst Endpoint          : u_cpu/reg_pc_reg
Worst Startpoint        : u_mem/data_out_reg
Timing Status           : VIOLATED
Core Utilization        : 75.5%
Standard Cell Area      : 100000
Macro Area              : 20000
Total Cell Area         : 120000
Instances               : 50000
Sequential Cells        : 5000
Total Wirelength        : 1000000
Max Horizontal Overflow : 5.0%
Max Vertical Overflow   : 3.0%
Total Overflow          : 8.0
Congested Bins          : 50
Worst Congestion Layer  : M3
Congestion Status       : PASS
DRC Violations          : 10
Shorts                  : 3
Opens                   : 2
Antenna Violations      : 1
Route Status            : dirty
Internal Power          : 10.5 mW
Switching Power         : 20.3 mW
Leakage Power           : 0.5 mW
Total Power             : 31.3 mW
"""
        rec = parse_pnr_report(report)
        assert rec["tool_family"] is None  # No ICC2/Innovus keyword
        assert rec["design_name"] == "test_design"
        assert rec["stage"] == "route"
        assert rec["setup_wns"] == -0.5
        assert rec["setup_tns"] == -2.5
        assert rec["setup_violations"] == 5
        assert rec["hold_wns"] == -0.1
        assert rec["hold_tns"] == -0.3
        assert rec["hold_violations"] == 2
        assert rec["worst_endpoint"] == "u_cpu/reg_pc_reg"
        assert rec["timing_met"] is False
        assert rec["core_utilization"] == 75.5
        assert rec["instance_count"] == 50000
        assert rec["sequential_count"] == 5000
        assert rec["total_wirelength"] == 1000000.0
        assert rec["congestion_pass"] is True
        assert rec["drc_total"] == 10
        assert rec["shorts"] == 3
        assert rec["opens"] == 2
        assert rec["antenna_violations"] == 1
        assert rec["route_completed"] is False
        assert rec["total_power"] == 31.3

    def test_parse_innovus_report(self):
        from eda_agentbench.pnr.pnr_report_parser import parse_pnr_report

        report = """Design          = innovus_design
Stage           = place
Tool Family     = Innovus
Setup WNS               = -1.2
Setup TNS               = -5.0
Setup Violating Paths   = 8
Core Utilization        = 80.0%
Instances               = 100000
"""
        rec = parse_pnr_report(report)
        assert rec["tool_family"] == "innovus"
        assert rec["design_name"] == "innovus_design"
        assert rec["stage"] == "place"
        assert rec["setup_wns"] == -1.2
        assert rec["setup_tns"] == -5.0
        assert rec["setup_violations"] == 8
        assert rec["core_utilization"] == 80.0
        assert rec["instance_count"] == 100000


class TestPnRReportQAEvaluator:
    """Test the PnR Report QA evaluator."""

    def test_numeric_tolerance(self):
        from eda_agentbench.evaluator.pnr_report_qa import _compare_values

        # Float within tolerance
        match, _ = _compare_values("10.0", "10.1", "setup_wns")
        assert match is True

        # Float outside tolerance
        match, _ = _compare_values("10.0", "10.5", "setup_wns")
        assert match is False

    def test_string_exact_match(self):
        from eda_agentbench.evaluator.pnr_report_qa import _compare_values

        match, _ = _compare_values("icc2", "icc2", "tool_family")
        assert match is True

        match, _ = _compare_values("icc2", "innovus", "tool_family")
        assert match is False

    def test_int_exact_match(self):
        from eda_agentbench.evaluator.pnr_report_qa import _compare_values

        match, _ = _compare_values("100", "100", "instance_count")
        assert match is True

        match, _ = _compare_values("100", "101", "instance_count")
        assert match is False

    def test_bool_match(self):
        from eda_agentbench.evaluator.pnr_report_qa import _compare_values

        match, _ = _compare_values("true", "true", "timing_met")
        assert match is True

        match, _ = _compare_values("true", "false", "timing_met")
        assert match is False

    def test_solution_scores_perfect(self, tmp_path):
        from eda_agentbench.evaluator.pnr_report_qa import PnRReportQAEvaluator

        task_dir = REPO_ROOT / "tasks" / "p8_pnr_report_qa" / "smoke" / "pnr_report_qa_0000"
        with open(task_dir / "metadata.json") as f:
            meta = json.load(f)

        evaluator = PnRReportQAEvaluator(task_dir, meta)

        # Copy solution to work_dir
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        import shutil
        shutil.copy2(task_dir / "solution" / "answer.txt", work_dir / "answer.txt")

        result = evaluator.evaluate_component("answer_match", work_dir, "", mode="submission")
        assert result.raw_score == 1.0

    def test_empty_answer_scores_zero(self, tmp_path):
        from eda_agentbench.evaluator.pnr_report_qa import PnRReportQAEvaluator

        task_dir = REPO_ROOT / "tasks" / "p8_pnr_report_qa" / "smoke" / "pnr_report_qa_0000"
        with open(task_dir / "metadata.json") as f:
            meta = json.load(f)

        evaluator = PnRReportQAEvaluator(task_dir, meta)

        work_dir = tmp_path / "work"
        work_dir.mkdir()
        with open(work_dir / "answer.txt", "w") as f:
            f.write("{}")

        result = evaluator.evaluate_component("answer_match", work_dir, "", mode="submission")
        assert result.raw_score == 0.0


class TestGenerator:
    """Test the PnR report QA generator."""

    def test_deterministic(self):
        from generators.p8_pnr_report_qa_gen import generate_report
        import random

        rng1 = random.Random(42)
        rng2 = random.Random(42)

        report1, oracle1 = generate_report(rng1, "icc2", "test_design", "route")
        report2, oracle2 = generate_report(rng2, "icc2", "test_design", "route")

        assert report1 == report2
        assert oracle1 == oracle2

    def test_icc2_vs_innovus_format(self):
        from generators.p8_pnr_report_qa_gen import generate_report
        import random

        rng = random.Random(42)
        report_icc2, _ = generate_report(rng, "icc2", "test", "route")
        rng = random.Random(42)
        report_innovus, _ = generate_report(rng, "innovus", "test", "route")

        assert "ICC2" in report_icc2
        assert "Innovus" in report_innovus


class TestTaskStructure:
    """Test task structure and metadata."""

    def test_smoke_task_valid(self):
        from eda_agentbench.schema import validate_metadata

        task_dir = REPO_ROOT / "tasks" / "p8_pnr_report_qa" / "smoke" / "pnr_report_qa_0000"
        with open(task_dir / "metadata.json") as f:
            meta = json.load(f)

        errors = validate_metadata(meta)
        assert errors == []

    def test_generated_tasks_valid(self):
        from eda_agentbench.schema import validate_metadata

        gen_dir = REPO_ROOT / "tasks" / "p8_pnr_report_qa" / "generated"
        for task_dir in sorted(gen_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            meta_path = task_dir / "metadata.json"
            if not meta_path.exists():
                continue
            with open(meta_path) as f:
                meta = json.load(f)
            errors = validate_metadata(meta)
            assert errors == [], f"Task {task_dir.name}: {errors}"

    def test_no_duplicate_ids(self):
        gen_dir = REPO_ROOT / "tasks" / "p8_pnr_report_qa" / "generated"
        smoke_dir = REPO_ROOT / "tasks" / "p8_pnr_report_qa" / "smoke"

        ids = []
        for task_dir in sorted(smoke_dir.iterdir()) + sorted(gen_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            meta_path = task_dir / "metadata.json"
            if not meta_path.exists():
                continue
            with open(meta_path) as f:
                meta = json.load(f)
            ids.append(meta["task_id"])

        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {[x for x in ids if ids.count(x) > 1]}"

    def test_smoke_id_unique(self):
        smoke_dir = REPO_ROOT / "tasks" / "p8_pnr_report_qa" / "smoke"
        gen_dir = REPO_ROOT / "tasks" / "p8_pnr_report_qa" / "generated"

        smoke_ids = set()
        for task_dir in smoke_dir.iterdir():
            if not task_dir.is_dir():
                continue
            meta_path = task_dir / "metadata.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    smoke_ids.add(json.load(f)["task_id"])

        gen_ids = set()
        for task_dir in gen_dir.iterdir():
            if not task_dir.is_dir():
                continue
            meta_path = task_dir / "metadata.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    gen_ids.add(json.load(f)["task_id"])

        assert smoke_ids.isdisjoint(gen_ids), f"Overlap: {smoke_ids & gen_ids}"

    def test_task_count(self):
        smoke_dir = REPO_ROOT / "tasks" / "p8_pnr_report_qa" / "smoke"
        gen_dir = REPO_ROOT / "tasks" / "p8_pnr_report_qa" / "generated"

        smoke_count = sum(1 for d in smoke_dir.iterdir() if d.is_dir() and (d / "metadata.json").exists())
        gen_count = sum(1 for d in gen_dir.iterdir() if d.is_dir() and (d / "metadata.json").exists())

        assert smoke_count == 1
        assert gen_count == 100
        assert smoke_count + gen_count == 101

    def test_tool_family_distribution(self):
        gen_dir = REPO_ROOT / "tasks" / "p8_pnr_report_qa" / "generated"
        icc2 = 0
        innovus = 0
        for task_dir in gen_dir.iterdir():
            if not task_dir.is_dir():
                continue
            meta_path = task_dir / "metadata.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)
                if meta["tool"] == ["icc2"]:
                    icc2 += 1
                elif meta["tool"] == ["innovus"]:
                    innovus += 1

        assert icc2 > 0, "No ICC2 tasks"
        assert innovus > 0, "No Innovus tasks"
        assert icc2 + innovus == 100
