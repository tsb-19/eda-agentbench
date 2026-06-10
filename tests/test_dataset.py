"""Tests for dataset evaluation and report: discovery, aggregation, buckets."""

from __future__ import annotations

import json
from pathlib import Path

from eda_agentbench.task.loader import TaskLoader
from eda_agentbench.cli import _build_dataset_summary, _generate_markdown_report


# --- Task discovery ---

def test_discover_all_tasks(tmp_path):
    """Discover tasks across multiple tracks including nested generated/."""
    # Create track with hand-crafted task
    t1 = tmp_path / "p1_rtl_debug" / "task_000001"
    (t1 / "files").mkdir(parents=True)
    (t1 / "hidden").mkdir(parents=True)
    (t1 / "solution").mkdir(parents=True)
    (t1 / "metadata.json").write_text('{"task_id":"task_000001"}')

    # Create track with generated tasks
    for i in range(3):
        tg = tmp_path / "p1_rtl_debug" / "generated" / f"task_{i:06d}"
        (tg / "files").mkdir(parents=True)
        (tg / "hidden").mkdir(parents=True)
        (tg / "solution").mkdir(parents=True)
        (tg / "metadata.json").write_text(f'{{"task_id":"task_{i:06d}"}}')

    # Create P4 track
    t4 = tmp_path / "p4_spice_sim" / "hspice_001"
    (t4 / "files").mkdir(parents=True)
    (t4 / "hidden").mkdir(parents=True)
    (t4 / "solution").mkdir(parents=True)
    (t4 / "metadata.json").write_text('{"task_id":"task_p4_001"}')

    loader = TaskLoader(tmp_path)
    all_tasks = loader.discover()
    assert len(all_tasks) == 5


def test_discover_filter_track(tmp_path):
    """Discover tasks filtered by track."""
    for track in ["p1_rtl_debug", "p4_spice_sim"]:
        d = tmp_path / track / "task_001"
        (d / "files").mkdir(parents=True)
        (d / "solution").mkdir(parents=True)
        (d / "hidden").mkdir(parents=True)
        (d / "metadata.json").write_text('{"task_id":"t1"}')

    loader = TaskLoader(tmp_path)
    p1 = loader.discover(track="p1_rtl_debug")
    assert len(p1) == 1
    assert "p1_rtl_debug" in str(p1[0])


def test_discover_skips_directories_without_metadata(tmp_path):
    """Directories without metadata.json are skipped."""
    d = tmp_path / "p1_rtl_debug" / "not_a_task"
    d.mkdir(parents=True)
    (d / "some_file.txt").write_text("no metadata here")

    loader = TaskLoader(tmp_path)
    assert loader.discover() == []


def test_discover_recursive_false(tmp_path):
    """With recursive=False, only finds top-level tasks."""
    t1 = tmp_path / "p1_rtl_debug" / "task_001"
    (t1 / "files").mkdir(parents=True)
    (t1 / "solution").mkdir(parents=True)
    (t1 / "metadata.json").write_text('{"task_id":"t1"}')

    tg = tmp_path / "p1_rtl_debug" / "generated" / "task_002"
    (tg / "files").mkdir(parents=True)
    (tg / "solution").mkdir(parents=True)
    (tg / "metadata.json").write_text('{"task_id":"t2"}')

    loader = TaskLoader(tmp_path)
    assert len(loader.discover(recursive=False)) == 1
    assert len(loader.discover(recursive=True)) == 2


# --- Summary aggregation ---

def _make_result(task_id: str, track: str, tool: list, difficulty: str,
                 status: str, total: float = 0.0, obj: float = 0.0, exp: float = 0.0) -> dict:
    return {
        "task_path": f"/fake/{task_id}",
        "task_id": task_id,
        "track": track,
        "tool": tool,
        "difficulty": difficulty,
        "status": status,
        "total_score": total,
        "objective_score": obj,
        "explanation_score": exp,
    }


