// Gate-level netlist for toggle_ff — used by PrimeTime STA
module toggle_ff (clk, rst_n, en, tff);
  input clk;
  input rst_n;
  input en;
  output tff;
  DFFX1 tff_reg (.D(tff_next), .CK(clk), .Q(tff));
endmodule
