module tb_public;
    reg clk=0, rst_n;
    wire [3:0] cnt;
    wire wrap;
    counter_mod uut (.clk(clk), .rst_n(rst_n), .cnt(cnt), .wrap(wrap));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; #20; rst_n = 1;
        repeat(9) @(posedge clk); #1;
        if (cnt === 4'd9) begin $display("PASS: t1 cnt=9"); pass=pass+1; end
        else begin $display("FAIL: t1 expected 9 got %0d", cnt); fail=fail+1; end
        @(posedge clk); #1;
        if (cnt === 4'd0 && wrap === 1) begin $display("PASS: t2 wraps at 10"); pass=pass+1; end
        else begin $display("FAIL: t2 expected cnt=0 wrap=1 got cnt=%0d wrap=%b", cnt, wrap); fail=fail+1; end
        @(posedge clk); #1;
        if (cnt === 4'd1 && wrap === 0) begin $display("PASS: t3 continues"); pass=pass+1; end
        else begin $display("FAIL: t3 expected cnt=1 wrap=0 got cnt=%0d wrap=%b", cnt, wrap); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
