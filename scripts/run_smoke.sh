#!/bin/bash
# EDA-AgentBench smoke test — runs all first-stage checks with explicit assertions
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

echo "=== Step 1: Install package ==="
pip install -e . 2>&1 | tail -3
echo ""

echo "=== Step 2: Detect tools ==="
DETECT_OUT=$(eda-bench detect-tools 2>&1)
echo "$DETECT_OUT"
echo "$DETECT_OUT" | grep -q "vcs.*synopsys.*YES" && check "VCS detected" "PASS" || check "VCS detected" "FAIL"
echo ""

echo "=== Step 3: Validate task ==="
VALIDATE_OUT=$(eda-bench validate-task tasks/p1_rtl_debug/task_000001 2>&1)
echo "$VALIDATE_OUT"
echo "$VALIDATE_OUT" | grep -q "VALID" && check "Task validation" "PASS" || check "Task validation" "FAIL"
echo ""

echo "=== Step 4: Evaluate with correct solution ==="
eda-bench evaluate-task tasks/p1_rtl_debug/task_000001 \
    --submission tasks/p1_rtl_debug/task_000001/solution 2>&1

# Find latest score.json for this task
SOLUTION_SCORE=$(find runs/task_000001 -name "score.json" -newer runs/task_000001 -exec ls -t {} + 2>/dev/null | head -1)
if [ -z "$SOLUTION_SCORE" ]; then
    SOLUTION_SCORE=$(ls -t runs/task_000001/*/score.json 2>/dev/null | head -1)
fi
SOLUTION_TOTAL=$(python3 -c "import json; d=json.load(open('$SOLUTION_SCORE')); print(d['total_score'])")
SOLUTION_OBJECTIVE=$(python3 -c "import json; d=json.load(open('$SOLUTION_SCORE')); print(d.get('objective_score', 'N/A'))")
echo "  Solution total_score: $SOLUTION_TOTAL"
echo "  Solution objective_score: $SOLUTION_OBJECTIVE"

python3 -c "
import json, sys
d = json.load(open('$SOLUTION_SCORE'))
ts = d['total_score']
assert ts == 1.0, f'Expected 1.0, got {ts}'
" 2>&1 && check "Solution total_score == 1.0" "PASS" || check "Solution total_score == 1.0" "FAIL"

echo ""

echo "=== Step 5: Evaluate with buggy original ==="
eda-bench evaluate-task tasks/p1_rtl_debug/task_000001 \
    --submission tasks/p1_rtl_debug/task_000001/buggy_submission 2>&1

BUGGY_SCORE=$(ls -t runs/task_000001/*/score.json 2>/dev/null | head -1)
BUGGY_TOTAL=$(python3 -c "import json; d=json.load(open('$BUGGY_SCORE')); print(d['total_score'])")
echo "  Buggy total_score: $BUGGY_TOTAL"

python3 -c "
import json, sys
d = json.load(open('$BUGGY_SCORE'))
ts = d['total_score']
assert ts < 1.0, f'Expected < 1.0, got {ts}'
# Check at least one test component failed
comps = {c['name']: c['raw_score'] for c in d['components']}
pub = comps.get('public_test', 1.0)
hid = comps.get('hidden_test', 1.0)
assert pub < 1.0 or hid < 1.0, f'Expected at least one test failure, public={pub} hidden={hid}'
" 2>&1 && check "Buggy score < 1.0 and has test failure" "PASS" || check "Buggy score < 1.0 and has test failure" "FAIL"

echo ""

echo "=== Step 6: Anti-cheat check ==="
# Verify that submitting forbidden files triggers anti-cheat fail
AC_OUT=$(eda-bench evaluate-task tasks/p1_rtl_debug/task_000001 \
    --submission tasks/p1_rtl_debug/task_000001/files 2>&1 || true)
echo "$AC_OUT" | grep -q "ANTI-CHEAT FAIL" && check "Forbidden file submission blocked" "PASS" || check "Forbidden file submission blocked" "FAIL"

echo ""

echo "=== Results: $PASS passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
    echo "SMOKE TEST FAILED"
    exit 1
else
    echo "ALL SMOKE TESTS PASSED"
fi
