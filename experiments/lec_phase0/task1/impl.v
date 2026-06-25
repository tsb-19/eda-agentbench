module top(input a, b, c, d, output z1, z2, z3);
  wire n_p, n_q, n_r, t2;
  assign n_p = (a & ~b) | (~a & b);
  assign n_q = ~(~c | ~d);
  assign n_r = n_p & n_q;
  assign z1 = n_r & a;
  assign z2 = n_r | d;
  assign t2 = n_p & c;
  assign z3 = t2;
endmodule
