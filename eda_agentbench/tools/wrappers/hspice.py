"""HSPICE tool wrapper."""

from __future__ import annotations

import subprocess
from pathlib import Path


class HSPICEWrapper:
    """Wraps HSPICE simulation invocation."""

    def __init__(self, env: dict[str, str]):
        self.env = env

    def run(self, work_dir: Path, netlist: str = "circuit.sp",
            timeout: int = 120) -> tuple[bool, str, Path | None]:
        """Run HSPICE on a netlist. Returns (success, output, lis_path)."""
        cmd = ["hspice", "-i", netlist]
        try:
            result = subprocess.run(
                cmd, cwd=work_dir, env=self.env,
                capture_output=True, text=True, timeout=timeout,
            )
            output = result.stdout + "\n" + result.stderr
            lis_path = work_dir / netlist.replace(".sp", ".lis")
            if not lis_path.is_file():
                lis_path = None
            return result.returncode == 0, output, lis_path
        except subprocess.TimeoutExpired:
            return False, "HSPICE timed out", None
        except FileNotFoundError:
            return False, "HSPICE not found in PATH", None
