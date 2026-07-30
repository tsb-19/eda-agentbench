# Public feedback (p14 workflow handoff). Verdict-first; FEEDBACK not the grade. Reports whether
# flow_config consumes the authority netlist + the SDC constrains the design, stage-1 evidence
# FRESH/STALE/MISSING, and (steps=2) stage-2 summary freshness. Never reveals expected hashes/nonce/
# digest. Reads only agent-visible files.

proc jstr {text key} {
    if {[regexp "\"$key\"\s*:\s*\"(\[^\"\]*)\"" $text -> v]} { return $v }
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
    } else { set ev_state "STALE" }
}
set s2_state "NA"
# stage-2 freshness: present and bound to the CURRENT stage-1 digest?
set s2_state "MISSING"
if {[file exists stage2_summary.json] && [file exists evidence_manifest.json]} {
    set fh [open stage2_summary.json r]; set s2t [read $fh]; close $fh
    set fh [open evidence_manifest.json r]; set s1t [read $fh]; close $fh
    set up ""; set s1dig ""
    regexp {"upstream_evidence_digest"\s*:\s*"([^"]*)"} $s2t -> up
    regexp {"report_digest"\s*:\s*"([^"]*)"} $s1t -> s1dig
    if {$up ne "" && $up eq $s1dig} { set s2_state "FRESH" } else { set s2_state "STALE" }
}

set net_match [expr {$consumed ne "" && $consumed eq $want_net}]
set npaths 0; set pt_status "NO_RUN"; set consumed_clk ""
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
            if {$ws >= -0.001} { set pt_status "OK" } else { set pt_status "VIOLATION" }
        }
    }
} else { set pt_status "NO_NETLIST" }

if {$net_match && $npaths > 0 && $pt_status eq "OK" && $ev_state eq "FRESH" && $s2_state eq "FRESH"} {
    puts "WORKFLOW_PUBLIC: OK consumed=$consumed/$consumed_clk manifest=$want_net/$want_clk constrained_paths=$npaths signoff=$pt_status evidence=$ev_state stage2=$s2_state"
} else {
    puts "WORKFLOW_PUBLIC: MISMATCH consumed=$consumed/$consumed_clk manifest=$want_net/$want_clk constrained_paths=$npaths signoff=$pt_status evidence=$ev_state stage2=$s2_state"
    if {!$net_match} {
        puts "PUBLIC_HINT: flow_config.json consumes a netlist the authority does not name (consumed=$consumed vs manifest=$want_net) -- check handoff_manifest.json / spec.md"
    }
    if {$npaths == 0} {
        puts "PUBLIC_HINT: zero constrained paths -- check constraints.sdc binds the consumed netlist's real clock PORT (authority clock=$want_clk)"
    }
    if {$ev_state ne "FRESH"} {
        puts "PUBLIC_HINT: stage-1 evidence is $ev_state -- after repairing inputs run 'bash run_evidence_stage1.sh' to regenerate timing_report.rpt + evidence_manifest.json"
    }
    if {$s2_state ne "FRESH"} {
        puts "PUBLIC_HINT: stage-2 summary is $s2_state -- after stage 1 is FRESH, run 'bash run_evidence_stage2.sh' so stage2_summary.json binds the current stage-1 digest"
    }
}
puts "=== CONSUMED FLOW ==="
puts "consumed=$consumed consumed_clock=$consumed_clk manifest=$want_net/$want_clk evidence=$ev_state"
if {$npaths > 0} { report_timing -delay_type max -nworst 1 }
puts "PUBLIC_DONE"
exit
