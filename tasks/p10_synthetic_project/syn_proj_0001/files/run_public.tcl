# Public feedback: apply your constraints and show real PrimeTime setup timing.
# This is FEEDBACK, not the grade. It shows whether sign-off currently passes and the
# worst violating path. A clean report is necessary but NOT sufficient: it does NOT tell
# you whether your constraints match the spec budget (that check is part of sign-off
# review and is not exposed here). Over-constraining is rejected at sign-off.
read_db tiny.db
set link_path "* tiny.db"
read_verilog design_netlist.v
link_design acc_stage
read_sdc constraints.sdc

# Verdict FIRST (concise) so the run_public.sh wrapper can surface it at the very top of
# stdout, ahead of the PrimeTime banner and the timing detail.
set wp [get_timing_paths -delay_type max -nworst 1]
if {[sizeof_collection $wp] == 0} {
    puts "PUBLIC_SIGNOFF: NO_PATHS"
} else {
    set s [get_attribute [index_collection $wp 0] slack]
    if {$s >= -0.001} {
        puts "PUBLIC_SIGNOFF: OK worst_slack=$s"
    } else {
        puts "PUBLIC_SIGNOFF: VIOLATION worst_slack=$s"
        puts "PUBLIC_HINT: inspect constraints.sdc against spec.md timing budgets"
    }
}
puts "=== WORST SETUP PATH ==="
report_timing -delay_type max -nworst 1
puts "PUBLIC_DONE"
exit
