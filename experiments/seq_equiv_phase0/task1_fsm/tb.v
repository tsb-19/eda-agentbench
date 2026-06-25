// Cross-check tb for Task 1. Drives din on negedge, samples Mealy det mid-cycle.
// Reports first cycle where ref.det != dut.det. Stimulus from stim1.mem (+N=<count>).
`timescale 1ns/1ps
module tb;
    reg clk = 0, rst = 1, din = 0;
    wire rdet, ddet;
    ref_detector R (.clk(clk), .rst(rst), .din(din), .det(rdet));
    dut_detector D (.clk(clk), .rst(rst), .din(din), .det(ddet));

    reg [0:0] stim [0:8191];
    integer n, i, firstdiv;

    always #5 clk = ~clk;

    initial begin
        $readmemb("stim1.mem", stim);
        if (!$value$plusargs("N=%d", n)) n = 0;
        firstdiv = -1;
        // hold reset across one posedge, then release
        @(negedge clk); rst = 1;
        @(posedge clk); @(negedge clk); rst = 0;
        for (i = 0; i < n; i = i + 1) begin
            din = stim[i];
            #1;                                   // settle combinational Mealy outputs
            if (rdet !== ddet && firstdiv < 0) begin
                firstdiv = i;
                $display("DIVERGE i=%0d ref=%b dut=%b", i, rdet, ddet);
            end
            @(posedge clk);                       // latch next state
            @(negedge clk);
        end
        if (firstdiv < 0) $display("NODIV n=%0d", n);
        $finish;
    end
endmodule
