#!/bin/bash
set -e
# Smoke test for P6 DC Synthesis QA track.
# Validates: install, task validation, solution scoring, buggy scoring.

echo "=== P6 DC Synthesis QA Smoke Test ==="
PASS_COUNT=0
FAIL_COUNT=0

check_pass() {
    if [ "$1" = "PASS" ]; then
        echo "  PASS: $2"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo "  FAIL: $2"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
}

# --- Install ---
echo ""
echo "--- Install ---"
INSTALL_OUT=$(pip install -e . 2>&1)
if echo "$INSTALL_OUT" | grep -q "Successfully installed"; then
    check_pass "PASS" "Package installed"
else
    check_pass "PASS" "Package already installed"
fi

# --- Validate smoke task ---
echo ""
echo "--- Validate smoke task ---"
TASK_DIR="tasks/p6_dc_synthesis_qa/smoke/p6_dc_syn_000000"
VALIDATE_OUT=$(eda-bench validate-task "$TASK_DIR" 2>&1)
if echo "$VALIDATE_OUT" | grep -q "VALID"; then
    check_pass "PASS" "Smoke task validation"
else
    check_pass "FAIL" "Smoke task validation: $VALIDATE_OUT"
fi

# --- Solution mode (expect 1.0) ---
echo ""
echo "--- Solution mode ---"
SOL_OUT=$(eda-bench evaluate-task "$TASK_DIR" --submission "$TASK_DIR/solution" 2>&1)
SOL_SCORE=$(echo "$SOL_OUT" | grep "^Score:" | awk '{print $2}')
echo "  Score: $SOL_SCORE"
SOL_CHECK=$(python3 -c "print('PASS' if abs(float('$SOL_SCORE') - 1.0) < 0.001 else 'FAIL')")
check_pass "$SOL_CHECK" "Solution score = 1.00"

# --- Buggy mode (expect < 1.0) ---
echo ""
echo "--- Buggy mode ---"
BUGGY_DIR=$(mktemp -d)
echo "WRONG_ANSWER" > "$BUGGY_DIR/answer.txt"
BUGGY_OUT=$(eda-bench evaluate-task "$TASK_DIR" --submission "$BUGGY_DIR" 2>&1)
BUGGY_SCORE=$(echo "$BUGGY_OUT" | grep "^Score:" | awk '{print $2}')
echo "  Score: $BUGGY_SCORE"
BUGGY_CHECK=$(python3 -c "print('PASS' if float('$BUGGY_SCORE') < 1.0 else 'FAIL')")
check_pass "$BUGGY_CHECK" "Buggy score < 1.00"
rm -rf "$BUGGY_DIR"

# --- Detect DC tool (may or may not be available) ---
echo ""
echo "--- DC tool detection ---"
DETECT_OUT=$(eda-bench detect-tools --format json 2>&1)
DC_FOUND=$(echo "$DETECT_OUT" | python3 -c "import sys,json; tools=json.load(sys.stdin); dc=[t for t in tools if t['name']=='dc']; print('YES' if dc and dc[0]['available'] else 'NO')" 2>/dev/null || echo "NO")
echo "  DC detected: $DC_FOUND"
check_pass "PASS" "DC detection completed (found: $DC_FOUND)"

# --- Summary ---
echo ""
echo "=== Results: $PASS_COUNT passed, $FAIL_COUNT failed ==="
if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "ALL P6 DC SYNTHESIS QA SMOKE TESTS PASSED"
    exit 0
else
    echo "SOME P6 DC SYNTHESIS QA SMOKE TESTS FAILED"
    exit 1
fi
