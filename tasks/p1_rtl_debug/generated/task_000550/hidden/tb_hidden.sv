module tb_hidden;
    reg [1:0] sel;
    reg [7:0] d0, d1, d2, d3;
    wire [7:0] y;
    mux4 uut (.sel(sel), .d0(d0), .d1(d1), .d2(d2), .d3(d3), .y(y));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        d0=8'h00; d1=8'h11; d2=8'h22; d3=8'h33;
        sel = 2'b10; #10;
        if (y === 8'h22) begin $display("PASS: t5 sel=2 alt"); pass=pass+1; end
        else begin $display("FAIL: t5 expected 22 got %h", y); fail=fail+1; end
        sel = 2'b11; #10;
        if (y === 8'h33) begin $display("PASS: t6 sel=3 alt"); pass=pass+1; end
        else begin $display("FAIL: t6 expected 33 got %h", y); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
