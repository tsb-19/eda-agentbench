# Public feedback: apply your constraints and show real PrimeTime setup timing.
# This is FEEDBACK, not the grade. It shows whether sign-off currently passes and the
# worst violating paths — it does NOT tell you whether your constraints match the spec
# budget (that check is part of sign-off review and is not exposed here). A clean
# report is necessary but not sufficient: over-constraining is rejected at sign-off.
read_db tiny.db
set link_path "* tiny.db"
read_verilog design_netlist.v
link_design acc_stage
read_sdc constraints.sdc

puts "=== SETUP PATHS (worst 10) ==="
report_timing -delay_type max -nworst 10

set wp [get_timing_paths -delay_type max -nworst 1]
if {[sizeof_collection $wp] == 0} {
    puts "PUBLIC_SIGNOFF: NO_PATHS"
} else {
    set s [get_attribute [index_collection $wp 0] slack]
    if {$s >= -0.001} {
        puts "PUBLIC_SIGNOFF: OK worst_slack=$s"
    } else {
        puts "PUBLIC_SIGNOFF: VIOLATION worst_slack=$s"
    }
}
puts "PUBLIC_DONE"
exit
