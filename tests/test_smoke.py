"""Integration smoke tests — run CLI commands and verify scores."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TASK_DIR = PROJECT_ROOT / "tasks" / "p1_rtl_debug" / "task_000001"


def run_bench(*args):
    """Run eda-bench CLI and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "-m", "eda_agentbench", *args],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    )
    return result.returncode, result.stdout, result.stderr


def latest_score_json():
    """Find the most recent score.json for task_000001."""
    runs_dir = PROJECT_ROOT / "runs" / "task_000001"
    if not runs_dir.is_dir():
        return None
    scores = sorted(runs_dir.glob("*/score.json"), key=lambda p: p.stat().st_mtime)
    return scores[-1] if scores else None


def test_detect_tools_finds_vcs():
    rc, stdout, stderr = run_bench("detect-tools")
    assert rc == 0
    assert "vcs" in stdout
    assert "YES" in stdout


def test_validate_task():
    rc, stdout, stderr = run_bench("validate-task", str(TASK_DIR))
    assert rc == 0
    assert "VALID" in stdout


def test_solution_scores_perfect():
    solution_dir = TASK_DIR / "solution"
    rc, stdout, stderr = run_bench("evaluate-task", str(TASK_DIR),
                                    "--submission", str(solution_dir))
    assert rc == 0, f"evaluate-task failed: {stderr}"
    score_path = latest_score_json()
    assert score_path is not None, "No score.json found"
    score = json.loads(score_path.read_text())
    assert score["total_score"] == 1.0, f"Expected 1.0, got {score['total_score']}"
    # objective_score = compile(0.1) + public(0.3) + hidden(0.5) = 0.9
    assert abs(score["objective_score"] - 0.9) < 0.01, f"Expected objective ~0.9, got {score['objective_score']}"
    assert score["passed"] is True


def test_buggy_scores_lower():
    buggy_dir = TASK_DIR / "buggy_submission"
    if not buggy_dir.is_dir():
        pytest.skip("buggy_submission not found")
    rc, stdout, stderr = run_bench("evaluate-task", str(TASK_DIR),
                                    "--submission", str(buggy_dir))
    assert rc == 0, f"evaluate-task failed: {stderr}"
    score_path = latest_score_json()
    assert score_path is not None
    score = json.loads(score_path.read_text())
    assert score["total_score"] < 1.0, f"Expected < 1.0, got {score['total_score']}"
    # At least one test must have failed
    comps = {c["name"]: c["raw_score"] for c in score["components"]}
    assert comps.get("public_test", 1.0) < 1.0 or comps.get("hidden_test", 1.0) < 1.0, \
        "Expected at least one test failure"


def test_forbidden_file_rejected():
    files_dir = TASK_DIR / "files"
    rc, stdout, stderr = run_bench("evaluate-task", str(TASK_DIR),
                                    "--submission", str(files_dir))
    # Should fail with anti-cheat
    assert rc != 0
    assert "ANTI-CHEAT FAIL" in stderr


def test_score_json_has_all_fields():
    solution_dir = TASK_DIR / "solution"
    run_bench("evaluate-task", str(TASK_DIR), "--submission", str(solution_dir))
    score_path = latest_score_json()
    assert score_path is not None
    score = json.loads(score_path.read_text())
    # Required fields
    for field in ["schema_version", "task_id", "track", "mode", "total_score",
                   "objective_score", "explanation_score", "components",
                   "anti_cheat", "resource_usage", "metadata"]:
        assert field in score, f"Missing field: {field}"
    # Components must have expected keys
    for comp in score["components"]:
        for key in ["name", "weight", "raw_score", "weighted_score", "details"]:
            assert key in comp, f"Component missing key: {key}"
