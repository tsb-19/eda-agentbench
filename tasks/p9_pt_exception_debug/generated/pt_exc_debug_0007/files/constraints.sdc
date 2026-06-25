create_clock -name clk -period 1.0 [get_ports clk]
set_input_delay  0.05 -clock clk [get_ports {op_in flag_in}]
set_output_delay 0.05 -clock clk [get_ports {res_out cc_out}]
