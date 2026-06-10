"""Task validation utilities."""

from __future__ import annotations

from pathlib import Path


def check_submission_forbidden(submission_dir: Path, forbidden_files: list[str]) -> list[str]:
    """Check if submission contains any forbidden files. Returns list of violations."""
    violations: list[str] = []
    if not submission_dir.is_dir():
        return violations
    for f in forbidden_files:
        if (submission_dir / f).is_file():
            violations.append(f)
    return violations
