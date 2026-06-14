"""PrimeTime report parser for timing report QA tasks.

Requires EDA_PT_CMD environment variable. Skips gracefully if not set.
"""

import json
import os
import re
from pathlib import Path

from validators.common.run_command import run_command
from validators.common.validation_record import create_validation_record


LOCAL_RUNS_DIR = Path(__file__).parent.parent.parent / ".local_runs"


def get_pt_cmd():
    """Get the PrimeTime command from environment, or None if not set."""
    return os.environ.get("EDA_PT_CMD")


def parse_timing_report(report_text: str) -> dict:
    """Extract key metrics from a timing report.

    Args:
        report_text: Raw timing report text.

    Returns:
        Dict of parsed metrics.
    """
    metrics = {}

    # Extract slack values
    slack_matches = re.findall(r"slack\s*[:=]\s*([-\d.]+)\s*(?:ns|ps)", report_text, re.IGNORECASE)
    if slack_matches:
        metrics["slack_values"] = [float(s) for s in slack_matches]
        metrics["worst_slack"] = min(float(s) for s in slack_matches)

    # Extract setup/hold violation counts
    setup_violations = len(re.findall(r"(?i)setup.*violation", report_text))
    hold_violations = len(re.findall(r"(?i)hold.*violation", report_text))
    metrics["setup_violation_count"] = setup_violations
    metrics["hold_violation_count"] = hold_violations

    # Extract path count
    path_count = re.findall(r"(?i)(\d+)\s+path", report_text)
    if path_count:
        metrics["path_count"] = int(path_count[0])

    return metrics


def validate_timing_task(
    task_dir: Path,
    task_id: str,
    timeout_sec: int = 300,
):
    """Validate a timing report QA task using PrimeTime.

    Args:
        task_dir: Path to the task directory.
        task_id: Task identifier.
        timeout_sec: Maximum execution time.

    Returns:
        Validation record dict, or None if PrimeTime is not available.
    """
    pt_cmd = get_pt_cmd()
    if not pt_cmd:
        print(f"[SKIP] EDA_PT_CMD not set, skipping PrimeTime validation for {task_id}")
        return None

    visible_dir = task_dir / "visible"
    if not visible_dir.exists():
        print(f"[SKIP] No visible/ directory in {task_dir}")
        return None

    # Find timing report files
    report_files = (
        list(visible_dir.glob("*.rpt"))
        + list(visible_dir.glob("*.timing"))
        + list(visible_dir.glob("*.txt"))
    )
    if not report_files:
        print(f"[SKIP] No timing report files in {visible_dir}")
        return None

    # Set up local runs directory
    run_dir = LOCAL_RUNS_DIR / "pt" / task_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Run PrimeTime with a simple script to read and analyze the report
    pt_script = run_dir / "run_pt.tcl"
    report = report_files[0]
    pt_script.write_text(
        f"read_timing_report {report}\n"
        f"report_timing\n"
        f"exit\n"
    )

    pt_args = [pt_cmd, "-f", str(pt_script)]
    result = run_command(pt_args, timeout_sec=timeout_sec, cwd=task_dir)

    # Store raw log
    raw_log = result["stdout"] + "\n" + result["stderr"]
    log_path = run_dir / "pt_raw.log"
    log_path.write_text(raw_log)

    # Parse metrics from the report itself
    report_text = report.read_text()
    parsed_metrics = parse_timing_report(report_text)
    parsed_metrics["elapsed_sec"] = result["elapsed_sec"]

    # Create normalized record
    record = create_validation_record(
        task_id=task_id,
        backend="pt",
        tool_name="Synopsys PrimeTime",
        tool_version="unknown",
        raw_log=raw_log,
        returncode=result["returncode"],
        parsed_metrics=parsed_metrics,
        notes=f"Timed out: {result['timed_out']}",
        raw_log_path=log_path,
    )

    # Save record
    record_path = run_dir / "validation_record.json"
    with open(record_path, "w") as f:
        json.dump(record, f, indent=2)

    print(f"[PT] {task_id}: {record['status']} (exit={result['returncode']})")
    return record


def main():
    """CLI entry point for PrimeTime validation."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m validators.pt.parse_report <task_dir>")
        sys.exit(1)

    task_dir = Path(sys.argv[1])
    task_id = task_dir.name

    record = validate_timing_task(task_dir, task_id)
    if record:
        print(json.dumps(record, indent=2))
    else:
        print("[SKIP] PrimeTime not available")


if __name__ == "__main__":
    main()
