# Timing constraints for the acc_stage handoff (functional scenario, typ corner).
# Editable. Currently STALE: still binds the pre-rename clock clk_old (the v1 clock port).
# The defect is the clock NAME/PORT binding (and the v1-only port set), NOT the timing numbers --
# do not chase the symptom by weakening period/uncertainty or adding timing exceptions.
create_clock -name clk_old -period 3.0 [get_ports clk_old]
set_clock_uncertainty 0.15 [get_clocks clk_old]
set_input_delay  1.4 -clock clk_old [get_ports din]
set_output_delay 1.1 -clock clk_old [get_ports dout]
