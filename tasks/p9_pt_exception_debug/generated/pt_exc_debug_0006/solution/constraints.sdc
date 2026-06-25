create_clock -name clk -period 0.5 [get_ports clk]
set_input_delay  0.05 -clock clk [get_ports {desc_in}]
set_output_delay 0.05 -clock clk [get_ports {mode2_out addr_out}]
set_false_path -from [get_pins desc_reg/CK] -to [get_pins mode2_reg/D]
