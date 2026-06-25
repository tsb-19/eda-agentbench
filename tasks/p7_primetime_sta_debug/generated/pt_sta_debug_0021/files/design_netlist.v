// Gate-level netlist for comparator_reg — used by PrimeTime STA
module comparator_reg (clk, rst_n, a, b, gt, eq);
  input clk;
  input rst_n;
  input [7:0] a;
  input [7:0] b;
  output gt;
  output eq;
  DFFX1 gt_reg (.D(gt_next), .CK(clk), .Q(gt));
  DFFX1 eq_reg (.D(eq_next), .CK(clk), .Q(eq));
endmodule
