# SDC constraints for comparator_reg
create_clock -name clk -period 5.0 [get_ports {clk}
set_clock_uncertainty 0.1 [get_clocks {clk}]

set_input_delay 0.5 -clock clk [get_ports {rst_n}]
set_input_delay 0.5 -clock clk [get_ports {a}]
set_input_delay 0.5 -clock clk [get_ports {b}]

set_output_delay 0.5 -clock clk [get_ports {gt}]
set_output_delay 0.5 -clock clk [get_ports {eq}]

set_max_area 0
