#!/bin/bash
# Hidden grader for p13 traj_handoff_0001 (trajectory / evidence-generation handoff). Trusted phases;
# no agent-controlled code runs in the grading decision:
#   Phase 0 select   : parse submitted flow_config.json (consumed) + authority clock -> selected*.tcl
#   Phase 1 launder  : run_launder.tcl read_sdc/write_sdc -> applied_hidden.sdc (injection-safe)
#   Phase 2 coverage : record TRUSTED PT facts (intended clock present?, #constrained paths)->coverage.txt
#   Phase 3 signoff  : FRESH session signs off consumed netlist from applied_hidden.sdc -> ^SIGNOFF_*
#   Phase 4 reference: regen_reference.sh re-runs the TRUSTED generator on the submitted inputs ->
#                      ref_timing_report.rpt + ref_evidence_manifest.json (the oracle's own evidence)
#   Phase 5 grade    : grade_trajectory.py compares submitted vs reference + authority -> ^markers
# [apply]-prefixed launder/coverage output cannot collide with the ^-anchored real markers.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
PY_CMD="${EDA_PY_CMD:-python3}"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then
    echo "SKIP: pt_shell not found (EDA_PT_CMD=$PT_CMD)"
    exit 0
fi
rm -f applied_hidden.sdc coverage.txt selected_launder.tcl selected_signoff.tcl \
      ref_timing_report.rpt ref_evidence_manifest.json

# --- Phase 0: selection from submitted flow_config + authority clock ---
"$PY_CMD" - <<'PYEOF'
import json, re
def jget(path, key, default=""):
    try:
        t = open(path).read()
    except OSError:
        return default
    m = re.search(r'"' + re.escape(key) + r'"\s*:\s*"([^"]*)"', t)
    return m.group(1) if m else default
sel = jget("flow_config.json", "netlist")
top = jget("flow_config.json", "top_module", "acc_stage")
sdc = jget("flow_config.json", "constraints", "constraints.sdc")
want_clk = jget("handoff_manifest.json", "clock", "clk_main")
open("selected_launder.tcl","w").write('set sel "%s"\nset top "%s"\nset sdc "%s"\n'%(sel,top,sdc))
open("selected_signoff.tcl","w").write('set sel "%s"\nset top "%s"\nset want_clk "%s"\n'%(sel,top,want_clk))
PYEOF

# --- Phase 1: launder agent SDC ---
APPLY_OUT="$("$PT_CMD" -f run_launder.tcl 2>&1)"; echo "$APPLY_OUT" | sed 's/^/[apply] /'

# --- Phase 2: coverage facts from the laundered SDC + consumed netlist ---
COV_OUT="$("$PT_CMD" -f run_coverage.tcl 2>&1)"; echo "$COV_OUT" | sed 's/^/[apply] /'

# --- Phase 3: fresh sign-off of consumed netlist from laundered SDC ---
SIGN_OUT="$("$PT_CMD" -f run_signoff.tcl 2>&1)"
echo "$SIGN_OUT" | grep -E "^SIGNOFF_OK|^SIGNOFF_FAIL" || echo "SIGNOFF_FAIL worst_slack=NONE no_marker"

# --- Phase 4: hidden reference re-run (trusted generator on submitted inputs) ---
bash regen_reference.sh >/dev/null 2>&1

# --- Phase 5: grade submitted vs reference + authority ---
"$PY_CMD" grade_trajectory.py handoff_truth.json 2>&1 || {
    echo "EVIDENCE_SCORE: 0.000"; echo "EVIDENCE_DETAIL: grade_error"
    echo "FINAL_ARTIFACT_CONSISTENCY_SCORE: 0.000"; echo "FINAL_ARTIFACT_CONSISTENCY_DETAIL: grade_error"
    echo "SCENARIO_CLOCK_SCORE: 0.000"; echo "SCENARIO_CLOCK_DETAIL: grade_error"
    echo "PROVENANCE_SCORE: 0.000"; echo "PROVENANCE_DETAIL: grade_error"
}
exit 0
