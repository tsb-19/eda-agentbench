// Gate-level timing model for acc_stage — timed by PrimeTime against tiny.db.
//
// Scalar-delay abstraction: BUFX1 chains stand in for the synthesized combinational
// depth of each path (each BUFX1 = 0.10 ns; DFFX1 clk->Q = 0.08, setup = 0.02). This
// is the same modelling style as the P9 track — async reset carries no setup path and
// is omitted; only the three governed timing paths are represented, with calibrated
// depth so every slack is exact:
//   input  din -> cap_reg  : depth 5  -> slack = 3.88 - input_delay  - 0.50
//   reg2reg cap_reg->acc_reg: depth 5  -> slack = 3.80 - 0.50
//   reg2out acc_reg-> dout : depth 9  -> slack = 3.82 - output_delay - 0.90   <-- drift target
//   input  en  -> en_reg   : depth 2  -> slack = 3.88 - input_delay  - 0.20
module acc_stage (clk, din, en, dout);
  input  clk;
  input  din;
  input  en;
  output dout;

  wire i0, i1, i2, i3, i4;                 // din input chain (depth 5)
  wire cap_q;
  wire r0, r1, r2, r3, r4;                 // reg->reg chain (depth 5)
  wire acc_q;
  wire o0, o1, o2, o3, o4, o5, o6, o7;     // reg->out chain (depth 9: 8 internal + port)
  wire e0, e1;                             // en input chain (depth 2)
  wire en_q;

  // din -> cap_reg/D  (input path, depth 5)
  BUFX1 ib0 (.A(din), .Y(i0));
  BUFX1 ib1 (.A(i0),  .Y(i1));
  BUFX1 ib2 (.A(i1),  .Y(i2));
  BUFX1 ib3 (.A(i2),  .Y(i3));
  BUFX1 ib4 (.A(i3),  .Y(i4));
  DFFX1 cap_reg (.D(i4), .CK(clk), .Q(cap_q));

  // cap_reg/Q -> acc_reg/D  (reg->reg, depth 5)
  BUFX1 rb0 (.A(cap_q), .Y(r0));
  BUFX1 rb1 (.A(r0),    .Y(r1));
  BUFX1 rb2 (.A(r1),    .Y(r2));
  BUFX1 rb3 (.A(r2),    .Y(r3));
  BUFX1 rb4 (.A(r3),    .Y(r4));
  DFFX1 acc_reg (.D(r4), .CK(clk), .Q(acc_q));

  // acc_reg/Q -> dout  (reg->out, depth 9 — governed by set_output_delay)
  BUFX1 ob0 (.A(acc_q), .Y(o0));
  BUFX1 ob1 (.A(o0), .Y(o1));
  BUFX1 ob2 (.A(o1), .Y(o2));
  BUFX1 ob3 (.A(o2), .Y(o3));
  BUFX1 ob4 (.A(o3), .Y(o4));
  BUFX1 ob5 (.A(o4), .Y(o5));
  BUFX1 ob6 (.A(o5), .Y(o6));
  BUFX1 ob7 (.A(o6), .Y(o7));
  BUFX1 ob8 (.A(o7), .Y(dout));

  // en -> en_reg/D  (input path, depth 2)
  BUFX1 eb0 (.A(en), .Y(e0));
  BUFX1 eb1 (.A(e0), .Y(e1));
  DFFX1 en_reg (.D(e1), .CK(clk), .Q(en_q));
endmodule
