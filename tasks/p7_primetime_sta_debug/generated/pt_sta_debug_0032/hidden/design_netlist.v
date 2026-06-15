// Gate-level netlist for alu_reg — used by PrimeTime STA
module alu_reg (clk, rst_n, op, a, b, result);
  input clk;
  input rst_n;
  input [1:0] op;
  input [7:0] a;
  input [7:0] b;
  output [7:0] result;
  DFFX1 result_reg_0 (.D(result_next_0), .CK(clk), .Q(result[0]));
  DFFX1 result_reg_1 (.D(result_next_1), .CK(clk), .Q(result[1]));
  DFFX1 result_reg_2 (.D(result_next_2), .CK(clk), .Q(result[2]));
  DFFX1 result_reg_3 (.D(result_next_3), .CK(clk), .Q(result[3]));
  DFFX1 result_reg_4 (.D(result_next_4), .CK(clk), .Q(result[4]));
  DFFX1 result_reg_5 (.D(result_next_5), .CK(clk), .Q(result[5]));
  DFFX1 result_reg_6 (.D(result_next_6), .CK(clk), .Q(result[6]));
  DFFX1 result_reg_7 (.D(result_next_7), .CK(clk), .Q(result[7]));
endmodule
