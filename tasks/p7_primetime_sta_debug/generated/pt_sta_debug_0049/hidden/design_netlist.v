// Gate-level netlist for mod10_counter — used by PrimeTime STA
module mod10_counter (clk, rst_n, en, mcnt);
  input clk;
  input rst_n;
  input en;
  output [3:0] mcnt;
  DFFX1 mcnt_reg_0 (.D(mcnt_next_0), .CK(clk), .Q(mcnt[0]));
  DFFX1 mcnt_reg_1 (.D(mcnt_next_1), .CK(clk), .Q(mcnt[1]));
  DFFX1 mcnt_reg_2 (.D(mcnt_next_2), .CK(clk), .Q(mcnt[2]));
  DFFX1 mcnt_reg_3 (.D(mcnt_next_3), .CK(clk), .Q(mcnt[3]));
endmodule
