module tb;
    reg clk, rst_n, sig;
    wire pulse;
    pulse_detect uut (.clk(clk), .rst_n(rst_n), .sig(sig), .pulse(pulse));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        clk = 0; rst_n = 0; sig = 0; #20;
        rst_n = 1; @(posedge clk); #1;
        if (pulse === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: no edge, pulse should be 0"); end
        sig = 1; @(posedge clk); #1;
        if (pulse === 1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: rising edge, pulse should be 1"); end
        @(posedge clk); #1;
        if (pulse === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: steady high, pulse should be 0"); end
        sig = 0; @(posedge clk); #1;
        if (pulse === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: falling edge, pulse should be 0"); end
        sig = 1; @(posedge clk); #1;
        if (pulse === 1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: second rising edge, pulse should be 1"); end
        @(posedge clk); #1;
        if (pulse === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: steady high again, pulse should be 0"); end
        if (fail === 0) $display("ALL_TESTS_PASS: %0d/%0d", pass, pass+fail);
        else $display("TEST_FAIL: %0d/%0d", pass, pass+fail);
        $finish;
    end
endmodule
