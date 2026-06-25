# Hidden grade phase — fresh session, reads only the laundered (trusted) SDC.
read_db tiny.db
set link_path "* tiny.db"
read_verilog design_netlist.v
link_design spi_core
read_sdc applied_hidden.sdc

set checks { {meet shift_reg/CK cap_reg/D} {timed1 cnt_reg/CK flag_reg/D 0.3} }
set total 0
set pass 0
set detail ""
foreach c $checks {
  incr total
  set typ [lindex $c 0]
  set frm [lindex $c 1]
  set to  [lindex $c 2]
  set ps [get_timing_paths -from [get_pins $frm] -to [get_pins $to] -delay_type max]
  set n [sizeof_collection $ps]
  if {$typ eq "exclude"} {
    if {$n == 0} {
      incr pass
      append detail " EXOK:$frm->$to"
    } else {
      set slk [get_attribute [index_collection $ps 0] slack]
      append detail " NOTEXCLUDED:$to=$slk"
    }
  } elseif {$typ eq "timed1"} {
    set exp [lindex $c 3]
    if {$n == 0} {
      append detail " NOTTIMED:$frm->$to"
    } else {
      set slk [get_attribute [index_collection $ps 0] slack]
      if {[expr {abs($slk - $exp)}] <= 0.05} {
        incr pass
        append detail " T1OK:$to=$slk"
      } else {
        append detail " RELAXED:$to=$slk/exp$exp"
      }
    }
  } else {
    if {$n == 0} {
      append detail " EXCLUDED:$frm->$to"
    } else {
      set slk [get_attribute [index_collection $ps 0] slack]
      if {$slk >= 0} {
        incr pass
        append detail " OK:$to=$slk"
      } else {
        append detail " VIOL:$to=$slk"
      }
    }
  }
}
set score [expr {double($pass)/$total}]
puts "EXC_SCORE: [format %.3f $score]"
puts "EXC_DETAIL:$detail"
exit
