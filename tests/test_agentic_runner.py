"""Tests for the agentic runner MVP.

All tests use tmp_path and real evaluators on synthetic QA tasks.
No EDA tools required.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Fixtures: minimal task directories
# ---------------------------------------------------------------------------

@pytest.fixture
def qa_task(tmp_path):
    """Create a minimal P3 QA task directory (no EDA tools needed)."""
    task_dir = tmp_path / "p3_timing_report_qa" / "smoke"
    task_dir.mkdir(parents=True)

    meta = {
        "task_id": "p3_timing_999999",
        "track": "p3_timing_report_qa",
        "tool": ["pt"],
        "difficulty": "easy",
        "data_type": "template_synthetic",
        "resource_preset": "fast",
        "timeout_sec": 30,
        "max_tool_calls": 10,
        "max_patch_attempts": 3,
        "max_output_tokens": 16000,
        "run_command": "echo QA",
        "files": {
            "visible": ["timing_report.rpt", "answer.txt"],
            "editable": ["answer.txt"],
            "hidden": [],
            "forbidden": ["timing_report.rpt"],
        },
        "scoring": {
            "evaluator": "timing_report_qa.TimingReportQAEvaluator",
            "weights": {
                "answer_match": 1.0,
            },
        },
        "answer": {
            "type": "numeric",
            "expected": "42.0",
            "tolerance": 0.01,
            "question_type": "wns",
        },
    }
    (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2))
    (task_dir / "prompt.md").write_text("What is the WNS?")

    files_dir = task_dir / "files"
    files_dir.mkdir()
    (files_dir / "timing_report.rpt").write_text(
        "Startpoint: clk\nEndpoint: reg_a\n slack: -42.00\n"
    )
    (files_dir / "answer.txt").write_text("WRONG\n")

    sol_dir = task_dir / "solution"
    sol_dir.mkdir()
    (sol_dir / "answer.txt").write_text("42.0\n")

    return task_dir


@pytest.fixture
def qa_task_p6(tmp_path):
    """Create a minimal P6 DC Synthesis QA task directory."""
    task_dir = tmp_path / "p6_dc_synthesis_qa" / "smoke"
    task_dir.mkdir(parents=True)

    meta = {
        "task_id": "p6_dc_syn_999999",
        "track": "p6_dc_synthesis_qa",
        "tool": ["dc"],
        "difficulty": "easy",
        "data_type": "template_synthetic",
        "resource_preset": "fast",
        "timeout_sec": 30,
        "max_tool_calls": 10,
        "max_patch_attempts": 3,
        "max_output_tokens": 16000,
        "run_command": "echo QA",
        "files": {
            "visible": ["synthesis_report.rpt", "answer.txt"],
            "editable": ["answer.txt"],
            "hidden": [],
            "forbidden": ["synthesis_report.rpt"],
        },
        "scoring": {
            "evaluator": "dc_synthesis_qa.DCSynthesisQAEvaluator",
            "weights": {
                "answer_match": 1.0,
            },
        },
        "answer": {
            "type": "numeric",
            "expected": "21250.75",
            "tolerance": 0.01,
            "question_type": "total_area",
        },
    }
    (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2))
    (task_dir / "prompt.md").write_text("What is the total area?")

    files_dir = task_dir / "files"
    files_dir.mkdir()
    (files_dir / "synthesis_report.rpt").write_text(
        "Total cell area: 21250.75\n"
    )
    (files_dir / "answer.txt").write_text("WRONG\n")

    sol_dir = task_dir / "solution"
    sol_dir.mkdir()
    (sol_dir / "answer.txt").write_text("21250.75\n")

    return task_dir


@pytest.fixture
def task_with_hidden(tmp_path):
    """Create a task with hidden files for security isolation tests."""
    task_dir = tmp_path / "p1_rtl_debug" / "test_task"
    task_dir.mkdir(parents=True)

    meta = {
        "task_id": "task_999999",
        "track": "p1_rtl_debug",
        "tool": ["vcs"],
        "difficulty": "easy",
        "data_type": "mutation_synthetic",
        "resource_preset": "fast",
        "timeout_sec": 30,
        "max_tool_calls": 10,
        "max_patch_attempts": 3,
        "max_output_tokens": 16000,
        "run_command": "bash run_public.sh && bash run_hidden.sh",
        "files": {
            "visible": ["design.sv", "run_public.sh"],
            "editable": ["design.sv"],
            "hidden": ["tb_hidden.sv", "run_hidden.sh"],
            "forbidden": ["run_public.sh"],
        },
        "scoring": {
            "evaluator": "rtl_debug.VCSRTLEvaluator",
            "weights": {
                "compile": 0.2,
                "public_test": 0.3,
                "hidden_test": 0.4,
                "explanation": 0.1,
            },
        },
    }
    (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2))
    (task_dir / "prompt.md").write_text("Fix the bug")

    files_dir = task_dir / "files"
    files_dir.mkdir()
    (files_dir / "design.sv").write_text("module top; endmodule\n")
    (files_dir / "run_public.sh").write_text("#!/bin/bash\necho PASS\n")

    hidden_dir = task_dir / "hidden"
    hidden_dir.mkdir()
    (hidden_dir / "tb_hidden.sv").write_text("module tb; /* secret testbench */ endmodule\n")
    (hidden_dir / "run_hidden.sh").write_text("#!/bin/bash\necho HIDDEN_PASS\n")

    sol_dir = task_dir / "solution"
    sol_dir.mkdir()
    (sol_dir / "design.sv").write_text("module top_fixed; endmodule\n")

    return task_dir


# ---------------------------------------------------------------------------
# Workspace tests
# ---------------------------------------------------------------------------

class TestWorkspace:
    def test_create_agent_workspace_qa(self, qa_task):
        from eda_agentbench.agentic.workspace import create_agent_workspace
        meta = json.loads((qa_task / "metadata.json").read_text())
        ws = create_agent_workspace(qa_task, meta)
        try:
            assert (ws / "timing_report.rpt").is_file()
            assert (ws / "answer.txt").is_file()
        finally:
            import shutil
            shutil.rmtree(ws, ignore_errors=True)

    def test_create_agent_workspace_no_hidden_files(self, task_with_hidden):
        """Agent workspace must NOT contain hidden files."""
        from eda_agentbench.agentic.workspace import create_agent_workspace
        meta = json.loads((task_with_hidden / "metadata.json").read_text())
        ws = create_agent_workspace(task_with_hidden, meta)
        try:
            # Visible files present
            assert (ws / "design.sv").is_file()
            assert (ws / "run_public.sh").is_file()
            # Hidden files ABSENT
            assert not (ws / "tb_hidden.sv").exists()
            assert not (ws / "run_hidden.sh").exists()
        finally:
            import shutil
            shutil.rmtree(ws, ignore_errors=True)

    def test_create_evaluator_workspace_has_hidden(self, task_with_hidden):
        """Evaluator workspace must contain hidden files."""
        from eda_agentbench.agentic.workspace import (
            create_agent_workspace, create_evaluator_workspace,
        )
        meta = json.loads((task_with_hidden / "metadata.json").read_text())
        agent_ws = create_agent_workspace(task_with_hidden, meta)
        eval_ws = create_evaluator_workspace(task_with_hidden, meta, agent_ws)
        try:
            # Visible files present
            assert (eval_ws / "design.sv").is_file()
            assert (eval_ws / "run_public.sh").is_file()
            # Hidden files present in evaluator workspace
            assert (eval_ws / "tb_hidden.sv").is_file()
            assert (eval_ws / "run_hidden.sh").is_file()
        finally:
            import shutil
            shutil.rmtree(agent_ws, ignore_errors=True)
            shutil.rmtree(eval_ws, ignore_errors=True)

    def test_evaluator_workspace_reflects_agent_edits(self, task_with_hidden):
        """Evaluator workspace should contain agent's edits overlaid on hidden files."""
        from eda_agentbench.agentic.workspace import (
            create_agent_workspace, create_evaluator_workspace,
        )
        meta = json.loads((task_with_hidden / "metadata.json").read_text())
        agent_ws = create_agent_workspace(task_with_hidden, meta)
        # Simulate agent editing design.sv
        (agent_ws / "design.sv").write_text("module top_fixed; endmodule\n")
        eval_ws = create_evaluator_workspace(task_with_hidden, meta, agent_ws)
        try:
            # Agent's edit should be in evaluator workspace
            assert "top_fixed" in (eval_ws / "design.sv").read_text()
            # Hidden files should also be present
            assert (eval_ws / "tb_hidden.sv").is_file()
        finally:
            import shutil
            shutil.rmtree(agent_ws, ignore_errors=True)
            shutil.rmtree(eval_ws, ignore_errors=True)


