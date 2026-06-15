# SDC constraints for updown_counter
create_clock -name clk -period 5.0 [get_ports {clk}]
set_clock_uncertainty 0.1 [get_clocks {clk}]

set_input_delay 0.5 -clock clk [get_ports {nonexistent_*}]
set_input_delay 0.5 -clock clk [get_ports {up}]

set_output_delay 0.5 -clock clk [get_ports {cnt}]

set_max_area 0
