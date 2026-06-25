// Cross-check tb for Task 2. Drives x,y on negedge, samples outp mid-cycle.
// ref.outp[n] = x[n-1]+y[n-1] (registered); dut.outp[n] = x[n-1]+y[n] (y un-registered).
// Reports first cycle where ref.outp != dut.outp. Stimulus from stim2.mem (+N=<count>).
`timescale 1ns/1ps
module tb;
    reg clk = 0, rst = 1;
    reg  [7:0] x = 0, y = 0;
    wire [7:0] rout, dout;
    ref_pipe R (.clk(clk), .rst(rst), .x(x), .y(y), .outp(rout));
    dut_pipe D (.clk(clk), .rst(rst), .x(x), .y(y), .outp(dout));

    // each line of stim2.mem is {x[7:0],y[7:0]} = 16 bits
    reg [15:0] stim [0:8191];
    integer n, i, firstdiv;

    always #5 clk = ~clk;

    initial begin
        $readmemh("stim2.mem", stim);
        if (!$value$plusargs("N=%d", n)) n = 0;
        firstdiv = -1;
        @(negedge clk); rst = 1;
        @(posedge clk); @(negedge clk); rst = 0;
        for (i = 0; i < n; i = i + 1) begin
            x = stim[i][15:8];
            y = stim[i][7:0];
            #1;
            if (rout !== dout && firstdiv < 0) begin
                firstdiv = i;
                $display("DIVERGE i=%0d ref=%0d dut=%0d", i, rout, dout);
            end
            @(posedge clk);
            @(negedge clk);
        end
        if (firstdiv < 0) $display("NODIV n=%0d", n);
        $finish;
    end
endmodule
