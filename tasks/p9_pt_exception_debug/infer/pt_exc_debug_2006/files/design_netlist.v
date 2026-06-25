// Gate-level netlist for dma_eng — timed by PrimeTime against tiny.db
module dma_eng (clk, desc_in, mode2_out, addr_out);
  input clk;
  input desc_in;
  output mode2_out;
  output addr_out;
  wire desc_reg_q;
  wire mode2_reg_d;
  wire addr_reg_d;
  wire desc_reg_qs_n0;
  wire desc_reg_qs_n1;
  wire desc_reg_qs_n2;
  wire desc_reg_qs_n3;
  wire desc_reg_qs_n4;
  wire desc_reg_dp_n0;
  wire desc_reg_dp_n1;
  DFFX1 desc_reg (.D(desc_in), .CK(clk), .Q(desc_reg_q));
  DFFX1 mode2_reg (.D(mode2_reg_d), .CK(clk), .Q(mode2_out));
  DFFX1 addr_reg (.D(addr_reg_d), .CK(clk), .Q(addr_out));
  BUFX1 desc_reg_qs_b0 (.A(desc_reg_q), .Y(desc_reg_qs_n0));
  BUFX1 desc_reg_qs_b1 (.A(desc_reg_qs_n0), .Y(desc_reg_qs_n1));
  BUFX1 desc_reg_qs_b2 (.A(desc_reg_qs_n1), .Y(desc_reg_qs_n2));
  BUFX1 desc_reg_qs_b3 (.A(desc_reg_qs_n2), .Y(desc_reg_qs_n3));
  BUFX1 desc_reg_qs_b4 (.A(desc_reg_qs_n3), .Y(desc_reg_qs_n4));
  BUFX1 desc_reg_qs_b5 (.A(desc_reg_qs_n4), .Y(mode2_reg_d));
  BUFX1 desc_reg_dp_b0 (.A(desc_reg_q), .Y(desc_reg_dp_n0));
  BUFX1 desc_reg_dp_b1 (.A(desc_reg_dp_n0), .Y(desc_reg_dp_n1));
  BUFX1 desc_reg_dp_b2 (.A(desc_reg_dp_n1), .Y(addr_reg_d));
endmodule
