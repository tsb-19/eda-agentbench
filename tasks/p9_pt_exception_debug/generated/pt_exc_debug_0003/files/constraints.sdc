create_clock -name clk -period 0.6 [get_ports clk]
set_input_delay  0.05 -clock clk [get_ports {coef_in x_in}]
set_output_delay 0.05 -clock clk [get_ports {y_out y_sum}]
