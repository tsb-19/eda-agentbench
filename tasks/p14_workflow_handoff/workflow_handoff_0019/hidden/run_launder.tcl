# Hidden launder phase (p13). read_sdc sandboxes the agent's constraints.sdc (which is Tcl); write_sdc
# regenerates a canonical applied SDC so the trusted reference report runs on clean constraints, not
# on the agent's raw (possibly injected) Tcl. selected_launder.tcl supplies sel/top (consumed netlist
# from the SUBMITTED flow_config.json). If the agent SDC binds a clock whose port is absent on the
# consumed netlist, read_sdc is caught and write_sdc still emits the (clock-less) canonical state ->
# the reference report then constrains zero paths (false-clean detected). Emits nothing trusted; its
# stdout is [apply]-prefixed by run_hidden.sh.
if {[file exists selected_launder.tcl]} { source selected_launder.tcl } else {
    set sel ""; set top "acc_stage"; set sdc "constraints.sdc"
}
set afh [open applied_hidden.sdc w]; close $afh
if {![info exists sel] || $sel eq "" || ![file exists $sel]} { exit }
if {[catch {
    read_db tiny.db
    set link_path "* tiny.db"
    read_verilog $sel
    link_design $top
} emsg]} { exit }
catch {read_sdc $sdc}
write_sdc -nosplit applied_hidden.sdc
exit
