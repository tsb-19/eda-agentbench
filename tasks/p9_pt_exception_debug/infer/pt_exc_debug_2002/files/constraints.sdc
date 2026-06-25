create_clock -name clk -period 0.8 [get_ports clk]
set_input_delay  0.05 -clock clk [get_ports {cfg_in}]
set_output_delay 0.05 -clock clk [get_ports {mode_out data_out}]
set_false_path -from [get_pins cfg_reg/CK]
