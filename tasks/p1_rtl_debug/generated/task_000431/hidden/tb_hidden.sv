module tb_hidden;
    reg [3:0] val;
    wire in_range;
    range_check uut (.val(val), .in_range(in_range));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        val = 4'd5; #10;
        if (in_range === 1'b1) begin $display("PASS: t5 val=5 in"); pass=pass+1; end
        else begin $display("FAIL: t5 val=5 expected 1 got %b", in_range); fail=fail+1; end
        val = 4'd10; #10;
        if (in_range === 1'b1) begin $display("PASS: t6 val=10 in"); pass=pass+1; end
        else begin $display("FAIL: t6 val=10 expected 1 got %b", in_range); fail=fail+1; end
        val = 4'd1; #10;
        if (in_range === 1'b0) begin $display("PASS: t7 val=1 out"); pass=pass+1; end
        else begin $display("FAIL: t7 val=1 expected 0 got %b", in_range); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
