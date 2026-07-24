# Stage-2 evidence sign-off (p14). Reports the cap_reg->acc_reg register path (distinct from stage 1's
# din->cap_reg worst path) and writes the real report body to report_body2.txt via redirect, so the
# stage-2 digest binds pt_shell's actual path table. EVFACT2_* facts on ^-anchored stdout lines.
if {[file exists selected.tcl]} { source selected.tcl } else {
    set sel ""; set top "acc_stage"; set sdc "constraints.sdc"
}
set bfh [open report_body2.txt w]; close $bfh
if {![info exists sel] || $sel eq "" || ![file exists $sel]} {
    puts "EVFACT2_SIGNOFF FAIL"; puts "EVFACT2_PATHS 0"; puts "EVFACT2_SLACK NONE"; exit
}
if {[catch {
    read_db tiny.db
    set link_path "* tiny.db"
    read_verilog $sel
    link_design $top
    read_sdc $sdc
    update_timing
} emsg]} {
    puts "EVFACT2_SIGNOFF FAIL"; puts "EVFACT2_PATHS 0"; puts "EVFACT2_SLACK NONE"; exit
}
# the register-to-register arc launched by cap_reg (reliable -from on the reg cell)
set wp [get_timing_paths -delay_type max -nworst 1 -from cap_reg]
if {[sizeof_collection $wp] == 0} {
    set wp [get_timing_paths -delay_type max -nworst 1]
}
set np [sizeof_collection $wp]
if {$np == 0} {
    puts "EVFACT2_SIGNOFF FAIL"; puts "EVFACT2_PATHS 0"; puts "EVFACT2_SLACK NONE"; exit
}
redirect report_body2.txt { report_timing -delay_type max -nworst 1 -from cap_reg }
set s [get_attribute [index_collection $wp 0] slack]
puts "EVFACT2_PATHS 1"
puts "EVFACT2_SLACK $s"
if {$s >= -0.001} { puts "EVFACT2_SIGNOFF OK" } else { puts "EVFACT2_SIGNOFF FAIL" }
exit
