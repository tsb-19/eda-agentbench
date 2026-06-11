module tb_public;
    reg [7:0] a, b;
    wire [8:0] sum;
    adder_wide uut (.a(a), .b(b), .sum(sum));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        a = 8'd10; b = 8'd20; #10;
        if (sum === 9'd30) begin $display("PASS: t1 simple add"); pass=pass+1; end
        else begin $display("FAIL: t1 expected 30 got %0d", sum); fail=fail+1; end
        a = 8'd200; b = 8'd100; #10;
        if (sum === 9'd300) begin $display("PASS: t2 overflow"); pass=pass+1; end
        else begin $display("FAIL: t2 expected 300 got %0d", sum); fail=fail+1; end
        a = 8'd255; b = 8'd255; #10;
        if (sum === 9'd510) begin $display("PASS: t3 max"); pass=pass+1; end
        else begin $display("FAIL: t3 expected 510 got %0d", sum); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
