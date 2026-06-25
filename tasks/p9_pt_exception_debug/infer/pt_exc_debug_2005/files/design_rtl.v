// Behavioral spec for spi_core. PrimeTime times the synthesized datapath in
// design_netlist.v; THIS file defines each register transfer's capture cadence.
// The timing intent (which transfers may take more than one cycle) is NOT stated
// anywhere -- infer it from the capture-enable logic below.
module spi_core_spec (clk, rst, mosi_in, tick_in, rx_out, flag_out);
  input clk;
  input rst;
  input mosi_in;
  input tick_in;
  output rx_out;
  output flag_out;

  // cadence counter: cap_reg_en is asserted once every 2 clocks
  reg [1:0] phase;
  always @(posedge clk or posedge rst)
    if (rst) phase <= 2'd0;
    else     phase <= (phase == 2'd1) ? 2'd0 : phase + 2'd1;
  wire cap_reg_en = (phase == 2'd0);

  // multi-cycle transfer: cap_reg samples shift_reg only when enabled,
  //   i.e. once per 2 clocks -> this path may take 2 cycles to settle
  reg shift_reg, cap_reg;
  always @(posedge clk)                    shift_reg <= mosi_in;
  always @(posedge clk) if (cap_reg_en) cap_reg <= shift_reg;
  assign rx_out = cap_reg;

  // single-cycle transfers: updated on EVERY clock -> must meet timing at 1 cycle
  reg cnt_reg, flag_reg;
  always @(posedge clk) cnt_reg <= tick_in;
  always @(posedge clk) flag_reg <= cnt_reg;
  assign flag_out = flag_reg;
endmodule
