# PrimeTime STA Debug — public TCL script
# Track errors
set error_count 0
set fail_reasons {}

# Read netlist and link design
read_verilog design_netlist.v
link_design parity_reg

# Read constraints and capture output for error checking
set source_log "source_output.log"
redirect -file $source_log { source -echo -verbose constraints.sdc }

# --- Constraint validation checks ---

# Check source output for PT errors
set fh [open $source_log r]
set source_content [read $fh]
close $fh

if {[regexp {Error:} $source_content]} {
    incr error_count
    lappend fail_reasons "pt_error_in_source"
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
set num_clocks [sizeof_collection $all_clks]
if {$num_clocks == 0} {
    incr error_count
    lappend fail_reasons "no_clocks_created"
} else {
    # Verify expected clock name exists
    set expected_clk "clk"
    set clk_found 0
    foreach_in_collection c $all_clks {
        if {[get_object_name $c] eq $expected_clk} {
            set clk_found 1
        }
    }
    if {$clk_found == 0} {
        incr error_count
        lappend fail_reasons "expected_clock_missing:$expected_clk"
    }
}

# Check 2: All ports must resolve
foreach port {clk rst_n data par} {
    if {[catch {get_ports $port} result]} {
        incr error_count
        lappend fail_reasons "port_not_found:$port"
    }
}

# Check 3: Report timing (must succeed — validates timing graph)
if {[catch {report_timing -max_paths 1} result]} {
    incr error_count
    lappend fail_reasons "report_timing_failed"
}

# Report
report_timing -max_paths 5
report_clocks

# Emit result
if {$error_count > 0} {
    set reason_str [join $fail_reasons ","]
    echo "TIMING_CHECK_FAIL: $reason_str"
    exit 1
} else {
    echo "TIMING_CHECK_OK"
    exit 0
}
