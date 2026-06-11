module tb_hidden;
    reg a, b, sel;
    wire y;
    mux2 uut (.a(a), .b(b), .sel(sel), .y(y));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        a=1; b=0; sel=1; #10;
        a=0; #10;
        if (y===1'b0) begin $display("PASS: t4 sel=1 a changed"); pass=pass+1; end
        else begin $display("FAIL: t4 expected 0 got %b", y); fail=fail+1; end
        a=0; b=0; sel=0; #10;
        b=1; #10;
        if (y===1'b1) begin $display("PASS: t5a b toggled up"); pass=pass+1; end
        else begin $display("FAIL: t5a expected 1 got %b", y); fail=fail+1; end
        b=0; #10;
        if (y===1'b0) begin $display("PASS: t5b b toggled down"); pass=pass+1; end
        else begin $display("FAIL: t5b expected 0 got %b", y); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
