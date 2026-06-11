#!/usr/bin/env bash
# P5 SPICE Deck Debug batch evaluation.
# Tests all 10 imported tasks in solution and buggy modes.
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TASKS_ROOT="$ROOT/tasks/p5_spice_deck_debug/imported"
PYTHON="${PYTHON:-python3}"

if [ ! -d "$TASKS_ROOT" ]; then
    echo "ERROR: P5 tasks not found at $TASKS_ROOT"
    echo "Run: python3 scripts/import_p5_tasks.py"
    exit 1
fi

echo "=== P5 SPICE Deck Debug Batch Evaluation ==="
echo "Tasks: $TASKS_ROOT"
echo ""

SOL_PASS=0
SOL_FAIL=0
BUG_PASS=0
BUG_FAIL=0
TOTAL=0

# Header
printf "%-30s %-20s %-8s %-8s %-8s\n" "task_id" "expected_error" "sol" "bug" "status"
printf "%-30s %-20s %-8s %-8s %-8s\n" "------" "---------------" "---" "---" "------"

for task_dir in "$TASKS_ROOT"/spice_deck_debug_*; do
    [ -d "$task_dir" ] || continue
    task_id=$(basename "$task_dir")
    meta="$task_dir/metadata.json"
    [ -f "$meta" ] || continue

    expected_err=$($PYTHON -c "import json; print(json.load(open('$meta')).get('expected_error_category','?'))")
    TOTAL=$((TOTAL + 1))

    # Solution mode: submit hidden/ (fixed deck)
    sol_score=$($PYTHON -c "
import sys, json
sys.path.insert(0, '$ROOT')
from eda_agentbench.cli import _evaluate_single
from pathlib import Path
meta = json.loads(open('$meta').read())
try:
    _, sr = _evaluate_single(Path('$task_dir'), Path('$task_dir/hidden'), meta, 300)
    print(f'{sr.total_score:.2f}')
except Exception as e:
    print(f'ERR:{e}')
" 2>/dev/null)

    # Buggy mode: submit visible/ (original buggy deck)
    bug_score=$($PYTHON -c "
import sys, json, tempfile, shutil
sys.path.insert(0, '$ROOT')
from eda_agentbench.cli import _evaluate_single
from pathlib import Path
meta = json.loads(open('$meta').read())
# Create buggy submission dir with only the editable file
buggy_dir = Path(tempfile.mkdtemp(prefix='p5_bug_'))
for ef in meta['files']['editable']:
    src = Path('$task_dir') / ef
    if src.is_file():
        shutil.copy2(src, buggy_dir / Path(ef).name)
try:
    _, sr = _evaluate_single(Path('$task_dir'), buggy_dir, meta, 300)
    print(f'{sr.total_score:.2f}')
except Exception as e:
    print(f'ERR:{e}')
finally:
    shutil.rmtree(buggy_dir, ignore_errors=True)
" 2>/dev/null)

    # Determine pass/fail
    sol_ok="NO"
    bug_ok="NO"
    if echo "$sol_score" | grep -qE '^0\.(9[0-9]|8[0-9])|^1\.0'; then
        sol_ok="YES"
        SOL_PASS=$((SOL_PASS + 1))
    else
        SOL_FAIL=$((SOL_FAIL + 1))
    fi
    if echo "$bug_score" | grep -qE '^0\.[0-4]'; then
        bug_ok="YES"
        BUG_PASS=$((BUG_PASS + 1))
    elif echo "$bug_score" | grep -qE '^0\.[0-5]'; then
        bug_ok="YES"
        BUG_PASS=$((BUG_PASS + 1))
    else
        BUG_FAIL=$((BUG_FAIL + 1))
    fi

    status="OK"
    if [ "$sol_ok" = "NO" ] || [ "$bug_ok" = "NO" ]; then
        status="FAIL"
    fi

    printf "%-30s %-20s %-8s %-8s %-8s\n" "$task_id" "$expected_err" "$sol_score" "$bug_score" "$status"
done

echo ""
echo "=== Summary ==="
echo "  Total:        $TOTAL"
echo "  Solution OK:   $SOL_PASS / $TOTAL"
echo "  Buggy  OK:     $BUG_PASS / $TOTAL"
echo "  Failures:      $((SOL_FAIL + BUG_FAIL))"

if [ "$SOL_FAIL" -gt 0 ] || [ "$BUG_FAIL" -gt 0 ]; then
    echo ""
    echo "FAILURE: Some tasks did not meet expectations."
    exit 1
fi

echo ""
echo "All P5 tasks passed."
