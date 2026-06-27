# Public handoff feedback (p12 stale-package triangle). Models the downstream flow: it consumes
# the netlist named in flow_config.json, applies constraints.sdc, and checks whether the consumed
# design matches the manifest AUTHORITY (handoff_manifest.json) and whether a real, non-empty
# timing graph signs off. This is FEEDBACK, not the grade. A clean PrimeTime report is necessary
# but NOT sufficient: the stale v1/clk_old island signs off green on the WRONG design, and a
# clock-name/port mismatch yields ZERO constrained paths while PT still prints "clean". Reads only
# agent-visible files (flow_config.json, the netlist it names, constraints.sdc, handoff_manifest.json,
# tiny.db); no hidden grading files.

proc jstr {text key} {
    if {[regexp "\"$key\"\\s*:\\s*\"(\[^\"\]*)\"" $text -> v]} { return $v }
    return ""
}
set ferr ""

# --- what the flow ACTUALLY consumes (flow_config.json) ---
set consumed_net ""; set top "acc_stage"; set sdc "constraints.sdc"
if {[file exists flow_config.json]} {
    set fh [open flow_config.json r]; set ftext [read $fh]; close $fh
    set consumed_net [jstr $ftext netlist]
    set t [jstr $ftext top_module]; if {$t ne ""} { set top $t }
    set s [jstr $ftext constraints]; if {$s ne ""} { set sdc $s }
} else { set ferr "no_flow_config" }

# --- what the manifest AUTHORITY says it SHOULD consume ---
set want_net ""; set want_clk ""
if {[file exists handoff_manifest.json]} {
    set fh [open handoff_manifest.json r]; set mtext [read $fh]; close $fh
    set want_net [jstr $mtext netlist]
    set want_clk [jstr $mtext clock]
}

set consumed_clk ""
set npaths 0
set pt_status "NO_RUN"
set slack_str "NONE"

if {$consumed_net ne "" && [file exists $consumed_net]} {
    if {[catch {
        read_db tiny.db
        set link_path "* tiny.db"
        read_verilog $consumed_net
        link_design $top
        read_sdc $sdc
        update_timing
    } emsg]} {
        set ferr "flow_error"
        set pt_status "LINK_OR_SDC_ERROR"
    } else {
        # which clock the applied SDC actually bound
        set clks [get_clocks -quiet *]
        if {[sizeof_collection $clks] > 0} {
            set consumed_clk [get_attribute [index_collection $clks 0] full_name]
        }
        # This PT version returns timing paths reliably only with -nworst 1; the signal is binary
        # (0 constrained paths = false-clean vs >=1 = a real timing graph).
        set npaths [sizeof_collection [get_timing_paths -delay_type max -nworst 1]]
        if {$npaths == 0} {
            set pt_status "NO_PATHS"
        } else {
            set ws [get_attribute [index_collection [get_timing_paths -delay_type max -nworst 1] 0] slack]
            set slack_str $ws
            if {$ws >= -0.001} { set pt_status "OK" } else { set pt_status "VIOLATION" }
        }
    }
} else {
    set ferr "no_consumed_netlist"
    set pt_status "NO_NETLIST"
}

# consumed design matches the manifest authority?
set net_match [expr {$consumed_net ne "" && $consumed_net eq $want_net}]

# VERDICT FIRST so run_public.sh can hoist it to the top of stdout.
if {$net_match && $npaths > 0 && $pt_status eq "OK"} {
    puts "HANDOFF_PUBLIC: OK consumed=$consumed_net/$consumed_clk manifest=$want_net/$want_clk constrained_paths=$npaths signoff=$pt_status worst_slack=$slack_str"
} else {
    puts "HANDOFF_PUBLIC: MISMATCH consumed=$consumed_net/$consumed_clk manifest=$want_net/$want_clk constrained_paths=$npaths signoff=$pt_status"
    if {!$net_match} {
        puts "PUBLIC_HINT: the flow consumes a netlist the manifest authority does not name (consumed=$consumed_net vs manifest=$want_net) -- check flow_config.json against handoff_manifest.json / spec.md"
    }
    if {$npaths == 0} {
        puts "PUBLIC_HINT: zero constrained paths -- a clean report here is meaningless; check that constraints.sdc binds the consumed netlist's real clock PORT (the manifest clock is $want_clk)"
    }
}
puts "=== CONSUMED FLOW ==="
puts "consumed_netlist=$consumed_net consumed_clock=$consumed_clk manifest_netlist=$want_net manifest_clock=$want_clk ferr=$ferr"
if {$npaths > 0} { report_timing -delay_type max -nworst 1 }
puts "PUBLIC_DONE"
exit
