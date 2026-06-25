# Timing constraints for acc_stage
# Must encode the interface budget from spec.md (I/O delays are budget sums, not literals).
create_clock -name clk -period 4.0 [get_ports clk]
set_clock_uncertainty 0.05 [get_clocks clk]
set_input_delay  2.13 -clock clk [get_ports {din en}]
set_output_delay 0.8 -clock clk [get_ports dout]
