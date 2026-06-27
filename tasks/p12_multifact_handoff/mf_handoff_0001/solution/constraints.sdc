# Timing constraints for the acc_stage handoff (functional scenario, typ corner).
# Restored to the CURRENT clock: binds clk_main (the v2 clock port), so the v2 sequential paths
# are actually constrained and PrimeTime signs off a meaningful timing run. The enable input `en`
# is part of the v2 interface and carries an input delay alongside `din`.
create_clock -name clk_main -period 3.0 [get_ports clk_main]
set_clock_uncertainty 0.15 [get_clocks clk_main]
set_input_delay  1.4 -clock clk_main [get_ports {din en}]
set_output_delay 1.1 -clock clk_main [get_ports dout]
