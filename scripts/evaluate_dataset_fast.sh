#!/bin/bash
set -e
# Fast sampled dataset evaluation smoke test.
# Covers all tracks with minimal tasks. Runs in ~2 minutes.

echo "=== Fast Sampled Dataset Evaluation ==="
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

SEED=123

# --- Solution mode: sample 1 per track ---
echo ""
echo "--- Solution mode (sample 1 per track, seed=$SEED) ---"
SOL_OUT=$(eda-bench evaluate-dataset tasks --submission-mode solution --sample-per-track 1 --seed $SEED 2>&1)
echo "$SOL_OUT" | grep -E "Total candidates|Tasks selected|Sampled|Submission mode" | sed 's/^/  /'

SOL_EVAL=$(echo "$SOL_OUT" | grep "Evaluated:" | awk '{print $2}')
SOL_PASS=$(echo "$SOL_OUT" | grep "Passed:" | head -1 | awk '{print $2}')
SOL_AVG=$(echo "$SOL_OUT" | grep "Avg score:" | awk '{print $NF}')
echo "  Evaluated: $SOL_EVAL, Passed: $SOL_PASS, Avg: $SOL_AVG"

SOL_PERFECT=$(python3 -c "print('PASS' if abs(float('$SOL_AVG') - 1.0) < 0.001 else 'FAIL')")
check_pass "$SOL_PERFECT" "Solution avg score = 1.00"
SOL_ALL=$(python3 -c "print('PASS' if '$SOL_PASS' == '$SOL_EVAL' else 'FAIL')")
check_pass "$SOL_ALL" "All selected solution tasks passed"

# --- Buggy mode: sample 1 per track ---
echo ""
echo "--- Buggy mode (sample 1 per track, seed=$SEED) ---"
BUG_OUT=$(eda-bench evaluate-dataset tasks --submission-mode buggy --sample-per-track 1 --seed $SEED 2>&1)
echo "$BUG_OUT" | grep -E "Total candidates|Tasks selected|Sampled|Submission mode" | sed 's/^/  /'

BUG_EVAL=$(echo "$BUG_OUT" | grep "Evaluated:" | awk '{print $2}')
BUG_AVG=$(echo "$BUG_OUT" | grep "Avg score:" | awk '{print $NF}')
echo "  Evaluated: $BUG_EVAL, Avg: $BUG_AVG"

BUG_LT1=$(python3 -c "print('PASS' if float('$BUG_AVG') < 1.0 else 'FAIL')")
check_pass "$BUG_LT1" "Buggy avg score < 1.0"

# --- Verify sampled metadata in summary ---
echo ""
echo "--- Sampling metadata check ---"
SOL_RUN=$(echo "$SOL_OUT" | grep "Run ID:" | awk '{print $NF}')
if [ -f "runs/$SOL_RUN/summary.json" ]; then
    SAMPLED=$(python3 -c "import json; d=json.load(open('runs/$SOL_RUN/summary.json')); print(d.get('sampled', False))")
    SEED_CHECK=$(python3 -c "import json; d=json.load(open('runs/$SOL_RUN/summary.json')); print(d.get('seed', ''))")
    TOTAL_CAND=$(python3 -c "import json; d=json.load(open('runs/$SOL_RUN/summary.json')); print(d.get('total_candidates', 0))")
    SEL_COUNT=$(python3 -c "import json; d=json.load(open('runs/$SOL_RUN/summary.json')); print(d.get('selected_task_count', 0))")
    echo "  sampled: $SAMPLED, seed: $SEED_CHECK, candidates: $TOTAL_CAND, selected: $SEL_COUNT"
    check_pass "$(python3 -c "print('PASS' if '$SAMPLED' == 'True' else 'FAIL')")" "Summary marks sampled=True"
    check_pass "$(python3 -c "print('PASS' if int('$SEL_COUNT') < int('$TOTAL_CAND') else 'FAIL')")" "Selected < total candidates"
else
    check_pass "FAIL" "summary.json not found"
fi

# --- Track coverage ---
echo ""
echo "--- Track coverage ---"
TRACKS=$(python3 -c "import json; d=json.load(open('runs/$SOL_RUN/summary.json')); print(' '.join(sorted(d.get('per_track', {}).keys())))")
echo "  Tracks in sample: $TRACKS"
TRACK_COUNT=$(echo "$TRACKS" | wc -w)
check_pass "$(python3 -c "print('PASS' if int('$TRACK_COUNT') >= 5 else 'FAIL')")" "At least 5 tracks covered"

# --- Summary ---
echo ""
echo "=== Results: $PASS_COUNT passed, $FAIL_COUNT failed ==="
if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "ALL FAST DATASET CHECKS PASSED"
    exit 0
else
    echo "SOME FAST DATASET CHECKS FAILED"
    exit 1
fi
