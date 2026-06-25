read_verilog -r golden.v
set_top r:/WORK/top
read_verilog -i impl.v
set_top i:/WORK/top
match
verify
exit
