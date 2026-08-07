create_clock -name clk -period 0.8 [get_ports clk]
set_input_delay  0.05 -clock clk [get_ports { cdc_in reset_in scan_in core_in }]
set_output_delay 0.05 -clock clk [get_ports { cdc_out reset_out scan_out core_out }]
