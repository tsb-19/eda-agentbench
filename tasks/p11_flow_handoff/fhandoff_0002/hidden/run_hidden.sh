#!/bin/bash
# Hidden grader for FlowHandoff Variant C. Three trusted phases, no agent-controlled code in the
# grading decision:
#   Phase 1  launder+coverage : run_hidden.tcl applies the agent SDC, write_sdc -> applied_hidden.sdc,
#             and records TRUSTED PrimeTime coverage facts (intended clock present?, #constrained
#             paths) to coverage.txt.
#   Phase 2  signoff          : a FRESH pt_shell session reads ONLY applied_hidden.sdc -> ^SIGNOFF_*.
#   Phase 3  grade            : grade_handoff.py reads the laundered SDC + coverage.txt + manifest +
#             handoff_truth.json AS DATA -> ^MANIFEST_* / ^HANDOFF_CONSISTENCY_* / masking markers.
# The [apply]-prefixed launder output cannot collide with the ^-anchored real markers.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
PY_CMD="${EDA_PY_CMD:-python3}"
APPLIED="applied_hidden.sdc"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then
    echo "SKIP: pt_shell not found (EDA_PT_CMD=$PT_CMD)"
    exit 0
fi

# --- Phase 1: launder + coverage ---
rm -f "$APPLIED" coverage.txt
APPLY_OUT="$("$PT_CMD" -f run_hidden.tcl 2>&1)"
echo "$APPLY_OUT" | sed 's/^/[apply] /'
if [ ! -s "$APPLIED" ]; then
    echo "SIGNOFF_FAIL worst_slack=NONE no_applied_sdc"
    echo "MANIFEST_SCORE: 0.000"
    echo "MANIFEST_DETAIL: no_applied_sdc"
    echo "HANDOFF_CONSISTENCY_SCORE: 0.000"
    echo "HANDOFF_CONSISTENCY_DETAIL: no_applied_sdc"
    exit 0
fi

# --- Phase 2: sign off from the laundered SDC, fresh session ---
SIGNOFF_OUT="$("$PT_CMD" -f run_signoff.tcl 2>&1)"
echo "$SIGNOFF_OUT" | grep -E "^SIGNOFF_OK|^SIGNOFF_FAIL" || echo "SIGNOFF_FAIL worst_slack=NONE no_signoff_marker"

# --- Phase 3: handoff/coverage grade (Python, all inputs read as data) ---
"$PY_CMD" grade_handoff.py "$APPLIED" handoff_truth.json handoff_manifest.json coverage.txt 2>&1 || {
    echo "MANIFEST_SCORE: 0.000"
    echo "MANIFEST_DETAIL: grade_handoff_error"
    echo "HANDOFF_CONSISTENCY_SCORE: 0.000"
    echo "HANDOFF_CONSISTENCY_DETAIL: grade_handoff_error"
}
exit 0
