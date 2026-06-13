// Gate-level netlist for mux_reg — used by PrimeTime STA
module mux_reg (clk, rst_n, sel, d0, d1, d2, d3, q);
  input clk;
  input rst_n;
  input [1:0] sel;
  input [7:0] d0;
  input [7:0] d1;
  input [7:0] d2;
  input [7:0] d3;
  output [7:0] q;
  DFFX1 q_reg_0 (.D(q_next_0), .CK(clk), .Q(q[0]));
  DFFX1 q_reg_1 (.D(q_next_1), .CK(clk), .Q(q[1]));
  DFFX1 q_reg_2 (.D(q_next_2), .CK(clk), .Q(q[2]));
  DFFX1 q_reg_3 (.D(q_next_3), .CK(clk), .Q(q[3]));
  DFFX1 q_reg_4 (.D(q_next_4), .CK(clk), .Q(q[4]));
  DFFX1 q_reg_5 (.D(q_next_5), .CK(clk), .Q(q[5]));
  DFFX1 q_reg_6 (.D(q_next_6), .CK(clk), .Q(q[6]));
  DFFX1 q_reg_7 (.D(q_next_7), .CK(clk), .Q(q[7]));
endmodule
