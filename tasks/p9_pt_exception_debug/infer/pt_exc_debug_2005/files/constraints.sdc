create_clock -name clk -period 0.5 [get_ports clk]
set_input_delay  0.05 -clock clk [get_ports {mosi_in tick_in}]
set_output_delay 0.05 -clock clk [get_ports {rx_out flag_out}]
