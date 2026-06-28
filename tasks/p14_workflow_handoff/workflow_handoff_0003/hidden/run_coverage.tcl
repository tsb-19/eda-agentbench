# Hidden coverage phase (p13). Records TRUSTED PrimeTime facts from the consumed netlist + the
# LAUNDERED SDC: is the intended (authority) clock bound, and how many paths are constrained.
if {[file exists selected_signoff.tcl]} { source selected_signoff.tcl } else {
    set sel ""; set top "acc_stage"; set want_clk "clk_main"
}
set present 0; set npaths 0
if {[info exists sel] && $sel ne "" && [file exists $sel] && [file exists applied_hidden.sdc]} {
    if {![catch {
        read_db tiny.db; set link_path "* tiny.db"
        read_verilog $sel; link_design $top; read_sdc applied_hidden.sdc; update_timing
    }]} {
        if {[sizeof_collection [get_clocks -quiet $want_clk]] > 0} { set present 1 }
        set npaths [sizeof_collection [get_timing_paths -delay_type max -nworst 1]]
    }
}
set fh [open coverage.txt w]
puts $fh "intended_clock_present $present"
puts $fh "constrained_paths $npaths"
close $fh
exit
