# Timing constraints for acc_stage
# Must encode the interface budget from spec.md (I/O delays are budget sums, not literals).
create_clock -name clk -period 4.0 [get_ports clk]
set_clock_uncertainty 0.10 [get_clocks clk]
set_input_delay  1.8 -clock clk [get_ports din]
set_input_delay  1.8 -clock clk [get_ports en]
set_output_delay 3.2 -clock clk [get_ports dout]
