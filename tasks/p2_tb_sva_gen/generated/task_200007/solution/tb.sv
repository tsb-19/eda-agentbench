module tb;
    reg clk, rst_n, en;
    wire [3:0] cnt;
    counter4 uut (.clk(clk), .rst_n(rst_n), .en(en), .cnt(cnt));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        clk = 0; rst_n = 0; en = 0; #20;
        rst_n = 1; en = 1;
        @(posedge clk); #1;
        if (cnt === 4'd1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: expected 1, got %0d", cnt); end
        @(posedge clk); #1;
        if (cnt === 4'd2) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: expected 2, got %0d", cnt); end
        @(posedge clk); #1;
        if (cnt === 4'd3) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: expected 3, got %0d", cnt); end
        en = 0; @(posedge clk); #1;
        if (cnt === 4'd3) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: hold expected 3, got %0d", cnt); end
        @(posedge clk); #1;
        if (cnt === 4'd3) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: still hold expected 3, got %0d", cnt); end
        en = 1; @(posedge clk); #1;
        if (cnt === 4'd4) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: resume expected 4, got %0d", cnt); end
        rst_n = 0; #10;
        if (cnt === 4'd0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: reset expected 0, got %0d", cnt); end
        if (fail === 0) $display("ALL_TESTS_PASS: %0d/%0d", pass, pass+fail);
        else $display("TEST_FAIL: %0d/%0d", pass, pass+fail);
        $finish;
    end
endmodule
