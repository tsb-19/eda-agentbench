#!/bin/bash
set -e
# Dataset-level smoke test: validate CLI, per-track discovery, scoring, report.
# Uses per-track single-task evaluation for speed. Full dataset validation
# is done separately via evaluate-dataset.

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

# --- Per-track solution mode (single task each) ---
for TRACK_DIR in tasks/p1_rtl_debug tasks/p2_tb_sva_gen tasks/p4_spice_sim tasks/p5_spice_deck_debug; do
    TRACK=$(basename "$TRACK_DIR")
    echo ""
    echo "--- $TRACK solution mode (single task) ---"

    # Find first task with solution/ or hidden/ (for P5)
    if [ "$TRACK" = "p5_spice_deck_debug" ]; then
        TASK_DIR=$(find "$TRACK_DIR" -name "metadata.json" -path "*/imported/*" | head -1 | xargs dirname)
        SUBMISSION="$TASK_DIR/hidden"
    else
        TASK_DIR=$(find "$TRACK_DIR" -name "metadata.json" | head -1 | xargs dirname)
        SUBMISSION="$TASK_DIR/solution"
    fi

    if [ -z "$TASK_DIR" ] || [ ! -d "$TASK_DIR" ]; then
        check_pass "FAIL" "$TRACK: no task found"
        continue
    fi

    OUT=$(eda-bench evaluate-task "$TASK_DIR" --submission "$SUBMISSION" 2>&1)
    SCORE=$(echo "$OUT" | grep "^Score:" | awk '{print $2}')
    echo "  Score: $SCORE"
    PERFECT=$(python3 -c "print('PASS' if abs(float('$SCORE') - 1.0) < 0.001 else 'FAIL')")
    check_pass "$PERFECT" "$TRACK solution score = 1.00"
done

# --- P3 solution mode (uses evaluate-dataset since task layout differs) ---
echo ""
echo "--- P3 solution mode (sample) ---"
P3_OUT=$(eda-bench evaluate-dataset tasks --submission-mode solution --track p3_timing_report_qa 2>&1)
P3_TOTAL=$(echo "$P3_OUT" | grep "Tasks found:" | awk '{print $NF}')
P3_AVG=$(echo "$P3_OUT" | grep "Avg score:" | awk '{print $NF}')
echo "  P3 tasks: $P3_TOTAL, avg: $P3_AVG"
P3_CHECK=$(python3 -c "print('PASS' if int('$P3_TOTAL') >= 100 else 'FAIL')")
check_pass "$P3_CHECK" "P3 task count >= 100"
P3_PERFECT=$(python3 -c "print('PASS' if abs(float('$P3_AVG') - 1.0) < 0.001 else 'FAIL')")
check_pass "$P3_PERFECT" "P3 solution avg score = 1.00"

# --- Discover all tracks ---
echo ""
echo "--- Track discovery ---"
ALL_OUT=$(eda-bench evaluate-dataset tasks --submission-mode solution 2>&1 | head -10)
ALL_TOTAL=$(echo "$ALL_OUT" | grep "Tasks found:" | awk '{print $NF}')
echo "  Total tasks found: $ALL_TOTAL"
ALL_CHECK=$(python3 -c "print('PASS' if int('$ALL_TOTAL') >= 2363 else 'FAIL')")
check_pass "$ALL_CHECK" "Total tasks >= 2363"

# --- Report generation ---
echo ""
echo "--- Report generation ---"
# Use the P3 run for report testing (small, fast)
P3_RUN=$(echo "$P3_OUT" | grep "Run ID:" | awk '{print $NF}')
REPORT_OUT=$(eda-bench report "runs/$P3_RUN" 2>&1)
if echo "$REPORT_OUT" | grep -q "EDA-AgentBench Dataset Report"; then
    check_pass "PASS" "Report generated"
else
    check_pass "FAIL" "Report generation"
fi

if [ -f "runs/$P3_RUN/summary.json" ]; then
    check_pass "PASS" "summary.json exists"
else
    check_pass "FAIL" "summary.json missing"
fi
if [ -f "runs/$P3_RUN/report.md" ]; then
    check_pass "PASS" "report.md exists"
else
    check_pass "FAIL" "report.md missing"
fi

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
P6_SMOKE=$(bash scripts/run_dc_synthesis_qa_smoke.sh 2>&1)
if echo "$P6_SMOKE" | grep -q "ALL P6 DC SYNTHESIS QA SMOKE TESTS PASSED"; then
    check_pass "PASS" "P6 DC synthesis QA smoke passes"
else
    check_pass "FAIL" "P6 DC synthesis QA smoke failed"
fi
RTL_SMOKE=$(bash scripts/run_smoke.sh 2>&1)
if echo "$RTL_SMOKE" | grep -q "ALL SMOKE TESTS PASSED"; then
    check_pass "PASS" "RTL smoke still passes"
else
    check_pass "FAIL" "RTL smoke failed"
fi

P2_SMOKE=$(bash scripts/run_p2_smoke.sh 2>&1)
if echo "$P2_SMOKE" | grep -q "ALL P2 SMOKE TESTS PASSED"; then
    check_pass "PASS" "P2 smoke passes"
else
    check_pass "FAIL" "P2 smoke failed"
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
