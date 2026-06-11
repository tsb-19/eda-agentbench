module tb_hidden;
    reg clk=0, rst_n, en;
    wire [3:0] cnt;
    counter_rst uut (.clk(clk), .rst_n(rst_n), .en(en), .cnt(cnt));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 1; en = 0; #20;
        rst_n = 0; #10; rst_n = 1; en = 1; #1;
        @(posedge clk); #1;
        @(posedge clk); #1;
        if (cnt === 4'd2) begin $display("PASS: t4 count after release"); pass=pass+1; end
        else begin $display("FAIL: t4 expected 2 got %0d", cnt); fail=fail+1; end
        en = 0; @(posedge clk); #1;
        if (cnt === 4'd2) begin $display("PASS: t5 hold when !en"); pass=pass+1; end
        else begin $display("FAIL: t5 expected 2 got %0d", cnt); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
