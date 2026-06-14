"""HSPICE commercial validation adapter for SPICE deck debug tasks.

Requires EDA_HSPICE_CMD environment variable, or hspice in PATH as fallback.
Skips gracefully if neither is available.

For spice_deck_debug tasks, performs debug contrast validation:
1. Runs the buggy deck from visible/ (must fail)
2. Runs the golden/fixed deck from hidden/ (must pass)
3. Verifies error category matches task metadata
4. Only then marks as debug_contrast_verified

Raw logs stored under .local_runs/ only.
Normalized summaries stored under tasks_validated/.
"""

import json
import os
import shutil
from pathlib import Path

from validators.common.run_command import run_command
from validators.common.log_normalizer import compute_raw_log_hash, extract_errors, normalize_log
from validators.common.validation_record import (
    create_run_record,
    create_validation_record,
    determine_debug_contrast,
)


REPO_ROOT = Path(__file__).parent.parent.parent
LOCAL_RUNS_DIR = REPO_ROOT / ".local_runs"
VALIDATED_DIR = REPO_ROOT / "tasks_validated"


def get_hspice_cmd():
    """Get the HSPICE command from env var, or discover from PATH."""
    cmd = os.environ.get("EDA_HSPICE_CMD")
    if cmd:
        return cmd
    import shutil as _shutil
    found = _shutil.which("hspice")
    if found:
        return found
    return None


def run_single_deck(
    hspice_cmd: str,
    deck_path: Path,
    run_dir: Path,
    log_name: str,
    timeout_sec: int = 300,
) -> tuple:
    """Run HSPICE on a single deck file.

    Args:
        hspice_cmd: Path to hspice executable.
        deck_path: Path to the SPICE deck file.
        run_dir: Directory to store raw logs.
        log_name: Name for the raw log file.
        timeout_sec: Maximum execution time.

    Returns:
        Tuple of (result_dict, raw_log, log_path).
    """
    deck_abs = deck_path.resolve()
    hspice_args = [hspice_cmd, str(deck_abs)]

    print(f"[HSPICE] Running: {' '.join(hspice_args)}")
    result = run_command(hspice_args, timeout_sec=timeout_sec, cwd=deck_path.parent.parent)

    raw_log = result["stdout"] + "\n" + result["stderr"]
    log_path = run_dir / log_name
    log_path.write_text(raw_log)

    return result, raw_log, log_path


