# Hidden fresh sign-off phase (p13). Signs off the consumed netlist from the LAUNDERED SDC ->
# ^SIGNOFF_OK / ^SIGNOFF_FAIL. Zero constrained paths => FAIL (a clean empty timing graph is not a pass).
if {[file exists selected_signoff.tcl]} { source selected_signoff.tcl } else { set sel "" }
if {![info exists sel] || $sel eq "" || ![file exists $sel] || ![file exists applied_hidden.sdc]} {
    puts "SIGNOFF_FAIL worst_slack=NONE no_inputs"; exit
}
read_db tiny.db; set link_path "* tiny.db"
read_verilog $sel; link_design $top; read_sdc applied_hidden.sdc
set wp [get_timing_paths -delay_type max -nworst 1]
if {[sizeof_collection $wp] == 0} {
    puts "SIGNOFF_FAIL worst_slack=NONE no_paths"
} else {
    set s [get_attribute [index_collection $wp 0] slack]
    if {$s >= -0.001} { puts "SIGNOFF_OK worst_slack=$s" } else { puts "SIGNOFF_FAIL worst_slack=$s" }
}
exit