# ---------------------------------------------------------------------------
# Snapshot and change detection tests
# ---------------------------------------------------------------------------

class TestSnapshotAndChanges:
    def test_snapshot_workspace(self, tmp_path):
        from eda_agentbench.agentic.workspace import snapshot_workspace
        d = tmp_path / "ws"
        d.mkdir()
        (d / "a.txt").write_text("hello")
        (d / "b.txt").write_text("world")
        snap = snapshot_workspace(d)
        assert "a.txt" in snap
        assert "b.txt" in snap
        assert len(snap["a.txt"]) == 64  # SHA-256 hex

    def test_compute_file_changes_added(self, tmp_path):
        from eda_agentbench.agentic.workspace import compute_file_changes
        before = {"a.txt": "abc123"}
        after = {"a.txt": "abc123", "b.txt": "def456"}
        changes = compute_file_changes(before, after)
        assert changes == {"b.txt": "added"}

    def test_compute_file_changes_modified(self):
        from eda_agentbench.agentic.workspace import compute_file_changes
        before = {"a.txt": "abc123"}
        after = {"a.txt": "XYZ789"}
        changes = compute_file_changes(before, after)
        assert changes == {"a.txt": "modified"}

    def test_compute_file_changes_deleted(self):
        from eda_agentbench.agentic.workspace import compute_file_changes
        before = {"a.txt": "abc123", "b.txt": "def456"}
        after = {"a.txt": "abc123"}
        changes = compute_file_changes(before, after)
        assert changes == {"b.txt": "deleted"}

    def test_compute_file_changes_no_change(self):
        from eda_agentbench.agentic.workspace import compute_file_changes
        before = {"a.txt": "abc123"}
        after = {"a.txt": "abc123"}
        changes = compute_file_changes(before, after)
        assert changes == {}


