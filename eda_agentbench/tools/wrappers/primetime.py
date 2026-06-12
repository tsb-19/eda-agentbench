"""PrimeTime (pt_shell) tool wrapper."""

from __future__ import annotations

import subprocess
from pathlib import Path


class PrimeTimeWrapper:
    """Wraps PrimeTime pt_shell invocation."""

    def __init__(self, env: dict[str, str]):
        self.env = env

    def run_script(self, work_dir: Path, script: str,
                   timeout: int = 120) -> tuple[bool, str]:
        """Run pt_shell with a tcl script. Returns (success, output)."""
        cmd = ["pt_shell", "-f", script]
        try:
            result = subprocess.run(
                cmd, cwd=work_dir, env=self.env,
                capture_output=True, text=True, timeout=timeout,
            )
            output = result.stdout + "\n" + result.stderr
            return result.returncode == 0, output
        except subprocess.TimeoutExpired:
            return False, "pt_shell timed out"
        except FileNotFoundError:
            return False, "pt_shell not found in PATH"

    def run_inline(self, work_dir: Path, commands: str,
                   timeout: int = 120) -> tuple[bool, str]:
        """Run pt_shell with inline tcl commands via -x. Returns (success, output)."""
        cmd = ["pt_shell", "-x", commands]
        try:
            result = subprocess.run(
                cmd, cwd=work_dir, env=self.env,
                capture_output=True, text=True, timeout=timeout,
            )
            output = result.stdout + "\n" + result.stderr
            return result.returncode == 0, output
        except subprocess.TimeoutExpired:
            return False, "pt_shell timed out"
        except FileNotFoundError:
            return False, "pt_shell not found in PATH"
