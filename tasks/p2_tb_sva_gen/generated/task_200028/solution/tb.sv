module tb;
    reg clk, rst_n;
    reg [3:0] req;
    wire [3:0] grant;
    arbiter_rr uut (.clk(clk), .rst_n(rst_n), .req(req), .grant(grant));
    always #5 clk = ~clk;
    integer pass, fail;
    task check_grant(input [3:0] exp);
        @(posedge clk); #1;
        if (grant === exp) begin pass=pass+1; end
        else begin fail=fail+1; $display("FAIL: grant=%b expected %b", grant, exp); end
    endtask
    initial begin
        pass = 0; fail = 0;
        clk = 0; rst_n = 0; req = 0; #20;
        rst_n = 1; @(posedge clk); #1;
        req = 4'b1111;
        check_grant(4'b0001);
        check_grant(4'b0010);
        check_grant(4'b0100);
        check_grant(4'b1000);
        check_grant(4'b0001);
        req = 4'b0100;
        check_grant(4'b0100);
        req = 4'b1010;
        check_grant(4'b1000);
        check_grant(4'b0010);
        if (fail === 0) $display("ALL_TESTS_PASS: %0d/%0d", pass, pass+fail);
        else $display("TEST_FAIL: %0d/%0d", pass, pass+fail);
        $finish;
    end
endmodule
