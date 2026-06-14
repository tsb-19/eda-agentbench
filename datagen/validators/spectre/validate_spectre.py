"""Spectre commercial validation adapter for SPICE deck debug tasks.

Requires EDA_SPECTRE_CMD environment variable. Skips gracefully if not set.
"""

import json
import os
from pathlib import Path

from validators.common.run_command import run_command
from validators.common.validation_record import create_validation_record


LOCAL_RUNS_DIR = Path(__file__).parent.parent.parent / ".local_runs"


def get_spectre_cmd():
    """Get the Spectre command from environment, or None if not set."""
    return os.environ.get("EDA_SPECTRE_CMD")


def validate_spectre_task(
    task_dir: Path,
    task_id: str,
    timeout_sec: int = 300,
):
    """Validate a SPICE deck debug task using Spectre.

    Args:
        task_dir: Path to the task directory.
        task_id: Task identifier.
        timeout_sec: Maximum execution time.

    Returns:
        Validation record dict, or None if Spectre is not available.
    """
    spectre_cmd = get_spectre_cmd()
    if not spectre_cmd:
        print(f"[SKIP] EDA_SPECTRE_CMD not set, skipping Spectre validation for {task_id}")
        return None

    visible_dir = task_dir / "visible"
    if not visible_dir.exists():
        print(f"[SKIP] No visible/ directory in {task_dir}")
        return None

    # Find Spectre netlist files
    netlist_files = (
        list(visible_dir.glob("*.scs"))
        + list(visible_dir.glob("*.sp"))
        + list(visible_dir.glob("*.spice"))
    )
    if not netlist_files:
        print(f"[SKIP] No Spectre netlist files in {visible_dir}")
        return None

    # Set up local runs directory
    run_dir = LOCAL_RUNS_DIR / "spectre" / task_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Run Spectre
    netlist = netlist_files[0]
    spectre_args = [spectre_cmd, str(netlist), "-format", "psfascii", "-raw", str(run_dir / "raw")]

    result = run_command(spectre_args, timeout_sec=timeout_sec, cwd=task_dir)

    # Store raw log
    raw_log = result["stdout"] + "\n" + result["stderr"]
    log_path = run_dir / "spectre_raw.log"
    log_path.write_text(raw_log)

    # Create normalized record
    record = create_validation_record(
        task_id=task_id,
        backend="spectre",
        tool_name="Cadence Spectre",
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

    print(f"[Spectre] {task_id}: {record['status']} (exit={result['returncode']})")
    return record


def main():
    """CLI entry point for Spectre validation."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m validators.spectre.validate_spectre <task_dir>")
        sys.exit(1)

    task_dir = Path(sys.argv[1])
    task_id = task_dir.name

    record = validate_spectre_task(task_dir, task_id)
    if record:
        print(json.dumps(record, indent=2))
    else:
        print("[SKIP] Spectre not available")


if __name__ == "__main__":
    main()
