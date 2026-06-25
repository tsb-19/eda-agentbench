create_clock -name clk -period 1.0 [get_ports clk]
set_input_delay  0.05 -clock clk [get_ports {ctrl_in}]
set_output_delay 0.05 -clock clk [get_ports {opt_out pix_out}]
set_false_path -from [get_pins ctrl_reg/CK] -to [get_pins opt_reg/D]
