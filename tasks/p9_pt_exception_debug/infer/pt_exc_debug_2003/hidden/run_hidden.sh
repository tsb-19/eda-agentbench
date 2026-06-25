#!/bin/bash
# Hidden grader (two-session, forge-resistant). Emits EXC_EXEC_OK / EXC_SCORE.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
APPLIED="applied_hidden.sdc"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then echo "SKIP: pt_shell not found (EDA_PT_CMD=$PT_CMD)"; exit 0; fi

rm -f "$APPLIED"
# Phase 1: launder. Prefix output so an injected "EXC_SCORE:" cannot match ^EXC_SCORE:.
APPLY_OUT="$("$PT_CMD" -f run_hidden.tcl 2>&1)"
echo "$APPLY_OUT" | sed 's/^/[apply] /'
if [ ! -s "$APPLIED" ]; then
    echo "EXC_EXEC_FAIL: no_applied_sdc"
    echo "EXC_SCORE: 0.000"
    exit 0
fi
echo "EXC_EXEC_OK"
# Phase 2: grade in a fresh session from the laundered (trusted) SDC.
GRADE_OUT="$("$PT_CMD" -f run_grade.tcl 2>&1)"
if echo "$GRADE_OUT" | grep -qE "^EXC_SCORE:"; then
    echo "$GRADE_OUT" | grep -E "^EXC_SCORE:|^EXC_DETAIL:"
else
    echo "EXC_SCORE: 0.000"
    echo "EXC_DETAIL: grade_session_produced_no_score"
fi
exit 0
