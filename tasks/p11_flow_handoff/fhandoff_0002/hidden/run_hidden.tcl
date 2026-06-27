# Hidden launder + coverage phase (Variant C). read_sdc sandboxes the agent's Tcl; write_sdc
# regenerates the canonical applied constraint state; then we record TRUSTED PrimeTime coverage
# facts (intended clock present?, number of constrained timing paths) to coverage.txt, which the
# Python grader reads as data. No agent Tcl runs in the grading decision; the verdict is computed
# from write_sdc output + these PT facts.
read_db tiny.db
set link_path "* tiny.db"
read_verilog design_netlist.v
link_design acc_stage
read_sdc constraints.sdc
write_sdc -nosplit applied_hidden.sdc

set want_clk "clk_main"
set present 0
if {[sizeof_collection [get_clocks -quiet $want_clk]] > 0} { set present 1 }
update_timing
# This PT version only returns timing paths reliably with -nworst 1; the coverage signal we
# need is binary (0 intended paths = false-clean vs >=1 = a real constrained timing graph).
set npaths [sizeof_collection [get_timing_paths -delay_type max -nworst 1]]

set fh [open coverage.txt w]
puts $fh "intended_clock_present $present"
puts $fh "constrained_paths $npaths"
close $fh
exit
