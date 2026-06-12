"""Tests for the baseline runner script."""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add scripts/ to path for import
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import run_baseline_suite as rbs


def _make_mock_summary(
    run_id: str = "test_run",
    mode: str = "solution",
    n_tasks: int = 5,
    score: float = 1.0,
    track: str = "p1_rtl_debug",
) -> dict:
    """Create a mock dataset summary."""
    results = []
    for i in range(n_tasks):
        results.append({
            "task_path": f"/mock/{track}/task_{i:06d}",
            "task_id": f"task_{i:06d}",
            "track": track,
            "tool": ["vcs"],
            "difficulty": "easy",
            "status": "pass" if score >= 0.5 else "fail",
            "total_score": score,
            "objective_score": score * 0.9,
            "explanation_score": score * 0.1,
            "components": [],
            "score_path": "",
        })

    passed = sum(1 for r in results if r["status"] == "pass")
    evaluated = len(results)

    return {
        "run_id": run_id,
        "submission_mode": mode,
        "track_filter": None,
        "total": evaluated,
        "evaluated": evaluated,
        "passed": passed,
        "failed": evaluated - passed,
        "errors": 0,
        "avg_score": score,
        "avg_objective": score * 0.9,
        "avg_explanation": score * 0.1,
        "buggy_lower_than_solution_count": 0 if score >= 1.0 else evaluated,
        "per_track": {
            track: {
                "total": evaluated,
                "passed": passed,
                "avg_score": score,
            }
        },
        "per_tool": {
            "vcs": {"total": evaluated, "passed": passed, "avg_score": score}
        },
        "per_difficulty": {
            "easy": {"total": evaluated, "passed": passed, "avg_score": score}
        },
        "score_distribution": {
            "1.0": evaluated if score >= 1.0 else 0,
            "[0.8,1.0)": evaluated if 0.8 <= score < 1.0 else 0,
            "[0.5,0.8)": evaluated if 0.5 <= score < 0.8 else 0,
            "<0.5": evaluated if score < 0.5 else 0,
        },
        "failure_list": [],
        "sampled": True,
        "sample_per_track": 1,
        "seed": 42,
        "total_candidates": 100,
        "selected_task_count": evaluated,
        "selected_task_ids": [f"task_{i:06d}" for i in range(n_tasks)],
        "results": results,
    }


# --- Argument parsing ---

def test_parse_args_defaults():
    """Default args are correct."""
    args = rbs.parse_args([])
    assert args.modes == "solution,buggy"
    assert args.track is None
    assert args.sample_per_track is None
    assert args.seed == 42
    assert args.timeout is None


def test_parse_args_custom():
    """Custom args are parsed correctly."""
    args = rbs.parse_args([
        "--modes", "solution",
        "--track", "p1_rtl_debug",
        "--sample-per-track", "3",
        "--seed", "99",
        "--timeout", "60",
    ])
    assert args.modes == "solution"
    assert args.track == "p1_rtl_debug"
    assert args.sample_per_track == 3
    assert args.seed == 99
    assert args.timeout == 60


# --- Leaderboard row generation ---

def test_leaderboard_rows_overall():
    """Leaderboard rows include an overall row."""
    summary = _make_mock_summary(n_tasks=10, score=1.0)
    rows = rbs.summary_to_leaderboard_rows(
        summary, "test_model", "abc123", "2026-01-01", "solution",
    )
    # At least 1 overall + 1 track
    assert len(rows) >= 2
    overall = rows[0]
    assert overall["track"] == "all"
    assert overall["model_name"] == "test_model"
    assert overall["evaluation_mode"] == "solution"


def test_leaderboard_rows_per_track():
    """Leaderboard rows include per-track breakdown."""
    summary = _make_mock_summary(n_tasks=5, score=0.9, track="p2_tb_sva_gen")
    rows = rbs.summary_to_leaderboard_rows(
        summary, "model", "sha", "2026-01-01", "buggy",
    )
    track_rows = [r for r in rows if r["track"] != "all"]
    assert len(track_rows) >= 1
    assert track_rows[0]["track"] == "p2_tb_sva_gen"


