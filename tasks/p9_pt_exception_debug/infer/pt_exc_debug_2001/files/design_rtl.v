// Behavioral spec for mac_unit. PrimeTime times the synthesized datapath in
// design_netlist.v; THIS file defines each register transfer's capture cadence.
// The timing intent (which transfers may take more than one cycle) is NOT stated
// anywhere -- infer it from the capture-enable logic below.
module mac_unit_spec (clk, rst, a_in, cmd_in, acc_out, stat_out);
  input clk;
  input rst;
  input a_in;
  input cmd_in;
  output acc_out;
  output stat_out;

  // cadence counter: acc_reg_en is asserted once every 2 clocks
  reg [1:0] phase;
  always @(posedge clk or posedge rst)
    if (rst) phase <= 2'd0;
    else     phase <= (phase == 2'd1) ? 2'd0 : phase + 2'd1;
  wire acc_reg_en = (phase == 2'd0);

  // multi-cycle transfer: acc_reg samples prod_reg only when enabled,
  //   i.e. once per 2 clocks -> this path may take 2 cycles to settle
  reg prod_reg, acc_reg;
  always @(posedge clk)                    prod_reg <= a_in;
  always @(posedge clk) if (acc_reg_en) acc_reg <= prod_reg;
  assign acc_out = acc_reg;

  // single-cycle transfers: updated on EVERY clock -> must meet timing at 1 cycle
  reg cmd_reg, stat_reg;
  always @(posedge clk) cmd_reg <= cmd_in;
  always @(posedge clk) stat_reg <= cmd_reg;
  assign stat_out = stat_reg;
endmodule
