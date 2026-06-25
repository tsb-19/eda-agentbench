// Behavioral spec for fir_tap. PrimeTime times the synthesized datapath in
// design_netlist.v; THIS file defines each register transfer's capture cadence.
// The timing intent (which transfers may take more than one cycle) is NOT stated
// anywhere -- infer it from the capture-enable logic below.
module fir_tap_spec (clk, rst, coef_in, x_in, y_out, y_sum);
  input clk;
  input rst;
  input coef_in;
  input x_in;
  output y_out;
  output y_sum;

  // cadence counter: mult_reg_en is asserted once every 2 clocks
  reg [1:0] phase;
  always @(posedge clk or posedge rst)
    if (rst) phase <= 2'd0;
    else     phase <= (phase == 2'd1) ? 2'd0 : phase + 2'd1;
  wire mult_reg_en = (phase == 2'd0);

  // multi-cycle transfer: mult_reg samples coef_reg only when enabled,
  //   i.e. once per 2 clocks -> this path may take 2 cycles to settle
  reg coef_reg, mult_reg;
  always @(posedge clk)                    coef_reg <= coef_in;
  always @(posedge clk) if (mult_reg_en) mult_reg <= coef_reg;
  assign y_out = mult_reg;

  // single-cycle transfers: updated on EVERY clock -> must meet timing at 1 cycle
  reg din_reg, sum_reg;
  always @(posedge clk) din_reg <= x_in;
  always @(posedge clk) sum_reg <= din_reg;
  assign y_sum = sum_reg;
endmodule
