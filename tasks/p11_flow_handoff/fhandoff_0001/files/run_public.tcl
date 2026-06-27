# Public handoff feedback: resolve the manifest, sign off the SELECTED netlist, report a verdict.
# This is FEEDBACK, not the grade. It shows which netlist the handoff manifest currently selects,
# whether that selection looks consistent (provenance hash + the interface the constraints expect),
# and whether PrimeTime setup sign-off passes. A clean PrimeTime report is necessary but NOT
# sufficient: it does NOT tell you whether the manifest selected the CURRENT design (that is the
# handoff contract, checked at grading). It reads ONLY agent-visible files; no hidden grading files.

# --- read the manifest (the handoff contract the downstream flow obeys) ---
set fh [open handoff_manifest.json r]; set mtext [read $fh]; close $fh
proc jget {txt key} {
    if {[regexp "\"$key\"\\s*:\\s*\"(\[^\"\]*)\"" $txt -> v]} { return $v }
    return ""
}
set sel_netlist [jget $mtext netlist]
set decl_hash   [jget $mtext netlist_provenance_sha256]
set top         [jget $mtext top_module]
set sdc         [jget $mtext constraints]
if {$sel_netlist eq ""} { set sel_netlist "MISSING" }
if {$top eq ""} { set top "acc_stage" }
if {$sdc eq ""} { set sdc "constraints.sdc" }

# --- provenance check: does the selected file's content hash match the manifest's claim? ---
set prov "UNKNOWN"
if {[file exists $sel_netlist]} {
    if {![catch {exec sha256sum $sel_netlist} shout]} {
        set actual [lindex [split $shout] 0]
        if {$decl_hash ne "" && $actual eq $decl_hash} { set prov "MATCH" } else { set prov "MISMATCH" }
    }
} else {
    set prov "NOFILE"
}

# --- run PrimeTime on the SELECTED netlist ---
set slack_str "NONE"
set pt_status "NO_PATHS"
if {[file exists $sel_netlist]} {
    read_db tiny.db
    set link_path "* tiny.db"
    read_verilog $sel_netlist
    link_design $top
    read_sdc $sdc
    set wp [get_timing_paths -delay_type max -nworst 1]
    if {[sizeof_collection $wp] == 0} {
        set pt_status "NO_PATHS"
    } else {
        set s [get_attribute [index_collection $wp 0] slack]
        set slack_str $s
        if {$s >= -0.001} { set pt_status "OK" } else { set pt_status "VIOLATION" }
    }
}

# --- VERDICT FIRST (concise) so run_public.sh can surface it at the very top of stdout ---
if {$prov eq "MATCH" && ($pt_status eq "OK")} {
    puts "HANDOFF_PUBLIC: OK selected=$sel_netlist provenance=$prov signoff=$pt_status worst_slack=$slack_str"
} else {
    puts "HANDOFF_PUBLIC: MISMATCH selected=$sel_netlist provenance=$prov signoff=$pt_status worst_slack=$slack_str"
    puts "PUBLIC_HINT: confirm handoff_manifest.json selects the CURRENT revision (interface per spec.md) with a matching provenance hash"
}
puts "=== SELECTED NETLIST SIGN-OFF ==="
if {[file exists $sel_netlist]} { report_timing -delay_type max -nworst 1 }
puts "PUBLIC_DONE"
exit
