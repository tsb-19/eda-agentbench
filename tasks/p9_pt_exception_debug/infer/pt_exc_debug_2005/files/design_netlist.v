// Gate-level netlist for spi_core — timed by PrimeTime against tiny.db
module spi_core (clk, mosi_in, tick_in, rx_out, flag_out);
  input clk;
  input mosi_in;
  input tick_in;
  output rx_out;
  output flag_out;
  wire shift_reg_q;
  wire cap_reg_d;
  wire cnt_reg_q;
  wire flag_reg_d;
  wire shift_reg_mc_n0;
  wire shift_reg_mc_n1;
  wire shift_reg_mc_n2;
  wire shift_reg_mc_n3;
  wire shift_reg_mc_n4;
  DFFX1 shift_reg (.D(mosi_in), .CK(clk), .Q(shift_reg_q));
  DFFX1 cap_reg (.D(cap_reg_d), .CK(clk), .Q(rx_out));
  DFFX1 cnt_reg (.D(tick_in), .CK(clk), .Q(cnt_reg_q));
  DFFX1 flag_reg (.D(flag_reg_d), .CK(clk), .Q(flag_out));
  BUFX1 shift_reg_mc_b0 (.A(shift_reg_q), .Y(shift_reg_mc_n0));
  BUFX1 shift_reg_mc_b1 (.A(shift_reg_mc_n0), .Y(shift_reg_mc_n1));
  BUFX1 shift_reg_mc_b2 (.A(shift_reg_mc_n1), .Y(shift_reg_mc_n2));
  BUFX1 shift_reg_mc_b3 (.A(shift_reg_mc_n2), .Y(shift_reg_mc_n3));
  BUFX1 shift_reg_mc_b4 (.A(shift_reg_mc_n3), .Y(shift_reg_mc_n4));
  BUFX1 shift_reg_mc_b5 (.A(shift_reg_mc_n4), .Y(cap_reg_d));
  BUFX1 cnt_reg_s_b0 (.A(cnt_reg_q), .Y(flag_reg_d));
endmodule
