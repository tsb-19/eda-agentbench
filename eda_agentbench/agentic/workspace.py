"""Workspace creation, snapshotting, and change detection for agentic runs."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path


def create_workspace(task_path: Path, meta: dict) -> Path:
    """Create a fresh temporary workspace from task files.

    Handles standard (files/) and P5 (visible/) layouts.
    Copies hidden/ contents for EDA tool execution.

    Returns: Path to workspace temp directory.
    """
    work_dir = Path(tempfile.mkdtemp(prefix="eda_agentic_"))
    is_p5 = meta.get("track") == "p5_spice_deck_debug"

    # Copy visible files
    if is_p5:
        src_visible = task_path / "visible"
    else:
        src_visible = task_path / "files"
    if src_visible.is_dir():
        shutil.copytree(src_visible, work_dir, dirs_exist_ok=True)

    # Copy hidden files (needed for EDA tool scripts)
    src_hidden = task_path / "hidden"
    if src_hidden.is_dir():
        shutil.copytree(src_hidden, work_dir, dirs_exist_ok=True)

    return work_dir


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
        # Match against forbidden list (both with and without leading components)
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
