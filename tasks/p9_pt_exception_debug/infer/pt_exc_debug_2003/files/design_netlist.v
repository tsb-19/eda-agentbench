// Gate-level netlist for fir_tap — timed by PrimeTime against tiny.db
module fir_tap (clk, coef_in, x_in, y_out, y_sum);
  input clk;
  input coef_in;
  input x_in;
  output y_out;
  output y_sum;
  wire coef_reg_q;
  wire mult_reg_d;
  wire din_reg_q;
  wire sum_reg_d;
  wire coef_reg_mc_n0;
  wire coef_reg_mc_n1;
  wire coef_reg_mc_n2;
  wire coef_reg_mc_n3;
  wire coef_reg_mc_n4;
  DFFX1 coef_reg (.D(coef_in), .CK(clk), .Q(coef_reg_q));
  DFFX1 mult_reg (.D(mult_reg_d), .CK(clk), .Q(y_out));
  DFFX1 din_reg (.D(x_in), .CK(clk), .Q(din_reg_q));
  DFFX1 sum_reg (.D(sum_reg_d), .CK(clk), .Q(y_sum));
  BUFX1 coef_reg_mc_b0 (.A(coef_reg_q), .Y(coef_reg_mc_n0));
  BUFX1 coef_reg_mc_b1 (.A(coef_reg_mc_n0), .Y(coef_reg_mc_n1));
  BUFX1 coef_reg_mc_b2 (.A(coef_reg_mc_n1), .Y(coef_reg_mc_n2));
  BUFX1 coef_reg_mc_b3 (.A(coef_reg_mc_n2), .Y(coef_reg_mc_n3));
  BUFX1 coef_reg_mc_b4 (.A(coef_reg_mc_n3), .Y(coef_reg_mc_n4));
  BUFX1 coef_reg_mc_b5 (.A(coef_reg_mc_n4), .Y(mult_reg_d));
  BUFX1 din_reg_s_b0 (.A(din_reg_q), .Y(sum_reg_d));
endmodule
