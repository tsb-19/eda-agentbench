# SpyGlass Lint Debug — public TCL script
# Auto-generated — do not edit

# Read design and set top
read_file -type verilog design.v
set_option top sq_toggle

# Run lint goal
current_goal lint/lint_rtl
run_goal

exit
