// Public testbench for mux2 — 3 test cases
module tb_public;
    reg a, b, sel;
    wire y;

    mux2 uut (.a(a), .b(b), .sel(sel), .y(y));

    integer pass_count;
    integer fail_count;

    initial begin
        pass_count = 0;
        fail_count = 0;

        // Test 1: sel=0, expect y=b=1
        a = 0; b = 1; sel = 0;
        #10;
        if (y === 1'b1) begin
            $display("PASS: test1 sel=0 y=b");
            pass_count = pass_count + 1;
        end else begin
            $display("FAIL: test1 sel=0 expected y=1, got y=%b", y);
            fail_count = fail_count + 1;
        end

        // Test 2: sel=1, expect y=a=1
        a = 1; b = 0; sel = 1;
        #10;
        if (y === 1'b1) begin
            $display("PASS: test2 sel=1 y=a");
            pass_count = pass_count + 1;
        end else begin
            $display("FAIL: test2 sel=1 expected y=1, got y=%b", y);
            fail_count = fail_count + 1;
        end

        // Test 3: sel=0, change b only — sensitivity list bug exposed
        a = 0; b = 1; sel = 0;
        #10;
        // Now change b to 0 while a and sel stay the same
        b = 0;
        #10;
        if (y === 1'b0) begin
            $display("PASS: test3 sel=0 b changed");
            pass_count = pass_count + 1;
        end else begin
            $display("FAIL: test3 sel=0 expected y=0 after b changed, got y=%b", y);
            fail_count = fail_count + 1;
        end

        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass_count, fail_count);
        $finish;
    end
endmodule
