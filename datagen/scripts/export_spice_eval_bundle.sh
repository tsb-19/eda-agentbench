#!/usr/bin/env bash
# Export evaluator-facing private bundles for validated SPICE tasks.
#
# Creates tasks_eval_private/spice_deck_debug_NNNN/ with:
#   - All task files (visible, hidden, oracle)
#   - grader_contract.json
#   - validation/ normalized records (no raw logs)
#   - metadata.json
#
# Usage:
#   bash scripts/export_spice_eval_bundle.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

echo "=== SPICE Eval Bundle Export ==="
echo ""

# Clean previous exports
rm -rf tasks_eval_private/spice_deck_debug_*
mkdir -p tasks_eval_private

MANIFEST="tasks_eval_private/manifest.jsonl"
> "$MANIFEST"

EXPORTED=0
FAILED=0

for task_dir in tasks_validated/spice_deck_debug_*/; do
    [ -d "$task_dir" ] || continue
    task_name=$(basename "$task_dir")

    # Check validation_status
    status=$(python3 -c "import json; print(json.load(open('${task_dir}metadata.json'))['validation_status'])" 2>/dev/null || echo "unknown")
    if [ "$status" != "debug_contrast_verified" ]; then
        echo "[SKIP] $task_name: validation_status=$status"
        FAILED=$((FAILED + 1))
        continue
    fi

    echo "--- Exporting $task_name ---"

    DEST="tasks_eval_private/$task_name"
    rm -rf "$DEST"

    # Copy validated task (includes hidden/, oracle/, validation/)
    cp -r "$task_dir" "$DEST"

    # Remove any raw log files from validation/
    find "$DEST/validation" -name "*.log" -type f -delete 2>/dev/null || true
    find "$DEST/validation" -name "*.lis" -type f -delete 2>/dev/null || true
    find "$DEST/validation" -name "*.raw" -type f -delete 2>/dev/null || true

    # Generate grader_contract.json
    python3 -c "
import json, os

meta = json.load(open('${DEST}/metadata.json'))
val = json.load(open('${DEST}/validation/validation_record.json'))

task_id = meta['task_id']
visible_files = meta.get('visible_files', [])
hidden_files = meta.get('hidden_files', [])
oracle_files = []
for root, dirs, files in os.walk('${DEST}/oracle'):
    for f in files:
        oracle_files.append(os.path.relpath(os.path.join(root, f), '${DEST}'))

# Build command template
backend = val['backend']
if backend == 'hspice':
    cmd_template = '{hspice_cmd} {file}'
elif backend == 'vcs':
    cmd_template = '{vcs_cmd} -full64 -sverilog {file}'
elif backend == 'spectre':
    cmd_template = '{spectre_cmd} {file}'
elif backend == 'pt':
    cmd_template = '{pt_cmd} -f {file}'
else:
    cmd_template = '{backend} {file}'

# Determine failure patterns from buggy run
failure_patterns = []
for err in val.get('buggy_run', {}).get('normalized_errors', []):
    if err['severity'] == 'error':
        failure_patterns.append({
            'category': err['category'],
            'severity': err['severity'],
            'description': err['message'][:120],
        })

contract = {
    'task_id': task_id,
    'task_family': meta['task_family'],
    'domain': meta['domain'],
    'editable_files': visible_files,
    'read_only_files': ['prompt.md', 'metadata.json'],
    'hidden_files': hidden_files,
    'oracle_files': oracle_files,
    'backend': backend,
    'backend_env_var': 'EDA_HSPICE_CMD' if backend == 'hspice' else 'EDA_' + backend.upper() + '_CMD',
    'command_template': cmd_template,
    'working_directory': 'visible/',
    'timeout_sec': meta.get('timeout_sec', 300),
    'success_criteria': {
        'exit_code': 0,
        'no_fatal_errors': True,
        'execution_based': True,
        'notes': 'Agent output must run with HSPICE (exit 0) and produce no fatal errors. Exact text match with oracle not required.',
    },
    'failure_patterns': failure_patterns,
    'normalized_error_categories': val.get('debug_contrast', {}).get('observed_error_categories', []),
    'public_task_path': f'tasks_public/{task_id}',
    'private_task_path': f'tasks_eval_private/{task_id}',
}

with open('${DEST}/grader_contract.json', 'w') as f:
    json.dump(contract, f, indent=2)
"

    # Append to manifest
    python3 -c "
import json
meta = json.load(open('${DEST}/metadata.json'))
contract = json.load(open('${DEST}/grader_contract.json'))
row = {
    'task_id': meta['task_id'],
    'task_family': meta['task_family'],
    'backend': contract['backend'],
    'backend_env_var': contract['backend_env_var'],
    'editable_files': contract['editable_files'],
    'grader_contract_file': 'grader_contract.json',
    'validation_status': meta['validation_status'],
    'expected_error_category': meta.get('expected_error_category', ''),
    'timeout_sec': contract['timeout_sec'],
}
print(json.dumps(row), file=open('$MANIFEST', 'a'))
"

    echo "[OK] $task_name exported to $DEST"
    EXPORTED=$((EXPORTED + 1))
done

echo ""
echo "=== Export Summary ==="
echo "Exported: $EXPORTED"
echo "Failed:   $FAILED"
echo "Manifest: $MANIFEST"

if [ "$FAILED" -gt 0 ]; then
    echo ""
    echo "[WARN] Some tasks failed export."
    exit 1
fi

echo ""
echo "All SPICE eval bundles exported."
echo ""
echo "NOTE: tasks_eval_private/ contains hidden/oracle files and is NOT for public release."
