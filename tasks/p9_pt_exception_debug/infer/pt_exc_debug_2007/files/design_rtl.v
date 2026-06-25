// Behavioral spec for alu_pipe. PrimeTime times the synthesized datapath in
// design_netlist.v; THIS file defines each register transfer's capture cadence.
// The timing intent (which transfers may take more than one cycle) is NOT stated
// anywhere -- infer it from the capture-enable logic below.
module alu_pipe_spec (clk, rst, op_in, flag_in, res_out, cc_out);
  input clk;
  input rst;
  input op_in;
  input flag_in;
  output res_out;
  output cc_out;

  // cadence counter: res_reg_en is asserted once every 2 clocks
  reg [1:0] phase;
  always @(posedge clk or posedge rst)
    if (rst) phase <= 2'd0;
    else     phase <= (phase == 2'd1) ? 2'd0 : phase + 2'd1;
  wire res_reg_en = (phase == 2'd0);

  // multi-cycle transfer: res_reg samples op_reg only when enabled,
  //   i.e. once per 2 clocks -> this path may take 2 cycles to settle
  reg op_reg, res_reg;
  always @(posedge clk)                    op_reg <= op_in;
  always @(posedge clk) if (res_reg_en) res_reg <= op_reg;
  assign res_out = res_reg;

  // single-cycle transfers: updated on EVERY clock -> must meet timing at 1 cycle
  reg flag_reg, cc_reg;
  always @(posedge clk) flag_reg <= flag_in;
  always @(posedge clk) cc_reg <= flag_reg;
  assign cc_out = cc_reg;
endmodule
