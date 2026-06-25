# Public feedback: apply your constraints and show real PrimeTime timing.
# FEEDBACK, not a verdict — there is no answer key. A clean report is necessary
# but NOT sufficient (signoff also rejects over-constraining / over-exclusion).
read_db tiny.db
set link_path "* tiny.db"
read_verilog design_netlist.v
link_design dma_eng
read_sdc constraints.sdc
puts "=== SETUP VIOLATIONS (worst 10) ==="
report_timing -delay_type max -nworst 10 -slack_lesser_than 0.0
puts "=== TIMING EXCEPTIONS IN EFFECT ==="
report_exceptions
puts "PUBLIC_DONE"
exit
