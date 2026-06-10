"""Spectre tool wrapper."""

from __future__ import annotations

import subprocess
from pathlib import Path


class SpectreWrapper:
    """Wraps Spectre simulation invocation."""

    def __init__(self, env: dict[str, str]):
        self.env = env

    def run(self, work_dir: Path, netlist: str = "circuit.scs",
            timeout: int = 120) -> tuple[bool, str, Path | None]:
        """Run Spectre on a netlist. Returns (success, output, raw_file).

        The raw_file is the path to the main output directory (spectre.out)
        or None if not found.
        """
        cmd = ["spectre", netlist, "+escchars", "+log", "spectre.out"]
        try:
            result = subprocess.run(
                cmd, cwd=work_dir, env=self.env,
                capture_output=True, text=True, timeout=timeout,
            )
            output = result.stdout + "\n" + result.stderr
            raw_dir = work_dir / "spectre.out"
            raw_file = raw_dir if raw_dir.is_dir() else None
            return result.returncode == 0, output, raw_file
        except subprocess.TimeoutExpired:
            return False, "Spectre timed out", None
        except FileNotFoundError:
            return False, "Spectre not found in PATH", None
