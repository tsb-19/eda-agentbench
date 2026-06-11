#!/bin/bash
# P3 Timing Report QA smoke test
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

PASS=0
FAIL=0

check() {
    local name="$1"
    local result="$2"
    if [ "$result" = "PASS" ]; then
        echo "  PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $name"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== P3 Timing Report QA Smoke Test ==="
echo ""

# --- Step 1: Validate smoke task ---
echo "--- Step 1: Validate smoke task ---"
VALIDATE_OUT=$(eda-bench validate-task tasks/p3_timing_report_qa/smoke 2>&1)
echo "$VALIDATE_OUT"
echo "$VALIDATE_OUT" | grep -q "VALID" && check "Smoke task validation" "PASS" || check "Smoke task validation" "FAIL"
echo ""

# --- Step 2: Generate 10 tasks ---
echo "--- Step 2: Generate 10 P3 tasks ---"
python3 scripts/generate_p3_tasks.py --count 10 --output-dir tasks/p3_timing_report_qa/generated_tmp 2>&1
GEN_COUNT=$(ls -d tasks/p3_timing_report_qa/generated_tmp/p3_timing_* 2>/dev/null | wc -l)
echo "  Generated: $GEN_COUNT tasks"
GEN_CHECK=$(python3 -c "print('PASS' if $GEN_COUNT == 10 else 'FAIL')")
check "Generated 10 tasks" "$GEN_CHECK"
echo ""

# --- Step 3: Validate generated tasks ---
echo "--- Step 3: Validate generated tasks ---"
VAL_PASS=0
for task_dir in tasks/p3_timing_report_qa/generated_tmp/p3_timing_*; do
    VALIDATE_OUT=$(eda-bench validate-task "$task_dir" 2>&1)
    if echo "$VALIDATE_OUT" | grep -q "VALID"; then
        VAL_PASS=$((VAL_PASS + 1))
    else
        echo "  INVALID: $task_dir"
        echo "$VALIDATE_OUT"
    fi
done
echo "  Validated: $VAL_PASS / $GEN_COUNT"
VAL_CHECK=$(python3 -c "print('PASS' if $VAL_PASS == $GEN_COUNT else 'FAIL')")
check "All generated tasks valid" "$VAL_CHECK"
echo ""

# --- Step 4: Evaluate smoke task with solution ---
echo "--- Step 4: Evaluate smoke task with solution ---"
eda-bench evaluate-task tasks/p3_timing_report_qa/smoke \
    --submission tasks/p3_timing_report_qa/smoke/solution 2>&1

SCORE_PATH=$(ls -t runs/p3_timing_000000/*/score.json 2>/dev/null | head -1)
if [ -n "$SCORE_PATH" ]; then
    SCORE_TOTAL=$(python3 -c "import json; d=json.load(open('$SCORE_PATH')); print(d['total_score'])")
    echo "  Solution total_score: $SCORE_TOTAL"
    SCORE_CHECK=$(python3 -c "print('PASS' if abs(float('$SCORE_TOTAL') - 1.0) < 0.001 else 'FAIL')")
    check "Solution scores 1.0" "$SCORE_CHECK"
else
    echo "  No score.json found"
    check "Solution scores 1.0" "FAIL"
fi
echo ""

# --- Step 5: Evaluate smoke task with wrong answer ---
echo "--- Step 5: Evaluate smoke task with wrong answer ---"
WRONG_DIR=$(mktemp -d)
echo "99.9999" > "$WRONG_DIR/answer.txt"
eda-bench evaluate-task tasks/p3_timing_report_qa/smoke \
    --submission "$WRONG_DIR" 2>&1

WRONG_SCORE_PATH=$(ls -t runs/p3_timing_000000/*/score.json 2>/dev/null | head -1)
if [ -n "$WRONG_SCORE_PATH" ]; then
    WRONG_TOTAL=$(python3 -c "import json; d=json.load(open('$WRONG_SCORE_PATH')); print(d['total_score'])")
    echo "  Wrong answer total_score: $WRONG_TOTAL"
    WRONG_CHECK=$(python3 -c "print('PASS' if float('$WRONG_TOTAL') < 0.5 else 'FAIL')")
    check "Wrong answer scores < 0.5" "$WRONG_CHECK"
else
    echo "  No score.json found"
    check "Wrong answer scores < 0.5" "FAIL"
fi
rm -rf "$WRONG_DIR"
echo ""

# --- Step 6: Generate 100 tasks (final) ---
echo "--- Step 6: Generate 100 P3 tasks (final) ---"
python3 scripts/generate_p3_tasks.py --count 100 --output-dir tasks/p3_timing_report_qa/generated 2>&1
FINAL_COUNT=$(ls -d tasks/p3_timing_report_qa/generated/p3_timing_* 2>/dev/null | wc -l)
echo "  Generated: $FINAL_COUNT tasks"
FINAL_CHECK=$(python3 -c "print('PASS' if $FINAL_COUNT == 100 else 'FAIL')")
check "Generated 100 tasks" "$FINAL_CHECK"
echo ""

# --- Step 7: Clean up temp dir ---
echo "--- Step 7: Clean up temp dir ---"
rm -rf tasks/p3_timing_report_qa/generated_tmp
check "Cleanup done" "PASS"
echo ""

# --- Results ---
echo "=== Results: $PASS passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
    echo "P3 SMOKE TEST FAILED"
    exit 1
else
    echo "ALL P3 SMOKE TESTS PASSED"
fi