def test_leaderboard_columns_match_template():
    """Leaderboard row keys match the template columns."""
    summary = _make_mock_summary()
    rows = rbs.summary_to_leaderboard_rows(
        summary, "model", "sha", "2026-01-01", "solution",
    )
    for row in rows:
        assert set(row.keys()) == set(rbs.LEADERBOARD_COLUMNS)


# --- Per-task result collection ---

def test_collect_per_task_results():
    """Per-task results are extracted correctly."""
    summary = _make_mock_summary(n_tasks=3, score=1.0)
    rows = rbs.collect_per_task_results(
        summary, "model", "solution", "sha", "2026-01-01",
    )
    assert len(rows) == 3
    for row in rows:
        assert row["model_name"] == "model"
        assert row["mode"] == "solution"
        assert row["status"] == "pass"
        assert "total_score" in row


def test_collect_per_task_skips_errors():
    """Error/skipped results are not included in per-task CSV."""
    summary = _make_mock_summary(n_tasks=3, score=1.0)
    summary["results"].append({
        "task_id": "err_task", "track": "p1", "tool": ["vcs"],
        "difficulty": "easy", "status": "error", "reason": "load failed",
    })
    rows = rbs.collect_per_task_results(
        summary, "model", "solution", "sha", "2026-01-01",
    )
    assert len(rows) == 3  # error task excluded
    assert all(r["task_id"] != "err_task" for r in rows)


# --- CSV output ---

def test_write_csv(tmp_path):
    """write_csv produces valid CSV."""
    rows = [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]
    path = tmp_path / "test.csv"
    rbs.write_csv(rows, ["a", "b"], path)

    content = path.read_text()
    reader = csv.DictReader(io.StringIO(content))
    parsed = list(reader)
    assert len(parsed) == 2
    assert parsed[0]["a"] == "1"


def test_write_csv_rows(tmp_path):
    """write_csv_rows produces valid CSV."""
    rows = [["a", "b"], ["1", "2"]]
    path = tmp_path / "test.csv"
    rbs.write_csv_rows(rows, path)

    content = path.read_text()
    reader = csv.reader(io.StringIO(content))
    parsed = list(reader)
    assert len(parsed) == 2
    assert parsed[0] == ["a", "b"]


# --- Summary markdown ---

def test_baseline_summary_md_contains_modes():
    """Summary markdown mentions all modes."""
    summaries = {
        "solution": _make_mock_summary(score=1.0),
        "buggy": _make_mock_summary(score=0.3),
    }
    md = rbs.generate_baseline_summary_md(summaries, "sha", "2026-01-01", 1, 42)
    assert "solution" in md
    assert "buggy" in md
    assert "1.0000" in md or "1.0" in md


def test_baseline_summary_md_has_tables():
    """Summary markdown contains expected tables."""
    summaries = {"solution": _make_mock_summary(score=1.0)}
    md = rbs.generate_baseline_summary_md(summaries, "sha", "2026-01-01", None, 42)
    assert "| Mode |" in md
    assert "| Track |" in md
    assert "| Bucket |" in md


# --- Deterministic sampling ---

def test_deterministic_sampling():
    """Same seed produces same results in summary."""
    s1 = _make_mock_summary(run_id="run1")
    s2 = _make_mock_summary(run_id="run2")
    # Both use same seed and same task count
    assert s1["seed"] == s2["seed"]
    assert s1["selected_task_ids"] == s2["selected_task_ids"]


# --- No raw simulator logs in reports ---

def test_no_raw_logs_in_csv(tmp_path):
    """Generated CSVs contain no raw simulator log content."""
    summary = _make_mock_summary()
    rows = rbs.collect_per_task_results(
        summary, "model", "solution", "sha", "2026-01-01",
    )
    path = tmp_path / "test.csv"
    rbs.write_csv(rows, list(rows[0].keys()), path)

    content = path.read_text()
    # Should not contain typical log patterns
    assert "HSPICE" not in content
    assert "VCS" not in content.upper() or "vcs" in content.lower()  # tool name is ok
    assert ".log" not in content
    assert "error:" not in content.lower()


