// Gate-level netlist for shift_reg — used by PrimeTime STA
module shift_reg (clk, rst_n, din, dout);
  input clk;
  input rst_n;
  input din;
  output [7:0] dout;
  DFFX1 dout_reg_0 (.D(dout_next_0), .CK(clk), .Q(dout[0]));
  DFFX1 dout_reg_1 (.D(dout_next_1), .CK(clk), .Q(dout[1]));
  DFFX1 dout_reg_2 (.D(dout_next_2), .CK(clk), .Q(dout[2]));
  DFFX1 dout_reg_3 (.D(dout_next_3), .CK(clk), .Q(dout[3]));
  DFFX1 dout_reg_4 (.D(dout_next_4), .CK(clk), .Q(dout[4]));
  DFFX1 dout_reg_5 (.D(dout_next_5), .CK(clk), .Q(dout[5]));
  DFFX1 dout_reg_6 (.D(dout_next_6), .CK(clk), .Q(dout[6]));
  DFFX1 dout_reg_7 (.D(dout_next_7), .CK(clk), .Q(dout[7]));
endmodule
