# PrimeTime STA Debug — hidden apply phase (isolated from grading)
read_verilog design_netlist.v
link_design fsm_ctrl

# Apply agent constraints. read_sdc sandboxes Tcl `proc`/`exit`; write_sdc then
# launders the genuine applied constraints to a fresh file (overwriting anything the
# agent's SDC wrote). Grading reads ONLY that file, in the .sh wrapper.
read_sdc constraints.sdc
write_sdc -nosplit applied_hidden.sdc
exit 0
