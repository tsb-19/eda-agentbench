# Hidden launder phase — apply agent constraints, then serialize the GENUINE
# constraint state. read_sdc sandboxes Tcl proc/exit; write_sdc overwrites any file the
# agent's SDC may have written. The verdict is computed in a fresh session (run_grade.tcl)
# reading only this laundered SDC, so no agent Tcl reaches grading.
read_db tiny.db
set link_path "* tiny.db"
read_verilog design_netlist.v
link_design fir_tap
read_sdc constraints.sdc
write_sdc -nosplit applied_hidden.sdc
exit
