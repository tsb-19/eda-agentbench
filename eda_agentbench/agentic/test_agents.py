"""Test agent factories for agentic runner validation.

Each function returns a shell command string that can be passed to
run_single_agentic() as the agent_cmd parameter. These agents use
the EDA_WORKSPACE and EDA_TASK_PATH environment variables.
"""

from __future__ import annotations

from pathlib import Path


def make_noop_agent() -> str:
    """Agent that does nothing. Score should be ~0 (no answer produced)."""
    return "true"


def make_copy_solution_agent(task_path: Path) -> str:
    """Agent that copies all solution files into the workspace.

    For standard tasks (P1, P2, P4, P6 constraint): copies solution/ contents.
    For P5: copies hidden/ contents (golden fixed deck).
    """
    solution_dir = task_path / "solution"
    if solution_dir.is_dir():
        return f"cp -r {solution_dir}/* $EDA_WORKSPACE/ 2>/dev/null || true"
    # Fallback: try hidden/ (P5 layout)
    hidden_dir = task_path / "hidden"
    if hidden_dir.is_dir():
        return f"cp -r {hidden_dir}/* $EDA_WORKSPACE/ 2>/dev/null || true"
    return "true"


def make_copy_answer_agent(task_path: Path) -> str:
    """Agent that copies solution/answer.txt into the workspace.

    For QA tasks (P3, P6 QA). Score should be 1.0.
    """
    solution_answer = task_path / "solution" / "answer.txt"
    if solution_answer.is_file():
        return f"cp {solution_answer} $EDA_WORKSPACE/answer.txt"
    return "true"


def make_buggy_answer_agent() -> str:
    """Agent that writes a deliberately wrong answer. Score should be ~0."""
    return "echo WRONG_ANSWER > $EDA_WORKSPACE/answer.txt"
