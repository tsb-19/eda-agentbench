module tb;
    reg [3:0] req;
    wire [1:0] grant;
    priority_enc uut (.req(req), .grant(grant));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        req = 4'b0001; #10;
        if (grant === 2'd0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: req[0] expected grant=0, got %0d", grant); end
        req = 4'b0010; #10;
        if (grant === 2'd1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: req[1] expected grant=1, got %0d", grant); end
        req = 4'b0100; #10;
        if (grant === 2'd2) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: req[2] expected grant=2, got %0d", grant); end
        req = 4'b1000; #10;
        if (grant === 2'd3) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: req[3] expected grant=3, got %0d", grant); end
        req = 4'b0011; #10;
        if (grant === 2'd0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: priority 0 over 1, got %0d", grant); end
        req = 4'b1100; #10;
        if (grant === 2'd2) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: priority 2 over 3, got %0d", grant); end
        req = 4'b1111; #10;
        if (grant === 2'd0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: all req priority 0, got %0d", grant); end
        req = 4'b0000; #10;
        if (grant === 2'd0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: no req, got %0d", grant); end
        if (fail === 0) $display("ALL_TESTS_PASS: %0d/%0d", pass, pass+fail);
        else $display("TEST_FAIL: %0d/%0d", pass, pass+fail);
        $finish;
    end
endmodule
