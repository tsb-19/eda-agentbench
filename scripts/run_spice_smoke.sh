#!/bin/bash
# HSPICE smoke test — validates P4 spice_sim task end-to-end
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

TASK_DIR="tasks/p4_spice_sim/hspice_rc_000001"
PASS=0
FAIL=0

check() {
    local name="$1" result="$2"
    if [ "$result" = "PASS" ]; then echo "  PASS: $name"; PASS=$((PASS + 1))
    else echo "  FAIL: $name"; FAIL=$((FAIL + 1)); fi
}

echo "=== HSPICE Smoke Test ==="

# Step 1: Validate task
echo ""
echo "--- Validate task ---"
VALIDATE_OUT=$(eda-bench validate-task "$TASK_DIR" 2>&1)
echo "$VALIDATE_OUT"
echo "$VALIDATE_OUT" | grep -q "VALID" && check "Task validation" "PASS" || check "Task validation" "FAIL"

# Step 2: Evaluate with solution
echo ""
echo "--- Evaluate with solution (expect PASS) ---"
eda-bench evaluate-task "$TASK_DIR" --submission "$TASK_DIR/solution" 2>&1

SOL_SCORE=$(python3 -c "
import json, glob, os
scores = sorted(glob.glob('runs/task_000001/*/score.json'), key=os.path.getmtime)
if scores: print(json.load(open(scores[-1]))['total_score'])
else: print('0')
")
echo "  Solution score: $SOL_SCORE"
python3 -c "exit(0 if abs(float('$SOL_SCORE') - 1.0) < 0.01 else 1)" 2>&1 \
    && check "Solution total_score == 1.0" "PASS" || check "Solution total_score == 1.0" "FAIL"

# Step 3: Evaluate with buggy baseline
echo ""
echo "--- Evaluate with buggy baseline (expect FAIL) ---"
mkdir -p /tmp/hspice_buggy
cp "$TASK_DIR/files/circuit.sp" /tmp/hspice_buggy/circuit.sp
eda-bench evaluate-task "$TASK_DIR" --submission /tmp/hspice_buggy 2>&1

BUG_SCORE=$(python3 -c "
import json, glob, os
scores = sorted(glob.glob('runs/task_000001/*/score.json'), key=os.path.getmtime)
if scores: print(json.load(open(scores[-1]))['total_score'])
else: print('1')
")
echo "  Buggy score: $BUG_SCORE"
python3 -c "exit(0 if float('$BUG_SCORE') < 1.0 else 1)" 2>&1 \
    && check "Buggy score < 1.0" "PASS" || check "Buggy score < 1.0" "FAIL"
rm -rf /tmp/hspice_buggy

# Step 4: Check logs and score exist
echo ""
echo "--- Check output files ---"
LATEST_RUN=$(ls -td runs/task_000001/*/ 2>/dev/null | head -1)
[ -f "${LATEST_RUN}raw_public.log" ] && check "raw_public.log exists" "PASS" || check "raw_public.log exists" "FAIL"
[ -f "${LATEST_RUN}sanitized_public.log" ] && check "sanitized_public.log exists" "PASS" || check "sanitized_public.log exists" "FAIL"
[ -f "${LATEST_RUN}score.json" ] && check "score.json exists" "PASS" || check "score.json exists" "FAIL"

# Step 5: Check score.json has required fields
python3 -c "
import json
d = json.load(open('${LATEST_RUN}score.json'))
for f in ['total_score', 'objective_score', 'explanation_score', 'components', 'anti_cheat']:
    assert f in d, f'Missing field: {f}'
print('  score.json has all required fields')
" 2>&1 && check "score.json fields" "PASS" || check "score.json fields" "FAIL"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && echo "ALL HSPICE SMOKE TESTS PASSED" || { echo "HSPICE SMOKE TESTS FAILED"; exit 1; }
