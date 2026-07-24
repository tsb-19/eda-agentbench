# Evidence sign-off TCL (shared by public run_evidence.sh and hidden regen_reference.sh via
# gen_evidence.py). Consumes the selection in selected.tcl (sel/top/sdc), signs off, writes the REAL
# report_timing body to report_body.txt via redirect (so the digest binds to pt_shell's actual path
# table, isolated from the script-echo that `pt_shell -f` interleaves on stdout), and prints EVFACT_*
# facts on ^-anchored stdout lines for gen_evidence.py.
if {[file exists selected.tcl]} { source selected.tcl } else {
    set sel ""; set top "acc_stage"; set sdc "constraints.sdc"
}
# start an empty body so a failed run yields a deterministic, empty report file
set bfh [open report_body.txt w]; close $bfh
if {![info exists sel] || $sel eq "" || ![file exists $sel]} {
    puts "EVFACT_SIGNOFF FAIL"; puts "EVFACT_PATHS 0"; puts "EVFACT_SLACK NONE"; exit
}
if {[catch {
    read_db tiny.db
    set link_path "* tiny.db"
    read_verilog $sel
    link_design $top
    read_sdc $sdc
    update_timing
} emsg]} {
    puts "EVFACT_SIGNOFF FAIL"; puts "EVFACT_PATHS 0"; puts "EVFACT_SLACK NONE"; exit
}
# This PT version returns timing paths reliably only with -nworst 1.
set wp [get_timing_paths -delay_type max -nworst 1]
set np [sizeof_collection $wp]
if {$np == 0} {
    puts "EVFACT_SIGNOFF FAIL"; puts "EVFACT_PATHS 0"; puts "EVFACT_SLACK NONE"; exit
}
# Redirect the real timing report to a file -- this is the content the digest binds to.
redirect report_body.txt { report_timing -delay_type max -nworst 1 }
set s [get_attribute [index_collection $wp 0] slack]
puts "EVFACT_PATHS 1"
puts "EVFACT_SLACK $s"
if {$s >= -0.001} { puts "EVFACT_SIGNOFF OK" } else { puts "EVFACT_SIGNOFF FAIL" }
exit
