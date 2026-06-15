# SDC constraints for decoder_reg
set_clock_uncertainty 0.1 [get_clocks {clk}]

set_input_delay 0.5 -clock clk [get_ports {rst_n}]
set_input_delay 0.5 -clock clk [get_ports {sel}]

set_output_delay 0.5 -clock clk [get_ports {onehot}]
