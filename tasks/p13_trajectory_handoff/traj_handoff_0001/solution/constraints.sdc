# Timing constraints for the acc_stage handoff (functional scenario, typ corner).
# Restored to the current clock clk_main (the v2 clock port); en is part of the v2 interface.
create_clock -name clk_main -period 3.0 [get_ports clk_main]
set_clock_uncertainty 0.15 [get_clocks clk_main]
set_input_delay  1.4 -clock clk_main [get_ports {din en}]
set_output_delay 1.1 -clock clk_main [get_ports dout]
