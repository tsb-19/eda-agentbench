module tb_hidden;
    reg clk=0, rst_n;
    reg [7:0] din;
    wire [7:0] dout;
    pipe2 uut (.clk(clk), .rst_n(rst_n), .din(din), .dout(dout));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; din = 0; #20;
        rst_n = 1;
        din = 8'hA5; @(posedge clk); #1;
        din = 8'h5A; @(posedge clk); #1;
        din = 8'hFF; @(posedge clk); #1;
        if (dout === 8'h5A) begin $display("PASS: t3 third cycle"); pass=pass+1; end
        else begin $display("FAIL: t3 expected 5a got %h", dout); fail=fail+1; end
        rst_n = 0; #10; rst_n = 1; #10;
        din = 8'h42; @(posedge clk); #1;
        din = 8'h00; @(posedge clk); #1;
        if (dout === 8'h42) begin $display("PASS: t4 after reset"); pass=pass+1; end
        else begin $display("FAIL: t4 expected 42 got %h", dout); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
