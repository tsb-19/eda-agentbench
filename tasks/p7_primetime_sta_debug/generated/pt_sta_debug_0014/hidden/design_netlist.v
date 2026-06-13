// Gate-level netlist for adder_pipe — used by PrimeTime STA
module adder_pipe (clk, rst_n, a, b, sum);
  input clk;
  input rst_n;
  input [15:0] a;
  input [15:0] b;
  output [16:0] sum;
  DFFX1 sum_reg_0 (.D(sum_next_0), .CK(clk), .Q(sum[0]));
  DFFX1 sum_reg_1 (.D(sum_next_1), .CK(clk), .Q(sum[1]));
  DFFX1 sum_reg_2 (.D(sum_next_2), .CK(clk), .Q(sum[2]));
  DFFX1 sum_reg_3 (.D(sum_next_3), .CK(clk), .Q(sum[3]));
  DFFX1 sum_reg_4 (.D(sum_next_4), .CK(clk), .Q(sum[4]));
  DFFX1 sum_reg_5 (.D(sum_next_5), .CK(clk), .Q(sum[5]));
  DFFX1 sum_reg_6 (.D(sum_next_6), .CK(clk), .Q(sum[6]));
  DFFX1 sum_reg_7 (.D(sum_next_7), .CK(clk), .Q(sum[7]));
  DFFX1 sum_reg_8 (.D(sum_next_8), .CK(clk), .Q(sum[8]));
  DFFX1 sum_reg_9 (.D(sum_next_9), .CK(clk), .Q(sum[9]));
  DFFX1 sum_reg_10 (.D(sum_next_10), .CK(clk), .Q(sum[10]));
  DFFX1 sum_reg_11 (.D(sum_next_11), .CK(clk), .Q(sum[11]));
  DFFX1 sum_reg_12 (.D(sum_next_12), .CK(clk), .Q(sum[12]));
  DFFX1 sum_reg_13 (.D(sum_next_13), .CK(clk), .Q(sum[13]));
  DFFX1 sum_reg_14 (.D(sum_next_14), .CK(clk), .Q(sum[14]));
  DFFX1 sum_reg_15 (.D(sum_next_15), .CK(clk), .Q(sum[15]));
  DFFX1 sum_reg_16 (.D(sum_next_16), .CK(clk), .Q(sum[16]));
endmodule
