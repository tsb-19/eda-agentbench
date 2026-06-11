module tb_public;
    reg clk=0, rst_n, en, load;
    reg [3:0] din;
    wire [3:0] cnt;
    en_counter uut (.clk(clk), .rst_n(rst_n), .en(en), .load(load), .din(din), .cnt(cnt));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; en = 0; load = 0; din = 0; #20;
        rst_n = 1;
        en = 1; @(posedge clk); #1;
        @(posedge clk); #1;
        @(posedge clk); #1;
        if (cnt === 4'd3) begin $display("PASS: t1 counts with en"); pass=pass+1; end
        else begin $display("FAIL: t1 expected 3 got %0d", cnt); fail=fail+1; end
        en = 0; @(posedge clk); #1;
        @(posedge clk); #1;
        if (cnt === 4'd3) begin $display("PASS: t2 holds when !en"); pass=pass+1; end
        else begin $display("FAIL: t2 expected 3 got %0d", cnt); fail=fail+1; end
        load = 1; din = 4'd7; @(posedge clk); #1;
        load = 0;
        if (cnt === 4'd7) begin $display("PASS: t3 load works"); pass=pass+1; end
        else begin $display("FAIL: t3 expected 7 got %0d", cnt); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
