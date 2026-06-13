#!/bin/bash
# DC Constraint Debug smoke test — validates P6 track end-to-end
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

TASK_DIR="tasks/p6_dc_constraint_debug/smoke"
PASS=0
FAIL=0
SKIP_DC=0

check() {
    local name="$1" result="$2"
    if [ "$result" = "PASS" ]; then echo "  PASS: $name"; PASS=$((PASS + 1))
    elif [ "$result" = "SKIP" ]; then echo "  SKIP: $name"; SKIP_DC=$((SKIP_DC + 1))
    else echo "  FAIL: $name"; FAIL=$((FAIL + 1)); fi
}

echo "=== DC Constraint Debug Smoke Test ==="

# Step 0: Generate smoke task if not present
if [ ! -d "$TASK_DIR" ]; then
    echo ""
    echo "--- Generating smoke task ---"
    python3 scripts/generate_p6_dc_constraint_debug_tasks.py --count 1 --seed 1 --output-dir "$TASK_DIR"
fi

# Step 1: Validate task
echo ""
echo "--- Validate task ---"
VALIDATE_OUT=$(python3 -m eda_agentbench validate-task "$TASK_DIR" 2>&1) || true
echo "$VALIDATE_OUT"
echo "$VALIDATE_OUT" | grep -q "VALID" && check "Task validation" "PASS" || check "Task validation" "FAIL"

# Step 2: Check dc_shell availability
echo ""
echo "--- Check dc_shell availability ---"
DC_CMD="${EDA_DC_CMD:-dc_shell}"
if command -v "$DC_CMD" &>/dev/null; then
    echo "  dc_shell found: $(which $DC_CMD)"
    DC_AVAILABLE=1
else
    echo "  dc_shell not found (EDA_DC_CMD=$DC_CMD) — will skip execution tests"
    DC_AVAILABLE=0
fi

# Step 3: Evaluate with solution (if DC available)
if [ "$DC_AVAILABLE" -eq 1 ]; then
    echo ""
    echo "--- Evaluate with solution (expect PASS) ---"
    python3 -m eda_agentbench evaluate-task "$TASK_DIR" --submission "$TASK_DIR/solution" 2>&1 || true

    TASK_ID=$(python3 -c "
import json
meta = json.load(open('$TASK_DIR/metadata.json'))
print(meta['task_id'])
")
    SOL_SCORE=$(python3 -c "
import json, glob, os
scores = sorted(glob.glob('runs/$TASK_ID/*/score.json'), key=os.path.getmtime)
if scores: print(json.load(open(scores[-1]))['total_score'])
else: print('0')
" 2>/dev/null) || SOL_SCORE="0"
    echo "  Solution score: $SOL_SCORE"
    python3 -c "exit(0 if abs(float('$SOL_SCORE') - 1.0) < 0.01 else 1)" 2>&1 \
        && check "Solution total_score == 1.0" "PASS" || check "Solution total_score == 1.0" "FAIL"

    # Step 4: Evaluate with buggy baseline
    echo ""
    echo "--- Evaluate with buggy baseline (expect FAIL) ---"
    mkdir -p /tmp/dc_buggy
    cp "$TASK_DIR/files/constraints.sdc" /tmp/dc_buggy/constraints.sdc
    python3 -m eda_agentbench evaluate-task "$TASK_DIR" --submission /tmp/dc_buggy 2>&1 || true

    BUG_SCORE=$(python3 -c "
import json, glob, os
scores = sorted(glob.glob('runs/$TASK_ID/*/score.json'), key=os.path.getmtime)
if scores: print(json.load(open(scores[-1]))['total_score'])
else: print('1')
" 2>/dev/null) || BUG_SCORE="1"
    echo "  Buggy score: $BUG_SCORE"
    python3 -c "exit(0 if float('$BUG_SCORE') < 1.0 else 1)" 2>&1 \
        && check "Buggy score < 1.0" "PASS" || check "Buggy score < 1.0" "FAIL"
    rm -rf /tmp/dc_buggy
else
    echo ""
    echo "--- Skipping execution tests (dc_shell not available) ---"
    check "Solution evaluation" "SKIP"
    check "Buggy evaluation" "SKIP"
fi

# Step 5: Check files exist
echo ""
echo "--- Check task structure ---"
[ -f "$TASK_DIR/metadata.json" ] && check "metadata.json exists" "PASS" || check "metadata.json exists" "FAIL"
[ -f "$TASK_DIR/prompt.md" ] && check "prompt.md exists" "PASS" || check "prompt.md exists" "FAIL"
[ -f "$TASK_DIR/files/design.v" ] && check "design.v exists" "PASS" || check "design.v exists" "FAIL"
[ -f "$TASK_DIR/files/constraints.sdc" ] && check "constraints.sdc exists" "PASS" || check "constraints.sdc exists" "FAIL"
[ -f "$TASK_DIR/files/run_public.sh" ] && check "run_public.sh exists" "PASS" || check "run_public.sh exists" "FAIL"
[ -d "$TASK_DIR/solution" ] && check "solution/ exists" "PASS" || check "solution/ exists" "FAIL"
[ -d "$TASK_DIR/hidden" ] && check "hidden/ exists" "PASS" || check "hidden/ exists" "FAIL"

# Step 6: Verify metadata
echo ""
echo "--- Verify metadata ---"
python3 -c "
import json
meta = json.load(open('$TASK_DIR/metadata.json'))
assert meta['track'] == 'p6_dc_constraint_debug', f'Wrong track: {meta[\"track\"]}'
assert 'dc' in meta['tool'], f'Wrong tool: {meta[\"tool\"]}'
assert 'constraints.sdc' in meta['files']['editable'], 'constraints.sdc not editable'
assert 'design.v' in meta['files']['forbidden'], 'design.v not forbidden'
# Check scoring uses new constraint_pass weight
assert 'constraint_pass' in meta['scoring']['weights'], 'Missing constraint_pass weight'
print('  metadata is valid')
" 2>&1 && check "Metadata fields" "PASS" || check "Metadata fields" "FAIL"

echo ""
echo "=== Results: $PASS passed, $FAIL failed, $SKIP_DC skipped ==="
if [ "$FAIL" -eq 0 ]; then
    echo "ALL DC CONSTRAINT DEBUG SMOKE TESTS PASSED"
    if [ "$SKIP_DC" -gt 0 ]; then
        echo "($SKIP_DC tests skipped — dc_shell not available)"
    fi
    exit 0
else
    echo "DC CONSTRAINT DEBUG SMOKE TESTS FAILED"
    exit 1
fi
