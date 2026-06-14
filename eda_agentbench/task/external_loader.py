"""Load and validate tasks from a generated bundle (produced by the in-repo datagen/ module)."""

from __future__ import annotations

import json
from pathlib import Path


class ExternalBundleError(Exception):
    pass


_REQUIRED_GRADER_FIELDS = ["task_id", "success_criteria", "command_template", "backend"]
_REQUIRED_MANIFEST_FIELDS = ["task_id", "backend", "backend_env_var", "editable_files", "grader_contract_file"]


def load_manifest(manifest_path: Path) -> list[dict]:
    """Load manifest.jsonl, returning list of entry dicts."""
    if not manifest_path.is_file():
        raise ExternalBundleError(f"Manifest not found: {manifest_path}")
    entries: list[dict] = []
    for i, line in enumerate(manifest_path.read_text().splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            raise ExternalBundleError(f"Invalid JSON on line {i+1} of {manifest_path}: {e}")
        for field in _REQUIRED_MANIFEST_FIELDS:
            if field not in entry:
                raise ExternalBundleError(f"Missing '{field}' in manifest line {i+1}")
        entries.append(entry)
    return entries


def load_grader_contract(contract_path: Path) -> dict:
    """Load and validate a grader_contract.json file."""
    if not contract_path.is_file():
        raise ExternalBundleError(f"Grader contract not found: {contract_path}")
    data = json.loads(contract_path.read_text())
    for field in _REQUIRED_GRADER_FIELDS:
        if field not in data:
            raise ExternalBundleError(f"Missing '{field}' in {contract_path}")
    sc = data.get("success_criteria", {})
    if not sc.get("execution_based"):
        raise ExternalBundleError(
            f"success_criteria.execution_based must be true in {contract_path}")
    return data


def validate_external_task(task_dir: Path, manifest_entry: dict) -> list[str]:
    """Validate an external bundle task directory. Returns list of error strings."""
    errors: list[str] = []
    task_id = manifest_entry["task_id"]

    # grader_contract.json
    contract_path = task_dir / "grader_contract.json"
    if not contract_path.is_file():
        errors.append(f"{task_id}: grader_contract.json missing")
    else:
        try:
            contract = load_grader_contract(contract_path)
            if contract["task_id"] != task_id:
                errors.append(f"{task_id}: task_id mismatch in grader_contract")
        except ExternalBundleError as e:
            errors.append(f"{task_id}: {e}")

    # editable_files must be under visible/
    for ef in manifest_entry.get("editable_files", []):
        if not ef.startswith("visible/"):
            errors.append(f"{task_id}: editable_file not under visible/: {ef}")
        elif not (task_dir / ef).is_file():
            errors.append(f"{task_id}: editable_file not found: {ef}")

    # backend_env_var
    if manifest_entry.get("backend_env_var") != "EDA_HSPICE_CMD":
        errors.append(f"{task_id}: backend_env_var must be EDA_HSPICE_CMD")

    # visible/ and hidden/ dirs
    if not (task_dir / "visible").is_dir():
        errors.append(f"{task_id}: visible/ directory missing")
    if not (task_dir / "hidden").is_dir():
        errors.append(f"{task_id}: hidden/ directory missing")
    if not (task_dir / "oracle").is_dir():
        errors.append(f"{task_id}: oracle/ directory missing")

    # prompt.md
    if not (task_dir / "prompt.md").is_file():
        errors.append(f"{task_id}: prompt.md missing")

    # No raw simulator logs should be present
    for ext in [".lis", ".log", ".raw", ".st0", ".sw0", ".trn", ".ac0", ".ic0"]:
        for f in task_dir.rglob(f"*{ext}"):
            errors.append(f"{task_id}: raw simulator output found: {f.relative_to(task_dir)}")

    return errors
