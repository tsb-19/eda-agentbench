"""Anti-cheat guard: SHA-256 snapshot and verification of forbidden files."""

from __future__ import annotations

import hashlib
from pathlib import Path


class ForbiddenModificationGuard:
    """Snapshots and verifies SHA-256 hashes of forbidden files."""

    def __init__(self):
        self._snapshots: dict[str, str] = {}  # relative_path -> sha256 hex

    def snapshot(self, base_dir: Path, forbidden_files: list[str]) -> None:
        """Record SHA-256 of every file in forbidden_files list."""
        for rel in forbidden_files:
            fpath = base_dir / rel
            if fpath.is_file():
                self._snapshots[rel] = self._sha256(fpath)

    def verify(self, base_dir: Path) -> tuple[bool, list[str]]:
        """Re-hash all snapshotted files. Returns (all_clean, list_of_mismatched_paths)."""
        mismatches: list[str] = []
        for rel, expected_hash in self._snapshots.items():
            fpath = base_dir / rel
            if not fpath.is_file():
                mismatches.append(f"{rel} (deleted)")
            elif self._sha256(fpath) != expected_hash:
                mismatches.append(rel)
        return len(mismatches) == 0, mismatches

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
