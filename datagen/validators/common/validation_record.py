"""Validation record creation and schema validation."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from validators.common.log_normalizer import compute_raw_log_hash, extract_errors, normalize_log


SCHEMA_PATH = Path(__file__).parent.parent.parent / "schemas" / "validation_record_schema.json"


def create_run_record(
    backend: str,
    expected_status: str,
    raw_log: str,
    returncode: int,
    raw_log_path: Optional[Path] = None,
) -> dict:
    """Create a single run record for a SPICE/VCS artifact.

    Args:
        backend: Backend name (vcs, hspice, spectre, pt).
        expected_status: Expected outcome (pass, fail, error).
        raw_log: Raw log output from the tool.
        returncode: Process exit code.
        raw_log_path: Path where raw log was stored (if any).

    Returns:
        Run record dict conforming to the schema.
    """
    raw_hash = compute_raw_log_hash(raw_log)
    normalized = normalize_log(raw_log)
    errors = extract_errors(normalized)

    # Determine actual status
    if returncode == 0 and not any(e["severity"] == "error" for e in errors):
        actual_status = "pass"
    elif returncode < 0:
        actual_status = "error"
    else:
        actual_status = "fail"

    return {
        "command_backend": backend,
        "expected_status": expected_status,
        "actual_status": actual_status,
        "exit_code": returncode,
        "normalized_errors": errors,
        "raw_log_sha256": raw_hash,
        "raw_log_retained": raw_log_path is not None,
    }


def determine_debug_contrast(
    buggy_run: dict,
    golden_run: dict,
    expected_error_category: Optional[str] = None,
) -> dict:
    """Determine debug contrast status from buggy and golden runs.

    For debug tasks (rtl_debug, spice_deck_debug):
    - buggy must fail (actual_status == "fail" or "error")
    - golden must pass (actual_status == "pass")
    - error category should match the task family

    Args:
        buggy_run: Run record for the buggy artifact.
        golden_run: Run record for the golden artifact.
        expected_error_category: Expected error category from task metadata.

    Returns:
        Debug contrast dict with analysis results.
    """
    buggy_failed = buggy_run["actual_status"] in ("fail", "error")
    golden_passed = golden_run["actual_status"] == "pass"

    # Check error category match
    observed_categories = set()
    for err in buggy_run.get("normalized_errors", []):
        observed_categories.add(err.get("category", "general"))

    error_category_match = True
    if expected_error_category:
        error_category_match = expected_error_category in observed_categories

    return {
        "buggy_failed_as_expected": buggy_failed,
        "golden_passed_as_expected": golden_passed,
        "error_category_match": error_category_match,
        "expected_error_category": expected_error_category,
        "observed_error_categories": sorted(observed_categories),
    }


def determine_validation_status(
    domain: str,
    buggy_run: Optional[dict] = None,
    golden_run: Optional[dict] = None,
    debug_contrast: Optional[dict] = None,
) -> str:
    """Determine the overall validation status.

    For debug tasks (rtl_debug, spice_deck_debug):
    - debug_contrast_verified: buggy failed AND golden passed
    - validation_failed: otherwise

    For non-debug tasks (timing_report_qa):
    - commercial_smoke_passed: golden/primary run passed
    - validation_failed: otherwise

    Args:
        domain: Task domain.
        buggy_run: Run record for buggy artifact.
        golden_run: Run record for golden artifact.
        debug_contrast: Debug contrast analysis.

    Returns:
        Validation status string.
    """
    if domain in ("rtl_debug", "spice_deck_debug"):
        if debug_contrast is None:
            return "validation_failed"
        if (debug_contrast.get("buggy_failed_as_expected") and
                debug_contrast.get("golden_passed_as_expected") and
                debug_contrast.get("error_category_match")):
            return "debug_contrast_verified"
        return "validation_failed"
    else:
        # For timing_report_qa and other non-debug domains
        if golden_run and golden_run.get("actual_status") == "pass":
            return "commercial_smoke_passed"
        return "validation_failed"


def create_validation_record(
    task_id: str,
    domain: str,
    backend: str,
    tool_name: str,
    tool_version: str,
    buggy_run: Optional[dict] = None,
    golden_run: Optional[dict] = None,
    fixed_run: Optional[dict] = None,
    debug_contrast: Optional[dict] = None,
    parsed_metrics: Optional[dict] = None,
    notes: str = "",
) -> dict:
    """Create a full validation record with structured runs.

    Args:
        task_id: Task identifier.
        domain: Task domain.
        backend: Backend name.
        tool_name: Canonical tool name.
        tool_version: Full tool version string (will be normalized).
        buggy_run: Run record for buggy artifact.
        golden_run: Run record for golden/fixed artifact.
        fixed_run: Optional run record for agent-produced fix.
        debug_contrast: Debug contrast analysis.
        parsed_metrics: Extracted metrics dict.
        notes: Free-text notes.

    Returns:
        Validation record dict conforming to the schema.
    """
    # Normalize version to major.minor
    version_parts = tool_version.split(".")
    if len(version_parts) >= 2:
        major = version_parts[0]
        minor = version_parts[1].split("-")[0]
        normalized_version = f"{major}.{minor}"
    else:
        normalized_version = tool_version

    # Determine overall validation status
    validation_status = determine_validation_status(
        domain, buggy_run, golden_run, debug_contrast
    )

    record = {
        "task_id": task_id,
        "domain": domain,
        "backend": backend,
        "tool_name": tool_name,
        "tool_version_normalized": normalized_version,
        "validation_status": validation_status,
        "validation_time_utc": datetime.now(timezone.utc).isoformat(),
        "notes": notes,
    }

    if buggy_run:
        record["buggy_run"] = buggy_run
    if golden_run:
        record["golden_run"] = golden_run
    if fixed_run:
        record["fixed_run"] = fixed_run
    if debug_contrast:
        record["debug_contrast"] = debug_contrast
    if parsed_metrics:
        record["parsed_metrics"] = parsed_metrics

    return record


def validate_record_schema(record: dict) -> tuple:
    """Check that a validation record conforms to the schema.

    Args:
        record: Validation record dict.

    Returns:
        Tuple of (is_valid, list_of_errors).
    """
    try:
        import jsonschema

        with open(SCHEMA_PATH) as f:
            schema = json.load(f)

        jsonschema.validate(instance=record, schema=schema)
        return True, []
    except jsonschema.ValidationError as e:
        return False, [str(e)]
    except Exception as e:
        return False, [f"Schema validation error: {e}"]
