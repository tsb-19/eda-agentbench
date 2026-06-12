module tb;
    reg [3:0] count;
    wire empty, almost_full, full;
    fifo_status uut (.count(count), .empty(empty), .almost_full(almost_full), .full(full));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        count = 4'd0; #10;
        if (empty===1 && almost_full===0 && full===0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: count=0: e=%b af=%b f=%b", empty, almost_full, full); end
        count = 4'd3; #10;
        if (empty===0 && almost_full===0 && full===0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: count=3: e=%b af=%b f=%b", empty, almost_full, full); end
        count = 4'd5; #10;
        if (empty===0 && almost_full===0 && full===0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: count=5: e=%b af=%b f=%b", empty, almost_full, full); end
        count = 4'd6; #10;
        if (empty===0 && almost_full===1 && full===0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: count=6: e=%b af=%b f=%b", empty, almost_full, full); end
        count = 4'd7; #10;
        if (empty===0 && almost_full===1 && full===0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: count=7: e=%b af=%b f=%b", empty, almost_full, full); end
        count = 4'd8; #10;
        if (empty===0 && almost_full===1 && full===1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: count=8: e=%b af=%b f=%b", empty, almost_full, full); end
        if (fail === 0) $display("ALL_TESTS_PASS: %0d/%0d", pass, pass+fail);
        else $display("TEST_FAIL: %0d/%0d", pass, pass+fail);
        $finish;
    end
endmodule
