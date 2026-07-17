# pt_signoff.tcl -- REFERENCE DESCRIPTION of the evidence flow (READ-ONLY documentation).
#
# The real flow is run by run_evidence.sh -> gen_evidence.py -> evidence_signoff.tcl. This file is
# here so you can see what the flow does. Do not edit it; repair the DATA inputs (flow_config.json,
# constraints.sdc) and then run `bash run_evidence.sh`.
#
# Flow (conceptually):
#   1. read flow_config.json -> ${flow_config(netlist)} is the consumed netlist
#   2. read_db tiny.db ; set link_path "* tiny.db"
#   3. read_verilog ${flow_config(netlist)} ; link_design ${flow_config(top_module)}
#   4. read_sdc constraints.sdc ; update_timing
#   5. report setup timing (max delay, -nworst 1); sign off iff worst slack >= 0 AND >=1 path is
#      actually constrained (a clean report on ZERO constrained paths is a false pass)
#   6. gen_evidence.py canonicalizes the real report -> timing_report.rpt, computes report_digest,
#      input hashes, and a deterministic run_nonce -> evidence_manifest.json
#
# Authority: handoff_manifest.json (netlist v2 / clk_main / func / typ). The handoff is correct only
# when the consumed netlist, the bound clock, AND the freshly generated evidence all agree with it.
