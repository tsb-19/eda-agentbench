#!/usr/bin/env python3
"""Import P5 SPICE deck debug tasks from external bundle."""
from __future__ import annotations
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eda_agentbench.task.external_loader import load_manifest, validate_external_task, ExternalBundleError

DEFAULT_BUNDLE = Path(__file__).resolve().parent.parent.parent / "eda-bench-prototypes" / "tasks_eval_private"
DEFAULT_DEST = Path(__file__).resolve().parent.parent / "tasks" / "p5_spice_deck_debug" / "imported"


def convert_metadata(manifest_entry: dict, contract: dict, bundle_root: Path) -> dict:
    """Convert external bundle metadata to main schema format."""
    task_id = manifest_entry["task_id"]
    editable = manifest_entry["editable_files"]

    task_src = bundle_root / task_id
    visible_files = [f"visible/{f.name}" for f in (task_src / "visible").iterdir() if f.is_file()]
    hidden_files = [f"hidden/{f.name}" for f in (task_src / "hidden").iterdir() if f.is_file()]
    forbidden = [f for f in visible_files if f not in editable]

    return {
        "task_id": task_id,
        "track": "p5_spice_deck_debug",
        "tool": ["hspice"],
        "difficulty": "easy",
        "data_type": "flow_synthetic",
        "resource_preset": "standard",
        "timeout_sec": manifest_entry.get("timeout_sec", 300),
        "max_tool_calls": 30,
        "max_patch_attempts": 8,
        "max_output_tokens": 32000,
        "files": {
            "visible": visible_files,
            "editable": editable,
            "hidden": hidden_files,
            "forbidden": forbidden,
        },
        "run_command": contract.get("command_template", "{hspice_cmd} {file}"),
        "scoring": {
            "weights": {
                "execution_pass": 0.9,
                "explanation": 0.1,
            },
            "evaluator": "spice_deck_debug.SPICEDeckDebugEvaluator",
        },
        "sanitizer": {"enabled": True},
        "source": "external_bundle",
        "expected_error_category": manifest_entry.get("expected_error_category"),
        "grader_contract": contract.get("success_criteria", {}),
    }


def import_task(task_id: str, manifest_entry: dict, bundle_root: Path,
                dest_root: Path, dry_run: bool = False) -> Path | None:
    """Import a single task from the external bundle."""
    src = bundle_root / task_id
    dst = dest_root / task_id

    if not src.is_dir():
        print(f"  ERROR: Source not found: {src}")
        return None

    contract_path = src / "grader_contract.json"
    try:
        contract = json.loads(contract_path.read_text())
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"  ERROR: {e}")
        return None

    errors = validate_external_task(src, manifest_entry)
    if errors:
        print(f"  VALIDATION ERRORS:")
        for e in errors:
            print(f"    {e}")
        return None

    if dry_run:
        print(f"  Would import {task_id} -> {dst}")
        return dst

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

    meta = convert_metadata(manifest_entry, contract, bundle_root)
    (dst / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")

    return dst


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Import P5 tasks from external bundle")
    parser.add_argument("--bundle-root", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--task", default=None, help="Import single task by ID")
    args = parser.parse_args()

    bundle_root = args.bundle_root.resolve()
    dest_root = args.dest.resolve()

    manifest_path = bundle_root / "manifest.jsonl"
    try:
        manifest = load_manifest(manifest_path)
    except ExternalBundleError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    if args.task:
        manifest = [e for e in manifest if e["task_id"] == args.task]
        if not manifest:
            print(f"ERROR: Task {args.task} not found in manifest")
            sys.exit(1)

    print(f"Importing {len(manifest)} P5 tasks from {bundle_root}")
    print(f"Destination: {dest_root}")
    print()

    dest_root.mkdir(parents=True, exist_ok=True)

    imported = 0
    failed = 0
    for entry in manifest:
        task_id = entry["task_id"]
        print(f"[{task_id}]")
        result = import_task(task_id, entry, bundle_root, dest_root, dry_run=args.dry_run)
        if result:
            imported += 1
            if not args.dry_run:
                print(f"  OK -> {result}")
        else:
            failed += 1

    print(f"\nDone: {imported} imported, {failed} failed")


if __name__ == "__main__":
    main()
