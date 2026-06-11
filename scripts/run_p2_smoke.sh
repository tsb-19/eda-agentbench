#!/bin/bash
# P2 Testbench/SVA Generation smoke test
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

echo "=== P2 TB/SVA Smoke Test ==="

echo ""
echo "=== Step 1: Install package ==="
pip install -e . 2>&1 | tail -3
echo ""

echo "=== Step 2: Validate task ==="
VALIDATE_OUT=$(eda-bench validate-task tasks/p2_rtl_gen/smoke/task_200000 2>&1)
echo "$VALIDATE_OUT"
echo "$VALIDATE_OUT" | grep -q "VALID" && check "Task validation" "PASS" || check "Task validation" "FAIL"
echo ""

echo "=== Step 3: Evaluate with correct solution ==="
eda-bench evaluate-task tasks/p2_rtl_gen/smoke/task_200000 \
    --submission tasks/p2_rtl_gen/smoke/task_200000/solution 2>&1

SOLUTION_SCORE=$(ls -t runs/task_200000/*/score.json 2>/dev/null | head -1)
SOLUTION_TOTAL=$(python3 -c "import json; d=json.load(open('$SOLUTION_SCORE')); print(d['total_score'])")
echo "  Solution total_score: $SOLUTION_TOTAL"

python3 -c "
import json, sys
d = json.load(open('$SOLUTION_SCORE'))
ts = d['total_score']
assert ts == 1.0, f'Expected 1.0, got {ts}'
comps = {c['name']: c['raw_score'] for c in d['components']}
assert comps.get('compile', 0) == 1.0, f'compile: {comps.get(\"compile\")}'
assert comps.get('golden_pass', 0) == 1.0, f'golden_pass: {comps.get(\"golden_pass\")}'
assert comps.get('mutant_1', 0) == 1.0, f'mutant_1: {comps.get(\"mutant_1\")}'
assert comps.get('mutant_2', 0) == 1.0, f'mutant_2: {comps.get(\"mutant_2\")}'
" 2>&1 && check "Solution total_score == 1.0" "PASS" || check "Solution total_score == 1.0" "FAIL"

echo ""

echo "=== Step 4: Evaluate with buggy (empty) submission ==="
eda-bench evaluate-task tasks/p2_rtl_gen/smoke/task_200000 \
    --submission tasks/p2_rtl_gen/smoke/task_200000/buggy_submission 2>&1

BUGGY_SCORE=$(ls -t runs/task_200000/*/score.json 2>/dev/null | head -1)
BUGGY_TOTAL=$(python3 -c "import json; d=json.load(open('$BUGGY_SCORE')); print(d['total_score'])")
echo "  Buggy total_score: $BUGGY_TOTAL"

python3 -c "
import json, sys
d = json.load(open('$BUGGY_SCORE'))
ts = d['total_score']
assert ts < 1.0, f'Expected < 1.0, got {ts}'
" 2>&1 && check "Buggy score < 1.0" "PASS" || check "Buggy score < 1.0" "FAIL"

echo ""

echo "=== Step 5: Anti-cheat check ==="
AC_OUT=$(eda-bench evaluate-task tasks/p2_rtl_gen/smoke/task_200000 \
    --submission tasks/p2_rtl_gen/smoke/task_200000/files 2>&1 || true)
echo "$AC_OUT" | grep -q "ANTI-CHEAT FAIL" && check "Forbidden file submission blocked" "PASS" || check "Forbidden file submission blocked" "FAIL"

echo ""

echo "=== Results: $PASS passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
    echo "P2 SMOKE TEST FAILED"
    exit 1
else
    echo "ALL P2 SMOKE TESTS PASSED"
fi
