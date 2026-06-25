#!/bin/bash
# Hidden grader (forge-resistant, mirrors the P9 two-session pattern).
#   Phase 1  launder : apply agent SDC -> write_sdc applied_hidden.sdc (output [apply]-prefixed)
#   Phase 2  signoff : FRESH pt_shell session reads ONLY applied_hidden.sdc -> ^SIGNOFF_OK/FAIL
#   Phase 3  spec    : grade_spec.py compares the laundered SDC to spec_truth.json -> ^CONSTRAINT_SPEC_*
# Markers are emitted only here / by the trusted phases; the [apply] prefix stops an
# agent-injected marker in constraints.sdc from matching the ^-anchored real markers.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
PY_CMD="${EDA_PY_CMD:-python3}"
APPLIED="applied_hidden.sdc"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then
    echo "SKIP: pt_shell not found (EDA_PT_CMD=$PT_CMD)"
    exit 0
fi

# --- Phase 1: launder (agent Tcl sandboxed via read_sdc; output prefixed/untrusted) ---
rm -f "$APPLIED"
APPLY_OUT="$("$PT_CMD" -f run_hidden.tcl 2>&1)"
echo "$APPLY_OUT" | sed 's/^/[apply] /'
if [ ! -s "$APPLIED" ]; then
    echo "SIGNOFF_FAIL worst_slack=NONE no_applied_sdc"
    echo "CONSTRAINT_SPEC_FAIL: no_applied_sdc"
    echo "CONSTRAINT_SPEC_SCORE: 0.000"
    exit 0
fi

# --- Phase 2: sign-off from the laundered (trusted) SDC, fresh session ---
SIGNOFF_OUT="$("$PT_CMD" -f run_signoff.tcl 2>&1)"
echo "$SIGNOFF_OUT" | grep -E "^SIGNOFF_OK|^SIGNOFF_FAIL" || echo "SIGNOFF_FAIL worst_slack=NONE no_signoff_marker"

# --- Phase 3: spec-equivalence grade (Python, reads the laundered SDC as data) ---
"$PY_CMD" grade_spec.py "$APPLIED" spec_truth.json 2>&1 || {
    echo "CONSTRAINT_SPEC_FAIL: grade_spec_error"
    echo "CONSTRAINT_SPEC_SCORE: 0.000"
}
exit 0
