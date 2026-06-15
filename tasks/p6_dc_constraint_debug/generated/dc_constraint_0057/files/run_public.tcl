# DC Constraint Debug — public TCL script
# Set library
set target_library "lsi_10k.db"
set link_library "* $target_library gtech.db"

# Track errors
set error_count 0
set fail_reasons {}

# Read RTL
analyze -format verilog [list design.v]
elaborate updown_counter
link

# Read constraints and capture output for error checking
set source_log "source_output.log"
redirect -file $source_log { source -echo -verbose constraints.sdc }

# --- Constraint validation checks ---

# Check source output for DC errors
set fh [open $source_log r]
set source_content [read $fh]
close $fh

if {[regexp {Error:} $source_content]} {
    incr error_count
    lappend fail_reasons "dc_error_in_source"
}

if {[regexp {Can't find} $source_content]} {
    incr error_count
    lappend fail_reasons "port_or_clock_not_found"
}

if {[regexp -nocase {unknown command} $source_content]} {
    incr error_count
    lappend fail_reasons "unsupported_command"
}

# Check 1: Clocks must exist
set all_clks [all_clocks]
if {[sizeof_collection $all_clks] == 0} {
    incr error_count
    lappend fail_reasons "no_clocks_created"
}

# Check 2: All ports must resolve
foreach port {clk rst_n up cnt} {
    if {[catch {get_ports $port} result]} {
        incr error_count
        lappend fail_reasons "port_not_found:$port"
    }
}

# Compile
if {[catch {compile_ultra -no_autoungroup} result]} {
    incr error_count
    lappend fail_reasons "compile_failed"
}

# Report
report_timing -max_paths 5
report_area

# Emit result
if {$error_count > 0} {
    set reason_str [join $fail_reasons ","]
    echo "CONSTRAINTS_FAIL: $reason_str"
    exit 1
} else {
    echo "CONSTRAINTS_OK"
    exit 0
}
