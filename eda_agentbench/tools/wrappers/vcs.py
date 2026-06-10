"""VCS tool wrapper."""

from __future__ import annotations

import subprocess
from pathlib import Path


class VCSWrapper:
    """Wraps VCS compilation and simulation."""

    def __init__(self, env: dict[str, str]):
        self.env = env

    def compile(self, work_dir: Path, source_files: list[str],
                output: str = "simv", timeout: int = 120) -> tuple[bool, str]:
        cmd = ["vcs", "-full64", "-sverilog"] + source_files + ["-o", output]
        try:
            result = subprocess.run(
                cmd, cwd=work_dir, env=self.env,
                capture_output=True, text=True, timeout=timeout,
            )
            return result.returncode == 0, result.stdout + "\n" + result.stderr
        except subprocess.TimeoutExpired:
            return False, "VCS compilation timed out"
        except FileNotFoundError:
            return False, "VCS not found in PATH"

    def simulate(self, work_dir: Path, simv: str = "simv",
                 timeout: int = 60) -> tuple[bool, str]:
        cmd = [f"./{simv}"]
        try:
            result = subprocess.run(
                cmd, cwd=work_dir, env=self.env,
                capture_output=True, text=True, timeout=timeout,
            )
            return result.returncode == 0, result.stdout + "\n" + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Simulation timed out"
        except FileNotFoundError:
            return False, f"Simulator {simv} not found"