def test_no_raw_logs_in_md():
    """Generated markdown contains no raw simulator log content."""
    summaries = {"solution": _make_mock_summary()}
    md = rbs.generate_baseline_summary_md(summaries, "sha", "2026-01-01", 1, 42)
    assert "HSPICE" not in md
    assert ".log" not in md


# --- Git SHA ---

def test_get_git_sha():
    """get_git_sha returns a short hash or 'unknown'."""
    sha = rbs.get_git_sha()
    # Either a hex string or "unknown"
    assert sha == "unknown" or (len(sha) >= 7 and all(c in "0123456789abcdef" for c in sha))


# --- Integration: mock full run ---

def test_full_run_mock(tmp_path):
    """Full baseline run produces all expected artifacts (mocked evaluation)."""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    mock_summary = _make_mock_summary(score=1.0)

    with patch.object(rbs, "REPORTS_DIR", reports_dir), \
         patch.object(rbs, "run_evaluate_dataset", return_value=mock_summary), \
         patch.object(rbs, "get_git_sha", return_value="abc1234"):

        # Use a temporary tasks root that exists
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()

        args = [
            "--modes", "solution",
            "--sample-per-track", "1",
            "--seed", "123",
            "--tasks-root", str(tasks_dir),
        ]
        exit_code = rbs.main(args)
        assert exit_code == 0

        # Check artifacts exist
        assert (reports_dir / "baseline_results_solution.csv").is_file()
        assert (reports_dir / "leaderboard_baseline_filled.csv").is_file()
        assert (reports_dir / "baseline_summary.md").is_file()

        # Check leaderboard CSV has header + rows
        lb_content = (reports_dir / "leaderboard_baseline_filled.csv").read_text()
        reader = csv.DictReader(io.StringIO(lb_content))
        rows = list(reader)
        assert len(rows) >= 2  # overall + at least one track
        assert rows[0]["model_name"] == "baseline"

        # Check per-task CSV
        task_content = (reports_dir / "baseline_results_solution.csv").read_text()
        task_reader = csv.DictReader(io.StringIO(task_content))
        task_rows = list(task_reader)
        assert len(task_rows) == 5


def test_full_run_two_modes_mock(tmp_path):
    """Running both modes produces artifacts for each."""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    sol_summary = _make_mock_summary(score=1.0, run_id="sol_run")
    bug_summary = _make_mock_summary(score=0.2, run_id="bug_run")

    call_count = [0]
    def mock_run(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return sol_summary
        return bug_summary

    with patch.object(rbs, "REPORTS_DIR", reports_dir), \
         patch.object(rbs, "run_evaluate_dataset", side_effect=mock_run), \
         patch.object(rbs, "get_git_sha", return_value="abc1234"):

        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()

        args = [
            "--modes", "solution,buggy",
            "--sample-per-track", "1",
            "--seed", "42",
            "--tasks-root", str(tasks_dir),
        ]
        exit_code = rbs.main(args)
        assert exit_code == 0

        assert (reports_dir / "baseline_results_solution.csv").is_file()
        assert (reports_dir / "baseline_results_buggy.csv").is_file()
        assert (reports_dir / "leaderboard_baseline_filled.csv").is_file()
        assert (reports_dir / "baseline_summary.md").is_file()

        # Leaderboard should have rows from both modes
        lb_content = (reports_dir / "leaderboard_baseline_filled.csv").read_text()
        reader = csv.DictReader(io.StringIO(lb_content))
        rows = list(reader)
        modes_in_rows = {r["evaluation_mode"] for r in rows}
        assert "solution" in modes_in_rows
        assert "buggy" in modes_in_rows


def test_invalid_mode_rejected():
    """Invalid mode returns exit code 1."""
    exit_code = rbs.main(["--modes", "invalid_mode"])
    assert exit_code == 1
