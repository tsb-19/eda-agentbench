# DC Constraint Debug — public TCL script
# Set library
set target_library "lsi_10k.db"
set link_library "* $target_library gtech.db"

# Track errors
set error_count 0

# Read RTL
analyze -format verilog [list design.v]
elaborate fsm_ctrl
link

# Read constraints
if {[catch {source -echo -verbose constraints.sdc} err]} {
    echo "ERROR: Failed to read constraints: $err"
    incr error_count
}

# Check design
check_design -summary

# Compile
if {[catch {compile_ultra -no_autoungroup} err]} {
    echo "ERROR: Compile failed: $err"
    incr error_count
}

# Report
report_timing -max_paths 5
report_area

if {$error_count > 0} {
    echo "PUBLIC_RESULT: FAIL ($error_count errors)"
    exit 1
} else {
    echo "PUBLIC_RESULT: PASS"
    exit 0
}
