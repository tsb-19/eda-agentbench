# SDC constraints for updown_counter
set_clock_uncertainty 0.1 [get_clocks {clk}]

set_input_delay 0.5 -clock clk [get_ports {rst_n}]
set_input_delay 0.5 -clock clk [get_ports {up}]

set_output_delay 0.5 -clock clk [get_ports {cnt}]

set_max_area 0
