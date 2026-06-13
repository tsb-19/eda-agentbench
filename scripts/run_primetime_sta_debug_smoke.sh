#!/bin/bash
# PrimeTime STA Debug smoke test — validates P7 track end-to-end
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

TASK_DIR="tasks/p7_primetime_sta_debug/smoke"
PASS=0
FAIL=0
SKIP_PT=0

check() {
    local name="$1" result="$2"
    if [ "$result" = "PASS" ]; then echo "  PASS: $name"; PASS=$((PASS + 1))
    elif [ "$result" = "SKIP" ]; then echo "  SKIP: $name"; SKIP_PT=$((SKIP_PT + 1))
    else echo "  FAIL: $name"; FAIL=$((FAIL + 1)); fi
}

echo "=== PrimeTime STA Debug Smoke Test ==="

# Step 0: Generate smoke task if not present
if [ ! -d "$TASK_DIR" ]; then
    echo ""
    echo "--- Generating smoke task ---"
    python3 scripts/generate_p7_primetime_sta_debug_tasks.py --count 1 --seed 1 --output-dir "$TASK_DIR"
fi

# Step 1: Validate task
echo ""
echo "--- Validate task ---"
VALIDATE_OUT=$(python3 -m eda_agentbench validate-task "$TASK_DIR" 2>&1) || true
echo "$VALIDATE_OUT"
echo "$VALIDATE_OUT" | grep -q "VALID" && check "Task validation" "PASS" || check "Task validation" "FAIL"

# Step 2: Check pt_shell availability
echo ""
echo "--- Check pt_shell availability ---"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
if command -v "$PT_CMD" &>/dev/null; then
    echo "  pt_shell found: $(which $PT_CMD)"
    PT_AVAILABLE=1
else
    echo "  pt_shell not found (EDA_PT_CMD=$PT_CMD) — will skip execution tests"
    PT_AVAILABLE=0
fi

# Step 3: Evaluate with solution (if PT available)
if [ "$PT_AVAILABLE" -eq 1 ]; then
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
    mkdir -p /tmp/pt_buggy
    cp "$TASK_DIR/files/constraints.sdc" /tmp/pt_buggy/constraints.sdc
    python3 -m eda_agentbench evaluate-task "$TASK_DIR" --submission /tmp/pt_buggy 2>&1 || true

    BUG_SCORE=$(python3 -c "
import json, glob, os
scores = sorted(glob.glob('runs/$TASK_ID/*/score.json'), key=os.path.getmtime)
if scores: print(json.load(open(scores[-1]))['total_score'])
else: print('1')
" 2>/dev/null) || BUG_SCORE="1"
    echo "  Buggy score: $BUG_SCORE"
    python3 -c "exit(0 if float('$BUG_SCORE') < 1.0 else 1)" 2>&1 \
        && check "Buggy score < 1.0" "PASS" || check "Buggy score < 1.0" "FAIL"
    rm -rf /tmp/pt_buggy
else
    echo ""
    echo "--- Skipping execution tests (pt_shell not available) ---"
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
assert meta['track'] == 'p7_primetime_sta_debug', f'Wrong track: {meta[\"track\"]}'
assert 'pt' in meta['tool'], f'Wrong tool: {meta[\"tool\"]}'
assert 'constraints.sdc' in meta['files']['editable'], 'constraints.sdc not editable'
assert 'design.v' in meta['files']['forbidden'], 'design.v not forbidden'
assert 'timing_check' in meta['scoring']['weights'], 'Missing timing_check weight'
print('  metadata is valid')
" 2>&1 && check "Metadata fields" "PASS" || check "Metadata fields" "FAIL"

echo ""
echo "=== Results: $PASS passed, $FAIL failed, $SKIP_PT skipped ==="
if [ "$FAIL" -eq 0 ]; then
    echo "ALL PRIMETIME STA DEBUG SMOKE TESTS PASSED"
    if [ "$SKIP_PT" -gt 0 ]; then
        echo "($SKIP_PT tests skipped — pt_shell not available)"
    fi
    exit 0
else
    echo "PRIMETIME STA DEBUG SMOKE TESTS FAILED"
    exit 1
fi
