module top(input a, b, c, d, e, f, g, h, output y1, y2);
  wire l1, l2, l3, l4, m1, m2, hi;
  assign l1 = a & b;
  assign l2 = c ^ d;
  assign l3 = e | f;
  assign l4 = g & h;
  assign m1 = l1 | l2;
  assign m2 = l3 ^ l4;
  assign hi = m1 & m2;
  assign y1 = hi ^ a;
  assign y2 = hi | h;
endmodule
