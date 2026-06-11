#!/bin/bash
set -e
# Dataset-level evaluation smoke test

echo "=== Dataset Evaluation Smoke Test ==="
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

# --- Solution mode: all tasks should score 1.00 ---
echo ""
echo "--- Solution mode (all tasks) ---"
SOL_OUT=$(eda-bench evaluate-dataset tasks --submission-mode solution 2>&1)
SOL_AVG=$(echo "$SOL_OUT" | grep "Avg score:" | awk '{print $NF}')
echo "  Avg score: $SOL_AVG"

SOL_PERFECT=$(python3 -c "print('PASS' if abs(float('$SOL_AVG') - 1.0) < 0.001 else 'FAIL')")
check_pass "$SOL_PERFECT" "Solution avg score = 1.00"

SOL_PASS=$(echo "$SOL_OUT" | grep "Passed:" | awk '{print $2}')
echo "  Passed: $SOL_PASS / 113"
SOL_ALL=$(python3 -c "print('PASS' if '$SOL_PASS' == '113' else 'FAIL')")
check_pass "$SOL_ALL" "All 113 tasks passed in solution mode"

# --- Buggy mode: all scores should be < 1.00 ---
echo ""
echo "--- Buggy mode (all tasks) ---"
BUG_OUT=$(eda-bench evaluate-dataset tasks --submission-mode buggy 2>&1)
BUG_AVG=$(echo "$BUG_OUT" | grep "Avg score:" | awk '{print $NF}')
echo "  Avg score: $BUG_AVG"

BUG_LT1=$(python3 -c "print('PASS' if float('$BUG_AVG') < 1.0 else 'FAIL')")
check_pass "$BUG_LT1" "Buggy avg score < 1.0"

BUG_ERR=$(echo "$BUG_OUT" | grep "Errors:" | awk '{print $2}')
echo "  Errors: $BUG_ERR"
BUG_NOERR=$(python3 -c "print('PASS' if '$BUG_ERR' == '0' else 'FAIL')")
check_pass "$BUG_NOERR" "No errors in buggy mode"

# --- Track filter: P1 only ---
echo ""
echo "--- P1 solution mode ---"
P1_OUT=$(eda-bench evaluate-dataset tasks --submission-mode solution --track p1_rtl_debug 2>&1)
P1_TOTAL=$(echo "$P1_OUT" | grep "Tasks found:" | awk '{print $NF}')
echo "  P1 tasks found: $P1_TOTAL"
P1_CHECK=$(python3 -c "print('PASS' if int('$P1_TOTAL') >= 21 else 'FAIL')")
check_pass "$P1_CHECK" "P1 task count >= 21"

# --- Track filter: P4 only ---
echo ""
echo "--- P4 solution mode ---"
P4_OUT=$(eda-bench evaluate-dataset tasks --submission-mode solution --track p4_spice_sim 2>&1)
P4_TOTAL=$(echo "$P4_OUT" | grep "Tasks found:" | awk '{print $NF}')
echo "  P4 tasks found: $P4_TOTAL"
P4_CHECK=$(python3 -c "print('PASS' if int('$P4_TOTAL') >= 2 else 'FAIL')")
check_pass "$P4_CHECK" "P4 task count >= 2"

# --- Report command ---
echo ""
echo "--- Report (solution dataset) ---"
SOL_RUN=$(echo "$SOL_OUT" | grep "Run ID:" | awk '{print $NF}')
REPORT_OUT=$(eda-bench report "runs/$SOL_RUN" 2>&1)
if echo "$REPORT_OUT" | grep -q "EDA-AgentBench Dataset Report"; then
    check_pass "PASS" "Report generated"
else
    check_pass "FAIL" "Report generation"
fi

# Check report files exist
if [ -f "runs/$SOL_RUN/summary.json" ]; then
    check_pass "PASS" "summary.json exists"
else
    check_pass "FAIL" "summary.json missing"
fi
if [ -f "runs/$SOL_RUN/report.md" ]; then
    check_pass "PASS" "report.md exists"
else
    check_pass "FAIL" "report.md missing"
fi

# Check report has per-track stats
if echo "$REPORT_OUT" | grep -q "Per-Track"; then
    check_pass "PASS" "Report has per-track stats"
else
    check_pass "FAIL" "Report missing per-track stats"
fi

if echo "$REPORT_OUT" | grep -q "Per-Tool"; then
    check_pass "PASS" "Report has per-tool stats"
else
    check_pass "FAIL" "Report missing per-tool stats"
fi

if echo "$REPORT_OUT" | grep -q "Score Distribution"; then
    check_pass "PASS" "Report has score distribution"
else
    check_pass "FAIL" "Report missing score distribution"
fi

# --- Existing smoke tests ---
echo ""
echo "--- Existing smoke tests ---"
RTL_SMOKE=$(bash scripts/run_smoke.sh 2>&1)
if echo "$RTL_SMOKE" | grep -q "ALL SMOKE TESTS PASSED"; then
    check_pass "PASS" "RTL smoke still passes"
else
    check_pass "FAIL" "RTL smoke failed"
fi

SPICE_SMOKE=$(bash scripts/run_spice_smoke.sh 2>&1)
if echo "$SPICE_SMOKE" | grep -q "ALL HSPICE SMOKE TESTS PASSED"; then
    check_pass "PASS" "HSPICE smoke still passes"
else
    check_pass "FAIL" "HSPICE smoke failed"
fi

SPECTRE_SMOKE=$(bash scripts/run_spectre_smoke.sh 2>&1)
if echo "$SPECTRE_SMOKE" | grep -q "ALL SPECTRE SMOKE TESTS PASSED"; then
    check_pass "PASS" "Spectre smoke still passes"
else
    check_pass "FAIL" "Spectre smoke failed"
fi

# --- Summary ---
echo ""
echo "=== Results: $PASS_COUNT passed, $FAIL_COUNT failed ==="
if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "ALL DATASET SMOKE TESTS PASSED"
    exit 0
else
    echo "SOME DATASET SMOKE TESTS FAILED"
    exit 1
fi
