// Behavioral spec for vid_ctrl. PrimeTime times the synthesized datapath in
// design_netlist.v; THIS file shows how each register is updated. Which transfers are
// quasi-static (safe to exclude) vs functional (must meet timing) is NOT stated --
// infer it from the write-enable conditions below.
module vid_ctrl_spec (clk, rst, ctrl_in, opt_out, pix_out);
  input clk;
  input rst;
  input ctrl_in;
  output opt_out;
  output pix_out;

  // boot controller: cfg_we is high only in the first cycle after reset
  reg boot_done;
  always @(posedge clk or posedge rst)
    if (rst) boot_done <= 1'b0; else boot_done <= 1'b1;
  wire cfg_we = ~boot_done;

  // ctrl_reg / opt_reg: written ONLY at boot (cfg_we) -> quasi-static once configured,
  //   so the ctrl_reg -> opt_reg path never toggles in operation
  reg ctrl_reg, opt_reg;
  always @(posedge clk) if (cfg_we) ctrl_reg <= ctrl_in;
  always @(posedge clk) if (cfg_we) opt_reg  <= ctrl_reg;
  assign opt_out = opt_reg;

  // pix_reg: recomputed from ctrl_reg on EVERY clock during operation,
  //   so the ctrl_reg -> pix_reg path is a real functional path that must meet timing
  reg pix_reg;
  always @(posedge clk) pix_reg <= ctrl_reg ^ ctrl_in;
  assign pix_out = pix_reg;
endmodule
