#!/bin/bash
# Hidden grader for p14 workflow handoff. Trusted phases; no agent code runs in the decision:
#   Phase 0 select  : parse submitted flow_config.json + authority clock -> selected*.tcl
#   Phase 1 launder : run_launder.tcl read_sdc/write_sdc -> applied_hidden.sdc (injection-safe)
#   Phase 2 coverage: TRUSTED PT facts (intended clock present?, #constrained paths)
#   Phase 3 signoff : FRESH session signs off consumed netlist from applied_hidden.sdc
#   Phase 4 ref     : regen_reference.sh re-runs the TRUSTED evidence chain on submitted inputs
#   Phase 5 grade   : grade_workflow.py compares submitted chain vs reference + authority
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
PY_CMD="${EDA_PY_CMD:-python3}"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then echo "SKIP: pt_shell not found"; exit 0; fi
rm -f applied_hidden.sdc coverage.txt selected_launder.tcl selected_signoff.tcl \
      ref_timing_report.rpt ref_evidence_manifest.json ref_stage2_summary.json

"$PY_CMD" - <<'PYX'
import json, re
def jget(path, key, default=''):
    try:
        t = open(path).read()
    except OSError:
        return default
    m = re.search(r'"' + re.escape(key) + r'"\s*:\s*"([^"]*)"', t)
    return m.group(1) if m else default
sel = jget('flow_config.json', 'netlist')
top = jget('flow_config.json', 'top_module', 'acc_stage')
sdc = jget('flow_config.json', 'constraints', 'constraints.sdc')
want_clk = jget('handoff_manifest.json', 'clock', 'clk_main')
open('selected_launder.tcl','w').write('set sel "%s"\nset top "%s"\nset sdc "%s"\n'%(sel,top,sdc))
open('selected_signoff.tcl','w').write('set sel "%s"\nset top "%s"\nset want_clk "%s"\n'%(sel,top,want_clk))
PYX

APPLY_OUT="$("$PT_CMD" -f run_launder.tcl 2>&1)"; echo "$APPLY_OUT" | sed 's/^/[apply] /'
COV_OUT="$("$PT_CMD" -f run_coverage.tcl 2>&1)"; echo "$COV_OUT" | sed 's/^/[apply] /'
SIGN_OUT="$("$PT_CMD" -f run_signoff.tcl 2>&1)"
echo "$SIGN_OUT" | grep -E "^SIGNOFF_OK|^SIGNOFF_FAIL" || echo "SIGNOFF_FAIL worst_slack=NONE no_marker"
bash regen_reference.sh >/dev/null 2>&1
"$PY_CMD" grade_workflow.py handoff_truth.json 2>&1 || {
    echo "EVIDENCE_SCORE: 0.000"; echo "EVIDENCE_DETAIL: grade_error"
    echo "FINAL_STATE_SCORE: 0.000"; echo "FINAL_STATE_DETAIL: grade_error"
    echo "STAGE_CHAIN_SCORE: 0.000"; echo "STAGE_CHAIN_DETAIL: grade_error"
    echo "PROVENANCE_SCORE: 0.000"; echo "PROVENANCE_DETAIL: grade_error"
}
exit 0
