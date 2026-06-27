# Public feedback (p13 trajectory handoff). Reports: (a) whether flow_config.json consumes the
# authority netlist and the SDC binds a clock that constrains the design, (b) whether the shipped
# evidence is FRESH/STALE/MISSING relative to the CURRENT inputs (by recomputing input hashes and
# comparing to evidence_manifest.json). FEEDBACK, not the grade -- it never reveals expected
# hashes/nonce/digest. Reads only agent-visible files; no hidden grading files.

proc jstr {text key} {
    if {[regexp "\"$key\"\\s*:\\s*\"(\[^\"\]*)\"" $text -> v]} { return $v }
    return ""
}
proc sha256_file {path} {
    if {![file exists $path]} { return "" }
    if {[catch {exec sha256sum $path} out]} { return "" }
    return [lindex [split $out] 0]
}

set consumed ""; set top "acc_stage"; set sdc "constraints.sdc"
if {[file exists flow_config.json]} {
    set fh [open flow_config.json r]; set ft [read $fh]; close $fh
    set consumed [jstr $ft netlist]
    set t [jstr $ft top_module]; if {$t ne ""} { set top $t }
    set s [jstr $ft constraints]; if {$s ne ""} { set sdc $s }
}
set want_net ""; set want_clk ""
if {[file exists handoff_manifest.json]} {
    set fh [open handoff_manifest.json r]; set mt [read $fh]; close $fh
    set want_net [jstr $mt netlist]; set want_clk [jstr $mt clock]
}

# evidence freshness: do the manifest's recorded input hashes match the CURRENT inputs?
set ev_state "MISSING"
if {[file exists evidence_manifest.json] && [file exists timing_report.rpt]} {
    set fh [open evidence_manifest.json r]; set et [read $fh]; close $fh
    set rec_fc ""; set rec_sdc ""; set rec_net ""
    regexp {"flow_config.json"\s*:\s*"([^"]*)"} $et -> rec_fc
    regexp {"constraints.sdc"\s*:\s*"([^"]*)"} $et -> rec_sdc
    regexp {"consumed_netlist"\s*:\s*"([^"]*)"} $et -> rec_net
    set cur_fc [sha256_file flow_config.json]
    set cur_sdc [sha256_file $sdc]
    set cur_net [sha256_file $consumed]
    if {$rec_fc eq $cur_fc && $rec_sdc eq $cur_sdc && $rec_net eq $cur_net && $cur_fc ne ""} {
        set ev_state "FRESH"
    } else {
        set ev_state "STALE"
    }
}

set net_match [expr {$consumed ne "" && $consumed eq $want_net}]

# run a quick sign-off of the consumed package for the verdict line
set npaths 0; set pt_status "NO_RUN"; set slack_str "NONE"; set consumed_clk ""
if {$consumed ne "" && [file exists $consumed]} {
    if {[catch {
        read_db tiny.db; set link_path "* tiny.db"
        read_verilog $consumed; link_design $top; read_sdc $sdc; update_timing
    } emsg]} {
        set pt_status "LINK_OR_SDC_ERROR"
    } else {
        set clks [get_clocks -quiet *]
        if {[sizeof_collection $clks] > 0} { set consumed_clk [get_attribute [index_collection $clks 0] full_name] }
        set npaths [sizeof_collection [get_timing_paths -delay_type max -nworst 1]]
        if {$npaths == 0} { set pt_status "NO_PATHS" } else {
            set ws [get_attribute [index_collection [get_timing_paths -delay_type max -nworst 1] 0] slack]
            set slack_str $ws
            if {$ws >= -0.001} { set pt_status "OK" } else { set pt_status "VIOLATION" }
        }
    }
} else { set pt_status "NO_NETLIST" }

# VERDICT FIRST.
if {$net_match && $npaths > 0 && $pt_status eq "OK" && $ev_state eq "FRESH"} {
    puts "TRAJECTORY_PUBLIC: OK consumed=$consumed/$consumed_clk manifest=$want_net/$want_clk constrained_paths=$npaths signoff=$pt_status evidence=$ev_state"
} else {
    puts "TRAJECTORY_PUBLIC: MISMATCH consumed=$consumed/$consumed_clk manifest=$want_net/$want_clk constrained_paths=$npaths signoff=$pt_status evidence=$ev_state"
    if {!$net_match} {
        puts "PUBLIC_HINT: flow_config.json consumes a netlist the authority does not name (consumed=$consumed vs manifest=$want_net) -- check it against handoff_manifest.json / spec.md"
    }
    if {$npaths == 0} {
        puts "PUBLIC_HINT: zero constrained paths -- check constraints.sdc binds the consumed netlist's real clock PORT (authority clock=$want_clk)"
    }
    if {$ev_state ne "FRESH"} {
        puts "PUBLIC_HINT: evidence is $ev_state -- after repairing the inputs you must rerun 'bash run_evidence.sh' to regenerate timing_report.rpt + evidence_manifest.json"
    }
}
puts "=== CONSUMED FLOW ==="
puts "consumed=$consumed consumed_clock=$consumed_clk manifest=$want_net/$want_clk evidence=$ev_state"
if {$npaths > 0} { report_timing -delay_type max -nworst 1 }
puts "PUBLIC_DONE"
exit
