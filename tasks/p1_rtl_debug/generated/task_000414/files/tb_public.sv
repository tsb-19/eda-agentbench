module tb_public;
    reg [3:0] val;
    wire in_range;
    range_check uut (.val(val), .in_range(in_range));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        val = 4'd0; #10;
        if (in_range === 1'b0) begin $display("PASS: t1 val=0 out"); pass=pass+1; end
        else begin $display("FAIL: t1 val=0 expected 0 got %b", in_range); fail=fail+1; end
        val = 4'd3; #10;
        if (in_range === 1'b1) begin $display("PASS: t2 val=3 in"); pass=pass+1; end
        else begin $display("FAIL: t2 val=3 expected 1 got %b", in_range); fail=fail+1; end
        val = 4'd12; #10;
        if (in_range === 1'b1) begin $display("PASS: t3 val=12 in"); pass=pass+1; end
        else begin $display("FAIL: t3 val=12 expected 1 got %b", in_range); fail=fail+1; end
        val = 4'd15; #10;
        if (in_range === 1'b0) begin $display("PASS: t4 val=15 out"); pass=pass+1; end
        else begin $display("FAIL: t4 val=15 expected 0 got %b", in_range); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
