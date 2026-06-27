# Timing constraints for the acc_stage handoff (functional scenario, typ corner).
# The clock object is bound to the design's real clock PORT clk_main, so the sequential paths
# are actually constrained and PrimeTime signs off a meaningful timing run.
create_clock -name clk_main -period 3.0 [get_ports clk_main]
set_clock_uncertainty 0.15 [get_clocks clk_main]
set_input_delay  1.4 -clock clk_main [get_ports {din en}]
set_output_delay 1.1 -clock clk_main [get_ports dout]
