module tb_public;
    reg a, b, sel;
    wire y;
    mux2 uut (.a(a), .b(b), .sel(sel), .y(y));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        a=0; b=1; sel=0; #10;
        if (y===1'b1) begin $display("PASS: t1 sel=0 y=b"); pass=pass+1; end
        else begin $display("FAIL: t1 sel=0 expected 1 got %b", y); fail=fail+1; end
        a=1; b=0; sel=1; #10;
        if (y===1'b1) begin $display("PASS: t2 sel=1 y=a"); pass=pass+1; end
        else begin $display("FAIL: t2 sel=1 expected 1 got %b", y); fail=fail+1; end
        a=0; b=1; sel=0; #10;
        b=0; #10;
        if (y===1'b0) begin $display("PASS: t3 b changed"); pass=pass+1; end
        else begin $display("FAIL: t3 expected 0 got %b", y); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
