module top(input a, b, c, d, e, output o1, o2, o3);
  wire m_s, m_t, m_u, w;
  assign m_s = ~(~a & ~b);
  assign m_t = ~(~c | ~d);
  assign m_u = m_s | m_t;
  assign o1 = m_u ^ e;
  assign o2 = m_u | a;
  assign w = m_s & e;
  assign o3 = w;
endmodule
