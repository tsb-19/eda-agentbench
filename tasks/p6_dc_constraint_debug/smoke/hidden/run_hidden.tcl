# DC Constraint Debug — hidden apply phase (isolated from grading)
set target_library "lsi_10k.db"
set link_library "* $target_library gtech.db"

# Read RTL
analyze -format verilog [list design.v]
elaborate counter
link

# Apply agent constraints. read_sdc sandboxes Tcl `proc`/`exit`; write_sdc then
# launders the genuine applied constraints to a fresh file (overwriting anything the
# agent's SDC wrote). Grading reads ONLY that file, in the .sh wrapper.
read_sdc constraints.sdc
write_sdc -nosplit applied_hidden.sdc
exit 0