# ---------------------------------------------------------------------------
# Forbidden modification tests
# ---------------------------------------------------------------------------

class TestForbiddenModifications:
    def test_clean(self):
        from eda_agentbench.agentic.workspace import detect_forbidden_modifications
        changes = {"answer.txt": "modified"}
        forbidden = ["timing_report.rpt"]
        clean, violations = detect_forbidden_modifications(changes, forbidden)
        assert clean is True
        assert violations == []

    def test_violation(self):
        from eda_agentbench.agentic.workspace import detect_forbidden_modifications
        changes = {"timing_report.rpt": "modified", "answer.txt": "modified"}
        forbidden = ["timing_report.rpt"]
        clean, violations = detect_forbidden_modifications(changes, forbidden)
        assert clean is False
        assert len(violations) == 1
        assert "timing_report.rpt" in violations[0]


# ---------------------------------------------------------------------------
# Hidden file isolation security tests
# ---------------------------------------------------------------------------

class TestHiddenIsolation:
    def test_hidden_files_absent_from_agent_workspace(self, task_with_hidden):
        """Agent workspace must not contain any hidden files."""
        from eda_agentbench.agentic.workspace import create_agent_workspace
        meta = json.loads((task_with_hidden / "metadata.json").read_text())
        ws = create_agent_workspace(task_with_hidden, meta)
        try:
            hidden_files = meta["files"]["hidden"]
            for hf in hidden_files:
                assert not (ws / hf).exists(), \
                    f"Hidden file {hf} found in agent workspace"
        finally:
            import shutil
            shutil.rmtree(ws, ignore_errors=True)

    def test_hidden_files_present_in_evaluator_workspace(self, task_with_hidden):
        """Evaluator workspace must contain hidden files for tool execution."""
        from eda_agentbench.agentic.workspace import (
            create_agent_workspace, create_evaluator_workspace,
        )
        meta = json.loads((task_with_hidden / "metadata.json").read_text())
        agent_ws = create_agent_workspace(task_with_hidden, meta)
        eval_ws = create_evaluator_workspace(task_with_hidden, meta, agent_ws)
        try:
            hidden_files = meta["files"]["hidden"]
            for hf in hidden_files:
                assert (eval_ws / hf).is_file(), \
                    f"Hidden file {hf} missing from evaluator workspace"
        finally:
            import shutil
            shutil.rmtree(agent_ws, ignore_errors=True)
            shutil.rmtree(eval_ws, ignore_errors=True)

    def test_agent_cannot_read_hidden_files(self, task_with_hidden):
        """Agent command that tries to read hidden files should fail."""
        from eda_agentbench.agentic.runner import run_single_agentic
        meta = json.loads((task_with_hidden / "metadata.json").read_text())
        # Agent tries to read hidden testbench
        agent_cmd = "cat $EDA_WORKSPACE/tb_hidden.sv 2>/dev/null && echo LEAKED || echo SAFE"
        runs_dir, score, result = run_single_agentic(
            task_with_hidden, agent_cmd, meta, timeout=30,
        )
        try:
            stdout = (runs_dir / "stdout.log").read_text()
            assert "LEAKED" not in stdout, \
                "Agent was able to read hidden file from workspace!"
            assert "SAFE" in stdout
        finally:
            import shutil
            shutil.rmtree(runs_dir, ignore_errors=True)

    def test_agent_cannot_list_hidden_files(self, task_with_hidden):
        """Agent should not see hidden files when listing workspace."""
        from eda_agentbench.agentic.runner import run_single_agentic
        meta = json.loads((task_with_hidden / "metadata.json").read_text())
        agent_cmd = "ls $EDA_WORKSPACE/"
        runs_dir, score, result = run_single_agentic(
            task_with_hidden, agent_cmd, meta, timeout=30,
        )
        try:
            stdout = (runs_dir / "stdout.log").read_text()
            assert "tb_hidden.sv" not in stdout
            assert "run_hidden.sh" not in stdout
            # But visible files should be listed
            assert "design.sv" in stdout
        finally:
            import shutil
            shutil.rmtree(runs_dir, ignore_errors=True)

    def test_solution_dir_not_in_agent_workspace(self, task_with_hidden):
        """Solution directory should not be accessible in agent workspace."""
        from eda_agentbench.agentic.workspace import create_agent_workspace
        meta = json.loads((task_with_hidden / "metadata.json").read_text())
        ws = create_agent_workspace(task_with_hidden, meta)
        try:
            assert not (ws / "solution").exists()
        finally:
            import shutil
            shutil.rmtree(ws, ignore_errors=True)

    def test_oracle_dir_not_in_agent_workspace(self, tmp_path):
        """Oracle directory (P5 layout) should not be in agent workspace."""
        from eda_agentbench.agentic.workspace import create_agent_workspace
        task_dir = tmp_path / "p5_task"
        (task_dir / "visible").mkdir(parents=True)
        (task_dir / "visible" / "bug.sp").write_text(".SUBCKT bug\n.ENDS")
        (task_dir / "hidden").mkdir()
        (task_dir / "hidden" / "fixed.sp").write_text(".SUBCKT fixed\n.ENDS")
        (task_dir / "oracle").mkdir()
        (task_dir / "oracle" / "answer.txt").write_text("The fix is...")
        meta = {
            "task_id": "spice_deck_debug_9999",
            "track": "p5_spice_deck_debug",
            "files": {
                "visible": ["bug.sp"],
                "editable": ["bug.sp"],
                "hidden": ["fixed.sp"],
                "forbidden": [],
            },
        }
        ws = create_agent_workspace(task_dir, meta)
        try:
            assert not (ws / "oracle").exists()
            assert not (ws / "hidden").exists()
            assert (ws / "bug.sp").is_file()
        finally:
            import shutil
            shutil.rmtree(ws, ignore_errors=True)


