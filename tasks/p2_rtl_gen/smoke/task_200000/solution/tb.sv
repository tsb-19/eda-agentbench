module tb;
    reg a, b, sel;
    wire y;
    mux2 uut (.a(a), .b(b), .sel(sel), .y(y));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        a=0; b=1; sel=0; #10;
        if (y===1'b1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: sel=0 expected y=1, got %b", y); end
        a=1; b=0; sel=1; #10;
        if (y===1'b1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: sel=1 expected y=1, got %b", y); end
        a=0; b=0; sel=0; #10;
        if (y===1'b0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: both 0 expected y=0, got %b", y); end
        a=1; b=1; sel=1; #10;
        if (y===1'b1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: both 1 expected y=1, got %b", y); end
        a=1; b=0; sel=0; #10;
        if (y===1'b0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: sel=0 expected y=b=0, got %b", y); end
        a=0; b=1; sel=1; #10;
        if (y===1'b0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: sel=1 expected y=a=0, got %b", y); end
        if (fail === 0) $display("ALL_TESTS_PASS: %0d/%0d", pass, pass+fail);
        else $display("TEST_FAIL: %0d/%0d", pass, pass+fail);
        $finish;
    end
endmodule
