# SDC constraints for shift_reg
create_clock -name clk -period 2.0 [get_ports {clk}]
set_clock_uncertainty 0.1 [get_clocks {clk}]

set_input_delay 0.5 -clock clk [get_ports {rst_n}]
set_input_delay 0.5 -clock clk [get_ports {din}]

set_output_delay 0.5 -clock clk [get_ports {dout}]

set_max_area 0
