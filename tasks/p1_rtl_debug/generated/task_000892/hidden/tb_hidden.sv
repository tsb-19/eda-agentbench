module tb_hidden;
    reg clk=0, rst_n;
    wire [3:0] cnt;
    wire wrap;
    counter_mod uut (.clk(clk), .rst_n(rst_n), .cnt(cnt), .wrap(wrap));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; #20; rst_n = 1;
        repeat(19) @(posedge clk); #1;
        @(posedge clk); #1;
        if (cnt === 4'd0 && wrap === 1) begin $display("PASS: t4 second wrap"); pass=pass+1; end
        else begin $display("FAIL: t4 expected wrap cnt=%0d wrap=%b", cnt, wrap); fail=fail+1; end
        rst_n = 0; #10; rst_n = 1; @(posedge clk); #1;
        if (cnt === 4'd1) begin $display("PASS: t5 after reset"); pass=pass+1; end
        else begin $display("FAIL: t5 expected 1 got %0d", cnt); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
