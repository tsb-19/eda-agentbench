module tb_hidden;
    reg clk=0, rst_n, en, load;
    reg [3:0] din;
    wire [3:0] cnt;
    en_counter uut (.clk(clk), .rst_n(rst_n), .en(en), .load(load), .din(din), .cnt(cnt));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; en = 0; load = 0; din = 0; #20; rst_n = 1;
        // Count with en=1
        en = 1; @(posedge clk); #1;
        @(posedge clk); #1;
        if (cnt === 4'd2) begin $display("PASS: t4 counted 2"); pass=pass+1; end
        else begin $display("FAIL: t4 expected 2 got %0d", cnt); fail=fail+1; end
        // Stop counting
        en = 0; @(posedge clk); #1;
        if (cnt === 4'd2) begin $display("PASS: t5 held at 2"); pass=pass+1; end
        else begin $display("FAIL: t5 expected 2 got %0d", cnt); fail=fail+1; end
        // Load value
        load = 1; din = 4'd9; @(posedge clk); #1;
        load = 0;
        if (cnt === 4'd9) begin $display("PASS: t6 loaded 9"); pass=pass+1; end
        else begin $display("FAIL: t6 expected 9 got %0d", cnt); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
