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

    def discover(self, track: str | None = None) -> list[Path]:
        """Find all task directories, optionally filtered by track."""
        results: list[Path] = []
        if track:
            track_dir = self.tasks_root / track
            if track_dir.is_dir():
                for d in sorted(track_dir.iterdir()):
                    if d.is_dir() and (d / "metadata.json").is_file():
                        results.append(d)
        else:
            for track_dir in sorted(self.tasks_root.iterdir()):
                if track_dir.is_dir():
                    for d in sorted(track_dir.iterdir()):
                        if d.is_dir() and (d / "metadata.json").is_file():
                            results.append(d)
        return results

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
