# Public feedback: agent_applied.sdc is built by run_public.sh (build_applied_sdc.py);
# show real PrimeTime timing + active exceptions. FEEDBACK, not a verdict.
read_db tiny.db
set link_path "* tiny.db"
read_verilog design.v
link_design p15_sta_top
read_sdc agent_applied.sdc
puts "=== SETUP VIOLATIONS (worst 10) ==="
report_timing -delay_type max -nworst 10 -slack_lesser_than 0.0
puts "=== TIMING EXCEPTIONS IN EFFECT ==="
report_exceptions
puts "PUBLIC_DONE"
exit
