// Gate-level netlist for accumulator — used by PrimeTime STA
module accumulator (clk, rst_n, en, data, acc);
  input clk;
  input rst_n;
  input en;
  input [7:0] data;
  output [15:0] acc;
  DFFX1 acc_reg_0 (.D(acc_next_0), .CK(clk), .Q(acc[0]));
  DFFX1 acc_reg_1 (.D(acc_next_1), .CK(clk), .Q(acc[1]));
  DFFX1 acc_reg_2 (.D(acc_next_2), .CK(clk), .Q(acc[2]));
  DFFX1 acc_reg_3 (.D(acc_next_3), .CK(clk), .Q(acc[3]));
  DFFX1 acc_reg_4 (.D(acc_next_4), .CK(clk), .Q(acc[4]));
  DFFX1 acc_reg_5 (.D(acc_next_5), .CK(clk), .Q(acc[5]));
  DFFX1 acc_reg_6 (.D(acc_next_6), .CK(clk), .Q(acc[6]));
  DFFX1 acc_reg_7 (.D(acc_next_7), .CK(clk), .Q(acc[7]));
  DFFX1 acc_reg_8 (.D(acc_next_8), .CK(clk), .Q(acc[8]));
  DFFX1 acc_reg_9 (.D(acc_next_9), .CK(clk), .Q(acc[9]));
  DFFX1 acc_reg_10 (.D(acc_next_10), .CK(clk), .Q(acc[10]));
  DFFX1 acc_reg_11 (.D(acc_next_11), .CK(clk), .Q(acc[11]));
  DFFX1 acc_reg_12 (.D(acc_next_12), .CK(clk), .Q(acc[12]));
  DFFX1 acc_reg_13 (.D(acc_next_13), .CK(clk), .Q(acc[13]));
  DFFX1 acc_reg_14 (.D(acc_next_14), .CK(clk), .Q(acc[14]));
  DFFX1 acc_reg_15 (.D(acc_next_15), .CK(clk), .Q(acc[15]));
endmodule
