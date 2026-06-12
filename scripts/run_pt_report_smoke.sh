#!/bin/bash
# PrimeTime Timing Report QA prototype smoke test
# Skips gracefully if PrimeTime is unavailable.
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

echo "=== PrimeTime Timing Report QA Prototype Smoke Test ==="
echo ""

# --- Step 0: Check PrimeTime availability ---
echo "--- Step 0: Check PrimeTime availability ---"
PT_AVAILABLE=0
if eda-bench detect-tools 2>&1 | grep -q "pt.*synopsys.*YES"; then
    echo "  PrimeTime detected"
    PT_AVAILABLE=1
else
    echo "  PrimeTime not available — running handcrafted mode only"
fi
echo ""

# --- Step 1: Generate handcrafted prototype tasks ---
echo "--- Step 1: Generate handcrafted prototype tasks ---"
python3 scripts/generate_pt_report_prototypes.py --mode handcrafted \
    --output-dir tasks/p3_timing_report_qa/pt_prototype 2>&1
GEN_COUNT=$(ls -d tasks/p3_timing_report_qa/pt_prototype/p3_timing_* 2>/dev/null | wc -l)
echo "  Generated: $GEN_COUNT tasks"
GEN_CHECK=$(python3 -c "print('PASS' if $GEN_COUNT == 8 else 'FAIL')")
check "Generated 8 handcrafted tasks" "$GEN_CHECK"
echo ""

# --- Step 2: Validate generated tasks ---
echo "--- Step 2: Validate generated tasks ---"
VAL_PASS=0
for task_dir in tasks/p3_timing_report_qa/pt_prototype/p3_timing_*; do
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
check "All prototype tasks valid" "$VAL_CHECK"
echo ""

# --- Step 3: Evaluate first task with solution ---
echo "--- Step 3: Evaluate first prototype task with solution ---"
FIRST_TASK=$(ls -d tasks/p3_timing_report_qa/pt_prototype/p3_timing_* | head -1)
eda-bench evaluate-task "$FIRST_TASK" \
    --submission "$FIRST_TASK/solution" 2>&1

TASK_NAME=$(basename "$FIRST_TASK")
SCORE_PATH=$(ls -t "runs/${TASK_NAME}"/*/score.json 2>/dev/null | head -1)
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

# --- Step 4: Evaluate first task with wrong answer ---
echo "--- Step 4: Evaluate first prototype task with wrong answer ---"
WRONG_DIR=$(mktemp -d)
echo "WRONG_ANSWER" > "$WRONG_DIR/answer.txt"
eda-bench evaluate-task "$FIRST_TASK" \
    --submission "$WRONG_DIR" 2>&1

WRONG_SCORE_PATH=$(ls -t "runs/${TASK_NAME}"/*/score.json 2>/dev/null | head -1)
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

# --- Results ---
echo "=== Results: $PASS passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
    echo "PT PROTOTYPE SMOKE TEST FAILED"
    exit 1
else
    echo "ALL PT PROTOTYPE SMOKE TESTS PASSED"
fi
