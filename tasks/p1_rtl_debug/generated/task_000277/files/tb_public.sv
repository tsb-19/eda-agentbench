module tb_public;
    reg clk=0, rst_n, en;
    wire [3:0] cnt;
    counter_rst uut (.clk(clk), .rst_n(rst_n), .en(en), .cnt(cnt));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; en = 0; #20;
        if (cnt === 4'd0) begin $display("PASS: t1 reset clears"); pass=pass+1; end
        else begin $display("FAIL: t1 expected 0 got %0d", cnt); fail=fail+1; end
        rst_n = 1; en = 1; @(posedge clk); #1;
        @(posedge clk); #1;
        @(posedge clk); #1;
        if (cnt === 4'd3) begin $display("PASS: t2 counts up"); pass=pass+1; end
        else begin $display("FAIL: t2 expected 3 got %0d", cnt); fail=fail+1; end
        rst_n = 0; #10;
        if (cnt === 4'd0) begin $display("PASS: t3 reset again"); pass=pass+1; end
        else begin $display("FAIL: t3 expected 0 got %0d", cnt); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
