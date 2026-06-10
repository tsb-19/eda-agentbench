module tb_public;
    reg [3:0] req;
    wire [1:0] grant;
    priority_enc uut (.req(req), .grant(grant));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        req = 4'b0001; #10;
        if (grant === 2'd0) begin $display("PASS: t1 req[0]"); pass=pass+1; end
        else begin $display("FAIL: t1 expected 0 got %0d", grant); fail=fail+1; end
        req = 4'b0010; #10;
        if (grant === 2'd1) begin $display("PASS: t2 req[1]"); pass=pass+1; end
        else begin $display("FAIL: t2 expected 1 got %0d", grant); fail=fail+1; end
        req = 4'b0100; #10;
        if (grant === 2'd2) begin $display("PASS: t3 req[2]"); pass=pass+1; end
        else begin $display("FAIL: t3 expected 2 got %0d", grant); fail=fail+1; end
        req = 4'b1000; #10;
        if (grant === 2'd3) begin $display("PASS: t4 req[3]"); pass=pass+1; end
        else begin $display("FAIL: t4 expected 3 got %0d", grant); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
