// Behavioral spec for rf_front. PrimeTime times the synthesized datapath in
// design_netlist.v; THIS file shows how each register is updated. Which transfers are
// quasi-static (safe to exclude) vs functional (must meet timing) is NOT stated --
// infer it from the write-enable conditions below.
module rf_front_spec (clk, rst, gain_in, band_out, samp_out);
  input clk;
  input rst;
  input gain_in;
  output band_out;
  output samp_out;

  // boot controller: cfg_we is high only in the first cycle after reset
  reg boot_done;
  always @(posedge clk or posedge rst)
    if (rst) boot_done <= 1'b0; else boot_done <= 1'b1;
  wire cfg_we = ~boot_done;

  // gain_reg / band_reg: written ONLY at boot (cfg_we) -> quasi-static once configured,
  //   so the gain_reg -> band_reg path never toggles in operation
  reg gain_reg, band_reg;
  always @(posedge clk) if (cfg_we) gain_reg <= gain_in;
  always @(posedge clk) if (cfg_we) band_reg  <= gain_reg;
  assign band_out = band_reg;

  // samp_reg: recomputed from gain_reg on EVERY clock during operation,
  //   so the gain_reg -> samp_reg path is a real functional path that must meet timing
  reg samp_reg;
  always @(posedge clk) samp_reg <= gain_reg ^ gain_in;
  assign samp_out = samp_reg;
endmodule
