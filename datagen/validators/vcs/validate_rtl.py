"""VCS commercial validation adapter for RTL debug tasks.

Requires EDA_VCS_CMD environment variable. Skips gracefully if not set.
"""

import json
import os
import shutil
from pathlib import Path

from validators.common.run_command import run_command
from validators.common.validation_record import create_validation_record


LOCAL_RUNS_DIR = Path(__file__).parent.parent.parent / ".local_runs"


def get_vcs_cmd():
    """Get the VCS command from environment, or None if not set."""
    return os.environ.get("EDA_VCS_CMD")


def validate_rtl_task(
    task_dir: Path,
    task_id: str,
    timeout_sec: int = 300,
):
    """Validate an RTL debug task using VCS.

    Args:
        task_dir: Path to the task directory.
        task_id: Task identifier.
        timeout_sec: Maximum execution time.

    Returns:
        Validation record dict, or None if VCS is not available.
    """
    vcs_cmd = get_vcs_cmd()
    if not vcs_cmd:
        print(f"[SKIP] EDA_VCS_CMD not set, skipping VCS validation for {task_id}")
        return None

    visible_dir = task_dir / "visible"
    if not visible_dir.exists():
        print(f"[SKIP] No visible/ directory in {task_dir}")
        return None

    # Collect Verilog files from visible/
    verilog_files = list(visible_dir.glob("*.v")) + list(visible_dir.glob("*.sv"))
    if not verilog_files:
        print(f"[SKIP] No Verilog files in {visible_dir}")
        return None

    # Set up local runs directory
    run_dir = LOCAL_RUNS_DIR / "vcs" / task_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Run VCS compilation
    vcs_args = [vcs_cmd, "-full64", "-sverilog", "-o", str(run_dir / "simv")]
    vcs_args.extend(str(f) for f in verilog_files)

    result = run_command(vcs_args, timeout_sec=timeout_sec, cwd=task_dir)

    # Store raw log
    raw_log = result["stdout"] + "\n" + result["stderr"]
    log_path = run_dir / "vcs_raw.log"
    log_path.write_text(raw_log)

    # Create normalized record
    record = create_validation_record(
        task_id=task_id,
        backend="vcs",
        tool_name="Synopsys VCS",
        tool_version="unknown",
        raw_log=raw_log,
        returncode=result["returncode"],
        parsed_metrics={"elapsed_sec": result["elapsed_sec"]},
        notes=f"Timed out: {result['timed_out']}",
        raw_log_path=log_path,
    )

    # Save record
    record_path = run_dir / "validation_record.json"
    with open(record_path, "w") as f:
        json.dump(record, f, indent=2)

    print(f"[VCS] {task_id}: {record['status']} (exit={result['returncode']})")
    return record


def main():
    """CLI entry point for VCS validation."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m validators.vcs.validate_rtl <task_dir>")
        sys.exit(1)

    task_dir = Path(sys.argv[1])
    task_id = task_dir.name

    record = validate_rtl_task(task_dir, task_id)
    if record:
        print(json.dumps(record, indent=2))
    else:
        print("[SKIP] VCS not available")


if __name__ == "__main__":
    main()
