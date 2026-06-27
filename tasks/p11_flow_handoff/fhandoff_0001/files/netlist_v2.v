// Gate-level timing model for acc_stage — HANDOFF NETLIST VERSION v2 (current).
// Post-ECO version: adds the `en` qualifier input and its en->en_reg path. This is the
// authoritative handoff netlist the current package must sign off (see spec.md).
// Scalar-delay abstraction (BUFX1 0.10, DFFX1 clk->Q 0.08, setup 0.02), timed vs tiny.db.
// Buffer-chain depths: din->cap_reg 13, cap_reg->acc_reg 21, acc_reg->dout 10, en->en_reg 8.
module acc_stage (clk, din, en, dout);
  input  clk;
  input  din;
  input  en;
  output dout;

  wire acc_d, acc_q, cap_d, cap_q, e0, e1, e2, e3, e4, e5, e6, en_d, en_q, i0, i1, i10, i11, i2, i3, i4, i5, i6, i7, i8, i9, o0, o1, o2, o3, o4, o5, o6, o7, o8, r0, r1, r10, r11, r12, r13, r14, r15, r16, r17, r18, r19, r2, r3, r4, r5, r6, r7, r8, r9;
  BUFX1 i_b0 (.A(din), .Y(i0));
  BUFX1 i_b1 (.A(i0), .Y(i1));
  BUFX1 i_b2 (.A(i1), .Y(i2));
  BUFX1 i_b3 (.A(i2), .Y(i3));
  BUFX1 i_b4 (.A(i3), .Y(i4));
  BUFX1 i_b5 (.A(i4), .Y(i5));
  BUFX1 i_b6 (.A(i5), .Y(i6));
  BUFX1 i_b7 (.A(i6), .Y(i7));
  BUFX1 i_b8 (.A(i7), .Y(i8));
  BUFX1 i_b9 (.A(i8), .Y(i9));
  BUFX1 i_b10 (.A(i9), .Y(i10));
  BUFX1 i_b11 (.A(i10), .Y(i11));
  BUFX1 i_b12 (.A(i11), .Y(cap_d));
  DFFX1 cap_reg (.D(cap_d), .CK(clk), .Q(cap_q));
  BUFX1 r_b0 (.A(cap_q), .Y(r0));
  BUFX1 r_b1 (.A(r0), .Y(r1));
  BUFX1 r_b2 (.A(r1), .Y(r2));
  BUFX1 r_b3 (.A(r2), .Y(r3));
  BUFX1 r_b4 (.A(r3), .Y(r4));
  BUFX1 r_b5 (.A(r4), .Y(r5));
  BUFX1 r_b6 (.A(r5), .Y(r6));
  BUFX1 r_b7 (.A(r6), .Y(r7));
  BUFX1 r_b8 (.A(r7), .Y(r8));
  BUFX1 r_b9 (.A(r8), .Y(r9));
  BUFX1 r_b10 (.A(r9), .Y(r10));
  BUFX1 r_b11 (.A(r10), .Y(r11));
  BUFX1 r_b12 (.A(r11), .Y(r12));
  BUFX1 r_b13 (.A(r12), .Y(r13));
  BUFX1 r_b14 (.A(r13), .Y(r14));
  BUFX1 r_b15 (.A(r14), .Y(r15));
  BUFX1 r_b16 (.A(r15), .Y(r16));
  BUFX1 r_b17 (.A(r16), .Y(r17));
  BUFX1 r_b18 (.A(r17), .Y(r18));
  BUFX1 r_b19 (.A(r18), .Y(r19));
  BUFX1 r_b20 (.A(r19), .Y(acc_d));
  DFFX1 acc_reg (.D(acc_d), .CK(clk), .Q(acc_q));
  BUFX1 o_b0 (.A(acc_q), .Y(o0));
  BUFX1 o_b1 (.A(o0), .Y(o1));
  BUFX1 o_b2 (.A(o1), .Y(o2));
  BUFX1 o_b3 (.A(o2), .Y(o3));
  BUFX1 o_b4 (.A(o3), .Y(o4));
  BUFX1 o_b5 (.A(o4), .Y(o5));
  BUFX1 o_b6 (.A(o5), .Y(o6));
  BUFX1 o_b7 (.A(o6), .Y(o7));
  BUFX1 o_b8 (.A(o7), .Y(o8));
  BUFX1 o_b9 (.A(o8), .Y(dout));
  BUFX1 e_b0 (.A(en), .Y(e0));
  BUFX1 e_b1 (.A(e0), .Y(e1));
  BUFX1 e_b2 (.A(e1), .Y(e2));
  BUFX1 e_b3 (.A(e2), .Y(e3));
  BUFX1 e_b4 (.A(e3), .Y(e4));
  BUFX1 e_b5 (.A(e4), .Y(e5));
  BUFX1 e_b6 (.A(e5), .Y(e6));
  BUFX1 e_b7 (.A(e6), .Y(en_d));
  DFFX1 en_reg (.D(en_d), .CK(clk), .Q(en_q));
endmodule
