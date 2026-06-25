create_clock -name clk -period 0.8 [get_ports clk]
set_input_delay  0.05 -clock clk [get_ports {gain_in}]
set_output_delay 0.05 -clock clk [get_ports {band_out samp_out}]
set_false_path -from [get_pins gain_reg/CK]
