# Hidden launder phase — apply the agent's constraints, then serialise the GENUINE
# applied constraint state to applied_hidden.sdc. read_sdc sandboxes Tcl proc/exit;
# write_sdc overwrites anything the agent's SDC may have written. The verdict is
# computed afterwards in a FRESH session (run_signoff.tcl) and by grade_spec.py reading
# ONLY this laundered file, so no agent-controlled Tcl can reach grading.
read_db tiny.db
set link_path "* tiny.db"
read_verilog design_netlist.v
link_design acc_stage
read_sdc constraints.sdc
write_sdc -nosplit applied_hidden.sdc
exit
