#!/bin/bash
# Batch evaluate all generated P1 RTL Debug tasks
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

TASKS_DIR="${1:-tasks/p1_rtl_debug/generated}"

if [ ! -d "$TASKS_DIR" ]; then
    echo "ERROR: Tasks directory not found: $TASKS_DIR"
    echo "Run: python scripts/generate_p1_tasks.py"
    exit 1
fi

TOTAL=0
VALID=0
SOL_PERFECT=0
BUGGY_LOWER=0
BUGGY_HAS_FAIL=0
FAIL_LIST=()

echo "=== Batch Evaluation: $TASKS_DIR ==="
echo ""

for task_dir in "$TASKS_DIR"/task_*; do
    [ -d "$task_dir" ] || continue
    task_name=$(basename "$task_dir")
    TOTAL=$((TOTAL + 1))

    # Validate
    if ! eda-bench validate-task "$task_dir" > /dev/null 2>&1; then
        echo "  FAIL validate: $task_name"
        FAIL_LIST+=("$task_name:validate")
        continue
    fi
    VALID=$((VALID + 1))

    # Evaluate with solution
    eda-bench evaluate-task "$task_dir" --submission "$task_dir/solution" > /dev/null 2>&1
    SOL_SCORE=$(python3 -c "
import json, glob, os
scores = sorted(glob.glob(os.path.join('runs', '$(basename "$task_dir")', '*', 'score.json')), key=os.path.getmtime)
if scores: print(json.load(open(scores[-1]))['total_score'])
else: print('0')
")
    if python3 -c "exit(0 if abs(float('$SOL_SCORE') - 1.0) < 0.01 else 1)"; then
        SOL_PERFECT=$((SOL_PERFECT + 1))
    else
        echo "  FAIL solution: $task_name score=$SOL_SCORE"
        FAIL_LIST+=("$task_name:solution=$SOL_SCORE")
    fi

    # Evaluate with buggy design
    mkdir -p "/tmp/buggy_sub_$task_name"
    cp "$task_dir/files/design.sv" "/tmp/buggy_sub_$task_name/design.sv"
    eda-bench evaluate-task "$task_dir" --submission "/tmp/buggy_sub_$task_name" > /dev/null 2>&1
    BUG_SCORE=$(python3 -c "
import json, glob, os
scores = sorted(glob.glob(os.path.join('runs', '$(basename "$task_dir")', '*', 'score.json')), key=os.path.getmtime)
if scores: print(json.load(open(scores[-1]))['total_score'])
else: print('1')
")
    HAS_FAIL=$(python3 -c "
import json, glob, os
scores = sorted(glob.glob(os.path.join('runs', '$(basename "$task_dir")', '*', 'score.json')), key=os.path.getmtime)
if scores:
    d = json.load(open(scores[-1]))
    comps = {c['name']: c['raw_score'] for c in d.get('components', [])}
    pub = comps.get('public_test', 1.0)
    hid = comps.get('hidden_test', 1.0)
    print('yes' if pub < 1.0 or hid < 1.0 else 'no')
else: print('no')
")
    rm -rf "/tmp/buggy_sub_$task_name"

    if python3 -c "exit(0 if float('$BUG_SCORE') < 1.0 else 1)"; then
        BUGGY_LOWER=$((BUGGY_LOWER + 1))
    else
        echo "  FAIL buggy not lower: $task_name score=$BUG_SCORE"
        FAIL_LIST+=("$task_name:buggy=$BUG_SCORE")
    fi

    if [ "$HAS_FAIL" = "yes" ]; then
        BUGGY_HAS_FAIL=$((BUGGY_HAS_FAIL + 1))
    fi

    # Print progress
    python3 -c "print(f'  {\"$task_name\":<20} sol={float(\"$SOL_SCORE\"):.2f}  bug={float(\"$BUG_SCORE\"):.2f}  fail={\"$HAS_FAIL\"}')"
done

echo ""
echo "=== Summary ==="
echo "  Total tasks:          $TOTAL"
echo "  Valid:                $VALID / $TOTAL"
echo "  Solution perfect 1.0: $SOL_PERFECT / $TOTAL"
echo "  Buggy score < 1.0:    $BUGGY_LOWER / $TOTAL"
echo "  Buggy has test fail:  $BUGGY_HAS_FAIL / $TOTAL"

if [ ${#FAIL_LIST[@]} -gt 0 ]; then
    echo ""
    echo "  Failures:"
    for f in "${FAIL_LIST[@]}"; do
        echo "    $f"
    done
fi

# Bug type distribution
echo ""
echo "=== Bug Type Distribution ==="
python3 -c "
import json, glob
from collections import Counter
EXPECTED = {
    'sensitivity_list': 2, 'blocking_nonblocking': 2, 'reset_polarity': 2,
    'width_truncation': 2, 'comparison_boundary': 2, 'wrong_mux_select': 2,
    'priority_order': 2, 'fsm_transition_error': 2, 'counter_off_by_one': 2,
    'enable_condition': 2,
}
types = Counter()
for meta_file in sorted(glob.glob('$TASKS_DIR/*/metadata.json')):
    meta = json.load(open(meta_file))
    types[meta.get('generator', {}).get('bug_type', 'unknown')] += 1
for bt in sorted(EXPECTED.keys()):
    cnt = types.get(bt, 0)
    mark = 'OK' if cnt == EXPECTED[bt] else 'MISMATCH'
    print(f'  {bt:<25} {cnt}  ({mark})')
"
DIST_OK=$(python3 -c "
import json, glob
from collections import Counter
EXPECTED = {
    'sensitivity_list': 2, 'blocking_nonblocking': 2, 'reset_polarity': 2,
    'width_truncation': 2, 'comparison_boundary': 2, 'wrong_mux_select': 2,
    'priority_order': 2, 'fsm_transition_error': 2, 'counter_off_by_one': 2,
    'enable_condition': 2,
}
types = Counter()
for meta_file in sorted(glob.glob('$TASKS_DIR/*/metadata.json')):
    meta = json.load(open(meta_file))
    types[meta.get('generator', {}).get('bug_type', 'unknown')] += 1
ok = all(types.get(bt, 0) == cnt for bt, cnt in EXPECTED.items()) and len(set(types.keys()) - set(EXPECTED.keys())) == 0
print('yes' if ok else 'no')
")

echo ""
ALL_OK=true
if [ "$SOL_PERFECT" -ne "$TOTAL" ]; then echo "  FAIL: solution scores"; ALL_OK=false; fi
if [ "$BUGGY_LOWER" -ne "$TOTAL" ]; then echo "  FAIL: buggy scores"; ALL_OK=false; fi
DIST_RESULT=$(echo "$DIST_OK" | tail -1)
if [ "$DIST_RESULT" != "yes" ]; then echo "  FAIL: bug type distribution"; ALL_OK=false; fi

if [ "$ALL_OK" = "true" ]; then
    echo "ALL CHECKS PASSED"
else
    echo "SOME CHECKS FAILED"
    exit 1
fi
