module top(input a, b, c, d, e, output o1, o2, o3);
  wire s, t, u;
  assign s = a | b;
  assign t = c & d;
  assign u = s & t;
  assign o1 = u ^ e;
  assign o2 = u | a;
  assign o3 = s & e;
endmodule
