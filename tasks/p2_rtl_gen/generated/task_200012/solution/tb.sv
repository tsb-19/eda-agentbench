module tb;
    reg clk, rst_n, go, finish;
    wire busy, completed;
    fsm_simple uut (.clk(clk), .rst_n(rst_n), .go(go), .finish(finish),
                    .busy(busy), .completed(completed));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        clk = 0; rst_n = 0; go = 0; finish = 0; #20;
        rst_n = 1;
        if (busy === 0 && completed === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: idle"); end
        go = 1; @(posedge clk); #1; go = 0;
        if (busy === 1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: busy expected 1, got %b", busy); end
        if (completed === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: completed should be 0 in RUN"); end
        finish = 1; @(posedge clk); #1; finish = 0;
        if (completed === 1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: completed expected 1, got %b", completed); end
        if (busy === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: busy should be 0 in DONE"); end
        @(posedge clk); #1;
        if (completed === 0 && busy === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: should be idle"); end
        if (fail === 0) $display("ALL_TESTS_PASS: %0d/%0d", pass, pass+fail);
        else $display("TEST_FAIL: %0d/%0d", pass, pass+fail);
        $finish;
    end
endmodule
