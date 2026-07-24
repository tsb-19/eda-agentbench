# clk_main (already correct; unchanged).
create_clock -name clk_main -period 3.0 [get_ports clk_main]
set_clock_uncertainty 0.15 [get_clocks clk_main]
set_input_delay  1.4 -clock clk_main [get_ports {din en}]
set_output_delay 1.1 -clock clk_main [get_ports dout]
