"""Task discovery and loading."""

from __future__ import annotations

import json
from pathlib import Path

from eda_agentbench.schema import validate_metadata


class TaskValidationError(Exception):
    pass


class TaskLoader:
    """Discovers and loads tasks from the tasks/ directory."""

    def __init__(self, tasks_root: Path):
        self.tasks_root = tasks_root

    def discover(self, track: str | None = None, recursive: bool = True) -> list[Path]:
        """Find all task directories, optionally filtered by track.

        Args:
            track: If set, only discover tasks under this track directory.
            recursive: If True, search subdirectories (e.g., generated/) for tasks.
        """
        results: list[Path] = []
        if track:
            track_dir = self.tasks_root / track
            if track_dir.is_dir():
                self._discover_in(track_dir, results, recursive)
        else:
            for track_dir in sorted(self.tasks_root.iterdir()):
                if track_dir.is_dir() and not track_dir.name.startswith("."):
                    self._discover_in(track_dir, results, recursive)
        return sorted(results, key=lambda p: str(p))

    def _discover_in(self, directory: Path, results: list[Path], recursive: bool) -> None:
        """Recursively discover task directories within a directory."""
        for d in sorted(directory.iterdir()):
            if not d.is_dir() or d.name.startswith("."):
                continue
            if (d / "metadata.json").is_file():
                results.append(d)
            elif recursive:
                self._discover_in(d, results, recursive)

    def load(self, task_path: Path) -> dict:
        """Load and validate a task. Returns metadata dict. Raises TaskValidationError."""
        meta_path = task_path / "metadata.json"
        if not meta_path.is_file():
            raise TaskValidationError(f"No metadata.json in {task_path}")

        meta = json.loads(meta_path.read_text())

        # Schema validation
        errors = validate_metadata(meta)
        if errors:
            raise TaskValidationError(f"Invalid metadata in {task_path}:\n" + "\n".join(errors))

        # Structural validation
        structural = self._validate_structure(task_path, meta)
        if structural:
            raise TaskValidationError(f"Structural errors in {task_path}:\n" + "\n".join(structural))

        return meta

    def _validate_structure(self, task_path: Path, meta: dict) -> list[str]:
        errors: list[str] = []
        files = meta["files"]

        # visible files must exist
        for f in files["visible"]:
            if not (task_path / "files" / f).is_file():
                errors.append(f"Visible file not found: files/{f}")

        # hidden files must exist
        for f in files["hidden"]:
            if not (task_path / "hidden" / f).is_file():
                errors.append(f"Hidden file not found: hidden/{f}")

        # solution dir must exist
        if not (task_path / "solution").is_dir():
            errors.append("solution/ directory not found")

        return errors
