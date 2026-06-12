module tb;
    reg clk, rst_n, valid_in, ready_out;
    reg [7:0] data_in;
    wire valid_out, ready_in;
    wire [7:0] data_out;
    vr_pipe uut (.clk(clk), .rst_n(rst_n), .valid_in(valid_in),
        .ready_out(ready_out), .data_in(data_in),
        .valid_out(valid_out), .ready_in(ready_in), .data_out(data_out));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        clk = 0; rst_n = 0; valid_in = 0; ready_out = 0; data_in = 0; #20;
        rst_n = 1; @(posedge clk); #1;
        if (ready_in === 1 && valid_out === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: idle state"); end
        data_in = 8'hAB; valid_in = 1; @(posedge clk); #1; valid_in = 0;
        if (ready_in === 0 && valid_out === 1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: pipe full"); end
        if (data_out === 8'hAB) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: data expected AB, got %h", data_out); end
        ready_out = 1; @(posedge clk); #1; ready_out = 0;
        if (ready_in === 1 && valid_out === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: back to idle"); end
        data_in = 8'h55; valid_in = 1; @(posedge clk); #1; valid_in = 0;
        if (valid_out === 1 && data_out === 8'h55) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: second data expected 55, got %h", data_out); end
        if (fail === 0) $display("ALL_TESTS_PASS: %0d/%0d", pass, pass+fail);
        else $display("TEST_FAIL: %0d/%0d", pass, pass+fail);
        $finish;
    end
endmodule
