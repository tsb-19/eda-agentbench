# SDC constraints for fsm_ctrl
create_clock -name clk -period 2.0 [get_ports {clk}]
set_clock_uncertainty 0.1 [get_clocks {clk}]

set_input_delay 0.5 -clock clk [get_ports {reset_n}]
set_input_delay 0.5 -clock clk [get_ports {start}]

set_output_delay 0.5 -clock clk [get_ports {busy}]
set_output_delay 0.5 -clock clk [get_ports {done}]

set_max_area 0
