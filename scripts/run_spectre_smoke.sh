#!/bin/bash
set -e
# Spectre smoke test: validate Spectre task works end-to-end

echo "=== Spectre Smoke Test ==="
TASK_DIR="tasks/p4_spice_sim/spectre_rc_000001"
SOLUTION_DIR="$TASK_DIR/solution"
BUGGY_DIR="/tmp/spectre_buggy_$$"
PASS_COUNT=0
FAIL_COUNT=0

# Create buggy submission (copy the original buggy circuit)
mkdir -p "$BUGGY_DIR"
cp "$TASK_DIR/files/circuit.scs" "$BUGGY_DIR/"

cleanup() {
    rm -rf "$BUGGY_DIR"
}
trap cleanup EXIT

check_pass() {
    if [ "$1" = "PASS" ]; then
        echo "  PASS: $2"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo "  FAIL: $2"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
}

check_fail() {
    if [ "$1" = "PASS" ]; then
        echo "  PASS: $2"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo "  FAIL: $2"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
}

# --- Validate task ---
echo ""
echo "--- Validate task ---"
VALIDATE_OUT=$(eda-bench validate-task "$TASK_DIR" 2>&1)
if echo "$VALIDATE_OUT" | grep -q "VALID"; then
    check_pass "PASS" "Task validation passed"
else
    check_fail "FAIL" "Task validation failed"
fi

# --- Check Spectre available ---
echo ""
echo "--- Check Spectre ---"
if command -v spectre &>/dev/null; then
    check_pass "PASS" "Spectre available"
else
    check_fail "FAIL" "Spectre not available"
fi

# --- Solution submission ---
echo ""
echo "--- Solution submission ---"
SOL_OUT=$(eda-bench evaluate-task "$TASK_DIR" --submission "$SOLUTION_DIR" 2>&1)
SOL_SCORE=$(echo "$SOL_OUT" | grep "^Score:" | awk '{print $2}')
echo "  Solution score: $SOL_SCORE"
SOL_OBJ=$(echo "$SOL_OUT" | grep "objective_score:" | awk '{print $2}')
echo "  Objective score: $SOL_OBJ"

# Check solution scores 1.00
SOL_INT=$(python3 -c "print(int(round(float('$SOL_SCORE'))))")
if [ "$SOL_INT" = "1" ]; then
    check_pass "PASS" "Solution score = 1.00"
else
    check_fail "FAIL" "Solution score = $SOL_SCORE (expected 1.00)"
fi

# Check tool_run PASS
if echo "$SOL_OUT" | grep "tool_run:" | grep -q "1.00"; then
    check_pass "PASS" "tool_run passed"
else
    check_fail "FAIL" "tool_run failed"
fi

# Check public_metric PASS
if echo "$SOL_OUT" | grep "public_metric:" | grep -q "PASS"; then
    check_pass "PASS" "public_metric passed"
else
    check_fail "FAIL" "public_metric failed"
fi

# Check hidden_metric PASS
if echo "$SOL_OUT" | grep "hidden_metric:" | grep -q "PASS"; then
    check_pass "PASS" "hidden_metric passed"
else
    check_fail "FAIL" "hidden_metric failed"
fi

# --- Buggy submission ---
echo ""
echo "--- Buggy submission ---"
BUG_OUT=$(eda-bench evaluate-task "$TASK_DIR" --submission "$BUGGY_DIR" 2>&1)
BUG_SCORE=$(echo "$BUG_OUT" | grep "^Score:" | awk '{print $2}')
echo "  Buggy score: $BUG_SCORE"

BUG_FLOAT=$(python3 -c "print(float('$BUG_SCORE'))")
BUG_LT=$(python3 -c "print('$BUG_FLOAT' < '1.0')")
if [ "$BUG_LT" = "True" ]; then
    check_pass "PASS" "Buggy score < 1.0"
else
    check_fail "FAIL" "Buggy score = $BUG_SCORE (expected < 1.0)"
fi

# Check that at least one metric failed for buggy
if echo "$BUG_OUT" | grep "public_metric:" | grep -q "FAIL"; then
    check_pass "PASS" "Buggy public_metric failed as expected"
elif echo "$BUG_OUT" | grep "hidden_metric:" | grep -q "FAIL"; then
    check_pass "PASS" "Buggy hidden_metric failed as expected"
else
    check_fail "FAIL" "Buggy metrics should fail"
fi

# --- Check output files ---
echo ""
echo "--- Check output files ---"
# Find latest run directory
LATEST_RUN=$(ls -td runs/task_000002/*/ 2>/dev/null | head -1)
if [ -n "$LATEST_RUN" ]; then
    if [ -f "$LATEST_RUN/raw_public.log" ]; then
        check_pass "PASS" "raw_public.log exists"
    else
        check_fail "FAIL" "raw_public.log missing"
    fi
    if [ -f "$LATEST_RUN/sanitized_public.log" ]; then
        check_pass "PASS" "sanitized_public.log exists"
    else
        check_fail "FAIL" "sanitized_public.log missing"
    fi
    if [ -f "$LATEST_RUN/score.json" ]; then
        check_pass "PASS" "score.json exists"
        # Check score.json has required fields
        python3 -c "
import json, sys
score = json.load(open('$LATEST_RUN/score.json'))
required = ['task_id', 'track', 'mode', 'total_score', 'components', 'anti_cheat']
missing = [f for f in required if f not in score]
if missing:
    print(f'Missing fields: {missing}')
    sys.exit(1)
else:
    print('score.json has all required fields')
" && check_pass "PASS" "score.json fields" || check_fail "FAIL" "score.json fields"
    else
        check_fail "FAIL" "score.json missing"
    fi
else
    check_fail "FAIL" "No run directory found"
fi

# --- Summary ---
echo ""
echo "=== Results: $PASS_COUNT passed, $FAIL_COUNT failed ==="
if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "ALL SPECTRE SMOKE TESTS PASSED"
    exit 0
else
    echo "SOME SPECTRE SMOKE TESTS FAILED"
    exit 1
fi
