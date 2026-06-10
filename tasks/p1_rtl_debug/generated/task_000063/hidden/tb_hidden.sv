module tb_hidden;
    reg [3:0] req;
    wire [1:0] grant;
    priority_enc uut (.req(req), .grant(grant));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        req = 4'b0011; #10;
        if (grant === 2'd0) begin $display("PASS: t5 priority 0 over 1"); pass=pass+1; end
        else begin $display("FAIL: t5 expected 0 got %0d", grant); fail=fail+1; end
        req = 4'b1100; #10;
        if (grant === 2'd2) begin $display("PASS: t6 priority 2 over 3"); pass=pass+1; end
        else begin $display("FAIL: t6 expected 2 got %0d", grant); fail=fail+1; end
        req = 4'b1111; #10;
        if (grant === 2'd0) begin $display("PASS: t7 all req priority 0"); pass=pass+1; end
        else begin $display("FAIL: t7 expected 0 got %0d", grant); fail=fail+1; end
        req = 4'b0000; #10;
        if (grant === 2'd0) begin $display("PASS: t8 no req"); pass=pass+1; end
        else begin $display("FAIL: t8 expected 0 got %0d", grant); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
