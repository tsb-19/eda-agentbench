"""Workspace creation, snapshotting, and change detection for agentic runs.

Security model:
- Agent workspace: visible + editable files ONLY. No hidden/oracle/scoring files.
- Evaluator workspace: agent output + hidden files merged. Created after agent exits.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path


def create_agent_workspace(task_path: Path, meta: dict) -> Path:
    """Create agent-visible workspace with ONLY visible+editable files.

    Hidden, oracle, solution, and scoring files are NEVER copied here.
    The agent process must not be able to read them.
    """
    work_dir = Path(tempfile.mkdtemp(prefix="eda_agent_"))
    is_p5 = meta.get("track") == "p5_spice_deck_debug"

    if is_p5:
        src_visible = task_path / "visible"
    else:
        src_visible = task_path / "files"
    if src_visible.is_dir():
        shutil.copytree(src_visible, work_dir, dirs_exist_ok=True)

    return work_dir


def create_evaluator_workspace(task_path: Path, meta: dict, agent_workspace: Path) -> Path:
    """Create evaluator-private workspace by merging agent output + hidden files.

    After the agent finishes, this workspace is used for EDA tool execution
    and evaluation. Hidden/oracle files from the task root are added here,
    along with the agent's edits from the agent workspace.
    """
    eval_dir = Path(tempfile.mkdtemp(prefix="eda_eval_"))
    is_p5 = meta.get("track") == "p5_spice_deck_debug"
    editable = set(meta["files"]["editable"])

    if is_p5:
        # Start with visible files from task
        src_visible = task_path / "visible"
        if src_visible.is_dir():
            shutil.copytree(src_visible, eval_dir, dirs_exist_ok=True)
        # Overlay agent's edits (editable .sp files)
        for ef in editable:
            edit_name = Path(ef).name
            src = agent_workspace / edit_name
            if src.is_file():
                shutil.copy2(src, eval_dir / edit_name)
    else:
        # Start with visible files from task
        src_files = task_path / "files"
        if src_files.is_dir():
            shutil.copytree(src_files, eval_dir, dirs_exist_ok=True)
        # Overlay agent's edits (editable files only)
        for ef in editable:
            src = agent_workspace / ef
            if src.is_file():
                shutil.copy2(src, eval_dir / ef)

    # Copy hidden files from task root (evaluator-only, never seen by agent)
    src_hidden = task_path / "hidden"
    if src_hidden.is_dir():
        shutil.copytree(src_hidden, eval_dir, dirs_exist_ok=True)

    return eval_dir


def snapshot_workspace(workspace: Path) -> dict[str, str]:
    """Compute SHA-256 of every file in workspace. Returns {relative_path: hex}."""
    snapshots: dict[str, str] = {}
    for fpath in sorted(workspace.rglob("*")):
        if fpath.is_file():
            rel = str(fpath.relative_to(workspace))
            snapshots[rel] = _sha256(fpath)
    return snapshots


def compute_file_changes(
    before: dict[str, str],
    after: dict[str, str],
) -> dict[str, str]:
    """Compare before/after snapshots. Returns {path: 'added'|'modified'|'deleted'}."""
    changes: dict[str, str] = {}
    all_paths = set(before) | set(after)
    for path in sorted(all_paths):
        in_before = path in before
        in_after = path in after
        if in_before and not in_after:
            changes[path] = "deleted"
        elif not in_before and in_after:
            changes[path] = "added"
        elif before[path] != after[path]:
            changes[path] = "modified"
    return changes


def detect_forbidden_modifications(
    changes: dict[str, str],
    forbidden_files: list[str],
) -> tuple[bool, list[str]]:
    """Check if any forbidden files were modified/added/deleted.

    Returns: (clean, list_of_violations).
    """
    violations: list[str] = []
    for fpath, change_type in changes.items():
        for forbidden in forbidden_files:
            if fpath == forbidden or fpath.endswith("/" + forbidden) or forbidden.endswith("/" + fpath):
                violations.append(f"{fpath} ({change_type})")
                break
    return len(violations) == 0, violations


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
