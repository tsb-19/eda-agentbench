# Timing constraints for the acc_stage handoff (functional scenario, typ corner).
# The clock object must be bound to the design's real clock PORT. If it is bound to a stale
# clock name that no longer exists on the netlist, no clock is created and the sequential
# paths go UNCONSTRAINED -- PrimeTime then reports no violations because nothing was checked.
create_clock -name clk_old -period 3.0 [get_ports clk_old]
set_clock_uncertainty 0.15 [get_clocks clk_old]
set_input_delay  1.4 -clock clk_old [get_ports {din en}]
set_output_delay 1.1 -clock clk_old [get_ports dout]
