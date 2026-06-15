// Gate-level netlist for parity_reg — used by PrimeTime STA
module parity_reg (clk, rst_n, data, par);
  input clk;
  input rst_n;
  input [7:0] data;
  output par;
  DFFX1 par_reg (.D(par_next), .CK(clk), .Q(par));
endmodule