def validate_spice_task(
    task_dir: Path,
    task_id: str,
    timeout_sec: int = 300,
):
    """Validate a SPICE deck debug task using HSPICE with debug contrast.

    For spice_deck_debug tasks:
    - Runs buggy deck from visible/ (expects failure)
    - Runs golden deck from hidden/ (expects success)
    - Verifies debug contrast

    Args:
        task_dir: Path to the task directory (under tasks_candidates/).
        task_id: Task identifier.
        timeout_sec: Maximum execution time.

    Returns:
        Validation record dict, or None if HSPICE is not available.
    """
    hspice_cmd = get_hspice_cmd()
    if not hspice_cmd:
        print(f"[SKIP] EDA_HSPICE_CMD not set and hspice not in PATH, skipping for {task_id}")
        return None

    visible_dir = task_dir / "visible"
    hidden_dir = task_dir / "hidden"
    oracle_dir = task_dir / "oracle"

    if not visible_dir.exists():
        print(f"[SKIP] No visible/ directory in {task_dir}")
        return None

    # Find buggy deck in visible/
    buggy_files = (
        list(visible_dir.glob("*.sp"))
        + list(visible_dir.glob("*.spice"))
        + list(visible_dir.glob("*.cir"))
    )
    if not buggy_files:
        print(f"[SKIP] No SPICE files in {visible_dir}")
        return None

    # Find golden deck in hidden/ or oracle/
    golden_files = (
        list(hidden_dir.glob("*.sp"))
        + list(hidden_dir.glob("*.spice"))
        + list(hidden_dir.glob("*.cir"))
        + list(oracle_dir.glob("*.sp"))
        + list(oracle_dir.glob("*.spice"))
        + list(oracle_dir.glob("*.cir"))
    ) if hidden_dir.exists() or oracle_dir.exists() else []

    # Set up local runs directory
    run_dir = LOCAL_RUNS_DIR / "hspice" / task_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Read task metadata for expected error category
    meta_path = task_dir / "metadata.json"
    meta = {}
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)

    # Use expected_error_category from metadata (set by generator)
    expected_error_category = meta.get("expected_error_category")

    # === Run 1: Buggy deck ===
    print(f"\n[HSPICE] === Buggy run for {task_id} ===")
    buggy_deck = buggy_files[0]
    buggy_result, buggy_raw_log, buggy_log_path = run_single_deck(
        hspice_cmd, buggy_deck, run_dir, "buggy_raw.log", timeout_sec
    )
    buggy_run = create_run_record(
        backend="hspice",
        expected_status="fail",
        raw_log=buggy_raw_log,
        returncode=buggy_result["returncode"],
        raw_log_path=buggy_log_path,
    )
    print(f"[HSPICE] Buggy run: {buggy_run['actual_status']} (exit={buggy_result['returncode']})")

    # Clean up HSPICE output files from task directory
    _cleanup_hspice_outputs(task_dir)

    # === Run 2: Golden deck ===
    golden_run = None
    debug_contrast = None
    if golden_files:
        print(f"\n[HSPICE] === Golden run for {task_id} ===")
        golden_deck = golden_files[0]
        golden_result, golden_raw_log, golden_log_path = run_single_deck(
            hspice_cmd, golden_deck, run_dir, "golden_raw.log", timeout_sec
        )
        golden_run = create_run_record(
            backend="hspice",
            expected_status="pass",
            raw_log=golden_raw_log,
            returncode=golden_result["returncode"],
            raw_log_path=golden_log_path,
        )
        print(f"[HSPICE] Golden run: {golden_run['actual_status']} (exit={golden_result['returncode']})")

        # Clean up HSPICE output files
        _cleanup_hspice_outputs(task_dir)

        # === Debug contrast analysis ===
        debug_contrast = determine_debug_contrast(
            buggy_run, golden_run, expected_error_category
        )
        print(f"\n[HSPICE] === Debug Contrast ===")
        print(f"  Buggy failed as expected: {debug_contrast['buggy_failed_as_expected']}")
        print(f"  Golden passed as expected: {debug_contrast['golden_passed_as_expected']}")
        print(f"  Error category match: {debug_contrast['error_category_match']}")
        print(f"  Expected category: {debug_contrast['expected_error_category']}")
        print(f"  Observed categories: {debug_contrast['observed_error_categories']}")
    else:
        print(f"\n[HSPICE] No golden deck found — skipping debug contrast")

    # === Create validation record ===
    record = create_validation_record(
        task_id=task_id,
        domain="spice_deck_debug",
        backend="hspice",
        tool_name="Synopsys HSPICE",
        tool_version="unknown",
        buggy_run=buggy_run,
        golden_run=golden_run,
        debug_contrast=debug_contrast,
        parsed_metrics={"elapsed_sec": buggy_result["elapsed_sec"]},
        notes=f"Buggy exit={buggy_result['returncode']}, timed_out={buggy_result['timed_out']}",
    )

    # === Copy to tasks_validated/ ===
    validated_task_dir = VALIDATED_DIR / task_id
    if validated_task_dir.exists():
        shutil.rmtree(validated_task_dir)

    _cleanup_hspice_outputs(task_dir)
    print(f"[HSPICE] Copying task to {validated_task_dir}")
    shutil.copytree(task_dir, validated_task_dir)

    # Create validation/ subdirectory
    val_dir = validated_task_dir / "validation"
    val_dir.mkdir(exist_ok=True)

    # Save validation record
    with open(val_dir / "validation_record.json", "w") as f:
        json.dump(record, f, indent=2)

    # Save normalized errors for buggy run
    with open(val_dir / "normalized_errors.json", "w") as f:
        json.dump(buggy_run["normalized_errors"], f, indent=2)

    # Save raw log hashes
    with open(val_dir / "raw_log.sha256", "w") as f:
        f.write(f"buggy: {buggy_run['raw_log_sha256']}\n")
        if golden_run:
            f.write(f"golden: {golden_run['raw_log_sha256']}\n")

    # Update metadata in the validated copy
    meta_path = validated_task_dir / "metadata.json"
    with open(meta_path) as f:
        meta = json.load(f)
    meta["validation_status"] = record["validation_status"]
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    # Save record under .local_runs/ too
    with open(run_dir / "validation_record.json", "w") as f:
        json.dump(record, f, indent=2)

    print(f"\n[HSPICE] {task_id}: {record['validation_status']}")
    print(f"[HSPICE] Validated task: {validated_task_dir}")
    return record


def _cleanup_hspice_outputs(task_dir: Path):
    """Remove HSPICE output files from a directory."""
    for ext in ["*.st0", "*.sw0", "*.ac0", "*.ic0", "*.lis", "*.log", "*.raw"]:
        for f in task_dir.glob(ext):
            f.unlink(missing_ok=True)


def main():
    """CLI entry point for HSPICE validation."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m validators.hspice.validate_spice <task_dir>")
        sys.exit(1)

    task_dir = Path(sys.argv[1])
    task_id = task_dir.name

    record = validate_spice_task(task_dir, task_id)
    if record:
        print(json.dumps(record, indent=2))
    else:
        print("[SKIP] HSPICE not available")


if __name__ == "__main__":
    main()
