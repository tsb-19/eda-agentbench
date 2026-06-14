"""Generic command runner with timeout, exit code capture, and output collection."""

import subprocess
import time
from pathlib import Path
from typing import Optional


def run_command(
    cmd: list[str],
    timeout_sec: int = 300,
    cwd: Optional[Path] = None,
    env: Optional[dict[str, str]] = None,
    stdin_data: Optional[str] = None,
) -> dict:
    """Run a command with timeout and capture output.

    Args:
        cmd: Command and arguments as a list.
        timeout_sec: Maximum execution time in seconds.
        cwd: Working directory for the command.
        env: Environment variables (merged with current env).
        stdin_data: Optional string to pipe to stdin.

    Returns:
        Dict with keys: returncode, stdout, stderr, elapsed_sec, timed_out.
    """
    import os

    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)

    start = time.time()
    timed_out = False

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=cwd,
            env=merged_env,
            input=stdin_data,
        )
        elapsed = time.time() - start
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "elapsed_sec": round(elapsed, 3),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as e:
        elapsed = time.time() - start
        stdout = e.stdout or ""
        stderr = e.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return {
            "returncode": -1,
            "stdout": stdout,
            "stderr": stderr + "\n[TIMEOUT]",
            "elapsed_sec": round(elapsed, 3),
            "timed_out": True,
        }
    except FileNotFoundError:
        return {
            "returncode": -2,
            "stdout": "",
            "stderr": f"[ERROR] Command not found: {cmd[0]}",
            "elapsed_sec": 0.0,
            "timed_out": False,
        }
