// Gate-level netlist for decoder_reg — used by PrimeTime STA
module decoder_reg (clk, rst_n, sel, onehot);
  input clk;
  input rst_n;
  input [1:0] sel;
  output [3:0] onehot;
  DFFX1 onehot_reg_0 (.D(onehot_next_0), .CK(clk), .Q(onehot[0]));
  DFFX1 onehot_reg_1 (.D(onehot_next_1), .CK(clk), .Q(onehot[1]));
  DFFX1 onehot_reg_2 (.D(onehot_next_2), .CK(clk), .Q(onehot[2]));
  DFFX1 onehot_reg_3 (.D(onehot_next_3), .CK(clk), .Q(onehot[3]));
endmodule
