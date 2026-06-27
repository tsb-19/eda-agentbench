# pt_signoff.tcl -- REFERENCE DESCRIPTION of the downstream sign-off flow (READ-ONLY).
#
# This file documents how the sign-off flow consumes the handoff package. The grader runs the real
# flow itself (it does NOT execute this file as the scoring step); it is here so you can see exactly
# what the flow does and which artifacts it reads. Do not edit it -- repair the DATA artifacts
# (flow_config.json, constraints.sdc, provenance.json) instead.
#
# Flow (conceptually):
#   1. read flow_config.json   -> ${flow_config(netlist)} is the netlist the flow consumes
#   2. read_db   tiny.db       ; set link_path "* tiny.db"
#   3. read_verilog ${flow_config(netlist)} ; link_design ${flow_config(top_module)}
#   4. read_sdc  constraints.sdc
#   5. report setup timing (max delay) and sign off if the worst slack is non-negative AND at least
#      one intended sequential path is actually constrained (a clean report on ZERO constrained
#      paths is a false pass)
#   6. the current sign-off evidence is recorded in provenance.json (revision + content hash +
#      clock + corner) and must match handoff_manifest.json
#
# Authority: handoff_manifest.json (which netlist/clock/scenario/corner the flow SHOULD consume).
# The flow is correct only when the consumed netlist, the bound clock, and the recorded provenance
# all agree with that authority.
