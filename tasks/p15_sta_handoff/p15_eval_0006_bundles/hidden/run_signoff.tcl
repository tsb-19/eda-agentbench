# Hidden signoff on the laundered (trusted) SDC. Zero constrained paths => FAIL.
read_db tiny.db
set link_path "* tiny.db"
read_verilog design.v
link_design p15_sta_top
read_sdc applied_hidden.sdc
set wp [get_timing_paths -delay_type max -nworst 1]
if {[sizeof_collection $wp] == 0} {
    puts "SIGNOFF_FAIL worst_slack=NONE no_paths"
} else {
    set s [get_attribute [index_collection $wp 0] slack]
    if {$s >= -0.001} { puts "SIGNOFF_OK worst_slack=$s" } else { puts "SIGNOFF_FAIL worst_slack=$s" }
}
exit
