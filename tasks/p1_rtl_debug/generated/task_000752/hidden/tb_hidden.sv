module tb_hidden;
    reg clk=0, rst_n, go, finish;
    wire busy, completed;
    fsm_simple uut (.clk(clk), .rst_n(rst_n), .go(go), .finish(finish),
                    .busy(busy), .completed(completed));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; #20; rst_n = 1;
        // First run
        go = 1; @(posedge clk); #1; go = 0;
        finish = 1; @(posedge clk); #1; finish = 0;
        // completed should be 1 right now (in S_DONE)
        if (completed === 1) begin $display("PASS: t4 first completed"); pass=pass+1; end
        else begin $display("FAIL: t4 expected 1 got %b", completed); fail=fail+1; end
        @(posedge clk); #1;
        // Back to idle
        if (completed === 0 && busy === 0) begin $display("PASS: t5 back to idle"); pass=pass+1; end
        else begin $display("FAIL: t5 expected idle"); fail=fail+1; end
        // Second run
        go = 1; @(posedge clk); #1; go = 0;
        finish = 1; @(posedge clk); #1; finish = 0;
        if (completed === 1) begin $display("PASS: t6 second completed"); pass=pass+1; end
        else begin $display("FAIL: t6 expected 1 got %b", completed); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
