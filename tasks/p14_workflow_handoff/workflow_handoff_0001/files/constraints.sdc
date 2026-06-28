# Timing constraints (STALE clk_old; restore to clk_main).
create_clock -name clk_old -period 3.0 [get_ports clk_old]
set_clock_uncertainty 0.15 [get_clocks clk_old]
set_input_delay  1.4 -clock clk_old [get_ports {din}]
set_output_delay 1.1 -clock clk_old [get_ports dout]
