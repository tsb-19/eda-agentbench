module tb_hidden;
    reg [7:0] a, b;
    wire [8:0] sum;
    adder_wide uut (.a(a), .b(b), .sum(sum));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        a = 8'd128; b = 8'd128; #10;
        if (sum === 9'd256) begin $display("PASS: t4 128+128"); pass=pass+1; end
        else begin $display("FAIL: t4 expected 256 got %0d", sum); fail=fail+1; end
        a = 8'd0; b = 8'd0; #10;
        if (sum === 9'd0) begin $display("PASS: t5 zero"); pass=pass+1; end
        else begin $display("FAIL: t5 expected 0 got %0d", sum); fail=fail+1; end
        a = 8'd255; b = 8'd1; #10;
        if (sum === 9'd256) begin $display("PASS: t6 255+1"); pass=pass+1; end
        else begin $display("FAIL: t6 expected 256 got %0d", sum); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
