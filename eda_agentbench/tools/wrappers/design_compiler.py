"""Design Compiler (dc_shell) tool wrapper."""

from __future__ import annotations

import subprocess
from pathlib import Path


class DesignCompilerWrapper:
    """Wraps dc_shell invocation for synthesis and constraint checking."""

    def __init__(self, env: dict[str, str]):
        self.env = env

    def run(self, work_dir: Path, script: str = "run.tcl",
            timeout: int = 300) -> tuple[bool, str]:
        """Run dc_shell on a TCL script. Returns (success, output)."""
        dc_cmd = self.env.get("EDA_DC_CMD", "dc_shell")
        cmd = [dc_cmd, "-f", script]
        try:
            result = subprocess.run(
                cmd, cwd=work_dir, env=self.env,
                capture_output=True, text=True, timeout=timeout,
            )
            output = result.stdout + "\n" + result.stderr
            return result.returncode == 0, output
        except subprocess.TimeoutExpired:
            return False, "dc_shell timed out"
        except FileNotFoundError:
            return False, f"dc_shell not found at '{dc_cmd}'"