# ---------------------------------------------------------------------------
# Test agent factories
# ---------------------------------------------------------------------------

class TestAgentFactories:
    def test_noop_agent(self):
        from eda_agentbench.agentic.test_agents import make_noop_agent
        cmd = make_noop_agent()
        assert isinstance(cmd, str)
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        assert result.returncode == 0

    def test_copy_solution_agent(self, qa_task):
        from eda_agentbench.agentic.test_agents import make_copy_solution_agent
        cmd = make_copy_solution_agent(qa_task)
        assert "solution" in cmd or "hidden" in cmd

    def test_copy_answer_agent(self, qa_task):
        from eda_agentbench.agentic.test_agents import make_copy_answer_agent
        cmd = make_copy_answer_agent(qa_task)
        assert "answer.txt" in cmd

    def test_buggy_answer_agent(self):
        from eda_agentbench.agentic.test_agents import make_buggy_answer_agent
        cmd = make_buggy_answer_agent()
        assert "WRONG_ANSWER" in cmd


# ---------------------------------------------------------------------------
# End-to-end agentic run tests
# ---------------------------------------------------------------------------

class TestAgenticRun:
    def test_noop_agent_qa_scores_zero(self, qa_task):
        from eda_agentbench.agentic.runner import run_single_agentic
        from eda_agentbench.agentic.test_agents import make_noop_agent
        meta = json.loads((qa_task / "metadata.json").read_text())
        runs_dir, score, result = run_single_agentic(
            qa_task, make_noop_agent(), meta, timeout=30,
        )
        try:
            assert result.agent_exit_code == 0
            assert result.agent_timed_out is False
            assert result.anti_cheat_clean is True
            # No-op leaves wrong default answer, so score should be 0
            assert score.total_score == 0.0
            assert score.mode == "agentic"
        finally:
            import shutil
            shutil.rmtree(runs_dir, ignore_errors=True)

    def test_copy_answer_agent_qa_scores_one(self, qa_task):
        from eda_agentbench.agentic.runner import run_single_agentic
        from eda_agentbench.agentic.test_agents import make_copy_answer_agent
        meta = json.loads((qa_task / "metadata.json").read_text())
        runs_dir, score, result = run_single_agentic(
            qa_task, make_copy_answer_agent(qa_task), meta, timeout=30,
        )
        try:
            assert result.agent_exit_code == 0
            assert result.anti_cheat_clean is True
            assert score.total_score == 1.0
            assert score.mode == "agentic"
        finally:
            import shutil
            shutil.rmtree(runs_dir, ignore_errors=True)

    def test_buggy_answer_agent_scores_zero(self, qa_task):
        from eda_agentbench.agentic.runner import run_single_agentic
        from eda_agentbench.agentic.test_agents import make_buggy_answer_agent
        meta = json.loads((qa_task / "metadata.json").read_text())
        runs_dir, score, result = run_single_agentic(
            qa_task, make_buggy_answer_agent(), meta, timeout=30,
        )
        try:
            assert result.agent_exit_code == 0
            assert score.total_score == 0.0
        finally:
            import shutil
            shutil.rmtree(runs_dir, ignore_errors=True)

    def test_p6_qa_copy_answer_scores_one(self, qa_task_p6):
        from eda_agentbench.agentic.runner import run_single_agentic
        from eda_agentbench.agentic.test_agents import make_copy_answer_agent
        meta = json.loads((qa_task_p6 / "metadata.json").read_text())
        runs_dir, score, result = run_single_agentic(
            qa_task_p6, make_copy_answer_agent(qa_task_p6), meta, timeout=30,
        )
        try:
            assert result.agent_exit_code == 0
            assert score.total_score == 1.0
        finally:
            import shutil
            shutil.rmtree(runs_dir, ignore_errors=True)

    def test_forbidden_modification_zeroes_score(self, qa_task):
        from eda_agentbench.agentic.runner import run_single_agentic
        meta = json.loads((qa_task / "metadata.json").read_text())
        # Agent that modifies the forbidden file
        agent_cmd = "echo HACKED > $EDA_WORKSPACE/timing_report.rpt"
        runs_dir, score, result = run_single_agentic(
            qa_task, agent_cmd, meta, timeout=30,
        )
        try:
            assert result.anti_cheat_clean is False
            assert len(result.forbidden_violations) > 0
            assert score.total_score == 0.0
            assert score.anti_cheat["forbidden_files_modified"] is True
        finally:
            import shutil
            shutil.rmtree(runs_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Timeout handling
# ---------------------------------------------------------------------------

class TestTimeout:
    def test_timeout_handling(self, qa_task):
        from eda_agentbench.agentic.runner import run_single_agentic
        meta = json.loads((qa_task / "metadata.json").read_text())
        # Agent that sleeps longer than timeout
        agent_cmd = "sleep 60"
        runs_dir, score, result = run_single_agentic(
            qa_task, agent_cmd, meta, timeout=2,
        )
        try:
            assert result.agent_timed_out is True
            assert result.agent_exit_code == -1
        finally:
            import shutil
            shutil.rmtree(runs_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Artifact output tests
# ---------------------------------------------------------------------------

class TestArtifacts:
    def test_transcript_jsonl_structure(self, qa_task):
        from eda_agentbench.agentic.runner import run_single_agentic
        from eda_agentbench.agentic.test_agents import make_noop_agent
        meta = json.loads((qa_task / "metadata.json").read_text())
        runs_dir, score, result = run_single_agentic(
            qa_task, make_noop_agent(), meta, timeout=30,
        )
        try:
            tpath = runs_dir / "transcript.jsonl"
            assert tpath.is_file()
            lines = [json.loads(line) for line in tpath.read_text().strip().split("\n")]
            types = [e["type"] for e in lines]
            assert "start" in types
            assert "end" in types
            assert "score" in types
        finally:
            import shutil
            shutil.rmtree(runs_dir, ignore_errors=True)

    def test_stdout_stderr_capture(self, qa_task):
        from eda_agentbench.agentic.runner import run_single_agentic
        meta = json.loads((qa_task / "metadata.json").read_text())
        agent_cmd = "echo HELLO_STDOUT && echo HELLO_STDERR >&2"
        runs_dir, score, result = run_single_agentic(
            qa_task, agent_cmd, meta, timeout=30,
        )
        try:
            assert (runs_dir / "stdout.log").is_file()
            assert (runs_dir / "stderr.log").is_file()
            assert "HELLO_STDOUT" in (runs_dir / "stdout.log").read_text()
            assert "HELLO_STDERR" in (runs_dir / "stderr.log").read_text()
        finally:
            import shutil
            shutil.rmtree(runs_dir, ignore_errors=True)

    def test_workspace_manifest_written(self, qa_task):
        from eda_agentbench.agentic.runner import run_single_agentic
        from eda_agentbench.agentic.test_agents import make_noop_agent
        meta = json.loads((qa_task / "metadata.json").read_text())
        runs_dir, score, result = run_single_agentic(
            qa_task, make_noop_agent(), meta, timeout=30,
        )
        try:
            mpath = runs_dir / "workspace_manifest.json"
            assert mpath.is_file()
            manifest = json.loads(mpath.read_text())
            assert "before" in manifest
            assert "after" in manifest
        finally:
            import shutil
            shutil.rmtree(runs_dir, ignore_errors=True)

    def test_workspace_manifest_no_hidden_files(self, task_with_hidden):
        """Manifest should only contain agent-visible files, not hidden ones."""
        from eda_agentbench.agentic.runner import run_single_agentic
        from eda_agentbench.agentic.test_agents import make_noop_agent
        meta = json.loads((task_with_hidden / "metadata.json").read_text())
        runs_dir, score, result = run_single_agentic(
            task_with_hidden, make_noop_agent(), meta, timeout=30,
        )
        try:
            mpath = runs_dir / "workspace_manifest.json"
            manifest = json.loads(mpath.read_text())
            all_files = set(manifest["before"].keys()) | set(manifest["after"].keys())
            for hf in meta["files"]["hidden"]:
                assert hf not in all_files, \
                    f"Hidden file {hf} leaked into workspace_manifest.json"
        finally:
            import shutil
            shutil.rmtree(runs_dir, ignore_errors=True)

    def test_modified_files_json_written(self, qa_task):
        from eda_agentbench.agentic.runner import run_single_agentic
        from eda_agentbench.agentic.test_agents import make_copy_answer_agent
        meta = json.loads((qa_task / "metadata.json").read_text())
        runs_dir, score, result = run_single_agentic(
            qa_task, make_copy_answer_agent(qa_task), meta, timeout=30,
        )
        try:
            mpath = runs_dir / "modified_files.json"
            assert mpath.is_file()
            modified = json.loads(mpath.read_text())
            assert "changes" in modified
            assert "forbidden_violations" in modified
            # answer.txt should be modified
            assert "answer.txt" in modified["changes"]
        finally:
            import shutil
            shutil.rmtree(runs_dir, ignore_errors=True)

    def test_score_json_format(self, qa_task):
        from eda_agentbench.agentic.runner import run_single_agentic
        from eda_agentbench.agentic.test_agents import make_copy_answer_agent
        meta = json.loads((qa_task / "metadata.json").read_text())
        runs_dir, score, result = run_single_agentic(
            qa_task, make_copy_answer_agent(qa_task), meta, timeout=30,
        )
        try:
            spath = runs_dir / "score.json"
            assert spath.is_file()
            score_data = json.loads(spath.read_text())
            for field in ["schema_version", "task_id", "track", "mode",
                          "total_score", "components", "anti_cheat",
                          "resource_usage", "metadata"]:
                assert field in score_data, f"Missing field: {field}"
            assert score_data["mode"] == "agentic"
        finally:
            import shutil
            shutil.rmtree(runs_dir, ignore_errors=True)

    def test_metadata_json_written(self, qa_task):
        from eda_agentbench.agentic.runner import run_single_agentic
        from eda_agentbench.agentic.test_agents import make_noop_agent
        meta = json.loads((qa_task / "metadata.json").read_text())
        runs_dir, score, result = run_single_agentic(
            qa_task, make_noop_agent(), meta, timeout=30,
        )
        try:
            mpath = runs_dir / "metadata.json"
            assert mpath.is_file()
            run_meta = json.loads(mpath.read_text())
            assert run_meta["mode"] == "agentic"
            assert run_meta["task_id"] == "p3_timing_999999"
            assert "agent_cmd" in run_meta
        finally:
            import shutil
            shutil.rmtree(runs_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------

class TestCLI:
    @staticmethod
    def run_bench(*args):
        result = subprocess.run(
            [sys.executable, "-m", "eda_agentbench", *args],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        return result.returncode, result.stdout, result.stderr

    def test_run_agent_help(self):
        rc, stdout, stderr = self.run_bench("run-agent", "--help")
        assert rc == 0
        assert "--agent-cmd" in stdout

    def test_run_agent_dataset_help(self):
        rc, stdout, stderr = self.run_bench("run-agent-dataset", "--help")
        assert rc == 0
        assert "--agent-cmd" in stdout
        assert "--sample-per-track" in stdout

    def test_run_agent_on_qa_task(self, qa_task):
        meta = json.loads((qa_task / "metadata.json").read_text())
        rc, stdout, stderr = self.run_bench(
            "run-agent", str(qa_task),
            "--agent-cmd", "cp $EDA_TASK_PATH/solution/answer.txt $EDA_WORKSPACE/",
        )
        assert rc == 0, f"Failed: {stderr}"
        assert "Score:" in stdout
        assert "1.00" in stdout

    def test_run_agent_noop_on_qa_task(self, qa_task):
        rc, stdout, stderr = self.run_bench(
            "run-agent", str(qa_task),
            "--agent-cmd", "true",
        )
        assert rc == 0, f"Failed: {stderr}"
        assert "Score:" in stdout
