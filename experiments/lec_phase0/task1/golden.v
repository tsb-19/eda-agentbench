module top(input a, b, c, d, output z1, z2, z3);
  wire p, q, r;
  assign p = a ^ b;
  assign q = c & d;
  assign r = p | q;
  assign z1 = r & a;
  assign z2 = r | d;
  assign z3 = p & c;
endmodule
