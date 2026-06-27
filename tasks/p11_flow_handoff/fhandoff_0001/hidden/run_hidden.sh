#!/bin/bash
# Hidden grader for FlowHandoff Variant A. Two trusted phases, no agent-controlled code runs:
#   Phase 1  consistency : grade_handoff.py reads the agent-repaired handoff_manifest.json +
#             package artifacts + hidden handoff_truth.json AS DATA -> ^MANIFEST_* /
#             ^HANDOFF_CONSISTENCY_* / ^HANDOFF_MASKING_DETECTED markers.
#   Phase 2  signoff     : a FRESH pt_shell session signs off the MANIFEST-SELECTED netlist
#             (selection parsed here, passed via env) -> ^SIGNOFF_OK / ^SIGNOFF_FAIL.
# The agent edits only handoff_manifest.json (JSON, not Tcl), so there is no Tcl-injection
# surface; the manifest is parsed as data with stdlib json/regex. Markers are emitted only by
# these trusted phases.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
PY_CMD="${EDA_PY_CMD:-python3}"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then
    echo "SKIP: pt_shell not found (EDA_PT_CMD=$PT_CMD)"
    exit 0
fi

# --- Phase 1: cross-artifact handoff consistency (Python, manifest read as data) ---
"$PY_CMD" grade_handoff.py handoff_manifest.json handoff_truth.json 2>&1 || {
    echo "MANIFEST_SCORE: 0.000"
    echo "MANIFEST_DETAIL: grade_handoff_error"
    echo "HANDOFF_CONSISTENCY_SCORE: 0.000"
    echo "HANDOFF_CONSISTENCY_DETAIL: grade_handoff_error"
}

# --- resolve the manifest-selected netlist/top/sdc and write them where the FORWARDER can see
#     them: a selected.tcl in the workspace (mirrored to the remote host). Env vars do NOT
#     survive the remote tool hop, so the sign-off session sources this file instead. ---
"$PY_CMD" - <<'PYEOF'
import json
m = json.load(open("handoff_manifest.json"))
sel = m.get("netlist", "")
top = m.get("top_module", "acc_stage")
sdc = m.get("constraints", "constraints.sdc")
with open("selected.tcl", "w") as f:
    f.write('set sel "%s"\nset top "%s"\nset sdc "%s"\n' % (sel, top, sdc))
PYEOF

# --- Phase 2: sign off the selected netlist in a fresh session ---
SIGNOFF_OUT="$("$PT_CMD" -f run_signoff.tcl 2>&1)"
echo "$SIGNOFF_OUT" | grep -E "^SIGNOFF_OK|^SIGNOFF_FAIL" || echo "SIGNOFF_FAIL worst_slack=NONE no_signoff_marker"
exit 0
