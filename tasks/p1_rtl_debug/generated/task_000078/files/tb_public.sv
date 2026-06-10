module tb_public;
    reg clk=0, rst_n, go, finish;
    wire busy, completed;
    fsm_simple uut (.clk(clk), .rst_n(rst_n), .go(go), .finish(finish),
                    .busy(busy), .completed(completed));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; go = 0; finish = 0; #20;
        rst_n = 1;
        if (busy === 0 && completed === 0) begin $display("PASS: t1 idle"); pass=pass+1; end
        else begin $display("FAIL: t1 expected idle"); fail=fail+1; end
        go = 1; @(posedge clk); #1; go = 0;
        if (busy === 1) begin $display("PASS: t2 run busy"); pass=pass+1; end
        else begin $display("FAIL: t2 expected 1 got %b", busy); fail=fail+1; end
        // Assert finish: at next posedge, state→S_DONE, completed pulses
        finish = 1; @(posedge clk); #1; finish = 0;
        if (completed === 1) begin $display("PASS: t3 completed pulses"); pass=pass+1; end
        else begin $display("FAIL: t3 expected 1 got %b", completed); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
