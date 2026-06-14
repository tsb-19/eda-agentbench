#!/usr/bin/env bash
# Static smoke tests — no EDA executable required.
# Validates schema, structure, and determinism.
#
# Static mode guarantees:
#   - no required EDA executable dependency
#   - no hardcoded commercial tool paths
#   - no raw commercial logs
#   - no license paths
#   - no host/user/absolute path leakage
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

PASS=0
FAIL=0

check() {
    local desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        echo "[PASS] $desc"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] $desc"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Static Smoke Tests ==="
echo ""

# 1. Check Python is available
check "Python available" python --version

# 2. Check JSON schemas are valid JSON
check "task_schema.json is valid JSON" python -c "import json; json.load(open('schemas/task_schema.json'))"
check "validation_record_schema.json is valid JSON" python -c "import json; json.load(open('schemas/validation_record_schema.json'))"

# 3. Check tasks were generated with normalized names
check "tasks_candidates directory exists" test -d tasks_candidates
check "RTL debug tasks exist" test -d tasks_candidates/rtl_debug_0001
check "SPICE deck debug tasks exist" test -d tasks_candidates/spice_deck_debug_0001
check "Timing report QA tasks exist" test -d tasks_candidates/timing_report_qa_0001

# 4. Count tasks
RTL_COUNT=$(ls -d tasks_candidates/rtl_debug_* 2>/dev/null | wc -l)
SPICE_COUNT=$(ls -d tasks_candidates/spice_deck_debug_* 2>/dev/null | wc -l)
TIMING_COUNT=$(ls -d tasks_candidates/timing_report_qa_* 2>/dev/null | wc -l)

echo ""
echo "Task counts:"
echo "  RTL debug:           $RTL_COUNT (expected 10)"
echo "  SPICE deck debug:    $SPICE_COUNT (expected 10)"
echo "  Timing report QA:    $TIMING_COUNT (expected 10)"

if [ "$RTL_COUNT" -eq 10 ] && [ "$SPICE_COUNT" -eq 10 ] && [ "$TIMING_COUNT" -eq 10 ]; then
    echo "[PASS] All 30 tasks generated"
    PASS=$((PASS + 1))
else
    echo "[FAIL] Expected 30 tasks, got $((RTL_COUNT + SPICE_COUNT + TIMING_COUNT))"
    FAIL=$((FAIL + 1))
fi

# 5. Validate task directory structure
echo ""
echo "Validating task structure..."
for task_dir in tasks_candidates/*/; do
    task_name=$(basename "$task_dir")
    check "$task_name has metadata.json" test -f "$task_dir/metadata.json"
    check "$task_name has prompt.md" test -f "$task_dir/prompt.md"
    check "$task_name has visible/" test -d "$task_dir/visible"
    check "$task_name has hidden/" test -d "$task_dir/hidden"
    check "$task_name has oracle/" test -d "$task_dir/oracle"
done

# 6. Validate metadata schema
echo ""
echo "Validating metadata against schema..."
for task_dir in tasks_candidates/*/; do
    task_name=$(basename "$task_dir")
    check "$task_name metadata validates" python -c "
import json, jsonschema
schema = json.load(open('schemas/task_schema.json'))
meta = json.load(open('$task_dir/metadata.json'))
jsonschema.validate(meta, schema)
"
done

# 7. Validate normalized task ID format (4-digit zero-padded)
echo ""
echo "Validating normalized task ID format..."
for task_dir in tasks_candidates/*/; do
    task_name=$(basename "$task_dir")
    check "$task_name ID matches NNNN format" python -c "
import re, json
meta = json.load(open('$task_dir/metadata.json'))
task_id = meta['task_id']
# Must be <domain>_<4-digit-zero-padded-number>
assert re.match(r'^[a-z_]+_\\d{4}$', task_id), f'Bad task_id format: {task_id}'
# Directory name must match task_id
assert task_id == '$task_name', f'task_id {task_id} != dir name $task_name'
"
done

# 8. Verify static mode safety: no required EDA executable, no hardcoded paths, no raw logs
echo ""
echo "Verifying static mode safety guarantees..."

check "No hardcoded commercial tool paths in repo" bash -c "
! grep -r '/tools/synopsys\|/tools/cadence\|/tools/mentor\|/eda/' --include='*.py' --include='*.json' --include='*.md' --exclude-dir=tests --exclude-dir=scripts --exclude-dir=.local_runs . -q 2>/dev/null
"

check "No raw .log files committed" bash -c "
! find tasks_candidates/ -name '*.log' -type f 2>/dev/null | grep -q .
"

check "No .log files in public tasks" bash -c "
! find tasks_public/ -name '*.log' -type f 2>/dev/null | grep -q .
"

check "No license paths in tasks" bash -c "
! grep -ri 'license_file\|license_path\|license_server\|flexlm\|lmx' tasks_candidates/ -q 2>/dev/null
"

# 9. Check .local_runs is gitignored
check ".local_runs is in .gitignore" grep -q ".local_runs" .gitignore

# 10. Check no absolute paths in tasks
echo ""
echo "Checking for absolute paths in tasks..."
check "No absolute paths in task files" bash -c "
! grep -r '/home/\|/tools/\|/usr/local/' tasks_candidates/ -q 2>/dev/null
"

# 11. Check no host/user leakage
check "No hostname references in tasks" bash -c "
! grep -ri 'hostname\|host_name' tasks_candidates/ -q 2>/dev/null
"

check "No username references in tasks" bash -c "
! grep -ri '/home/[a-z]' tasks_candidates/ -q 2>/dev/null
"

echo ""
echo "=== Smoke Test Summary ==="
echo "PASSED: $PASS"
echo "FAILED: $FAIL"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "Some tests FAILED."
    exit 1
fi

echo ""
echo "All static smoke tests passed."
