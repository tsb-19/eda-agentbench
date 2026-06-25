// Gate-level netlist for updown_counter — used by PrimeTime STA
module updown_counter (clk, rst_n, up, cnt);
  input clk;
  input rst_n;
  input up;
  output [7:0] cnt;
  DFFX1 cnt_reg_0 (.D(cnt_next_0), .CK(clk), .Q(cnt[0]));
  DFFX1 cnt_reg_1 (.D(cnt_next_1), .CK(clk), .Q(cnt[1]));
  DFFX1 cnt_reg_2 (.D(cnt_next_2), .CK(clk), .Q(cnt[2]));
  DFFX1 cnt_reg_3 (.D(cnt_next_3), .CK(clk), .Q(cnt[3]));
  DFFX1 cnt_reg_4 (.D(cnt_next_4), .CK(clk), .Q(cnt[4]));
  DFFX1 cnt_reg_5 (.D(cnt_next_5), .CK(clk), .Q(cnt[5]));
  DFFX1 cnt_reg_6 (.D(cnt_next_6), .CK(clk), .Q(cnt[6]));
  DFFX1 cnt_reg_7 (.D(cnt_next_7), .CK(clk), .Q(cnt[7]));
endmodule
