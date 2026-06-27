# Hidden sign-off phase — FRESH session, signs off the MANIFEST-SELECTED netlist.
# run_hidden.sh writes the manifest-parsed selection into selected.tcl (a workspace file the
# tool forwarder mirrors to the remote host — env vars do NOT survive the remote hop). This
# script sources it for sel/top/sdc, then emits ^SIGNOFF_OK / ^SIGNOFF_FAIL from the global
# worst setup slack of the SELECTED design.
if {[file exists selected.tcl]} { source selected.tcl } else {
    set sel ""; set top "acc_stage"; set sdc "constraints.sdc"
}
if {![info exists sel] || $sel eq "" || ![file exists $sel]} {
    puts "SIGNOFF_FAIL worst_slack=NONE no_netlist"
    exit
}
read_db tiny.db
set link_path "* tiny.db"
read_verilog $sel
link_design $top
read_sdc $sdc

set wp [get_timing_paths -delay_type max -nworst 1]
if {[sizeof_collection $wp] == 0} {
    puts "SIGNOFF_FAIL worst_slack=NONE no_paths"
} else {
    set s [get_attribute [index_collection $wp 0] slack]
    if {$s >= -0.001} {
        puts "SIGNOFF_OK worst_slack=$s"
    } else {
        puts "SIGNOFF_FAIL worst_slack=$s"
    }
}
exit
