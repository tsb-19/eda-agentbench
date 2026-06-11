#!/bin/bash
# Large-scale dataset evaluation script
# Supports P1-only, P4-only, or all tracks

MODE="${1:-all}"  # all, p1, p4
SOLUTION_ONLY="${2:-}"  # --solution-only to skip buggy mode

TASKS_ROOT="tasks"
RUN_ID="large_$(date +%Y%m%d_%H%M%S)"

echo "=== Large Dataset Evaluation ==="
echo "Mode: $MODE"
echo "Run ID: $RUN_ID"
echo ""

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

extract_field() {
    # Extract field from output, default to "N/A" if not found
    echo "$1" | grep "$2" | awk '{print $NF}' | head -1
}

# --- Solution mode ---
echo ""
echo "--- Solution mode ---"
if [ "$MODE" = "p1" ]; then
    SOL_OUT=$(eda-bench evaluate-dataset tasks --submission-mode solution --track p1_rtl_debug --run-id "${RUN_ID}_sol" 2>&1)
elif [ "$MODE" = "p4" ]; then
    SOL_OUT=$(eda-bench evaluate-dataset tasks --submission-mode solution --track p4_spice_sim --run-id "${RUN_ID}_sol" 2>&1)
else
    SOL_OUT=$(eda-bench evaluate-dataset tasks --submission-mode solution --run-id "${RUN_ID}_sol" 2>&1)
fi

SOL_AVG=$(extract_field "$SOL_OUT" "Avg score:")
SOL_TOTAL=$(extract_field "$SOL_OUT" "Tasks found:")
SOL_PASS=$(echo "$SOL_OUT" | grep "Passed:" | awk '{print $2}' | head -1)
SOL_ERR=$(echo "$SOL_OUT" | grep "Errors:" | awk '{print $2}' | head -1)

echo "  Tasks: $SOL_TOTAL, Passed: $SOL_PASS, Avg: $SOL_AVG, Errors: $SOL_ERR"

if [ -n "$SOL_AVG" ] && [ "$SOL_AVG" != "N/A" ]; then
    SOL_PERFECT=$(python3 -c "print('PASS' if abs(float('$SOL_AVG') - 1.0) < 0.001 else 'FAIL')")
else
    SOL_PERFECT="FAIL"
fi
check_pass "$SOL_PERFECT" "Solution avg = 1.00"

if [ -n "$SOL_ERR" ] && [ "$SOL_ERR" = "0" ]; then
    check_pass "PASS" "No errors in solution mode"
else
    check_pass "FAIL" "Errors in solution mode: ${SOL_ERR:-unknown}"
fi

# --- Buggy mode ---
if [ "$SOLUTION_ONLY" != "--solution-only" ]; then
    echo ""
    echo "--- Buggy mode ---"
    if [ "$MODE" = "p1" ]; then
        BUG_OUT=$(eda-bench evaluate-dataset tasks --submission-mode buggy --track p1_rtl_debug --run-id "${RUN_ID}_bug" 2>&1)
    elif [ "$MODE" = "p4" ]; then
        BUG_OUT=$(eda-bench evaluate-dataset tasks --submission-mode buggy --track p4_spice_sim --run-id "${RUN_ID}_bug" 2>&1)
    else
        BUG_OUT=$(eda-bench evaluate-dataset tasks --submission-mode buggy --run-id "${RUN_ID}_bug" 2>&1)
    fi

    BUG_AVG=$(extract_field "$BUG_OUT" "Avg score:")
    BUG_TOTAL=$(extract_field "$BUG_OUT" "Tasks found:")
    BUG_ERR=$(echo "$BUG_OUT" | grep "Errors:" | awk '{print $2}' | head -1)

    echo "  Tasks: $BUG_TOTAL, Avg: $BUG_AVG, Errors: $BUG_ERR"

    if [ -n "$BUG_AVG" ] && [ "$BUG_AVG" != "N/A" ]; then
        BUG_LT1=$(python3 -c "print('PASS' if float('$BUG_AVG') < 1.0 else 'FAIL')")
    else
        BUG_LT1="FAIL"
    fi
    check_pass "$BUG_LT1" "Buggy avg < 1.0"

    if [ -n "$BUG_ERR" ] && [ "$BUG_ERR" = "0" ]; then
        check_pass "PASS" "No errors in buggy mode"
    else
        check_pass "FAIL" "Errors in buggy mode: ${BUG_ERR:-unknown}"
    fi
fi

# --- Report ---
echo ""
echo "--- Report ---"
SOL_RUN_ID=$(echo "$SOL_OUT" | grep "Run ID:" | awk '{print $NF}' | head -1)
if [ -n "$SOL_RUN_ID" ] && [ -d "runs/$SOL_RUN_ID" ]; then
    REPORT_OUT=$(eda-bench report "runs/$SOL_RUN_ID" --format all 2>&1)
    if echo "$REPORT_OUT" | grep -q "EDA-AgentBench Dataset Report"; then
        check_pass "PASS" "Report generated"
    else
        check_pass "FAIL" "Report generation"
    fi
else
    check_pass "FAIL" "Run directory not found: runs/${SOL_RUN_ID:-unknown}"
fi

# --- Failure summary ---
echo ""
echo "--- Failure summary ---"
if [ "$SOL_ERR" = "0" ]; then
    echo "  No failures in solution mode"
else
    echo "  Solution mode failures: ${SOL_ERR:-unknown}"
fi

# --- Summary ---
echo ""
echo "=== Results: $PASS_COUNT passed, $FAIL_COUNT failed ==="
if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "ALL LARGE DATASET TESTS PASSED"
    exit 0
else
    echo "SOME LARGE DATASET TESTS FAILED"
    exit 1
fi