def test_summary_counts():
    """Summary correctly counts total/evaluated/passed/failed/errors."""
    results = [
        _make_result("t1", "p1", ["vcs"], "easy", "pass", 1.0),
        _make_result("t2", "p1", ["vcs"], "easy", "fail", 0.5),
        _make_result("t3", "p4", ["hspice"], "easy", "error"),
        _make_result("t4", "p4", ["spectre"], "easy", "skipped"),
    ]
    summary = _build_dataset_summary(results, "test_run", "solution", None)
    assert summary["total"] == 4
    assert summary["evaluated"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["errors"] == 2


def test_summary_averages():
    """Summary computes correct averages."""
    results = [
        _make_result("t1", "p1", ["vcs"], "easy", "pass", 1.0, 0.9, 0.1),
        _make_result("t2", "p1", ["vcs"], "easy", "fail", 0.6, 0.5, 0.1),
    ]
    summary = _build_dataset_summary(results, "test", "solution", None)
    assert abs(summary["avg_score"] - 0.8) < 0.001
    assert abs(summary["avg_objective"] - 0.7) < 0.001
    assert abs(summary["avg_explanation"] - 0.1) < 0.001


def test_summary_per_track():
    """Summary groups by track correctly."""
    results = [
        _make_result("t1", "p1_rtl_debug", ["vcs"], "easy", "pass", 1.0),
        _make_result("t2", "p1_rtl_debug", ["vcs"], "easy", "fail", 0.5),
        _make_result("t3", "p4_spice_sim", ["hspice"], "easy", "pass", 1.0),
    ]
    summary = _build_dataset_summary(results, "test", "solution", None)
    assert summary["per_track"]["p1_rtl_debug"]["total"] == 2
    assert summary["per_track"]["p1_rtl_debug"]["passed"] == 1
    assert summary["per_track"]["p4_spice_sim"]["total"] == 1
    assert summary["per_track"]["p4_spice_sim"]["passed"] == 1


def test_summary_per_tool():
    """Summary groups by tool correctly."""
    results = [
        _make_result("t1", "p1", ["vcs"], "easy", "pass", 1.0),
        _make_result("t2", "p4", ["hspice"], "easy", "pass", 1.0),
        _make_result("t3", "p4", ["spectre"], "easy", "fail", 0.6),
    ]
    summary = _build_dataset_summary(results, "test", "solution", None)
    assert summary["per_tool"]["vcs"]["total"] == 1
    assert summary["per_tool"]["hspice"]["total"] == 1
    assert summary["per_tool"]["spectre"]["total"] == 1


def test_summary_per_difficulty():
    """Summary groups by difficulty correctly."""
    results = [
        _make_result("t1", "p1", ["vcs"], "easy", "pass", 1.0),
        _make_result("t2", "p1", ["vcs"], "medium", "fail", 0.5),
    ]
    summary = _build_dataset_summary(results, "test", "solution", None)
    assert summary["per_difficulty"]["easy"]["total"] == 1
    assert summary["per_difficulty"]["medium"]["total"] == 1


# --- Score distribution buckets ---

def test_score_distribution_all_buckets():
    """Score distribution places scores in correct buckets."""
    results = [
        _make_result("t1", "p1", ["vcs"], "easy", "pass", 1.0),       # 1.0
        _make_result("t2", "p1", ["vcs"], "easy", "pass", 0.9),       # [0.8,1.0)
        _make_result("t3", "p1", ["vcs"], "easy", "pass", 0.8),       # [0.8,1.0)
        _make_result("t4", "p1", ["vcs"], "easy", "fail", 0.6),       # [0.5,0.8)
        _make_result("t5", "p1", ["vcs"], "easy", "fail", 0.5),       # [0.5,0.8)
        _make_result("t6", "p1", ["vcs"], "easy", "fail", 0.3),       # <0.5
    ]
    summary = _build_dataset_summary(results, "test", "solution", None)
    dist = summary["score_distribution"]
    assert dist["1.0"] == 1
    assert dist["[0.8,1.0)"] == 2
    assert dist["[0.5,0.8)"] == 2
    assert dist["<0.5"] == 1


def test_score_distribution_boundary():
    """Score exactly at 0.8 goes to [0.8, 1.0) bucket."""
    results = [
        _make_result("t1", "p1", ["vcs"], "easy", "pass", 0.8),
    ]
    summary = _build_dataset_summary(results, "test", "solution", None)
    assert summary["score_distribution"]["[0.8,1.0)"] == 1
    assert summary["score_distribution"]["[0.5,0.8)"] == 0


def test_score_distribution_empty():
    """Empty results produce zero counts."""
    summary = _build_dataset_summary([], "test", "solution", None)
    assert summary["total"] == 0
    assert all(v == 0 for v in summary["score_distribution"].values())


# --- Failure list ---

def test_failure_list():
    """Failure list includes failed and error tasks."""
    results = [
        _make_result("t1", "p1", ["vcs"], "easy", "pass", 1.0),
        _make_result("t2", "p1", ["vcs"], "easy", "fail", 0.3),
        _make_result("t3", "p4", ["hspice"], "easy", "error"),
    ]
    summary = _build_dataset_summary(results, "test", "solution", None)
    failures = summary["failure_list"]
    assert len(failures) == 2
    ids = {f["task_id"] for f in failures}
    assert "t2" in ids
    assert "t3" in ids


def test_buggy_lower_than_solution_count():
    """buggy_lower_than_solution_count counts tasks with score < 1.0."""
    results = [
        _make_result("t1", "p1", ["vcs"], "easy", "pass", 1.0),
        _make_result("t2", "p1", ["vcs"], "easy", "fail", 0.6),
        _make_result("t3", "p1", ["vcs"], "easy", "fail", 0.2),
    ]
    summary = _build_dataset_summary(results, "test", "buggy", None)
    assert summary["buggy_lower_than_solution_count"] == 2


def test_buggy_lower_than_solution_count_all_perfect():
    """buggy_lower_than_solution_count is 0 when all scores are 1.0."""
    results = [
        _make_result("t1", "p1", ["vcs"], "easy", "pass", 1.0),
        _make_result("t2", "p1", ["vcs"], "easy", "pass", 1.0),
    ]
    summary = _build_dataset_summary(results, "test", "solution", None)
    assert summary["buggy_lower_than_solution_count"] == 0


# --- Markdown report ---

def test_markdown_report_contains_sections():
    """Markdown report contains expected sections."""
    results = [
        _make_result("t1", "p1_rtl_debug", ["vcs"], "easy", "pass", 1.0),
    ]
    summary = _build_dataset_summary(results, "test_run", "solution", "p1_rtl_debug")
    md = _generate_markdown_report(summary)
    assert "EDA-AgentBench Dataset Report" in md
    assert "test_run" in md
    assert "p1_rtl_debug" in md
    assert "Score Distribution" in md
    assert "Per-Track" in md
    assert "Per-Tool" in md


# --- CLI arg parsing ---

def test_cli_evaluate_dataset_args():
    """evaluate-dataset CLI parses arguments correctly."""
    import argparse
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    p_ds = sub.add_parser("evaluate-dataset")
    p_ds.add_argument("tasks_root")
    p_ds.add_argument("--submission-mode", choices=["solution", "buggy"], default="solution")
    p_ds.add_argument("--track", default=None)
    p_ds.add_argument("--timeout", type=int, default=None)
    p_ds.add_argument("--run-id", default=None)

    args = parser.parse_args(["evaluate-dataset", "tasks", "--submission-mode", "buggy", "--track", "p1_rtl_debug"])
    assert args.tasks_root == "tasks"
    assert args.submission_mode == "buggy"
    assert args.track == "p1_rtl_debug"
    assert args.timeout is None


def test_cli_report_args():
    """report CLI parses arguments correctly."""
    import argparse
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    p_rep = sub.add_parser("report")
    p_rep.add_argument("runs_dir")
    p_rep.add_argument("--format", choices=["terminal", "json", "markdown", "all"], default="all")
    p_rep.add_argument("--output", default=None)

    args = parser.parse_args(["report", "runs/dataset_20260101", "--format", "json"])
    assert args.runs_dir == "runs/dataset_20260101"
    assert args.format == "json"


def test_cli_report_args_default():
    """report CLI defaults to all format."""
    import argparse
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    p_rep = sub.add_parser("report")
    p_rep.add_argument("runs_dir")
    p_rep.add_argument("--format", choices=["terminal", "json", "markdown", "all"], default="all")

    args = parser.parse_args(["report", "runs/test"])
    assert args.format == "all"
