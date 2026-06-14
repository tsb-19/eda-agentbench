#!/usr/bin/env bash
# Batch package all HSPICE-validated SPICE tasks for public release.
#
# Iterates over tasks_validated/spice_deck_debug_*,
# requires validation_status=debug_contrast_verified,
# calls scripts/package_public_task.sh for each,
# writes tasks_public/manifest.jsonl and tasks_public/README.md.
#
# Usage:
#   bash scripts/package_spice_public_batch.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

echo "=== SPICE Public Batch Packaging ==="
echo ""

# Clean previous public tasks
rm -rf tasks_public/spice_deck_debug_*
mkdir -p tasks_public

MANIFEST="tasks_public/manifest.jsonl"
> "$MANIFEST"

PACKAGED=0
FAILED=0

for task_dir in tasks_validated/spice_deck_debug_*/; do
    [ -d "$task_dir" ] || continue
    task_name=$(basename "$task_dir")

    # Check validation_status
    status=$(python3 -c "import json; print(json.load(open('${task_dir}metadata.json'))['validation_status'])" 2>/dev/null || echo "unknown")

    if [ "$status" != "debug_contrast_verified" ]; then
        echo "[SKIP] $task_name: validation_status=$status (need debug_contrast_verified)"
        FAILED=$((FAILED + 1))
        continue
    fi

    # Package the task
    echo "--- Packaging $task_name ---"
    if bash scripts/package_public_task.sh "$task_dir" 2>&1; then
        PACKAGED=$((PACKAGED + 1))

        # Append to manifest
        python3 -c "
import json
meta = json.load(open('${task_dir}metadata.json'))
val = json.load(open('${task_dir}validation/validation_record.json'))
row = {
    'task_id': meta['task_id'],
    'domain': meta['domain'],
    'task_family': meta['task_family'],
    'difficulty': meta['difficulty'],
    'expected_error_category': meta.get('expected_error_category', ''),
    'validation_status': meta['validation_status'],
    'validated_backend': val['backend'],
    'public_release_safe': meta['public_release_safe'],
    'prompt_file': meta['prompt_file'],
    'visible_files': meta['visible_files'],
    'oracle_description': meta['oracle_description'],
    'license_notes': meta['license_notes'],
}
print(json.dumps(row), file=open('$MANIFEST', 'a'))
"
    else
        echo "[FAIL] $task_name: packaging failed"
        FAILED=$((FAILED + 1))
    fi
    echo ""
done

# Write README.md
cat > tasks_public/README.md << 'READMEEOF'
# EDA-Agent-Bench: Public SPICE Deck Debug Tasks

This directory contains the public-safe release of the SPICE deck debug task subset
from EDA-Agent-Bench.

## Contents

- **10 SPICE deck debug tasks** (`spice_deck_debug_0001` through `spice_deck_debug_0010`)
- **manifest.jsonl** — Machine-readable task index (one JSON object per line)

## Task Structure

Each task contains:
- `prompt.md` — Natural-language task description
- `metadata.json` — Task metadata and validation status
- `visible/` — Buggy SPICE deck visible to the agent
- `validation/` — Normalized validation results

## Validation

All tasks are **debug_contrast_verified** via commercial HSPICE validation:
- Buggy deck fails with the expected error category
- Golden/fixed deck passes
- Error category matches task metadata

## Error Categories Covered

| Category | Count | Description |
|----------|-------|-------------|
| missing_model | 2 | Model name typo or absent |
| missing_subckt | 2 | Undefined subcircuit |
| wrong_pin_count | 1 | Pin count mismatch |
| duplicate_element | 2 | Same element name used twice |
| missing_include | 1 | .include references nonexistent file |
| unsupported_dialect | 1 | Invalid model level |
| invalid_directive | 1 | Malformed .include |

## Safety

All tasks are verified to contain:
- No raw commercial tool logs
- No absolute local paths
- No license variable references
- No hostname/username leakage
- No raw simulator output files

## License

Apache-2.0. Synthetic content only — no proprietary circuit data.
READMEEOF

echo ""
echo "=== Batch Packaging Summary ==="
echo "Packaged: $PACKAGED"
echo "Failed:   $FAILED"
echo "Manifest: $MANIFEST"

if [ "$FAILED" -gt 0 ]; then
    echo ""
    echo "[WARN] Some tasks failed packaging."
    exit 1
fi

echo ""
echo "All SPICE tasks packaged for public release."
