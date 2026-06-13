# DC Constraint Debug — hidden TCL script
# Set library
set target_library "lsi_10k.db"
set link_library "* $target_library gtech.db"

# Track errors
set error_count 0

# Read RTL
analyze -format verilog [list design.v]
elaborate counter
link

# Read constraints
if {[catch {source -echo -verbose constraints.sdc} err]} {
    echo "ERROR: Failed to read constraints: $err"
    incr error_count
}

# Check design (strict)
check_design -summary

# Check timing
check_timing

# Compile
if {[catch {compile_ultra -no_autoungroup} err]} {
    echo "ERROR: Compile failed: $err"
    incr error_count
}

# Verify timing
report_timing -max_paths 10 -delay max
report_timing -max_paths 10 -delay min

# Check for violations
set timing_violations [get_timing_paths -max_paths 1 -slack_lesser_than 0]
if {[sizeof_collection $timing_violations] > 0} {
    echo "HIDDEN_RESULT: FAIL (timing violations found)"
    exit 1
}

if {$error_count > 0} {
    echo "HIDDEN_RESULT: FAIL ($error_count errors)"
    exit 1
} else {
    echo "HIDDEN_RESULT: PASS"
    exit 0
}
