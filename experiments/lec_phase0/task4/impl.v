module top(input a, b, c, d, e, f, g, h, output y1, y2);
  wire n1, n2, n3, n4, n5, n6, n7;
  assign n1 = ~(~a | ~b);
  assign n2 = c & d;
  assign n3 = ~(~e & ~f);
  assign n4 = ~(~g | ~h);
  assign n5 = n1 | n2;
  assign n6 = (n3 & ~n4) | (~n3 & n4);
  assign n7 = n5 & n6;
  assign y1 = n7 ^ a;
  assign y2 = n7 | h;
endmodule
