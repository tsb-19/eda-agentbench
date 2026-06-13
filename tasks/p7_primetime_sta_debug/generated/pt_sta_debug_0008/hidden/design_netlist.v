// Gate-level netlist for fsm_ctrl — used by PrimeTime STA
module fsm_ctrl (clk, rst_n, start, busy, done);
  input clk;
  input rst_n;
  input start;
  output busy;
  output done;
  DFFX1 state_reg_0 (.D(state_next_0), .CK(clk), .Q(state[0]));
  DFFX1 state_reg_1 (.D(state_next_1), .CK(clk), .Q(state[1]));
  DFFX1 busy_reg (.D(busy_next), .CK(clk), .Q(busy));
  DFFX1 done_reg (.D(done_next), .CK(clk), .Q(done));
endmodule
