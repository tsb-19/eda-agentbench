// Behavioral spec for dma_eng. PrimeTime times the synthesized datapath in
// design_netlist.v; THIS file shows how each register is updated. Which transfers are
// quasi-static (safe to exclude) vs functional (must meet timing) is NOT stated --
// infer it from the write-enable conditions below.
module dma_eng_spec (clk, rst, desc_in, mode2_out, addr_out);
  input clk;
  input rst;
  input desc_in;
  output mode2_out;
  output addr_out;

  // boot controller: cfg_we is high only in the first cycle after reset
  reg boot_done;
  always @(posedge clk or posedge rst)
    if (rst) boot_done <= 1'b0; else boot_done <= 1'b1;
  wire cfg_we = ~boot_done;

  // desc_reg / mode2_reg: written ONLY at boot (cfg_we) -> quasi-static once configured,
  //   so the desc_reg -> mode2_reg path never toggles in operation
  reg desc_reg, mode2_reg;
  always @(posedge clk) if (cfg_we) desc_reg <= desc_in;
  always @(posedge clk) if (cfg_we) mode2_reg  <= desc_reg;
  assign mode2_out = mode2_reg;

  // addr_reg: recomputed from desc_reg on EVERY clock during operation,
  //   so the desc_reg -> addr_reg path is a real functional path that must meet timing
  reg addr_reg;
  always @(posedge clk) addr_reg <= desc_reg ^ desc_in;
  assign addr_out = addr_reg;
endmodule
