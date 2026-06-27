# Public handoff feedback (Variant C): apply the constraints, then report whether the intended
# clock is actually bound and the sequential paths are constrained. This is FEEDBACK, not the
# grade. A clean PrimeTime report is necessary but NOT sufficient: if the clock name is stale,
# PT reports "clean" while constraining ZERO intended paths. Reads only agent-visible files
# (design_netlist.v, tiny.db, constraints.sdc, handoff_manifest.json); no hidden grading files.
read_db tiny.db
set link_path "* tiny.db"
read_verilog design_netlist.v
link_design acc_stage
read_sdc constraints.sdc

# intended clock from the manifest (read as text; no hidden file)
set fh [open handoff_manifest.json r]; set mtext [read $fh]; close $fh
set want_clk "clk_main"
if {[regexp {"clock"\s*:\s*"([^"]*)"} $mtext -> c]} { set want_clk $c }

# does the intended clock object exist, and how many endpoints does it constrain?
set clks [get_clocks -quiet *]
set nclk [sizeof_collection $clks]
set want_present 0
if {[sizeof_collection [get_clocks -quiet $want_clk]] > 0} { set want_present 1 }
update_timing
# This PT version returns timing paths reliably only with -nworst 1; the feedback signal we
# surface is binary (0 intended paths constrained = false-clean vs >=1 = a real timing graph).
set npaths [sizeof_collection [get_timing_paths -delay_type max -nworst 1]]

set slack_str "NONE"; set pt_status "NO_PATHS"
if {$npaths == 0} {
    set pt_status "NO_PATHS"
} else {
    set s [get_attribute [index_collection [get_timing_paths -delay_type max -nworst 1] 0] slack]
    set slack_str $s
    if {$s >= -0.001} { set pt_status "OK" } else { set pt_status "VIOLATION" }
}

# VERDICT FIRST so run_public.sh can hoist it to the top of stdout.
if {$want_present && $npaths > 0 && $pt_status eq "OK"} {
    puts "HANDOFF_PUBLIC: OK clock=$want_clk constrained_paths=$npaths signoff=$pt_status worst_slack=$slack_str"
} else {
    puts "HANDOFF_PUBLIC: MISMATCH clock=$want_clk clock_bound=$want_present constrained_paths=$npaths signoff=$pt_status"
    if {$npaths == 0} {
        puts "PUBLIC_HINT: zero intended paths are constrained -- a clean report here is meaningless; check the clock NAME bound in constraints.sdc against the design clock port (spec.md)"
    } else {
        puts "PUBLIC_HINT: confirm constraints.sdc binds the intended clock from spec.md and constrains the sequential paths"
    }
}
puts "=== CLOCKS / WORST PATH ==="
puts "clocks_defined=$nclk intended=$want_clk present=$want_present"
if {$npaths > 0} { report_timing -delay_type max -nworst 1 }
puts "PUBLIC_DONE"
exit
