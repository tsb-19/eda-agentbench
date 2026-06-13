// Gate-level netlist for counter — used by PrimeTime STA
module counter (clk, rst_n, en, count);
  input clk;
  input rst_n;
  input en;
  output [7:0] count;
  DFFX1 count_reg_0 (.D(count_next_0), .CK(clk), .Q(count[0]));
  DFFX1 count_reg_1 (.D(count_next_1), .CK(clk), .Q(count[1]));
  DFFX1 count_reg_2 (.D(count_next_2), .CK(clk), .Q(count[2]));
  DFFX1 count_reg_3 (.D(count_next_3), .CK(clk), .Q(count[3]));
  DFFX1 count_reg_4 (.D(count_next_4), .CK(clk), .Q(count[4]));
  DFFX1 count_reg_5 (.D(count_next_5), .CK(clk), .Q(count[5]));
  DFFX1 count_reg_6 (.D(count_next_6), .CK(clk), .Q(count[6]));
  DFFX1 count_reg_7 (.D(count_next_7), .CK(clk), .Q(count[7]));
endmodule
