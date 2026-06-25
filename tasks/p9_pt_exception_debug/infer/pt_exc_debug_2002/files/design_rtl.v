// Behavioral spec for cfg_bus. PrimeTime times the synthesized datapath in
// design_netlist.v; THIS file shows how each register is updated. Which transfers are
// quasi-static (safe to exclude) vs functional (must meet timing) is NOT stated --
// infer it from the write-enable conditions below.
module cfg_bus_spec (clk, rst, cfg_in, mode_out, data_out);
  input clk;
  input rst;
  input cfg_in;
  output mode_out;
  output data_out;

  // boot controller: cfg_we is high only in the first cycle after reset
  reg boot_done;
  always @(posedge clk or posedge rst)
    if (rst) boot_done <= 1'b0; else boot_done <= 1'b1;
  wire cfg_we = ~boot_done;

  // cfg_reg / mode_reg: written ONLY at boot (cfg_we) -> quasi-static once configured,
  //   so the cfg_reg -> mode_reg path never toggles in operation
  reg cfg_reg, mode_reg;
  always @(posedge clk) if (cfg_we) cfg_reg <= cfg_in;
  always @(posedge clk) if (cfg_we) mode_reg  <= cfg_reg;
  assign mode_out = mode_reg;

  // data_reg: recomputed from cfg_reg on EVERY clock during operation,
  //   so the cfg_reg -> data_reg path is a real functional path that must meet timing
  reg data_reg;
  always @(posedge clk) data_reg <= cfg_reg ^ cfg_in;
  assign data_out = data_reg;
endmodule
