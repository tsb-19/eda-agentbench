// Hidden testbench for mux2 — 2 additional test cases
module tb_hidden;
    reg a, b, sel;
    wire y;

    mux2 uut (.a(a), .b(b), .sel(sel), .y(y));

    integer pass_count;
    integer fail_count;

    initial begin
        pass_count = 0;
        fail_count = 0;

        // Test 4: sel=1, change a only — y should update
        a = 1; b = 0; sel = 1;
        #10;
        a = 0;
        #10;
        if (y === 1'b0) begin
            $display("PASS: test4 sel=1 a changed");
            pass_count = pass_count + 1;
        end else begin
            $display("FAIL: test4 sel=1 expected y=0 after a changed, got y=%b", y);
            fail_count = fail_count + 1;
        end

        // Test 5: sel=0, b toggles twice
        a = 0; b = 0; sel = 0;
        #10;
        b = 1;
        #10;
        if (y === 1'b1) begin
            $display("PASS: test5a sel=0 b toggled to 1");
            pass_count = pass_count + 1;
        end else begin
            $display("FAIL: test5a sel=0 expected y=1, got y=%b", y);
            fail_count = fail_count + 1;
        end
        b = 0;
        #10;
        if (y === 1'b0) begin
            $display("PASS: test5b sel=0 b toggled to 0");
            pass_count = pass_count + 1;
        end else begin
            $display("FAIL: test5b sel=0 expected y=0, got y=%b", y);
            fail_count = fail_count + 1;
        end

        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass_count, fail_count);
        $finish;
    end
endmodule
