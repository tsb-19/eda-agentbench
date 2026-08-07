#!/bin/bash
# Hidden grader (forge-resistant, two-phase). Runs in the FLATTENED evaluator workspace
# (files/ + hidden/ co-located). Writes signoff_result.json, then emits grade markers.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
PY_CMD="${EDA_PY_CMD:-python3}"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then echo '{"signoff_green": false, "fatal": "pt_shell not found"}' > signoff_result.json; exit 0; fi
"$PY_CMD" build_applied_sdc.py
# Phase 1: launder (output [apply]-prefixed so an injected marker cannot match ^marker)
APPLY_OUT="$("$PT_CMD" -f run_launder.tcl 2>&1)"; echo "$APPLY_OUT" | sed 's/^/[apply] /'
# Phase 2: signoff on laundered SDC
SIGN_OUT="$("$PT_CMD" -f run_signoff.tcl 2>&1)"
SIGN_LINE=$(echo "$SIGN_OUT" | grep -E '^SIGNOFF_OK|^SIGNOFF_FAIL' || echo 'SIGNOFF_FAIL worst_slack=NONE no_marker')
SLACK=$(echo "$SIGN_LINE" | sed -E 's/.*worst_slack=([-0-9.]+|NONE).*/\1/')
GREEN=$(echo "$SIGN_LINE" | grep -q '^SIGNOFF_OK' && echo true || echo false)
AEX=$(grep -cE 'set_false_path|set_multicycle_path' applied_hidden.sdc 2>/dev/null || echo 0)
cat > signoff_result.json <<JSON
{"signoff_green": $GREEN, "worst_slack": "$SLACK", "applied_exception_lines": $AEX, "expected_exception_lines": 1, "signoff_line": "$SIGN_LINE"}
JSON
# Phase 3: provenance/authority grade (python; reads truth + signoff_result + applied_hidden.sdc from cwd)
"$PY_CMD" grade_sta_handoff.py
exit 0
