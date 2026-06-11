module tb_public;
    reg [1:0] sel;
    reg [7:0] d0, d1, d2, d3;
    wire [7:0] y;
    mux4 uut (.sel(sel), .d0(d0), .d1(d1), .d2(d2), .d3(d3), .y(y));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        d0=8'hAA; d1=8'hBB; d2=8'hCC; d3=8'hDD;
        sel = 2'b00; #10;
        if (y === 8'hAA) begin $display("PASS: t1 sel=0"); pass=pass+1; end
        else begin $display("FAIL: t1 expected AA got %h", y); fail=fail+1; end
        sel = 2'b01; #10;
        if (y === 8'hBB) begin $display("PASS: t2 sel=1"); pass=pass+1; end
        else begin $display("FAIL: t2 expected BB got %h", y); fail=fail+1; end
        sel = 2'b10; #10;
        if (y === 8'hCC) begin $display("PASS: t3 sel=2"); pass=pass+1; end
        else begin $display("FAIL: t3 expected CC got %h", y); fail=fail+1; end
        sel = 2'b11; #10;
        if (y === 8'hDD) begin $display("PASS: t4 sel=3"); pass=pass+1; end
        else begin $display("FAIL: t4 expected DD got %h", y); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
