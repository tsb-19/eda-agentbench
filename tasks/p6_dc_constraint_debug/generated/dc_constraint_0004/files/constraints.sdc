# SDC constraints for counter
create_clock -name clk -period 3.0 [get_ports {clk}]
set_clock_uncertainty 0.1 [get_clocks {clk}]

set_input_delay 0.5 -clock clk [get_ports {rst_n}]

set_output_delay 0.5 -clock clk [get_ports {count}]

set_max_area 0
