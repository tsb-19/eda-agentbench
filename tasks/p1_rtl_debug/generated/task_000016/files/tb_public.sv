module tb_public;
    reg clk=0, rst_n;
    reg [7:0] din;
    wire [7:0] dout;
    pipe2 uut (.clk(clk), .rst_n(rst_n), .din(din), .dout(dout));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; din = 8'hAA; #20;
        rst_n = 1;
        din = 8'h11; @(posedge clk); #1;
        din = 8'h22; @(posedge clk); #1;
        if (dout === 8'h11) begin $display("PASS: t1 pipeline latency"); pass=pass+1; end
        else begin $display("FAIL: t1 expected 11 got %h", dout); fail=fail+1; end
        din = 8'h33; @(posedge clk); #1;
        if (dout === 8'h22) begin $display("PASS: t2 pipeline shift"); pass=pass+1; end
        else begin $display("FAIL: t2 expected 22 got %h", dout); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
