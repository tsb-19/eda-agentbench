#!/usr/bin/env bash
# Batch HSPICE contrast validation for all SPICE deck debug tasks.
#
# Iterates over tasks_candidates/spice_deck_debug_*,
# runs HSPICE contrast validation, and produces a summary table.
#
# Usage:
#   bash scripts/validate_spice_batch.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# Check HSPICE availability
HSPICE_CMD="${EDA_HSPICE_CMD:-}"
if [ -z "$HSPICE_CMD" ]; then
    HSPICE_CMD=$(which hspice 2>/dev/null || true)
fi
if [ -z "$HSPICE_CMD" ]; then
    echo "[ERROR] HSPICE not found. Set EDA_HSPICE_CMD or add hspice to PATH."
    exit 1
fi

echo "=== SPICE Deck Debug Batch Validation ==="
echo "HSPICE: $HSPICE_CMD"
echo ""

# Clean previous results
rm -rf tasks_validated/spice_deck_debug_* .local_runs/hspice/spice_deck_debug_*

# Results storage
RESULTS_FILE=$(mktemp)
echo "task_id|expected_bug_type|observed_error_category|buggy_failed|golden_passed|status" > "$RESULTS_FILE"

PASS_COUNT=0
FAIL_COUNT=0
TOTAL=0

for task_dir in tasks_candidates/spice_deck_debug_*/; do
    task_name=$(basename "$task_dir")
    TOTAL=$((TOTAL + 1))

    echo "--- Validating $task_name ---"

    # Read expected error category from metadata
    expected_cat=$(python3 -c "import json; print(json.load(open('${task_dir}metadata.json')).get('expected_error_category', 'unknown'))" 2>/dev/null || echo "unknown")

    # Run validation
    export EDA_HSPICE_CMD="$HSPICE_CMD"
    OUTPUT=$(python3 -m validators.hspice.validate_spice "$task_dir" 2>&1) || true

    # Parse results
    status=$(echo "$OUTPUT" | grep -o '"validation_status": "[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"/\1/' || echo "unknown")
    buggy_failed=$(echo "$OUTPUT" | grep -o '"buggy_failed_as_expected": [a-z]*' | head -1 | sed 's/.*: //' || echo "unknown")
    golden_passed=$(echo "$OUTPUT" | grep -o '"golden_passed_as_expected": [a-z]*' | head -1 | sed 's/.*: //' || echo "unknown")
    observed_cat=$(echo "$OUTPUT" | grep -o '"observed_error_categories": \[[^]]*\]' | head -1 | sed 's/.*\[//;s/\]//' | tr -d '"' || echo "unknown")

    echo "$task_name|$expected_cat|$observed_cat|$buggy_failed|$golden_passed|$status" >> "$RESULTS_FILE"

    if [ "$status" = "debug_contrast_verified" ]; then
        PASS_COUNT=$((PASS_COUNT + 1))
        echo "[PASS] $task_name: $status"
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "[FAIL] $task_name: $status"
        echo "       Expected category: $expected_cat"
        echo "       Observed categories: $observed_cat"
        echo "       Buggy failed: $buggy_failed, Golden passed: $golden_passed"
    fi
    echo ""
done

# Print summary table
echo ""
echo "=== Summary Table ==="
echo ""
printf "%-25s %-20s %-30s %-8s %-8s %s\n" "task_id" "expected_bug" "observed_categories" "bug_fail" "gold_ok" "status"
printf "%-25s %-20s %-30s %-8s %-8s %s\n" "-------------------------" "--------------------" "------------------------------" "--------" "--------" "-------------------------"

tail -n +2 "$RESULTS_FILE" | while IFS='|' read -r tid exp obs bfail gpass stat; do
    printf "%-25s %-20s %-30s %-8s %-8s %s\n" "$tid" "$exp" "$obs" "$bfail" "$gpass" "$stat"
done

echo ""
echo "=== Results ==="
echo "Total:  $TOTAL"
echo "Passed: $PASS_COUNT (debug_contrast_verified)"
echo "Failed: $FAIL_COUNT"

# Save summary to tasks_validated/
mkdir -p tasks_validated
cp "$RESULTS_FILE" tasks_validated/spice_batch_summary.csv

echo ""
echo "Summary saved to: tasks_validated/spice_batch_summary.csv"

rm -f "$RESULTS_FILE"

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo ""
    echo "[WARN] Some tasks failed validation. See details above."
    exit 1
fi

echo ""
echo "All SPICE tasks passed debug contrast validation."
