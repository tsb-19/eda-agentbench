# Hidden launder: read the agent-applied SDC, serialize the resolved constraint state.
set afh [open applied_hidden.sdc w]; close $afh
read_db tiny.db
set link_path "* tiny.db"
read_verilog design.v
link_design p15_sta_top
catch { read_sdc agent_applied.sdc }
write_sdc -nosplit applied_hidden.sdc
exit
