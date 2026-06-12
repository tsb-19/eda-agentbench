module tb;
    reg clk, rst_n, sig;
    wire rising, falling;
    edge_detect uut (.clk(clk), .rst_n(rst_n), .sig(sig), .rising(rising), .falling(falling));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        clk = 0; rst_n = 0; sig = 0; #20;
        rst_n = 1; @(posedge clk); #1;
        sig = 1; #1;
        if (rising === 1 && falling === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: rising edge: r=%b f=%b", rising, falling); end
        @(posedge clk); #1;
        if (rising === 0 && falling === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: steady high: r=%b f=%b", rising, falling); end
        sig = 0; #1;
        if (rising === 0 && falling === 1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: falling edge: r=%b f=%b", rising, falling); end
        @(posedge clk); #1;
        if (rising === 0 && falling === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: steady low: r=%b f=%b", rising, falling); end
        sig = 1; #1;
        if (rising === 1 && falling === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: second rising edge: r=%b f=%b", rising, falling); end
        if (fail === 0) $display("ALL_TESTS_PASS: %0d/%0d", pass, pass+fail);
        else $display("TEST_FAIL: %0d/%0d", pass, pass+fail);
        $finish;
    end
endmodule
