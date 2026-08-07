// Family A STA handoff netlist (generated; timed vs tiny.db). Top: p15_sta_top.
// One register-to-register path per partition; marginally timed so any exception binding
// leaves report_timing green (tool success != semantic correctness).
module p15_sta_top (clk, cdc_in, reset_in, scan_in, core_in, cdc_out, reset_out, scan_out, core_out);
  input clk;
  input cdc_in;
  input reset_in;
  input scan_in;
  input core_in;
  output cdc_out;
  output reset_out;
  output scan_out;
  output core_out;
  wire cdc_a, cdc_b;
  DFFX1 cdc_src (.D(cdc_in), .CK(clk), .Q(cdc_a));
  BUFX1 cdc_b0 (.A(cdc_a), .Y(cdc_b));
  DFFX1 cdc_dst (.D(cdc_b), .CK(clk), .Q(cdc_out));
  wire reset_a, reset_b;
  DFFX1 reset_src (.D(reset_in), .CK(clk), .Q(reset_a));
  BUFX1 reset_b0 (.A(reset_a), .Y(reset_b));
  DFFX1 reset_dst (.D(reset_b), .CK(clk), .Q(reset_out));
  wire scan_a, scan_b;
  DFFX1 scan_src (.D(scan_in), .CK(clk), .Q(scan_a));
  BUFX1 scan_b0 (.A(scan_a), .Y(scan_b));
  DFFX1 scan_dst (.D(scan_b), .CK(clk), .Q(scan_out));
  wire core_a, core_b;
  DFFX1 core_src (.D(core_in), .CK(clk), .Q(core_a));
  BUFX1 core_b0 (.A(core_a), .Y(core_b));
  DFFX1 core_dst (.D(core_b), .CK(clk), .Q(core_out));
endmodule
