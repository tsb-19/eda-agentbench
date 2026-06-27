# Hidden sign-off phase (Variant C) — FRESH session, reads ONLY the laundered (trusted) SDC.
# Emits ^SIGNOFF_OK / ^SIGNOFF_FAIL from the global worst setup slack. A stale/wrong clock name
# yields ZERO constrained paths -> SIGNOFF_FAIL (no_paths): an empty timing graph is NOT a valid
# sign-off, so the false-clean cannot earn the signoff component.
read_db tiny.db
set link_path "* tiny.db"
read_verilog design_netlist.v
link_design acc_stage
read_sdc applied_hidden.sdc

set wp [get_timing_paths -delay_type max -nworst 1]
if {[sizeof_collection $wp] == 0} {
    puts "SIGNOFF_FAIL worst_slack=NONE no_paths"
} else {
    set s [get_attribute [index_collection $wp 0] slack]
    if {$s >= -0.001} {
        puts "SIGNOFF_OK worst_slack=$s"
    } else {
        puts "SIGNOFF_FAIL worst_slack=$s"
    }
}
exit
